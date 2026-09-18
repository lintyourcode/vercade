import asyncio

import pytest

from tests.e2e.conftest import Chat
from tests.judge import match

pytestmark = pytest.mark.e2e


def test_lists_servers(chat: Chat) -> None:
    guild = chat.user_stub.client.get_guild(chat.server.guild_id)
    assert guild is not None

    reply = chat.ask("Which Discord servers are you in?")
    assert asyncio.run(
        match(
            reply.content,
            f"says the bot is in a server named {guild.name!r}",
            "Discord message",
        )
    )
