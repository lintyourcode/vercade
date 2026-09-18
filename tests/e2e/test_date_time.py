import asyncio

import pytest

from tests.e2e.conftest import Chat
from tests.judge import match

pytestmark = pytest.mark.e2e


def test_knows_date_and_time(chat: Chat) -> None:
    reply = chat.ask("What is the current date and time?")
    assert asyncio.run(
        match(
            reply.content,
            "states a specific current date and time",
            "Discord message",
        )
    )
