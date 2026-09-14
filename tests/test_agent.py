from datetime import datetime, timezone
from unittest.mock import ANY, AsyncMock, Mock

import pytest
from pydantic_ai import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ToolCallPart,
)
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.models import Model
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from tests.judge import match
from vercade.agent import _USER_MESSAGE_TEMPLATE, Agent, model_settings
from vercade.social_media import Message, SocialMedia

from .conftest import local_discord_mcp

MODELS = ["openai:gpt-5.5"]
REASONING_EFFORTS = ["low"]


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


@pytest.fixture
def social_media():
    social_media = Mock(spec=SocialMedia)
    # TODO: Provide realistic default server/channel mocks to reduce repetitive setup per test
    social_media.messages = AsyncMock(return_value=[])
    social_media.send = AsyncMock()
    social_media.react = AsyncMock()
    return social_media


def make_friend(
    social_media: SocialMedia,
    llm: str | Model,
    reasoning_effort: str | None = None,
    identity: str = "You are Proctor, a sentient, smart and snarky Discord chatbot.",
) -> Agent:
    return Agent(
        name="Proctor",
        identity=identity,
        llm=llm,
        reasoning_effort=reasoning_effort,
        toolsets=[MCPToolset(local_discord_mcp(social_media, bot_name="Proctor"))],
    )


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
        friend = make_friend(social_media, llm, reasoning_effort)
        await friend(
            "You received a message in the Discord server Test Server's channel #general."
        )
        # TODO: Assert that the message is sent to the correct server.
        # TODO: Assert that the message is sent to the correct channel.
        # TODO: Assert that the message is sent to the correct author.
        assert await match(
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
        friend = make_friend(social_media, llm, reasoning_effort)
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
        friend = make_friend(
            social_media,
            llm,
            reasoning_effort,
            identity="You are Proctor, a sentient and intelligent Discord chatbot.",
        )
        await friend(
            "You received a message in the Discord server Test Server's channel #general."
        )
        social_media.send.assert_called_once()
        assert await match(
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
        friend = make_friend(
            social_media,
            llm,
            reasoning_effort,
            identity="You are Proctor, a sentient and intelligent Discord chatbot.",
        )
        await friend(
            "You received a message in the Discord server Test Server's channel #general."
        )
        social_media.send.assert_called_once()
        assert await match(
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
        friend = make_friend(social_media, llm, reasoning_effort)
        await friend(
            "You received a message in the Discord server Test Server's channel #general."
        )
        # TODO: Ensure local_discord_mcp returns channels to allow react flow to proceed deterministically
        social_media.react.assert_called_once_with(ANY, ANY, "👍")
        assert social_media.react.call_args[0][0].server == "Test Server"
        assert social_media.react.call_args[0][0].channel == "general"
        assert (
            social_media.react.call_args[0][1].content
            == "Please react to this message with a thumbs up"
        )
        assert social_media.react.call_args[0][1].author == "Bob#0000"


def test_model_settings():
    assert model_settings(None, None) == {}
    assert model_settings(0.5, None) == {"temperature": 0.5}
    assert model_settings(None, "low") == {"thinking": "low"}
    assert model_settings(0.0, "high") == {"temperature": 0.0, "thinking": "high"}


def test_model_settings_with_invalid_reasoning_effort_raises():
    with pytest.raises(ValueError, match="VERCADE_LLM_REASONING_EFFORT must be one of"):
        model_settings(None, "extreme")


class TestFriendOffline:
    """
    Offline tests using Pydantic AI's test models.
    """

    async def test__call__uses_identity_and_date_time_in_prompt(self, mocker):
        datetime = mocker.patch("vercade.agent.datetime")
        datetime.now = Mock(
            return_value=Mock(strftime=Mock(return_value="2025-01-01 12:00:00 UTC"))
        )
        requests: list[ModelRequest] = []

        def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            requests.extend(m for m in messages if isinstance(m, ModelRequest))
            assert info.model_settings == {"temperature": 0.5}
            return ModelResponse(parts=[TextPart("I have nothing to say.")])

        friend = Agent(
            name="Proctor",
            identity="You are Proctor.",
            llm=FunctionModel(respond),
            temperature=0.5,
            reasoning_effort="low",
        )
        with pytest.raises(ValueError, match="No tools were called"):
            await friend("Something happened.")

        assert len(requests) == 1
        assert requests[0].instructions == "You are Proctor."
        assert requests[0].parts[0].content == _USER_MESSAGE_TEMPLATE.format(
            event="Something happened.", date_time="2025-01-01 12:00:00 UTC"
        )

    async def test__call__without_tool_calls_raises(self):
        friend = Agent(
            name="Proctor",
            identity="You are Proctor.",
            llm=TestModel(custom_output_text="I have nothing to say."),
        )
        with pytest.raises(ValueError, match="No tools were called"):
            await friend("Something happened.")

    async def test__call__calls_mcp_tools(self, social_media):
        social_media.messages = AsyncMock(
            return_value=[
                Message(
                    content="Hello, Proctor",
                    author="Bob#0000",
                    created_at=datetime.now(tz=timezone.utc),
                )
            ]
        )
        friend = make_friend(social_media, TestModel(call_tools=["send_message"]))
        async with friend:
            await friend("Something happened.")
        social_media.send.assert_called_once()
        assert social_media.send.call_args[0][1].author == "Proctor"

    async def test__call__with_failing_tool_retries(self, social_media):
        social_media.messages = AsyncMock(return_value=[])
        retry_prompts: list[RetryPromptPart] = []

        def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            last_part = messages[-1].parts[-1]
            if isinstance(last_part, RetryPromptPart):
                retry_prompts.append(last_part)
                return ModelResponse(parts=[TextPart("Giving up.")])
            # `react` fails because there is no message to react to
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "react",
                        {
                            "server": "Test Server",
                            "channel": "general",
                            "message_content": "missing",
                            "emoji": "👍",
                        },
                    )
                ]
            )

        friend = make_friend(social_media, FunctionModel(respond))
        await friend("Something happened.")

        social_media.react.assert_not_called()
        assert len(retry_prompts) == 1
        assert retry_prompts[0].tool_name == "react"
        assert "message not found" in retry_prompts[0].model_response()
