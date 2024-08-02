import asyncio
from collections import defaultdict
from functools import partial
from datetime import datetime
import json
import os
from typing import Any, Dict, List, Optional, Union

from litellm import ChatCompletionMessageToolCall, completion, moderation

from friendbot.message import Message, MessageContext
from friendbot.social_media import SocialMedia


_USER_MESSAGE_TEMPLATE = "You just received a message in the Discord server {server}'s channel #{channel}. You may use any tools available to you, if you would like to respond to the message."


class Friend:
    def __init__(self, identity: str, llm: Optional[str] = None) -> None:
        if not identity:
            raise ValueError("identity must be a non-empty string")

        if os.getenv("OPENAI_API_KEY") is None:
            raise ValueError("OPENAI_API_KEY environment variable must be set")

        self._identity = identity
        self._conversations = defaultdict(lambda: defaultdict(list))
        self._llm = llm or os.getenv("LLM")

    def _format_author(self, author: str) -> str:
        if author == self._identity:
            return "You"
        else:
            return author

    def _parse_input(self, input: str) -> Dict[str, Any]:
        try:
            return json.loads(input)
        except json.JSONDecodeError:
            return {"content": input}

    def _date_and_time(self, input: Union[str, Dict[str, Any]]) -> str:
        if self._parse_input(input):
            return "Unexpected argument: {input}"
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")

    def _clean_channel(self, channel: str) -> str:
        if channel.startswith("#"):
            channel = channel[1:]
        return channel

    def _read_messages(self, input: Any) -> str:
        input = self._parse_input(input)
        server = input["server"]
        channel = self._clean_channel(input["channel"])
        if (
            server not in self._conversations
            or channel not in self._conversations[server]
        ):
            return "No conversation found"
        conversation = self._conversations[server][channel]
        if len(conversation) > 20:
            conversation = conversation[-20:]
            self._conversations[server][channel] = conversation
        return json.dumps(
            [
                {
                    "author": self._format_author(message.author),
                    "content": message.content,
                }
                for message in conversation
                if not moderation(input=message.content).results[0].flagged
            ]
        )

    async def _send_message(self, input: str, social_media: SocialMedia) -> str:
        input = self._parse_input(input)
        content = input["content"]
        server = input["server"]
        channel = self._clean_channel(input["channel"])
        if not content:
            return "content must be a non-empty string"
        message = Message(content=content, author=self._identity)
        try:
            await social_media.send(
                MessageContext(social_media, server, channel), message
            )
        except Exception as e:
            return f"Failed to send message: {e}"
        self._conversations[server][channel].append(message)
        return "Message sent"

    @property
    def _tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "date_and_time",
                    "description": "Get the current date and time",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "send_message",
                    "description": "Send a message in the current Discord channel. This is the only way to communicate with the user.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "server": {
                                "type": "string",
                                "description": "The name of the Discord server to send the message in",
                            },
                            "channel": {
                                "type": "string",
                                "description": "The name of the Discord channel to send the message in",
                            },
                            "content": {
                                "type": "string",
                                "description": "The markdown content of the message",
                            },
                        },
                        "required": ["server", "channel", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_messages",
                    "description": "Read the 20 most recent messages from the current Discord channel",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "server": {
                                "type": "string",
                                "description": "The name of the Discord server to read the messages from",
                            },
                            "channel": {
                                "type": "string",
                                "description": "The name of the Discord channel to read the messages from",
                            },
                        },
                        "required": ["server", "channel"],
                    },
                },
            },
        ]

    async def _run_tool(
        self, tool_call: ChatCompletionMessageToolCall, functions: Dict[str, Any]
    ) -> None:
        if tool_call.function.name not in functions:
            raise ValueError(f"Unknown tool: {tool_call.name}")

        function = functions[tool_call.function.name]
        if asyncio.iscoroutinefunction(function):
            result = await function(tool_call.function.arguments)
        else:
            result = function(tool_call.function.arguments)
        print(
            f"Tool {tool_call.function.name} called with {tool_call.function.arguments} returned {result}"
        )
        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_call.function.name,
            "content": result,
        }

    async def __call__(self, context: MessageContext, message: Message) -> None:
        """
        Perform action(s) in response to a message.

        Args:
            context: The context where the message was received.
            message: The message received.
        """

        if not message:
            raise ValueError("message cannot be None")

        functions = {
            "date_and_time": self._date_and_time,
            "send_message": partial(
                self._send_message, social_media=context.social_media
            ),
            "read_messages": self._read_messages,
        }

        conversation = self._conversations[context.server][context.channel]
        conversation.append(message)

        # Conversation with LLM
        chat_history = [
            {
                "role": "system",
                "content": self._identity,
            },
            {
                "role": "user",
                "content": _USER_MESSAGE_TEMPLATE.format(
                    server=context.server, channel=context.channel
                ),
            },
        ]
        ran_tools = False
        while True:
            response = (
                completion(
                    model=self._llm,
                    temperature=0.9,
                    messages=chat_history,
                    tools=self._tools,
                )
                .choices[0]
                .message
            )
            print(f"Thought: {response.content}")
            if not response.tool_calls:
                if not ran_tools:
                    raise ValueError(f"No tools were called\n\n{response.content}")
                break
            tool_results = await asyncio.gather(
                *[
                    self._run_tool(tool_call, functions)
                    for tool_call in response.tool_calls
                ]
            )
            chat_history += [
                response,
                *tool_results,
            ]
            ran_tools = True
