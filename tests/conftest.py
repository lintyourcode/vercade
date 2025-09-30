from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from vercade.social_media import Message, MessageContext, SocialMedia


class _McpBlock:
    def __init__(self, text: str) -> None:
        self.text = text

    def model_dump(self) -> dict[str, Any]:
        return {
            "type": "text",
            "text": self.text,
        }


class _McpResult:
    def __init__(self, content: list[_McpBlock], is_error: bool = False) -> None:
        self.content = content
        self.is_error = is_error


class _McpTool:
    def __init__(
        self, name: str, description: str, input_schema: dict[str, Any]
    ) -> None:
        self.name = name
        self.description = description
        self.inputSchema = input_schema


# TODO: Remove social media instance and hardcode tool responses to reduce scope creep
class LocalDiscordMcp:
    """
    Minimal in-process MCP client that exposes Discord-like tools backed by a SocialMedia instance.
    """

    def __init__(self, social: SocialMedia, bot_name: str) -> None:
        self._social = social
        self._bot_name = bot_name
        self._tools = [
            _McpTool(
                name="list_servers",
                description="Return the list of Discord servers you have access to.",
                input_schema={"type": "object", "properties": {}},
            ),
            _McpTool(
                name="list_channels",
                description="Return the list of channel names in a given Discord server.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "server": {"type": "string", "description": "Server name"}
                    },
                    "required": ["server"],
                },
            ),
            _McpTool(
                name="get_messages",
                description="Return recent messages from a server/channel. Use this to see what the user said.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "server": {"type": "string"},
                        "channel": {"type": "string"},
                        "limit": {"type": "integer", "default": 50},
                    },
                    "required": ["server", "channel"],
                },
            ),
            _McpTool(
                name="send_message",
                description="Send a message to a server/channel. Use this to respond to the user.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "server": {"type": "string"},
                        "channel": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["server", "channel", "content"],
                },
            ),
            _McpTool(
                name="react",
                description="React to a specific message with an emoji. Identify the message by exact content.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "server": {"type": "string"},
                        "channel": {"type": "string"},
                        "message_content": {"type": "string"},
                        "emoji": {"type": "string"},
                    },
                    "required": ["server", "channel", "message_content", "emoji"],
                },
            ),
        ]

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def list_tools(self) -> list[_McpTool]:
        return self._tools

    async def call_tool(self, name: str, args: dict[str, Any]) -> _McpResult:
        if name == "list_servers":
            # Fake implementation: return a static set of servers
            servers = ["Test Server", "Test Server 2"]
            return _McpResult([_McpBlock("\n".join(servers))])
        if name == "list_channels":
            # Fake implementation: return a static set of channels for any server
            channels = ["general", "spam"]
            return _McpResult([_McpBlock("\n".join(channels))])
        if name == "get_messages":
            ctx = MessageContext(self._social, args["server"], args["channel"])  # type: ignore[index]
            msgs = await self._social.messages(ctx, limit=int(args.get("limit", 50)))
            # Provide a simple text dump so the model can read it
            dump = "\n\n".join(f"{m.author}: {m.content}" for m in msgs)
            return _McpResult([_McpBlock(dump)])
        if name == "send_message":
            ctx = MessageContext(self._social, args["server"], args["channel"])  # type: ignore[index]
            await self._social.send(
                ctx,
                Message(
                    content=args["content"],
                    author=self._bot_name,
                    created_at=datetime.now(tz=timezone.utc),
                ),
            )  # type: ignore[index]
            return _McpResult([_McpBlock("ok")])
        if name == "react":
            ctx = MessageContext(self._social, args["server"], args["channel"])  # type: ignore[index]
            msgs = await self._social.messages(ctx, limit=50)
            target = next(
                (m for m in msgs if m.content == args["message_content"]), None
            )  # type: ignore[index]
            if target is None:
                return _McpResult([_McpBlock("message not found")], is_error=True)
            await self._social.react(ctx, target, args["emoji"])  # type: ignore[index]
            return _McpResult([_McpBlock("ok")])
        return _McpResult([_McpBlock(f"unknown tool: {name}")], is_error=True)
