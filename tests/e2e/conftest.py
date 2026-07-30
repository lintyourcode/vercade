import asyncio
import json
import os
import queue
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from collections.abc import Coroutine, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple, TypeVar

import discord
import dotenv
import pytest

from tests.e2e.discord_identity import fetch_bot_identity

REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_ENV_VARS = (
    "DISCORD_TOKEN",
    "VERCADE_E2E_USER_STUB_TOKEN",
    "VERCADE_E2E_GUILD_ID",
    "OPENAI_API_KEY",
)
SETUP_COMMAND = "poetry run python -m tests.e2e.setup_server"

READY_LINE = "Connected"
READY_TIMEOUT_SECONDS = 120.0
CONNECT_TIMEOUT_SECONDS = 60.0
DISCORD_CALL_TIMEOUT_SECONDS = 30.0
STOP_TIMEOUT_SECONDS = 10.0

# discord-mcp-plus is used because it supports DISCORD_MCP_TOOLS: the tool
# allowlist keeps the agent under OpenAI's 128-tool API cap, which
# @quadslab.io/discord-mcp (139 tools, no allowlist support) exceeds.
MCP_CONFIG = {
    "mcpServers": {
        "discord": {
            "command": "npx",
            "args": ["-y", "discord-mcp-plus"],
            "env": {
                "DISCORD_TOKEN": "$DISCORD_TOKEN",
                "DISCORD_GUILD_ID": "$VERCADE_E2E_GUILD_ID",
                "DISCORD_MCP_TOOLS": "send_message,get_messages,list_channels",
            },
        }
    }
}

T = TypeVar("T")


class E2ESettings(NamedTuple):
    discord_token: str
    user_stub_token: str
    guild_id: int


@dataclass(frozen=True)
class E2EServer:
    guild_id: int
    vercade_user_id: int
    vercade_name: str


@dataclass(frozen=True)
class ReceivedMessage:
    author_id: int
    author_name: str
    channel_id: int
    content: str


@dataclass(frozen=True)
class E2EChannel:
    id: int
    name: str


class UserStub:
    def __init__(self, client: discord.Client, loop: asyncio.AbstractEventLoop) -> None:
        self._client = client
        self._loop = loop
        self._messages: queue.Queue[ReceivedMessage] = queue.Queue()

    @property
    def client(self) -> discord.Client:
        return self._client

    @property
    def stub_user_id(self) -> int:
        if self._client.user is None:
            raise RuntimeError("User stub client is not connected")
        return self._client.user.id

    def record(self, message: discord.Message) -> None:
        if message.author.id == self.stub_user_id:
            return
        self._messages.put(
            ReceivedMessage(
                author_id=message.author.id,
                author_name=message.author.name,
                channel_id=message.channel.id,
                content=message.content,
            )
        )

    def run(
        self,
        coro: Coroutine[Any, Any, T],
        timeout: float = DISCORD_CALL_TIMEOUT_SECONDS,
    ) -> T:
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result(
            timeout=timeout
        )

    def send_message(self, channel_id: int, content: str) -> None:
        async def _send() -> None:
            channel = self._client.get_channel(channel_id)
            if channel is None:
                channel = await self._client.fetch_channel(channel_id)
            if not isinstance(channel, discord.abc.Messageable):
                raise TypeError(f"Channel {channel_id} is not messageable")
            await channel.send(content)

        self.run(_send())

    def wait_for_message(
        self, author_id: int, channel_id: int, timeout: float
    ) -> ReceivedMessage | None:
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            try:
                message = self._messages.get(timeout=remaining)
            except queue.Empty:
                return None
            if message.author_id == author_id and message.channel_id == channel_id:
                return message


class VercadeProcess:
    def __init__(self, process: subprocess.Popen[str], output: deque[str]) -> None:
        self.process = process
        self.output = output

    def dump_output(self) -> str:
        return "\n".join(self.output)


@pytest.fixture(scope="session")
def e2e_settings() -> E2ESettings:
    dotenv.load_dotenv()
    missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]
    if shutil.which("npx") is None:
        missing.append("npx on PATH (install Node.js)")
    if missing:
        pytest.skip(
            "E2E prerequisites missing: "
            + ", ".join(missing)
            + f". Configure .env (see template.env) and run `{SETUP_COMMAND}`."
        )
    return E2ESettings(
        discord_token=os.environ["DISCORD_TOKEN"],
        user_stub_token=os.environ["VERCADE_E2E_USER_STUB_TOKEN"],
        guild_id=int(os.environ["VERCADE_E2E_GUILD_ID"]),
    )


@pytest.fixture(scope="session")
def e2e_server(e2e_settings: E2ESettings) -> E2EServer:
    vercade = asyncio.run(fetch_bot_identity(e2e_settings.discord_token))
    return E2EServer(
        guild_id=e2e_settings.guild_id,
        vercade_user_id=vercade.id,
        vercade_name=vercade.name,
    )


@pytest.fixture(scope="session")
def user_stub(e2e_settings: E2ESettings, e2e_server: E2EServer) -> Iterator[UserStub]:
    intents = discord.Intents(guilds=True, guild_messages=True, message_content=True)
    client = discord.Client(intents=intents)
    loop = asyncio.new_event_loop()
    ready = threading.Event()
    start_errors: list[BaseException] = []

    stub = UserStub(client, loop)

    @client.event
    async def on_ready() -> None:
        ready.set()

    @client.event
    async def on_message(message: discord.Message) -> None:
        stub.record(message)

    def _capture_start_error(task: asyncio.Task[None]) -> None:
        if not task.cancelled() and task.exception() is not None:
            start_errors.append(task.exception())

    def _run_loop() -> None:
        asyncio.set_event_loop(loop)
        task = loop.create_task(client.start(e2e_settings.user_stub_token))
        task.add_done_callback(_capture_start_error)
        loop.run_forever()

    thread = threading.Thread(target=_run_loop, name="e2e-user-stub", daemon=True)
    thread.start()

    def _shutdown() -> None:
        try:
            asyncio.run_coroutine_threadsafe(client.close(), loop).result(
                timeout=STOP_TIMEOUT_SECONDS
            )
        except (TimeoutError, RuntimeError, discord.DiscordException, OSError) as e:
            print(f"Ignoring error while closing user stub client: {e}")
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=STOP_TIMEOUT_SECONDS)

    deadline = time.monotonic() + CONNECT_TIMEOUT_SECONDS
    while time.monotonic() < deadline and not start_errors:
        if ready.wait(timeout=0.5):
            break

    if not ready.is_set():
        detail = f": {start_errors[0]}" if start_errors else ""
        _shutdown()
        pytest.fail(
            f"User stub bot did not connect to Discord within "
            f"{CONNECT_TIMEOUT_SECONDS:.0f}s{detail}"
        )

    guild = client.get_guild(e2e_server.guild_id)
    if guild is None:
        _shutdown()
        pytest.fail(
            f"User stub bot is not a member of guild {e2e_server.guild_id}. "
            f"Run `{SETUP_COMMAND}` to provision the test server."
        )

    try:
        stub.run(guild.fetch_member(e2e_server.vercade_user_id))
    except discord.NotFound:
        _shutdown()
        pytest.fail(
            "Vercade bot is not a member of the e2e guild. "
            f"Run `{SETUP_COMMAND}` and follow the invite instructions."
        )

    yield stub
    _shutdown()


@pytest.fixture(scope="session")
def e2e_channel(e2e_server: E2EServer, user_stub: UserStub) -> Iterator[E2EChannel]:
    guild = user_stub.client.get_guild(e2e_server.guild_id)
    if guild is None:
        pytest.fail(
            f"User stub bot lost access to guild {e2e_server.guild_id}; "
            f"re-run `{SETUP_COMMAND}`."
        )
    try:
        channel = user_stub.run(guild.create_text_channel(f"e2e-{int(time.time())}"))
    except discord.Forbidden:
        pytest.fail(
            "User stub bot cannot create channels in the e2e guild. "
            f"Re-run `{SETUP_COMMAND}` to grant it the required permissions."
        )
    yield E2EChannel(id=channel.id, name=channel.name)
    try:
        user_stub.run(channel.delete())
    except discord.NotFound:
        pass


def _await_ready(process: subprocess.Popen[str], lines: queue.Queue[str]) -> bool:
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        try:
            line = lines.get(timeout=min(remaining, 1.0))
        except queue.Empty:
            if process.poll() is not None:
                return False
            continue
        if line == READY_LINE:
            return True


@pytest.fixture(scope="session")
def vercade_process(
    e2e_server: E2EServer,
    e2e_channel: E2EChannel,
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[VercadeProcess]:
    config_path = tmp_path_factory.mktemp("e2e-mcp") / "config.json"
    config_path.write_text(json.dumps(MCP_CONFIG))

    env = os.environ.copy() | {
        "VERCADE_NAME": e2e_server.vercade_name,
        "VERCADE_IDENTITY": (
            f"You are {e2e_server.vercade_name}, a helpful and friendly chatbot."
        ),
        "VERCADE_SCHEDULE_INTERVAL": "disabled",
        "MCP_PATH": str(config_path),
        "VERCADE_LOG_LEVEL": "WARNING",
    }
    # -u: the child's stdout is a pipe, so Python would otherwise block-buffer
    # it and the "Connected" readiness line would never reach us.
    process = subprocess.Popen(
        [sys.executable, "-u", "-m", "vercade"],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    output: deque[str] = deque(maxlen=1000)
    lines: queue.Queue[str] = queue.Queue()

    def _reader() -> None:
        assert process.stdout is not None
        for raw_line in process.stdout:
            line = raw_line.rstrip()
            output.append(line)
            lines.put(line)

    reader = threading.Thread(target=_reader, name="vercade-output", daemon=True)
    reader.start()

    vercade = VercadeProcess(process, output)
    if not _await_ready(process, lines):
        process.kill()
        process.wait(timeout=STOP_TIMEOUT_SECONDS)
        reader.join(timeout=STOP_TIMEOUT_SECONDS)
        pytest.fail(
            f"Vercade subprocess did not print {READY_LINE!r} within "
            f"{READY_TIMEOUT_SECONDS:.0f}s (exit code {process.returncode}). "
            f"Captured output:\n{vercade.dump_output()}"
        )

    yield vercade

    process.terminate()
    try:
        process.wait(timeout=STOP_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=STOP_TIMEOUT_SECONDS)
    reader.join(timeout=STOP_TIMEOUT_SECONDS)
    if process.returncode not in (0, -signal.SIGTERM):
        print(
            f"Vercade subprocess exited with code {process.returncode} during "
            f"the test run. Captured output:\n{vercade.dump_output()}"
        )
