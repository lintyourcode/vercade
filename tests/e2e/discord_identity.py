from dataclasses import dataclass

import aiohttp

DISCORD_API_BASE = "https://discord.com/api/v10"


@dataclass(frozen=True)
class BotIdentity:
    id: int
    name: str


async def fetch_bot_identity(token: str) -> BotIdentity:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{DISCORD_API_BASE}/users/@me",
            headers={"Authorization": f"Bot {token}"},
        ) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"GET /users/@me failed with status {response.status}: "
                    f"{await response.text()}"
                )
            data = await response.json()
    return BotIdentity(id=int(data["id"]), name=data["username"])
