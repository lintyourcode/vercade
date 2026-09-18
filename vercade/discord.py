from collections.abc import Awaitable, Callable

import discord

from vercade.agent import Agent


class DiscordClient(discord.Client):
    def __init__(
        self,
        *,
        activity: discord.Activity | None = None,
        friend: Agent = None,
        loop=None,
        **options,
    ) -> None:
        super().__init__(loop=loop, intents=discord.Intents.default(), **options)

        if not friend:
            raise ValueError("please provide a Friend instance")

        self._respond_task = None
        self._activity = activity
        self._agent = friend

        self.on_ready_callback: Callable[[], Awaitable[None]] | None = None
        # Invoked for messages from other users; the bot's own messages are
        # never forwarded.
        self.on_message_callback: (
            Callable[[discord.Message], Awaitable[None]] | None
        ) = None

    async def on_ready(self) -> None:
        if self._activity:
            await self.change_presence(activity=self._activity)

        if self.on_ready_callback:
            await self.on_ready_callback()

    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.user:
            return

        if self.on_message_callback:
            await self.on_message_callback(message)
