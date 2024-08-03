from typing import Any

from friendbot.message import Message, MessageContext


class SocialMedia:
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
