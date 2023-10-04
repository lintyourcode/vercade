import os

import dotenv

from friendbot.discord import DiscordClient
from friendbot.friend import Friend


def main():
    dotenv.load_dotenv()

    if not os.getenv("FRIENDBOT_IDENTITY"):
        raise ValueError("FRIENDBOT_IDENTITY environment variable must be set")
    identity = os.getenv("FRIENDBOT_IDENTITY")

    if not os.getenv("DISCORD_TOKEN"):
        raise ValueError("DISCORD_TOKEN environment variable must be set")
    discord_token = os.getenv("DISCORD_TOKEN")

    friend = Friend(identity=identity)
    proctor = DiscordClient(friend=friend)
    proctor.run(discord_token)
