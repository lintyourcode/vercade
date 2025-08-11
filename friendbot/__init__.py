import logging
import os
import json
import fastmcp

from discord import CustomActivity
import dotenv
import nest_asyncio

from friendbot.agent import Agent
from friendbot.discord import DiscordClient
from friendbot.trigger import Trigger


async def main():
    dotenv.load_dotenv()
    nest_asyncio.apply()
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

    if not os.getenv("FRIENDBOT_FAST_LLM"):
        raise ValueError("FRIENDBOT_FAST_LLM environment variable must be set")
    fast_llm = os.getenv("FRIENDBOT_FAST_LLM")

    temperature = os.getenv("FRIENDBOT_LLM_TEMPERATURE")
    temperature = float(temperature) if temperature else None

    if os.getenv("MCP_PATH"):
        with open(os.getenv("MCP_PATH")) as f:
            mcp_client = fastmcp.Client(json.load(f))
    else:
        mcp_client = None

    async with mcp_client:
        # TODO: Rename `friend` to `agent`
        friend = Agent(
            name=name,
            identity=identity,
            llm=llm,
            fast_llm=fast_llm,
            temperature=temperature,
            reasoning_effort=os.getenv("FRIENDBOT_LLM_REASONING_EFFORT"),
            mcp_client=mcp_client,
        )
        # TODO: Rename `proctor` to `discord`
        proctor = DiscordClient(activity=activity, friend=friend)
        Trigger(proctor, friend)
        proctor.run(discord_token)
