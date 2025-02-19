import asyncio
import re
from typing import List, Tuple

import discord

from friendbot.agent import Agent
from friendbot.social_media import Channel, Embed, Message, MessageContext, Reaction, Server, SocialMedia


class DiscordClient(discord.Client, SocialMedia):
    def __init__(self, *, friend: Agent = None, loop=None, **options) -> None:
        intents = discord.Intents.default()
        intents.members = True
        discord.Client.__init__(self, loop=loop, intents=intents, **options)
        SocialMedia.__init__(self)

        if not friend:
            raise ValueError("please provide a Friend instance")

        self._respond_task = None
        self._agent = friend

    async def _discord_message_to_message(self, message: discord.Message) -> Message:
        content = message.system_content

        # Replace Discord mentions with @username mentions
        for mention in message.mentions:
            content = content.replace(mention.mention, f"@{mention.name}")

        reactions = []
        for reaction in message.reactions:
            users = []
            async for user in reaction.users():
                users.append(user.name)
            reactions.append(
                Reaction(
                    emoji=self._emoji_name(reaction.emoji),
                    users=users,
                )
            )

        return Message(
            content=content,
            author=message.author.name,
            embeds=[Embed(url=embed.url) for embed in message.embeds],
            reactions=reactions,
        )

    def _emoji_name(self, emoji: discord.PartialEmoji | discord.Emoji | str) -> str:
        if isinstance(emoji, discord.PartialEmoji) or isinstance(emoji, discord.Emoji):
            return emoji.name
        if isinstance(emoji, str):
            return emoji
        raise ValueError(f"Unknown emoji type: {type(emoji)}")

    async def on_ready(self) -> None:
        if self._agent.name != self.user.name:
            raise ValueError(
                f"Friend name {self._agent.name} does not match Discord bot name {self.user.name}"
            )

        if self.on_ready_callback:
            await self.on_ready_callback()

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

    async def on_message(self, message: discord.Message) -> None:
        if self.on_message_callback:
            await self.on_message_callback(
                MessageContext(
                    social_media=self,
                    server=message.guild.name,
                    channel=message.channel.name,
                ),
                await self._discord_message_to_message(message),
            )

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

    async def servers(self) -> List[Server]:
        return [Server(guild.name) for guild in self.guilds]

    async def channels(self, server_name: str) -> List[Channel]:
        guild = discord.utils.get(self.guilds, name=server_name)
        if not guild:
            raise ValueError(f"Guild {server_name} not found")
        return [Channel(channel.name) for channel in guild.text_channels]

    async def messages(
        self, context: MessageContext, limit: int = 100
    ) -> List[Message]:
        guild, channel = await self._get_guild_and_channel(context)
        return list(
            reversed(
                [
                    await self._discord_message_to_message(message)
                    async for message in channel.history(limit=limit)
                ]
            )
        )

    async def send(self, context: MessageContext, message: Message) -> None:
        if not self.is_ready():
            return

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
