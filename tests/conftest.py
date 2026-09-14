from __future__ import annotations

from datetime import datetime, timezone

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from vercade.social_media import Message, MessageContext, SocialMedia


# TODO: Remove social media instance and hardcode tool responses to reduce scope creep
def local_discord_mcp(social: SocialMedia, bot_name: str) -> FastMCP:
    """
    In-process MCP server exposing Discord-like tools backed by a SocialMedia instance.
    """

    server = FastMCP("discord")

    @server.tool
    def list_servers() -> str:
        """Return the list of Discord servers you have access to."""
        # Fake implementation: return a static set of servers
        return "Test Server\nTest Server 2"

    @server.tool
    def list_channels(server: str) -> str:
        """Return the list of channel names in a given Discord server."""
        # Fake implementation: return a static set of channels for any server
        return "general\nspam"

    @server.tool
    async def get_messages(server: str, channel: str, limit: int = 50) -> str:
        """Return recent messages from a server/channel. Use this to see what the user said."""
        ctx = MessageContext(social, server, channel)
        msgs = await social.messages(ctx, limit=limit)
        # Provide a simple text dump so the model can read it
        return "\n\n".join(f"{m.author}: {m.content}" for m in msgs)

    @server.tool
    async def send_message(server: str, channel: str, content: str) -> str:
        """Send a message to a server/channel. Use this to respond to the user."""
        ctx = MessageContext(social, server, channel)
        await social.send(
            ctx,
            Message(
                content=content,
                author=bot_name,
                created_at=datetime.now(tz=timezone.utc),
            ),
        )
        return "ok"

    @server.tool
    async def react(server: str, channel: str, message_content: str, emoji: str) -> str:
        """React to a specific message with an emoji. Identify the message by exact content."""
        ctx = MessageContext(social, server, channel)
        msgs = await social.messages(ctx, limit=50)
        target = next((m for m in msgs if m.content == message_content), None)
        if target is None:
            raise ToolError("message not found")
        await social.react(ctx, target, emoji)
        return "ok"

    return server
