from datetime import datetime
import dotenv
import pytest

from unittest.mock import AsyncMock, Mock, ANY

from friendbot.friend import Friend
from friendbot.message import Message, MessageContext
from friendbot.social_media import SocialMedia


MODELS = ["gpt-4o-mini", "claude-3-5-sonnet-20240620"]


dotenv.load_dotenv()


@pytest.fixture
def social_media():
    social_media = Mock(spec=SocialMedia)
    social_media.send = AsyncMock()
    return social_media


class TestFriend:
    @pytest.mark.parametrize("llm", MODELS)
    async def test__call__with_greeting_responds_with_nonempty_message(
        self, social_media, llm
    ):
        friend = Friend(
            identity="You are Proctor, a sentient, smart and snarky Discord chatbot.",
            llm=llm,
        )
        context = MessageContext(
            social_media=social_media, server="Test Server", channel="general"
        )
        await friend(context, Message(content="Hello, Proctor", author="Bob#0000"))
        assert social_media.send.called_once_with(
            context, Message(content=ANY, author="Bob#0000")
        )
        content = social_media.send.call_args[0][1].content
        assert isinstance(content, str)
        assert content

    @pytest.mark.parametrize("llm", MODELS)
    async def test__call__multiple_times_remembers_previous_messages(
        self, social_media, llm
    ):
        friend = Friend(
            identity="You are Proctor, a sentient, smart and snarky Discord chatbot.",
            llm=llm,
        )
        context = MessageContext(
            social_media=social_media, server="Test Server", channel="general"
        )
        await friend(
            context, Message(content="Hi, my favorite color is blue", author="Bob#0000")
        )
        await friend(
            context, Message(content="What's my favorite color?", author="Bob#0000")
        )
        assert social_media.send.called_once_with(
            context, Message(content=ANY, author="Bob#0000")
        )
        content = social_media.send.call_args[0][1].content
        assert isinstance(content, str)
        assert "blue" in content.lower()
