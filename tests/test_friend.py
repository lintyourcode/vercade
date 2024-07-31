from datetime import datetime
import dotenv
import pytest

from friendbot.friend import Friend, Message


dotenv.load_dotenv()


@pytest.fixture
def friend():
    return Friend(
        identity="You are Proctor, a sentient, smart and snarky Discord chatbot.",
    )


class TestFriend:
    def test__call__with_greeting_responds_with_nonempty_message(self, friend: Friend):
        responses = friend(Message(content="Hello, Proctor", author="Bob#0000"))
        assert len(responses) == 1
        assert isinstance(responses[0].content, str)
        assert responses[0].content

    def test__call__multiple_times_remembers_previous_messages(self, friend: Friend):
        friend(Message(content="Hi, my favorite color is blue", author="Bob#0000"))
        responses = friend(
            Message(content="What's my favorite color?", author="Bob#0000")
        )
        assert len(responses) == 1
        assert isinstance(responses[0].content, str)
        assert "blue" in responses[0].content.lower()
