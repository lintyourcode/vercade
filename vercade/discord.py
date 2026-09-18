import discord

from vercade.agent import Agent
from vercade.social_media import (
    Channel,
    Embed,
    Message,
    MessageContext,
    Reaction,
    Server,
    SocialMedia,
)


def _server_from_guild(guild: discord.Guild | None) -> Server | None:
    if guild is None:
        return None
    return Server(id=guild.id, name=guild.name)


def _channel_name(channel: object) -> str:
    name = getattr(channel, "name", None)
    if name:
        return name
    recipient = getattr(channel, "recipient", None)
    recipient_name = getattr(recipient, "name", None) if recipient is not None else None
    if recipient_name:
        return recipient_name
    return "DM"


class DiscordClient(discord.Client, SocialMedia):
    def __init__(
        self,
        *,
        activity: discord.Activity | None = None,
        friend: Agent = None,
        loop=None,
        **options,
    ) -> None:
        discord.Client.__init__(
            self, loop=loop, intents=discord.Intents.default(), **options
        )
        SocialMedia.__init__(self)

        if not friend:
            raise ValueError("please provide a Friend instance")

        self._respond_task = None
        self._activity = activity
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
            created_at=message.created_at,
            embeds=[Embed(url=embed.url) for embed in message.embeds],
            reactions=reactions,
        )

    def _emoji_name(self, emoji: discord.PartialEmoji | discord.Emoji | str) -> str:
        if isinstance(emoji, discord.PartialEmoji | discord.Emoji):
            return emoji.name
        if isinstance(emoji, str):
            return emoji
        raise ValueError(f"Unknown emoji type: {type(emoji)}")

    async def on_ready(self) -> None:
        if self._activity:
            await self.change_presence(activity=self._activity)

        if self.on_ready_callback:
            await self.on_ready_callback()

    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.user:
            return

        if self.on_message_callback:
            await self.on_message_callback(
                MessageContext(
                    social_media=self,
                    server=_server_from_guild(message.guild),
                    channel=Channel(
                        id=message.channel.id,
                        name=_channel_name(message.channel),
                    ),
                ),
                await self._discord_message_to_message(message),
            )

    async def _get_guild_and_channel(
        self, context: MessageContext
    ) -> tuple[discord.Guild | None, discord.abc.Messageable]:
        if context.server is None:
            channel = self.get_channel(context.channel.id)
            if not channel:
                raise ValueError(f"Channel {context.channel.id} not found")
            return None, channel

        guild = discord.utils.get(self.guilds, id=context.server.id)
        if not guild:
            raise ValueError(f"Guild {context.server.id} not found")
        channel = discord.utils.get(guild.text_channels, name=context.channel.name)
        if not channel:
            raise ValueError(f"Channel {context.channel.id} not found")
        return guild, channel

    async def messages(
        self, context: MessageContext, limit: int = 100
    ) -> list[Message]:
        _, channel = await self._get_guild_and_channel(context)
        return list(
            reversed(
                [
                    await self._discord_message_to_message(message)
                    async for message in channel.history(limit=limit)
                ]
            )
        )
