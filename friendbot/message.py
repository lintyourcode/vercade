from __future__ import annotations


class MessageContext:
    def __init__(self, social_media: SocialMedia, server: str, channel: str) -> None:
        self.social_media = social_media
        self.server = server
        self.channel = channel


class Message:
    def __init__(self, content: str, author: str = None) -> None:
        if not content:
            raise ValueError("content must be a non-empty string")

        self._content = content
        self._author = author

    @property
    def content(self) -> str:
        return self._content

    @property
    def author(self) -> str:
        return self._author

    def __str__(self) -> str:
        return f"{self.author}: {self.content}"
