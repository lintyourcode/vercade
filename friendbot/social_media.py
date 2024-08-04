from typing import Any, List

from friendbot.message import Message, MessageContext


class SocialMedia:
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
