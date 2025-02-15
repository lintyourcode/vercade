import asyncio
import random
from friendbot.agent import Agent
from friendbot.social_media import Message, MessageContext, SocialMedia


class Trigger:
    """
    Trigger for invoking an agent.
    """

    def __init__(self, social_media: SocialMedia, friend: Agent) -> None:
        self._agent = friend
        self._response_task: asyncio.Task | None = None

        social_media.on_ready_callback = self.connect
        social_media.on_message_callback = self.read_message

    def _should_respond(self, message: Message) -> bool:
        if message.author == self._agent.name:
            return False

        if len(message.mentions) > 0 and self._agent.name not in message.mentions:
            return False

        return True

    async def _respond(self, context: MessageContext) -> None:
        messages = await context.social_media.messages(context, limit=1)
        if len(messages) > 0 and not self._should_respond(messages[0]):
            return

        await self._agent(context)

    async def connect(self) -> None:
        """
        Initialize the trigger.

        Can only be called once the social media is ready.
        """

        print("Connected")

        # TODO: Respond to old messages in various contexts

    async def _read_message(self, context: MessageContext, message: Message) -> None:
        # Send a few messages
        await self._respond(context)

        # Sometimes send a follow-up message in a few minutes
        if random.randint(0, 1) == 0:
            await asyncio.sleep(4.0 * 60.0 * random.random() + 60.0)
            await self._respond(context)

        # TODO: Respond to old messages in other contexts

    async def read_message(self, context: MessageContext, message: Message) -> None:
        """
        Respond to a new message (if appropriate).

        Args:
            context: Context where the message was received.
            message: New message to respond to.
        """

        if not self._should_respond(message):
            return

        # If we're already working on a response to a previous message, cancel
        # that and start responding to the new message
        if self._response_task and not self._response_task.done():
            self._response_task.cancel()

        self._response_task = asyncio.create_task(self._read_message(context, message))
