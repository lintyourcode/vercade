import asyncio
import random

import discord
import openai

from friendbot.friend import Friend, Message


class DiscordClient(discord.Client):
    def __init__(self, *, friend: Friend = None, loop=None, **options) -> None:
        super().__init__(loop=loop, intents=discord.Intents.default(), **options)

        if not friend:
            raise ValueError("please provide a Friend instance")

        self._respond_task = None
        self._friend = friend

    async def _get_last_message(self, channel: discord.TextChannel) -> discord.Message:
        async for message in channel.history(limit=1):
            return message
        else:
            return None

    def _mentions_other_user(self, message: discord.Message) -> bool:
        if len(message.mentions) > 0 and not self._mentioned_in(message):
            # If we're working on a response to a previous message, cancel that
            if self._respond_task and not self._respond_task.done():
                self._respond_task.cancel()

            return True

        return False

    def _should_respond_to(self, message: discord.Message) -> bool:
        if message.author == self.user:
            return False

        if self._mentions_other_user(message):
            return False

        return True

    def _should_stop_after(self, message: discord.Message) -> bool:
        return self._mentions_other_user(message)

    async def _sleep(self, min_delay: float, max_delay: float) -> None:
        delay = (max_delay - min_delay) * random.random() + min_delay

        # Prevent negative numbers
        delay = max(0, delay)

        await asyncio.sleep(delay)

    async def _respond_to_old_messages(self) -> None:
        channels = list(self.get_all_channels())
        random.shuffle(channels)
        # Reply to all channels
        for channel in channels:
            if not isinstance(channel, discord.TextChannel):
                continue

            last_message = await self._get_last_message(channel)
            if not last_message or not self._should_respond_to(last_message):
                continue

            await self._sleep(-45.0, 60.0)
            await self._send_messages(channel)

    async def on_ready(self) -> None:
        print(f"Logged in as {self.user}")

        # Not sure if this condition will ever be met, but it's good to be safe
        if self._respond_task and not self._respond_task.done():
            self._respond_task.cancel()

        self._respond_task = asyncio.ensure_future(self._respond_to_old_messages())

    def _mentioned_in(self, message: discord.Message) -> bool:
        client_members = self.get_all_members()
        for mention in message.mentions:
            if mention in client_members:
                return True

        return False

    async def _send_messages(self, channel: discord.TextChannel) -> None:
        async with channel.typing():
            response = None
            while response is None:
                try:
                    last_message = await self._get_last_message(channel)
                    if not self._should_respond_to(last_message):
                        return

                    response = self._friend(
                        Message(
                            content=last_message.content,
                            author=last_message.author.name,
                        )
                    )

                except openai.OpenAIError as e:
                    print(f"OpenAIError ({e}) - waiting to retry...")
                    # Wait before trying again
                    await self._sleep(60.0, 3.0 * 60.0)

            if response:
                await channel.send(response.content)

    async def _on_message(self, message: discord.Message) -> None:
        channel = message.channel

        # Initial delay
        await self._sleep(-75.0, 60.0)

        # Send a few messages
        await self._send_messages(channel)

        # Sometimes send a message in an hour or so
        if random.randint(0, 1) == 0:
            await self._sleep(60.0, 2.0 * 60.0 * 60.0)
            await self._send_messages(channel)

        # Always check and respond to existing messages after we're done with
        # everyth8ing else
        await self._respond_to_old_messages()

    async def on_message(self, message: discord.Message) -> None:
        if not self.is_ready():
            return

        if not self._should_respond_to(message):
            return

        # If we're working on a response to a previous message, cancel that
        if self._respond_task and not self._respond_task.done():
            self._respond_task.cancel()

        self._respond_task = asyncio.create_task(self._on_message(message))
