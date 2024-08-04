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
    social_media.messages = AsyncMock(return_value=[])
    social_media.send = AsyncMock()
    social_media.react = AsyncMock()
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
        social_media.messages = AsyncMock(
            return_value=[Message(content="Hello, Proctor", author="Bob#0000")]
        )
        await friend(context)
        # TODO: Update expected author to the friend's identity
        assert social_media.send.called_once_with(
            context, Message(content=ANY, author="Bob#0000")
        )
        content = social_media.send.call_args[0][1].content
        assert isinstance(content, str)
        assert content

    @pytest.mark.parametrize("llm", MODELS)
    async def test__call__reacts_to_message(self, social_media, llm):
        friend = Friend(
            identity="You are Proctor, a sentient, smart and snarky Discord chatbot.",
            llm=llm,
        )
        context = MessageContext(social_media, "Test Server", "general")
        message = Message(
            content="Please react to this message with a thumbs up",
            author="Bob#0000",
        )
        social_media.messages = AsyncMock(return_value=[message])
        await friend(context)
        assert social_media.react.called_once_with(context, message, "👍")
