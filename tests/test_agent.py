import logging
from unittest.mock import Mock

import pytest
from pydantic_ai import ModelMessage, ModelRequest, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from vercade.agent import _USER_MESSAGE_TEMPLATE, Agent


@pytest.mark.parametrize(
    ("temperature", "reasoning_effort", "expected"),
    [
        (None, None, {}),
        (0.5, None, {"temperature": 0.5}),
        (None, "low", {"thinking": "low"}),
        (0.0, "high", {"temperature": 0.0, "thinking": "high"}),
        (None, "extreme", {"thinking": "extreme"}),
    ],
)
def test_model_settings_are_passed_to_pydantic_ai(
    mocker,
    temperature: float | None,
    reasoning_effort: str | None,
    expected: dict[str, object],
):
    pydantic_agent = mocker.patch("vercade.agent.PydanticAgent")

    Agent(
        identity="You are Proctor.",
        llm=TestModel(),
        temperature=temperature,
        reasoning_effort=reasoning_effort,
    )

    assert pydantic_agent.call_args.kwargs["model_settings"] == expected


async def test__call__uses_identity_and_date_time_in_prompt(mocker):
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
        identity="You are Proctor.",
        llm=FunctionModel(respond),
        temperature=0.5,
        reasoning_effort="low",
    )
    await friend("Something happened.")

    assert len(requests) == 1
    assert requests[0].instructions == "You are Proctor."
    assert requests[0].parts[0].content == _USER_MESSAGE_TEMPLATE.format(
        event="Something happened.", date_time="2025-01-01 12:00:00 UTC"
    )


async def test__call__without_tool_calls_succeeds(caplog):
    friend = Agent(
        identity="You are Proctor.",
        llm=TestModel(custom_output_text="I have nothing to say."),
    )
    with caplog.at_level(logging.INFO, logger="vercade.agent"):
        await friend("Something happened.")

    assert "[Thought] I have nothing to say." in caplog.text
