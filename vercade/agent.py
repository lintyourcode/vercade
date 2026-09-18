import logging
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Self, cast

from pydantic_ai import Agent as PydanticAgent
from pydantic_ai import RetryPromptPart, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.capabilities import AgentCapability
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings, ThinkingEffort
from pydantic_ai.toolsets import AbstractToolset
from pydantic_ai.usage import UsageLimits

logger = logging.getLogger(__name__)

# TODO: Make social media-specific
_USER_MESSAGE_TEMPLATE = "{event} The current date and time is {date_time}. You may use any tools available to you, or do nothing at all. The user cannot see your responses directly, so you must use the tools if you would like to respond to the user. Take your time and think carefully before responding. When you are done, finish by replying with a concise summary of the actions you took (or say that you took none)."


class Agent:
    """
    Social media AI agent.
    """

    def __init__(
        self,
        identity: str,
        llm: str | Model,
        temperature: float | None = None,
        reasoning_effort: str | None = None,
        toolsets: Sequence[AbstractToolset] = (),
        capabilities: Sequence[AgentCapability] = (),
    ) -> None:
        """
        Initialize the agent.

        Args:
            identity: Natural language description of the agent.
            llm: LLM to use for the agent, as a Pydantic AI `<provider>:<model>` name or model.
            temperature: Temperature to use for the agent's LLM.
            reasoning_effort: Reasoning effort for the agent (e.g. "low", "medium", "high").
            toolsets: Toolsets (e.g. MCP servers) available to the agent.
            capabilities: Capabilities (e.g. skills) available to the agent.
        """

        if not identity:
            raise ValueError("identity must be a non-empty string")

        model_settings = ModelSettings()
        if temperature is not None:
            model_settings["temperature"] = temperature
        if reasoning_effort is not None:
            model_settings["thinking"] = cast(ThinkingEffort, reasoning_effort)

        self._agent = PydanticAgent(
            llm,
            instructions=identity,
            model_settings=model_settings,
            toolsets=toolsets,
            capabilities=capabilities,
            # Tool errors are sent back to the LLM as retry prompts; a large
            # budget keeps the run going rather than aborting after one error.
            retries=50,
        )

    async def __aenter__(self) -> Self:
        await self._agent.__aenter__()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self._agent.__aexit__(*exc_info)

    async def __call__(self, event: str) -> None:
        """
        Respond to an event (e.g. a new message) using the available tools.

        Args:
            event: Natural language description of the event.
        """

        logger.debug("Starting agent")
        result = await self._agent.run(
            _USER_MESSAGE_TEMPLATE.format(
                event=event,
                date_time=datetime.now(tz=timezone.utc).strftime(
                    "%Y-%m-%d %H:%M:%S %Z"
                ),
            ),
            usage_limits=UsageLimits(request_limit=None),
        )
        logger.debug("Agent done.")

        logger.info("AGENT LOGS")
        tool_calls: dict[str, ToolCallPart] = {}
        for message in result.new_messages():
            for part in message.parts:
                if isinstance(part, TextPart):
                    logger.info("[Thought] %s", part.content)
                elif isinstance(part, ToolCallPart):
                    tool_calls[part.tool_call_id] = part
                elif isinstance(part, ToolReturnPart):
                    args = tool_calls[part.tool_call_id].args
                    logger.info(
                        "[Tool] %s called with %s returned %s",
                        part.tool_name,
                        args,
                        part.model_response_str(),
                    )
                elif isinstance(part, RetryPromptPart) and part.tool_name:
                    args = tool_calls[part.tool_call_id].args
                    logger.warning(
                        "[Tool] %s called with %s failed, retry recommended: %s",
                        part.tool_name,
                        args,
                        part.model_response(),
                    )
