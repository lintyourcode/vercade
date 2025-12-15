import logging
import os
import json
import re
import fastmcp

from discord import CustomActivity
import dotenv
import nest_asyncio

from vercade.agent import Agent
from vercade.discord import DiscordClient
from vercade.trigger import Trigger


# TODO(#22): Move outside of __init__.py
def _parse_schedule_interval_seconds(value: str | None) -> float | None:
    """
    Parse VERCADE_SCHEDULE_INTERVAL into seconds.

    Supports raw seconds (e.g. "300"), or suffixed values like "15m", "2h", "45s".
    Disable scheduling with one of: "0", "off", "false", "disabled", "none", "no".
    Returns None to indicate disabled.
    """

    if value is None or value.strip() == "":
        return None

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
            "VERCADE_SCHEDULE_INTERVAL must be a number of seconds or end with s/m/h (e.g. '300', '15m', '2h', or 'off')"
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

    log_level = os.getenv("VERCADE_LOG_LEVEL")
    if log_level:
        logging.basicConfig(level=log_level.upper())
    logging.getLogger("LiteLLM").setLevel(logging.WARNING)

    if not os.getenv("VERCADE_NAME"):
        raise ValueError("VERCADE_NAME environment variable must be set")
    name = os.getenv("VERCADE_NAME")

    if not os.getenv("VERCADE_IDENTITY"):
        raise ValueError("VERCADE_IDENTITY environment variable must be set")
    identity = os.getenv("VERCADE_IDENTITY")

    activity = os.getenv("VERCADE_ACTIVITY")
    if activity:
        activity = CustomActivity(name=activity)

    if not os.getenv("DISCORD_TOKEN"):
        raise ValueError("DISCORD_TOKEN environment variable must be set")
    discord_token = os.getenv("DISCORD_TOKEN")

    if not os.getenv("VERCADE_LLM"):
        raise ValueError("VERCADE_LLM environment variable must be set")
    llm = os.getenv("VERCADE_LLM")

    temperature = os.getenv("VERCADE_LLM_TEMPERATURE")
    temperature = float(temperature) if temperature else None

    # TODO(#22): Move mcp client initialization to own module
    if os.getenv("MCP_PATH"):
        with open(os.getenv("MCP_PATH")) as f:
            config = json.load(f)
        # Resolve MCP server environment variables
        for server in config["mcpServers"].values():
            for key, value in server.get("env", {}).items():
                if value.startswith("$"):
                    server["env"][key] = os.getenv(value.lstrip("$"))
        mcp_client = fastmcp.Client(config)
    else:
        mcp_client = None

    schedule_interval_seconds = _parse_schedule_interval_seconds(
        os.getenv("VERCADE_SCHEDULE_INTERVAL")
    )

    async with mcp_client:
        agent = Agent(
            name=name,
            identity=identity,
            llm=llm,
            temperature=temperature,
            reasoning_effort=os.getenv("VERCADE_LLM_REASONING_EFFORT"),
            mcp_client=mcp_client,
        )
        # TODO: Rename `proctor` to `discord`
        proctor = DiscordClient(activity=activity, friend=agent)
        Trigger(proctor, agent, schedule_interval_seconds=schedule_interval_seconds)
        proctor.run(discord_token)
