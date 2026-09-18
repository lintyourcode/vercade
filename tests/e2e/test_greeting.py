import asyncio

import pytest

from tests.e2e.conftest import Chat
from tests.judge import match

pytestmark = pytest.mark.e2e


def test_greeting_reciprocated(chat: Chat) -> None:
    reply = chat.ask("Hello!")
    assert asyncio.run(
        match(
            reply.content,
            "a friendly greeting in response to a user saying hello",
            "Discord message",
        )
    )
