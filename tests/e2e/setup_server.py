import asyncio
import os
import time
from dataclasses import dataclass
from pathlib import Path

import discord
import dotenv

from tests.e2e.discord_identity import BotIdentity, fetch_bot_identity

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
GUILD_NAME = "vercade-e2e"
POLL_INTERVAL_SECONDS = 2.0
POLL_TIMEOUT_SECONDS = 600.0

VERCADE_PERMISSIONS = discord.Permissions(
    view_channel=True,
    send_messages=True,
    read_message_history=True,
)
# The user stub creates and deletes a fresh channel for every test run.
USER_STUB_PERMISSIONS = discord.Permissions(
    view_channel=True,
    send_messages=True,
    read_message_history=True,
    manage_channels=True,
)


@dataclass(frozen=True)
class _Bot:
    client: discord.Client
    identity: BotIdentity
    application_id: int
    required_permissions: discord.Permissions

    @property
    def invite_url(self) -> str:
        return (
            "https://discord.com/oauth2/authorize"
            f"?client_id={self.application_id}&scope=bot"
            f"&permissions={self.required_permissions.value}"
        )


def _permission_names(value: int) -> list[str]:
    names: list[str] = []
    seen_flags: set[int] = set()
    for name, flag in discord.Permissions.VALID_FLAGS.items():
        if value & flag and flag not in seen_flags:
            names.append(name.replace("_", " "))
            seen_flags.add(flag)
    return names


async def _ensure_ready(bot: _Bot, guild_id: int) -> discord.Guild:
    invite_url = f"{bot.invite_url}&guild_id={guild_id}&disable_guild_select=true"
    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
    last_problem: str | None = None
    while time.monotonic() < deadline:
        try:
            guild = await bot.client.fetch_guild(guild_id)
            member = await guild.fetch_member(bot.identity.id)
        except (discord.NotFound, discord.Forbidden):
            problem = f"{bot.identity.name} is not in the test server"
        else:
            missing = bot.required_permissions.value & ~member.guild_permissions.value
            if not missing:
                if last_problem is None:
                    print(f"{bot.identity.name} is already in the test server.")
                else:
                    print(f"{bot.identity.name} is set up and ready.")
                return guild
            names = ", ".join(_permission_names(missing))
            problem = f"{bot.identity.name} is missing permissions: {names}"
        if problem != last_problem:
            last_problem = problem
            print(
                f"{problem}. Open the invite link below to fix it "
                f"(server pre-selected):\n{invite_url}"
            )
            print(
                f"Waiting for {bot.identity.name} "
                "(polling every 2s, up to 10 minutes)..."
            )
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
    raise SystemExit(
        f"{bot.identity.name} was not set up within 10 minutes. "
        "Open the invite URL above, authorize the bot, and re-run this script."
    )


async def main() -> None:
    dotenv.load_dotenv(ENV_PATH)
    missing = [
        name
        for name in ("DISCORD_TOKEN", "VERCADE_E2E_USER_STUB_TOKEN")
        if not os.getenv(name)
    ]
    if missing:
        raise SystemExit(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Set them in .env at the repo root (see template.env)."
        )

    raw_guild_id = os.getenv("VERCADE_E2E_GUILD_ID", "").strip()
    if not raw_guild_id.isdigit():
        raise SystemExit(
            "VERCADE_E2E_GUILD_ID must be set to a numeric server ID in "
            f"{ENV_PATH}. Discord no longer allows bots to create servers, "
            "so create one manually in the Discord app "
            f"(suggested name: {GUILD_NAME}), then copy its ID "
            "(Developer Mode > right-click the server > Copy Server ID)."
        )
    guild_id = int(raw_guild_id)

    stub_client = discord.Client(intents=discord.Intents.none())
    vercade_client = discord.Client(intents=discord.Intents.none())
    try:
        await stub_client.login(os.environ["VERCADE_E2E_USER_STUB_TOKEN"])
        await vercade_client.login(os.environ["DISCORD_TOKEN"])

        stub = _Bot(
            client=stub_client,
            identity=await fetch_bot_identity(
                os.environ["VERCADE_E2E_USER_STUB_TOKEN"]
            ),
            application_id=(await stub_client.application_info()).id,
            required_permissions=USER_STUB_PERMISSIONS,
        )
        vercade = _Bot(
            client=vercade_client,
            identity=await fetch_bot_identity(os.environ["DISCORD_TOKEN"]),
            application_id=(await vercade_client.application_info()).id,
            required_permissions=VERCADE_PERMISSIONS,
        )

        guild = await _ensure_ready(stub, guild_id)
        await _ensure_ready(vercade, guild_id)
        print(
            f"Setup complete: {vercade.identity.name} and "
            f"{stub.identity.name} are both members of "
            f"{guild.name!r} (id {guild_id}) with the permissions they need."
        )
    finally:
        await stub_client.close()
        await vercade_client.close()


def cli() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    cli()
