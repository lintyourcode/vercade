import logging
import os
import json
import fastmcp

import dotenv
import nest_asyncio
from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec

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

    if not os.getenv("PINECONE_API_KEY"):
        raise ValueError("PINECONE_API_KEY environment variable must be set")
    if not os.getenv("PINECONE_INDEX_NAME"):
        raise ValueError("PINECONE_INDEX_NAME environment variable must be set")
    index_name = os.getenv("PINECONE_INDEX_NAME")

    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable must be set")

    pinecone = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    if index_name not in [index.name for index in pinecone.list_indexes()]:
        pinecone.create_index(
            name=index_name,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(
                cloud=os.getenv("PINECONE_CLOUD", "aws"),
                region=os.getenv("PINECONE_REGION", "us-west-2"),
            ),
        )

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
            moderate_messages=os.getenv("FRIENDBOT_MODERATE_MESSAGES"),
            llm=llm,
            fast_llm=fast_llm,
            pinecone_index=pinecone.Index(index_name),
            embedding_model=os.getenv(
                "FRIENDBOT_EMBEDDING_MODEL", "text-embedding-3-small"
            ),
            temperature=temperature,
            reasoning_effort=os.getenv("FRIENDBOT_LLM_REASONING_EFFORT"),
            mcp_client=mcp_client,
        )
        # TODO: Rename `proctor` to `discord`
        proctor = DiscordClient(friend=friend)
        Trigger(proctor, friend)
        proctor.run(discord_token)
