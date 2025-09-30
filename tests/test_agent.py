import dotenv
import pytest
from unittest.mock import AsyncMock, Mock, ANY
from datetime import datetime, timezone

from litellm import completion

from vercade.agent import Agent
from vercade.social_media import Message, SocialMedia
from .conftest import LocalDiscordMcp


MODELS = ["gpt-5"]
REASONING_EFFORTS = ["low"]

dotenv.load_dotenv()


def get_parameters() -> list[tuple[str, str]]:
    """
    Return a list of parameters for the tests.

    Each parameter is a tuple of a model and a reasoning effort.
    """

    return [
        (model, reasoning_effort)
        for model in MODELS
        for reasoning_effort in REASONING_EFFORTS
    ]


def match(text: str, condition: str, text_type: str = "text") -> bool:
    text_type = text_type.lower()
    response = completion(
        model="gpt-5-mini",
        reasoning_effort="low",
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
    @pytest.mark.parametrize("llm, reasoning_effort", get_parameters())
    async def test__call__knows_date_and_time(
        self, mocker, social_media, llm, reasoning_effort
    ):
        datetime = mocker.patch("vercade.agent.datetime")
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
            reasoning_effort=reasoning_effort,
            mcp_client=LocalDiscordMcp(social_media, bot_name="Proctor"),
        )
        await friend(
            "You received a message in the Discord server Test Server's channel #general."
        )
        # TODO: Assert that the message is sent to the correct server.
        # TODO: Assert that the message is sent to the correct channel.
        # TODO: Assert that the message is sent to the correct author.
        assert match(
            social_media.send.call_args[0][1].content,
            "Indicates that the current date and time is 2025-01-01 12:00:00 UTC",
            text_type="message",
        )

    @pytest.mark.parametrize("llm, reasoning_effort", get_parameters())
    async def test__call__with_greeting_responds_with_nonempty_message(
        self, social_media, llm, reasoning_effort
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
            reasoning_effort=reasoning_effort,
            mcp_client=LocalDiscordMcp(social_media, bot_name="Proctor"),
        )
        await friend(
            "You received a message in the Discord server Test Server's channel #general."
        )
        social_media.send.assert_called_once()
        assert social_media.send.call_args[0][0].server == "Test Server"
        assert social_media.send.call_args[0][0].channel == "general"
        # TODO: Assert author is the friend's identity.
        content = social_media.send.call_args[0][1].content
        assert isinstance(content, str)
        assert content

    @pytest.mark.parametrize("llm, reasoning_effort", get_parameters())
    async def test__call__lists_servers(self, social_media, llm, reasoning_effort):
        social_media.messages = AsyncMock(
            return_value=[
                Message(
                    content="List the servers you have access to",
                    author="Bob#0000",
                    created_at=datetime.now(tz=timezone.utc),
                )
            ]
        )
        friend = Agent(
            name="Proctor",
            identity="You are Proctor, a sentient and intelligent Discord chatbot.",
            llm=llm,
            reasoning_effort=reasoning_effort,
            mcp_client=LocalDiscordMcp(social_media, bot_name="Proctor"),
        )
        await friend(
            "You received a message in the Discord server Test Server's channel #general."
        )
        social_media.send.assert_called_once()
        assert match(
            social_media.send.call_args[0][1].content,
            "Indicates that the bot has access to the following servers: Test Server, Test Server 2",
            "message",
        )

    @pytest.mark.parametrize("llm, reasoning_effort", get_parameters())
    async def test__call__lists_channels(self, social_media, llm, reasoning_effort):
        social_media.messages = AsyncMock(
            return_value=[
                Message(
                    content="List the channels in the server Test Server",
                    author="Bob#0000",
                    created_at=datetime.now(tz=timezone.utc),
                )
            ]
        )
        friend = Agent(
            name="Proctor",
            identity="You are Proctor, a sentient and intelligent Discord chatbot.",
            llm=llm,
            reasoning_effort=reasoning_effort,
            mcp_client=LocalDiscordMcp(social_media, bot_name="Proctor"),
        )
        await friend(
            "You received a message in the Discord server Test Server's channel #general."
        )
        social_media.send.assert_called_once()
        assert match(
            social_media.send.call_args[0][1].content,
            "Indicates that Discord server Test Server has the following channels: general, spam",
            "message",
        )

    @pytest.mark.parametrize("llm, reasoning_effort", get_parameters())
    async def test__call__reacts_to_message(self, social_media, llm, reasoning_effort):
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
            reasoning_effort=reasoning_effort,
            mcp_client=LocalDiscordMcp(social_media, bot_name="Proctor"),
        )
        await friend(
            "You received a message in the Discord server Test Server's channel #general."
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
