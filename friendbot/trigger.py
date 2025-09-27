import asyncio
import random
import uuid

from friendbot.agent import Agent
from friendbot.social_media import Message, MessageContext, SocialMedia


class Trigger:
    """
    Trigger for invoking an agent.

    * Runs background tasks on a schedule
    * Responds to Discord messages (can respond to multiple channels in parallel)
    """

    def __init__(
        self,
        social_media: SocialMedia,
        friend: Agent,
        *,
        schedule_interval_seconds: float | None = 60 * 60,
    ) -> None:
        self._agent = friend
        # TODO(#14): Type `response_tasks` as `dict[int, dict[int, asyncio.Task]]`
        self._response_tasks: dict[int, dict[str, asyncio.Task]] = {}
        # TODO: Remove unused `schedule_task`
        self._schedule_task: asyncio.Task | None = None
        self._scheduled_tasks: dict[str, asyncio.Task] = {}
        self._schedule_interval_seconds = schedule_interval_seconds

        self._social_media = social_media
        social_media.on_ready_callback = self.connect
        social_media.on_message_callback = self.read_message

    def _should_respond(self, message: Message) -> bool:
        if message.author == self._agent.name:
            return False

        if len(message.mentions) > 0 and self._agent.name not in message.mentions:
            return False

        return True

    async def _run_idle(self) -> None:
        while True:
            if random.randint(0, 1) == 0:
                task_id = str(uuid.uuid4())
                self._scheduled_tasks[task_id] = asyncio.create_task(
                    self._agent(
                        "You are currently idle. If you'd like, you can choose to do something interesting to pass the time. You may also choose to do nothing at all."
                    )
                )
                self._scheduled_tasks[task_id].add_done_callback(
                    lambda task, task_id=task_id: self._scheduled_tasks.pop(task_id)
                )
            await asyncio.sleep(self._schedule_interval_seconds)

    async def _respond(self, context: MessageContext) -> None:
        messages = await context.social_media.messages(context, limit=1)
        if len(messages) > 0 and not self._should_respond(messages[0]):
            return

        await self._agent(
            f"You received a message in the Discord server {context.server.name} (with id {context.server.id}) and channel {context.channel.name} (with id {context.channel.id})."
        )

    async def connect(self) -> None:
        """
        Initialize the trigger.

        Can only be called once the social media is ready.
        """

        print("Connected")

        # Start scheduler if enabled
        if self._schedule_interval_seconds and self._schedule_interval_seconds > 0:
            self._schedule_task = asyncio.create_task(self._run_idle())

    def _remove_response_task(self, context: MessageContext) -> None:
        if not self._response_tasks.get(context.server.id, {}).get(context.channel.id):
            return

        del self._response_tasks[context.server.id][context.channel.id]
        if len(self._response_tasks[context.server.id]) == 0:
            del self._response_tasks[context.server.id]

    async def read_message(self, context: MessageContext, message: Message) -> None:
        """
        Respond to a new message (if appropriate).

        Args:
            context: Context where the message was received.
            message: New message to respond to.
        """

        if not self._should_respond(message):
            return

        # If we're already working on a response to a previous message in the
        # same channel, cancel it
        task = self._response_tasks.get(context.server.id, {}).get(context.channel.id)
        if task and not task.done():
            task.cancel()
            # Ensure the task is actually cancelled before proceeding to avoid duplicate sends
            try:
                await task
            except asyncio.CancelledError:
                pass
            self._remove_response_task(context)

        task = asyncio.create_task(self._respond(context))
        self._response_tasks.setdefault(context.server.id, {})[
            context.channel.id
        ] = task
        task.add_done_callback(
            lambda task, context=context: self._remove_response_task(context)
        )
