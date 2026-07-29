from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from tests.e2e import setup_server
from tests.e2e.discord_identity import BotIdentity
from tests.e2e.setup_server import _Bot, _ensure_ready, _permission_names

GUILD_ID = 123456789


def make_bot(
    client: AsyncMock,
    required_permissions: discord.Permissions,
) -> _Bot:
    return _Bot(
        client=client,
        identity=BotIdentity(id=111, name="test-bot"),
        application_id=222,
        required_permissions=required_permissions,
    )


def make_member(permissions: discord.Permissions) -> MagicMock:
    member = MagicMock()
    member.guild_permissions = permissions
    return member


def make_client(*member_results: object) -> tuple[AsyncMock, MagicMock]:
    guild = MagicMock()
    guild.fetch_member = AsyncMock(side_effect=list(member_results))
    client = AsyncMock()
    client.fetch_guild = AsyncMock(return_value=guild)
    return client, guild


def not_found() -> discord.NotFound:
    return discord.NotFound(MagicMock(), "Not Found")


def test_invite_url_requests_the_required_permissions() -> None:
    bot = make_bot(AsyncMock(), setup_server.USER_STUB_PERMISSIONS)
    assert bot.invite_url == (
        "https://discord.com/oauth2/authorize"
        f"?client_id={bot.application_id}&scope=bot"
        f"&permissions={setup_server.USER_STUB_PERMISSIONS.value}"
    )


def test_user_stub_requires_manage_channels() -> None:
    # Regression: the e2e fixtures create and delete a channel per test run.
    assert setup_server.USER_STUB_PERMISSIONS.manage_channels


def test_vercade_requires_only_chat_permissions() -> None:
    permissions = setup_server.VERCADE_PERMISSIONS
    assert permissions.view_channel
    assert permissions.send_messages
    assert permissions.read_message_history
    assert not permissions.manage_channels


def test_permission_names_excludes_aliases() -> None:
    names = _permission_names(discord.Permissions(view_channel=True).value)
    assert len(names) == 1


async def test_ready_when_member_has_permissions() -> None:
    client, guild = make_client(make_member(setup_server.USER_STUB_PERMISSIONS))
    bot = make_bot(client, setup_server.USER_STUB_PERMISSIONS)

    result = await _ensure_ready(bot, GUILD_ID)

    assert result is guild
    client.fetch_guild.assert_awaited_once_with(GUILD_ID)
    guild.fetch_member.assert_awaited_once_with(bot.identity.id)


async def test_waits_for_bot_to_join(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(setup_server, "POLL_INTERVAL_SECONDS", 0)
    client, guild = make_client(
        not_found(), make_member(setup_server.VERCADE_PERMISSIONS)
    )

    result = await _ensure_ready(
        make_bot(client, setup_server.VERCADE_PERMISSIONS), GUILD_ID
    )

    assert result is guild
    assert "is not in the test server" in capsys.readouterr().out


async def test_waits_for_missing_permissions_to_be_granted(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(setup_server, "POLL_INTERVAL_SECONDS", 0)
    required = setup_server.USER_STUB_PERMISSIONS
    lacking = make_member(
        discord.Permissions(
            view_channel=True, send_messages=True, read_message_history=True
        )
    )
    client, guild = make_client(lacking, make_member(required))
    bot = make_bot(client, required)

    result = await _ensure_ready(bot, GUILD_ID)

    assert result is guild
    out = capsys.readouterr().out
    assert "missing permissions" in out
    assert "manage channels" in out
    assert bot.invite_url in out


async def test_times_out_if_bot_never_joins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(setup_server, "POLL_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(setup_server, "POLL_TIMEOUT_SECONDS", 0.05)
    client, _ = make_client()
    client.fetch_guild.side_effect = not_found()

    with pytest.raises(SystemExit):
        await _ensure_ready(
            make_bot(client, setup_server.VERCADE_PERMISSIONS), GUILD_ID
        )
