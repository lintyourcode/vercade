from collections.abc import AsyncIterator
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from vercade.discord import DiscordClient, _channel_name, _server_from_guild
from vercade.social_media import Channel, MessageContext


def _discord_message(
    *,
    content: str = "hello",
    author: object | None = None,
    guild: object | None = None,
    channel: object | None = None,
) -> Mock:
    message = Mock()
    message.author = author if author is not None else Mock(name="author")
    message.author.name = "alice"
    message.guild = guild
    if channel is None:
        channel = Mock()
        channel.id = 2
        channel.name = "general"
    message.channel = channel
    message.system_content = content
    message.mentions = []
    message.reactions = []
    message.embeds = []
    message.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return message


@pytest.fixture
async def discord_client() -> AsyncIterator[DiscordClient]:
    client = DiscordClient(friend=Mock())
    try:
        yield client
    finally:
        await client.close()


def test_server_from_guild_none():
    assert _server_from_guild(None) is None


def test_server_from_guild_copies_id_and_name():
    guild = Mock()
    guild.id = 7
    guild.name = "Vercade"
    server = _server_from_guild(guild)
    assert server is not None
    assert server.id == 7
    assert server.name == "Vercade"


def test_channel_name_uses_channel_name():
    assert _channel_name(SimpleNamespace(name="general")) == "general"


def test_channel_name_uses_dm_recipient_when_name_missing():
    channel = SimpleNamespace(recipient=SimpleNamespace(name="alice"))
    assert _channel_name(channel) == "alice"


def test_channel_name_falls_back_to_dm():
    assert _channel_name(SimpleNamespace()) == "DM"


async def test_on_message_guild_forwards_server_and_channel(
    discord_client: DiscordClient,
):
    received: list[tuple[MessageContext, object]] = []

    async def on_message(context: MessageContext, message: object) -> None:
        received.append((context, message))

    discord_client.on_message_callback = on_message
    guild = SimpleNamespace(id=1, name="Vercade")
    channel = SimpleNamespace(id=2, name="general")
    await discord_client.on_message(
        _discord_message(content="ping", guild=guild, channel=channel)
    )

    assert len(received) == 1
    context, message = received[0]
    assert context.server is not None
    assert context.server.id == 1
    assert context.server.name == "Vercade"
    assert context.channel.id == 2
    assert context.channel.name == "general"
    assert message.content == "ping"


async def test_on_message_direct_message_does_not_require_guild(
    discord_client: DiscordClient,
):
    received: list[MessageContext] = []

    async def on_message(context: MessageContext, message: object) -> None:
        received.append(context)

    discord_client.on_message_callback = on_message
    channel = Mock(spec=["id", "recipient"])
    channel.id = 99
    channel.recipient = SimpleNamespace(name="alice")

    await discord_client.on_message(
        _discord_message(content="hi", guild=None, channel=channel)
    )

    assert len(received) == 1
    context = received[0]
    assert context.server is None
    assert context.channel.id == 99
    assert context.channel.name == "alice"


async def test_on_message_ignores_the_bots_own_messages(
    discord_client: DiscordClient, mocker
):
    discord_client.on_message_callback = AsyncMock()
    bot_user = Mock()
    mocker.patch.object(DiscordClient, "user", bot_user)
    await discord_client.on_message(_discord_message(author=bot_user))
    discord_client.on_message_callback.assert_not_called()


async def test_messages_reads_direct_message_history(
    discord_client: DiscordClient, mocker
):
    history_message = _discord_message(content="earlier")

    async def history(*, limit: int = 100):
        yield history_message

    dm_channel = Mock()
    dm_channel.history = history
    mocker.patch.object(discord_client, "get_channel", return_value=dm_channel)

    result = await discord_client.messages(
        MessageContext(
            social_media=discord_client,
            server=None,
            channel=Channel(id=99, name="alice"),
        )
    )

    assert len(result) == 1
    assert result[0].content == "earlier"


async def test_messages_direct_message_missing_channel_raises(
    discord_client: DiscordClient, mocker
):
    mocker.patch.object(discord_client, "get_channel", return_value=None)
    with pytest.raises(ValueError, match="Channel 99 not found"):
        await discord_client.messages(
            MessageContext(
                social_media=discord_client,
                server=None,
                channel=Channel(id=99, name="alice"),
            )
        )
