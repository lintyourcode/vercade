import asyncio
import uuid

import discord

from vercade.agent import Agent
from vercade.discord import DiscordClient


class Trigger:
    """
    Trigger for invoking an agent.

    * Runs background tasks on a schedule
    * Responds to Discord messages (can respond to multiple channels in parallel)
    """

    def __init__(
        self,
        client: DiscordClient,
        friend: Agent,
        *,
        schedule_interval_seconds: float | None = None,
    ) -> None:
        self._agent = friend
        # TODO(#14): Type `response_tasks` as `dict[int, dict[int, asyncio.Task]]`
        self._response_tasks: dict[int, dict[str, asyncio.Task]] = {}
        # TODO: Remove unused `schedule_task`
        self._schedule_task: asyncio.Task | None = None
        self._scheduled_tasks: dict[str, asyncio.Task] = {}
        self._schedule_interval_seconds = schedule_interval_seconds

        self._client = client
        client.on_ready_callback = self.connect
        client.on_message_callback = self.read_message

    async def _run_idle(self) -> None:
        while True:
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

    async def connect(self) -> None:
        """
        Initialize the trigger.

        Can only be called once the Discord client is ready.
        """

        print("Connected")

        # Start scheduler if enabled
        if self._schedule_interval_seconds and self._schedule_interval_seconds > 0:
            self._schedule_task = asyncio.create_task(self._run_idle())

    def _remove_response_task(self, guild_id: int, channel_id: int) -> None:
        if not self._response_tasks.get(guild_id, {}).get(channel_id):
            return

        del self._response_tasks[guild_id][channel_id]
        if len(self._response_tasks[guild_id]) == 0:
            del self._response_tasks[guild_id]

    async def read_message(self, message: discord.Message) -> None:
        """
        Respond to a new message (if appropriate).

        Args:
            message: New message to respond to.
        """

        guild = message.guild
        channel = message.channel

        # If we're already working on a response to a previous message in the
        # same channel, cancel it
        task = self._response_tasks.get(guild.id, {}).get(channel.id)
        if task and not task.done():
            task.cancel()
            # Ensure the task is actually cancelled before proceeding to avoid duplicate sends
            try:
                await task
            except asyncio.CancelledError:
                pass
            self._remove_response_task(guild.id, channel.id)

        task = asyncio.create_task(
            self._agent(
                f"You received a message in the Discord server {guild.name} (with id {guild.id}) and channel {channel.name} (with id {channel.id})."
            )
        )
        self._response_tasks.setdefault(guild.id, {})[channel.id] = task
        task.add_done_callback(
            lambda task: self._remove_response_task(guild.id, channel.id)
        )
