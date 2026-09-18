import asyncio

import pytest

from tests.e2e.conftest import Chat
from tests.judge import match

pytestmark = pytest.mark.e2e


def test_lists_channels(chat: Chat) -> None:
    reply = chat.ask("List the channels in this server.")
    assert asyncio.run(
        match(
            reply.content,
            f"lists this server's channels, including one named {chat.channel.name!r}",
            "Discord message",
        )
    )
