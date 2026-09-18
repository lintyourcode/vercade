import pytest

from tests.e2e.conftest import SECRET_WORD, Chat

pytestmark = pytest.mark.e2e


def test_follows_skill_instructions(chat: Chat) -> None:
    reply = chat.ask("What is the secret word?")
    assert SECRET_WORD in reply.content
