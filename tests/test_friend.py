from datetime import datetime
import dotenv
import pytest

from friendbot.friend import Friend, Message, MessageContext


MODELS = ["gpt-4o-mini", "claude-3-5-sonnet-20240620"]


dotenv.load_dotenv()


class TestFriend:
    @pytest.mark.parametrize("llm", MODELS)
    def test__call__with_greeting_responds_with_nonempty_message(self, llm: str):
        friend = Friend(
            identity="You are Proctor, a sentient, smart and snarky Discord chatbot.",
            llm=llm,
        )
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

    @pytest.mark.parametrize("llm", MODELS)
    def test__call__multiple_times_remembers_previous_messages(self, llm: str):
        friend = Friend(
            identity="You are Proctor, a sentient, smart and snarky Discord chatbot.",
            llm=llm,
        )
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
