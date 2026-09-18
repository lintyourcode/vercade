import pytest

from tests.e2e.conftest import Chat

pytestmark = pytest.mark.e2e


def test_reacts_to_message(chat: Chat) -> None:
    message_id = chat.send("Please react to this message with a thumbs up.")
    assert chat.wait_for_reaction(message_id) == ["👍"]
