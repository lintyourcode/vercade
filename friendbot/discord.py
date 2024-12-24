import asyncio
import random
import re
from typing import List, Tuple

import discord

from friendbot.friend import Friend
from friendbot.social_media import Embed, Message, MessageContext, Reaction, SocialMedia


class DiscordClient(discord.Client, SocialMedia):
    def __init__(self, *, friend: Friend = None, loop=None, **options) -> None:
        intents = discord.Intents.default()
        intents.members = True
        discord.Client.__init__(self, loop=loop, intents=intents, **options)
        SocialMedia.__init__(self)

        if not friend:
            raise ValueError("please provide a Friend instance")

        self._respond_task = None
        self._friend = friend

    async def _get_last_message(self, channel: discord.TextChannel) -> discord.Message:
        async for message in channel.history(limit=1):
            return message
        else:
            return None

    def _emoji_name(self, emoji: discord.PartialEmoji | discord.Emoji | str) -> str:
        if isinstance(emoji, discord.PartialEmoji) or isinstance(emoji, discord.Emoji):
            return emoji.name
        if isinstance(emoji, str):
            return emoji
        raise ValueError(f"Unknown emoji type: {type(emoji)}")

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

            await self._sleep(0.0, 600.0)
            await self._respond_to_messages(channel)

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

    def _format_message_for_friend(self, message: discord.Message) -> str:
        content = message.system_content

        # Replace Discord mentions with @username mentions
        for mention in message.mentions:
            content = content.replace(mention.mention, f"@{mention.name}")

        return content

    def _format_message_for_discord(
        self, message: Message, channel: discord.TextChannel
    ) -> str:
        content = message.content

        # Replace @username mentions with Discord mentions
        all_users = {user.name: user for user in channel.guild.members}
        mentions = re.findall(r"@(\w+)", content)
        for username in mentions:
            user = all_users.get(username)
            if not user:
                print(f"User {username} not found")

            content = content.replace(f"@{username}", f"<@{user.id}>")

        return content

    async def _respond_to_messages(self, channel: discord.TextChannel) -> None:
        last_message = await self._get_last_message(channel)
        if not self._should_respond_to(last_message):
            return

        responses = await self._friend(
            MessageContext(
                social_media=self,
                server=channel.guild.name,
                channel=channel.name,
            )
        )

        for guild_name, conversations in responses.items():
            for channel_name, responses in conversations.items():
                for response in responses:
                    guild = discord.utils.get(self.guilds, name=guild_name)
                    if not guild:
                        raise ValueError(f"Guild {guild_name} not found")
                    channel = discord.utils.get(guild.text_channels, name=channel_name)
                    if not channel:
                        raise ValueError(f"Channel {channel_name} not found")
                    async with channel.typing():
                        await asyncio.sleep(len(response.content) / 20.0)
                        await channel.send(
                            self._format_message_for_discord(response, channel)
                        )

    async def _on_message(self, message: discord.Message) -> None:
        channel = message.channel

        # Send a few messages
        await self._respond_to_messages(channel)

        # Sometimes send a message in an hour or so
        if random.randint(0, 1) == 0:
            await self._sleep(60.0, 5.0 * 60.0)
            await self._respond_to_messages(channel)

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

    async def _get_guild_and_channel(
        self, context: MessageContext
    ) -> Tuple[discord.Guild, discord.TextChannel]:
        guild = discord.utils.get(self.guilds, name=context.server)
        if not guild:
            raise ValueError(f"Guild {context.server} not found")
        channel = discord.utils.get(guild.text_channels, name=context.channel)
        if not channel:
            raise ValueError(f"Channel {context.channel} not found")
        return guild, channel

    async def _get_message(
        self,
        guild: discord.Guild,
        channel: discord.TextChannel,
        message: Message,
        fetch_limit: int = 100,
    ) -> discord.Message:
        async for msg in channel.history(limit=fetch_limit):
            if msg.content == message.content:
                return msg

    async def messages(
        self, context: MessageContext, limit: int = 100
    ) -> List[Message]:
        guild, channel = await self._get_guild_and_channel(context)
        return reversed(
            [
                Message(
                    content=self._format_message_for_friend(message),
                    author=message.author.name,
                    embeds=[
                        Embed(
                            url=embed.url,
                        )
                        for embed in message.embeds
                    ],
                    reactions=[
                        Reaction(
                            emoji=self._emoji_name(reaction.emoji),
                            users=[user.name async for user in reaction.users()],
                        )
                        for reaction in message.reactions
                    ],
                )
                async for message in channel.history(limit=limit)
            ]
        )

    async def send(self, context: MessageContext, message: Message) -> None:
        guild, channel = await self._get_guild_and_channel(context)
        async with channel.typing():
            await asyncio.sleep(len(message.content) / 20.0)
        await channel.send(self._format_message_for_discord(message, channel))

    async def react(
        self, context: MessageContext, message: Message, emoji: str
    ) -> None:
        """
        React to a message with an emoji.
        """

        guild, channel = await self._get_guild_and_channel(context)
        discord_message = await self._get_message(guild, channel, message)
        discord_emoji = discord.utils.get(guild.emojis, name=emoji) or emoji
        await discord_message.add_reaction(discord_emoji)
