import dotenv
import pytest
from unittest.mock import AsyncMock, Mock, ANY
from datetime import datetime, timezone
from typing import Any

from litellm import completion

from friendbot.agent import Agent
from friendbot.social_media import Channel, Message, Server, SocialMedia
from .conftest import LocalDiscordMcp


MODELS = ["gpt-4o", "anthropic/claude-3-5-sonnet-latest"]
FAST_MODELS = ["gpt-4o-mini"]


dotenv.load_dotenv()


def get_parameters() -> list[tuple[str, str]]:
    """
    Return a list of parameters for the tests.
    """

    return [(model, fast_model) for model in MODELS for fast_model in FAST_MODELS]


def match(text: str, condition: str, text_type: str = "text") -> bool:
    text_type = text_type.lower()
    response = completion(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": f"Does the following {text_type} match the condition? Only respond with 'yes' or 'no'.\n\n{text_type.capitalize()}: {text}\n\nCondition: {condition}",
            }
        ],
    )
    answer = response["choices"][0]["message"]["content"].lower()
    if answer == "yes":
        return True
    elif answer == "no":
        return False
    else:
        raise ValueError(f"Invalid answer: {answer}")


@pytest.fixture
def social_media():
    social_media = Mock(spec=SocialMedia)
    # TODO: Provide realistic default server/channel mocks to reduce repetitive setup per test
    social_media.messages = AsyncMock(return_value=[])
    social_media.send = AsyncMock()
    social_media.react = AsyncMock()
    return social_media


class TestFriend:
    @pytest.mark.parametrize("llm, fast_llm", get_parameters())
    async def test__call__knows_date_and_time(
        self, mocker, social_media, llm, fast_llm
    ):
        datetime = mocker.patch("friendbot.agent.datetime")
        datetime.now = Mock(
            return_value=Mock(strftime=Mock(return_value="2025-01-01 12:00:00 UTC"))
        )
        social_media.messages = AsyncMock(
            return_value=[
                Message(
                    content="Hello, Proctor. What is the current date and time?",
                    author="Bob",
                    created_at=datetime.now(tz=timezone.utc),
                )
            ]
        )
        friend = Agent(
            name="Proctor",
            identity="You are Proctor, a sentient, smart and snarky Discord chatbot.",
            llm=llm,
            fast_llm=fast_llm,
            mcp_client=LocalDiscordMcp(social_media, bot_name="Proctor"),
        )
        await friend(
            "You received a message in the Discord server Test Server's channel #general.",
            social_media,
        )
        # TODO: Assert that the message is sent to the correct server.
        # TODO: Assert that the message is sent to the correct channel.
        # TODO: Assert that the message is sent to the correct author.
        assert match(
            social_media.send.call_args[0][1].content,
            "Indicates that the current date and time is 2025-01-01 12:00:00 UTC",
            text_type="message",
        )

    @pytest.mark.parametrize("llm, fast_llm", get_parameters())
    async def test__call__with_greeting_responds_with_nonempty_message(
        self, social_media, llm, fast_llm
    ):
        social_media.messages = AsyncMock(
            return_value=[
                Message(
                    content="Hello, Proctor",
                    author="Bob#0000",
                    created_at=datetime.now(tz=timezone.utc),
                )
            ]
        )
        friend = Agent(
            name="Proctor",
            identity="You are Proctor, a sentient, smart and snarky Discord chatbot.",
            llm=llm,
            mcp_client=LocalDiscordMcp(social_media, bot_name="Proctor"),
        )
        await friend(
            "You received a message in the Discord server Test Server's channel #general.",
            social_media,
        )
        social_media.send.assert_called_once()
        assert social_media.send.call_args[0][0].server == "Test Server"
        assert social_media.send.call_args[0][0].channel == "general"
        # TODO: Assert author is the friend's identity.
        content = social_media.send.call_args[0][1].content
        assert isinstance(content, str)
        assert content

    @pytest.mark.parametrize("llm, fast_llm", get_parameters())
    async def test__call__lists_servers(self, social_media, llm, fast_llm):
        social_media.messages = AsyncMock(
            return_value=[
                Message(
                    content="List the servers you have access to",
                    author="Bob#0000",
                    created_at=datetime.now(tz=timezone.utc),
                )
            ]
        )
        social_media.servers = AsyncMock(
            return_value=[
                Server(name="Test Server"),
                Server(name="Test Server 2"),
            ]
        )
        friend = Agent(
            name="Proctor",
            identity="You are Proctor, a sentient and intelligent Discord chatbot.",
            llm=llm,
            fast_llm=fast_llm,
            mcp_client=LocalDiscordMcp(social_media, bot_name="Proctor"),
        )
        await friend(
            "You received a message in the Discord server Test Server's channel #general.",
            social_media,
        )
        social_media.send.assert_called_once()
        social_media.servers.assert_called_once()
        assert match(
            social_media.send.call_args[0][1].content,
            "Indicates that the bot has access to the following servers: Test Server, Test Server 2",
            "message",
        )

    @pytest.mark.parametrize("llm, fast_llm", get_parameters())
    async def test__call__lists_channels(self, social_media, llm, fast_llm):
        social_media.messages = AsyncMock(
            return_value=[
                Message(
                    content="List the channels in the server Test Server",
                    author="Bob#0000",
                    created_at=datetime.now(tz=timezone.utc),
                )
            ]
        )
        # TODO: Provide channel ids here to match Channel(id, name) signature
        social_media.channels = AsyncMock(
            return_value=[
                Channel(name="general"),
                Channel(name="spam"),
            ]
        )
        friend = Agent(
            name="Proctor",
            identity="You are Proctor, a sentient and intelligent Discord chatbot.",
            llm=llm,
            fast_llm=fast_llm,
            mcp_client=LocalDiscordMcp(social_media, bot_name="Proctor"),
        )
        await friend(
            "You received a message in the Discord server Test Server's channel #general.",
            social_media,
        )
        social_media.send.assert_called_once()
        social_media.channels.assert_called_once_with("Test Server")
        assert match(
            social_media.send.call_args[0][1].content,
            "Indicates that the bot has access to the following channels: general, spam",
            "message",
        )

    @pytest.mark.parametrize("llm, fast_llm", get_parameters())
    async def test__call__reacts_to_message(self, social_media, llm, fast_llm):
        message = Message(
            content="Please react to this message with a thumbs up",
            author="Bob#0000",
            created_at=datetime.now(tz=timezone.utc),
        )
        social_media.messages = AsyncMock(return_value=[message])
        friend = Agent(
            name="Proctor",
            identity="You are Proctor, a sentient, smart and snarky Discord chatbot.",
            llm=llm,
            mcp_client=LocalDiscordMcp(social_media, bot_name="Proctor"),
        )
        await friend(
            "You received a message in the Discord server Test Server's channel #general.",
            social_media,
        )
        # TODO: Ensure LocalDiscordMcp returns channels to allow react flow to proceed deterministically
        social_media.react.assert_called_once_with(ANY, ANY, "👍")
        assert social_media.react.call_args[0][0].server == "Test Server"
        assert social_media.react.call_args[0][0].channel == "general"
        assert (
            social_media.react.call_args[0][1].content
            == "Please react to this message with a thumbs up"
        )
        assert social_media.react.call_args[0][1].author == "Bob#0000"
