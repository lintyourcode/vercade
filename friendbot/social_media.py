from friendbot.message import Message, MessageContext


class SocialMedia:
    async def send(self, context: MessageContext, message: Message) -> None:
        """
        Send a message to the social media platform.
        """

        raise NotImplementedError("Subclasses must implement this method")
