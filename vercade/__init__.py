import logging
import os

import dotenv
import pydantic_ai
from discord import CustomActivity
from discord.utils import setup_logging
from pydantic_ai.mcp import load_mcp_toolsets

from vercade.agent import Agent
from vercade.discord import DiscordClient
from vercade.skills import load_skills
from vercade.trigger import Trigger, parse_schedule_interval_seconds


async def main():
    dotenv.load_dotenv()
    # Vercade owns its output: skip Pydantic AI's one-time first-run banner.
    pydantic_ai.BANNER_ENABLED = False

    log_level = os.getenv("VERCADE_LOG_LEVEL")
    if log_level:
        logging.basicConfig(level=log_level.upper())
    # Equivalent to what discord.Client.run() does; we use Client.start() instead.
    setup_logging(root=False)

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

    if not os.getenv("MCP_PATH"):
        raise ValueError("MCP_PATH environment variable must be set")
    toolsets = load_mcp_toolsets(os.getenv("MCP_PATH"))

    skills = load_skills()

    schedule_interval_seconds = parse_schedule_interval_seconds(
        os.getenv("VERCADE_SCHEDULE_INTERVAL")
    )

    agent = Agent(
        identity=identity,
        llm=llm,
        temperature=temperature,
        reasoning_effort=os.getenv("VERCADE_LLM_REASONING_EFFORT") or None,
        toolsets=toolsets,
        capabilities=[skills] if skills else (),
    )
    # TODO: Rename `proctor` to `discord`
    proctor = DiscordClient(activity=activity, friend=agent)
    Trigger(proctor, agent, schedule_interval_seconds=schedule_interval_seconds)
    async with agent, proctor:
        await proctor.start(discord_token)
