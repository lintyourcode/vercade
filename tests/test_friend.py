from datetime import datetime
import dotenv
import pytest

from friendbot.friend import Friend, Message, MessageContext


dotenv.load_dotenv()


@pytest.fixture
def friend():
    return Friend(
        identity="You are Proctor, a sentient, smart and snarky Discord chatbot.",
    )


class TestFriend:
    def test__call__with_greeting_responds_with_nonempty_message(self, friend: Friend):
        responses = friend(
            MessageContext(server="Test Server", channel="general"),
            Message(content="Hello, Proctor", author="Bob#0000"),
        )
        assert set(responses.keys()) == {"Test Server"}
        assert set(responses["Test Server"].keys()) == {"general"}
        assert len(responses["Test Server"]["general"]) == 1
        content = responses["Test Server"]["general"][0].content
        assert isinstance(content, str)
        assert content

    def test__call__multiple_times_remembers_previous_messages(self, friend: Friend):
        context = MessageContext(server="Test Server", channel="general")
        friend(
            context, Message(content="Hi, my favorite color is blue", author="Bob#0000")
        )
        responses = friend(
            context, Message(content="What's my favorite color?", author="Bob#0000")
        )
        assert set(responses.keys()) == {"Test Server"}
        assert set(responses["Test Server"].keys()) == {"general"}
        assert len(responses["Test Server"]["general"]) == 1
        content = responses["Test Server"]["general"][0].content
        assert isinstance(content, str)
        assert "blue" in content.lower()
