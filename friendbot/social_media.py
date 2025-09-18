from __future__ import annotations
from typing import Awaitable, Callable, List
import re
from datetime import datetime


class Server:
    def __init__(self, name: str) -> None:
        self.name = name


class Channel:
    def __init__(self, id: int, name: str) -> None:
        self.id = id
        self.name = name


class Reaction:
    def __init__(self, emoji: str, users: List[str]) -> None:
        self.emoji = emoji
        self.users = users


class Embed:
    def __init__(self, url: str) -> None:
        self.url = url


class MessageContext:
    # TODO: Type `server` as `Server`
    def __init__(
        self, social_media: SocialMedia, server: str, channel: Channel
    ) -> None:
        self.social_media = social_media
        self.server = server
        self.channel = channel


class Message:
    _MENTION_REGEX = re.compile(r"@(\w+)")

    def __init__(
        self,
        content: str,
        author: str,
        created_at: datetime.datetime,
        embeds: List[Embed] = [],
        reactions: List[Reaction] = [],
    ) -> None:
        self._content = content
        self._author = author
        self._created_at = created_at
        self._mentions = self._MENTION_REGEX.findall(content)
        self._embeds = embeds
        self._reactions = reactions

    @property
    def content(self) -> str:
        return self._content

    @property
    def author(self) -> str:
        return self._author

    @property
    def created_at(self) -> datetime.datetime:
        return self._created_at

    @property
    def mentions(self) -> List[str]:
        return self._mentions

    @property
    def reactions(self) -> List[Reaction]:
        return self._reactions

    @property
    def embeds(self) -> List[Embed]:
        return self._embeds

    def __str__(self) -> str:
        return f"{self.author}: {self.content}"


class SocialMedia:
    def __init__(self) -> None:
        self.on_ready_callback: Callable[[], Awaitable[None]] | None = None
        self.on_message_callback: (
            Callable[[MessageContext, Message], Awaitable[None]] | None
        ) = None

    async def messages(
        self, context: MessageContext, limit: int = 100
    ) -> List[Message]:
        """
        Get the history of messages from the social media platform.

        Parameters:
            limit: The max number of messages to retrieve.

        Returns:
            A list of messages.
        """

        raise NotImplementedError("Subclasses must implement this method")

    async def send(self, context: MessageContext, message: Message) -> None:
        """
        Send a message to the social media platform.
        """

        raise NotImplementedError("Subclasses must implement this method")

    async def react(
        self, context: MessageContext, message: Message, reaction: str
    ) -> None:
        """
        React to a message on the social media platform.
        """

        raise NotImplementedError("Subclasses must implement this method")
