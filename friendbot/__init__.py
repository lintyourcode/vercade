import logging
import os
import json
import re
import fastmcp

from discord import CustomActivity
import dotenv
import nest_asyncio

from friendbot.agent import Agent
from friendbot.discord import DiscordClient
from friendbot.trigger import Trigger


def _parse_schedule_interval_seconds(value: str | None) -> float | None:
    """
    Parse FRIENDBOT_SCHEDULE_INTERVAL into seconds.

    Supports raw seconds (e.g. "300"), or suffixed values like "15m", "2h", "45s".
    Disable scheduling with one of: "0", "off", "false", "disabled", "none", "no".
    Returns None to indicate disabled.
    """

    if value is None or value.strip() == "":
        return 60.0 * 60.0

    normalized = value.strip().lower()
    if normalized in {"0", "off", "false", "disabled", "none", "no"}:
        return None

    # Plain seconds
    try:
        return float(normalized)
    except ValueError:
        pass

    match = re.fullmatch(r"(\d+(?:\.\d*)?)([smh])", normalized)
    if not match:
        raise ValueError(
            "FRIENDBOT_SCHEDULE_INTERVAL must be a number of seconds or end with s/m/h (e.g. '300', '15m', '2h', or 'off')"
        )

    amount = float(match.group(1))
    unit = match.group(2)
    if unit == "s":
        return amount
    if unit == "m":
        return amount * 60.0
    if unit == "h":
        return amount * 60.0 * 60.0
    # Should never reach here due to regex
    raise ValueError("Invalid schedule interval unit")


async def main():
    dotenv.load_dotenv()
    nest_asyncio.apply()

    log_level = os.getenv("FRIENDBOT_LOG_LEVEL")
    if log_level:
        log_level = log_level.upper()
        if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError(
                "FRIENDBOT_LOG_LEVEL must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL"
            )
        logging.basicConfig(level=log_level)
    logging.getLogger("LiteLLM").setLevel(logging.WARNING)

    if not os.getenv("FRIENDBOT_NAME"):
        raise ValueError("FRIENDBOT_NAME environment variable must be set")
    name = os.getenv("FRIENDBOT_NAME")

    if not os.getenv("FRIENDBOT_IDENTITY"):
        raise ValueError("FRIENDBOT_IDENTITY environment variable must be set")
    identity = os.getenv("FRIENDBOT_IDENTITY")

    activity = os.getenv("FRIENDBOT_ACTIVITY")
    if activity:
        activity = CustomActivity(name=activity)

    if not os.getenv("DISCORD_TOKEN"):
        raise ValueError("DISCORD_TOKEN environment variable must be set")
    discord_token = os.getenv("DISCORD_TOKEN")

    if not os.getenv("FRIENDBOT_LLM"):
        raise ValueError("FRIENDBOT_LLM environment variable must be set")
    llm = os.getenv("FRIENDBOT_LLM")

    temperature = os.getenv("FRIENDBOT_LLM_TEMPERATURE")
    temperature = float(temperature) if temperature else None

    if os.getenv("MCP_PATH"):
        with open(os.getenv("MCP_PATH")) as f:
            mcp_client = fastmcp.Client(json.load(f))
    else:
        mcp_client = None

    schedule_interval_seconds = _parse_schedule_interval_seconds(
        os.getenv("FRIENDBOT_SCHEDULE_INTERVAL")
    )

    async with mcp_client:
        # TODO: Rename `friend` to `agent`
        friend = Agent(
            name=name,
            identity=identity,
            llm=llm,
            temperature=temperature,
            reasoning_effort=os.getenv("FRIENDBOT_LLM_REASONING_EFFORT"),
            mcp_client=mcp_client,
        )
        # TODO: Rename `proctor` to `discord`
        proctor = DiscordClient(activity=activity, friend=friend)
        Trigger(proctor, friend, schedule_interval_seconds=schedule_interval_seconds)
        proctor.run(discord_token)
