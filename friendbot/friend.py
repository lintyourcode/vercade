import asyncio
from functools import partial
from datetime import datetime
import json
import os
import re
from typing import Any, Dict, List, Optional, Union

from litellm import ChatCompletionMessageToolCall, completion, embedding, moderation
import pinecone

from friendbot.social_media import Message, MessageContext, SocialMedia


_USER_MESSAGE_TEMPLATE = "You just received a message in the Discord server {server}'s channel #{channel}. You may use any tools available to you, or do nothing at all."


class Friend:
    """
    Social media AI agent.
    """

    def __init__(
        self,
        identity: str,
        pinecone_index: pinecone.Index,
        moderate_messages: bool = True,
        llm: Optional[str] = None,
        web_llm: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ) -> None:
        """
        Initialize the agent.

        Args:
            identity: Natural language description of the agent.
            pinecone_index: Pinecone index for storing memories.
            moderate_messages: Whether to ignore messages that are flagged as
                inappropriate.
            llm: LLM to use for the agent.
            web_llm: LLM to use to search the web.
            embedding_model: Embedding model to use for the agent.
        """

        if not identity:
            raise ValueError("identity must be a non-empty string")

        if os.getenv("OPENAI_API_KEY") is None:
            raise ValueError("OPENAI_API_KEY environment variable must be set")

        self._identity = identity
        self._pinecone_index = pinecone_index
        self._moderate_messages = moderate_messages
        self._llm = llm or os.getenv("LLM")
        self._embedding_model = embedding_model or os.getenv("EMBEDDING_MODEL")
        self._web_llm = web_llm or os.getenv("FRIENDBOT_WEB_LLM")

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

    def _search_web(self, input: str) -> str:
        input = self._parse_input(input)
        query = input.get("query")
        if not query:
            return "query must be a non-empty string"
        return (
            completion(
                model=self._web_llm,
                api_key=os.getenv("PERPLEXITY_API_KEY"),
                api_base="https://api.perplexity.ai",
                temperature=0.1,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that searches the web for information.",
                    },
                    {
                        "role": "user",
                        "content": query,
                    },
                ],
            )
            .choices[0]
            .message.content
        )

    def _clean_channel(self, channel: str) -> str:
        if channel.startswith("#"):
            channel = channel[1:]
        return channel

    async def _read_messages(self, input: Any, social_media: SocialMedia) -> str:
        input = self._parse_input(input)
        server = input["server"]
        channel = self._clean_channel(input["channel"])
        try:
            limit = int(input.get("limit", 20))
        except ValueError:
            return "limit must be an integer"
        context = MessageContext(social_media, server, channel)
        try:
            conversation = await social_media.messages(context, limit=limit)
        except Exception as e:
            return f"Failed to read messages: {e}"
        return json.dumps(
            [
                {
                    "author": self._format_author(message.author),
                    "content": message.content,
                    "embeds": [embed.url for embed in message.embeds],
                    "reactions": [
                        {
                            "emoji": reaction.emoji,
                            "users": reaction.users,
                        }
                        for reaction in message.reactions
                    ],
                }
                for message in conversation
                if not self._moderate_messages
                or not moderation(input=message.content).results[0].flagged
            ]
        )

    async def _send_message(self, input: str, social_media: SocialMedia) -> str:
        input = self._parse_input(input)
        content = input["content"]
        server = input.get("server")
        if not server:
            return "server must be a non-empty string"
        channel = input.get("channel")
        if not channel:
            return "channel must be a non-empty string"
        channel = self._clean_channel(channel)
        if not content:
            return "content must be a non-empty string"
        message = Message(content=content, author=self._identity)
        try:
            await social_media.send(
                MessageContext(social_media, server, channel), message
            )
        except Exception as e:
            return f"Failed to send message: {e}"
        return "Message sent"

    async def _react(self, input: str, social_media: SocialMedia) -> str:
        input = self._parse_input(input)
        server = input["server"]
        channel = self._clean_channel(input["channel"])
        message = Message(
            content=input["message"]["content"], author=input["message"]["author"]
        )
        emoji = input["emoji"]
        if not emoji:
            return "emoji must be a non-empty string"
        try:
            await social_media.react(
                MessageContext(social_media, server, channel), message, emoji
            )
        except Exception as e:
            return f"Failed to react to message: {e}"
        return "Reaction added"

    def _save_memory(self, input: str) -> str:
        input = self._parse_input(input)
        memory = input["content"]
        if not memory:
            return "memory must be a non-empty string"
        id = re.sub(r"[^0-9a-zA-Z]+", "-", memory).replace("-", "").lower()
        metadata = {
            "content": memory,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z"),
        }
        vector = (
            embedding(model=self._embedding_model, input=memory)
            .get("data")[0]
            .get("embedding")
        )

        existing_memories = self._pinecone_index.query(vector=vector, top_k=1)[
            "matches"
        ]
        if existing_memories and existing_memories[0]["score"] > 0.7:
            return "Memory already exists"
        self._pinecone_index.upsert(vectors=[(id, vector, metadata)])
        return "Memory saved"

    def _get_memories(self, input: str) -> str:
        input = self._parse_input(input)
        query = input.get("query", "")
        if not query:
            return "query must be a non-empty string"
        top_k = input.get("top_k", 10)
        vector = (
            embedding(model=self._embedding_model, input=query)
            .get("data")[0]
            .get("embedding")
        )
        return json.dumps(
            {
                "memories": [
                    memory.metadata
                    for memory in self._pinecone_index.query(
                        vector=vector, top_k=top_k, include_metadata=True
                    )["matches"]
                ]
            }
        )

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
                    "name": "search_web",
                    "description": "Search the web for information. Useful for finding up-to-date context or niche information.",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
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
                    "name": "react",
                    "description": "React to a Discord message with an emoji",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "server": {
                                "type": "string",
                                "description": "The name of the Discord server to react in",
                            },
                            "channel": {
                                "type": "string",
                                "description": "The name of the Discord channel to react in",
                            },
                            "message": {
                                "type": "object",
                                "properties": {
                                    "content": {
                                        "type": "string",
                                        "description": "The content of the message to react to",
                                    },
                                    "author": {
                                        "type": "string",
                                        "description": "The author of the message to react to",
                                    },
                                },
                                "required": ["content", "author"],
                            },
                            "emoji": {
                                "type": "string",
                                "description": "The emoji to react with",
                            },
                        },
                        "required": ["server", "channel", "message", "emoji"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_messages",
                    "description": "Read the most recent messages from the current Discord channel. Useful for getting context for the current conversation.",
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
                            "limit": {
                                "type": "integer",
                                "description": "The number of messages to read",
                                "default": 20,
                            },
                        },
                        "required": ["server", "channel"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_memories",
                    "description": "Search your memory vector database for memories related to a piece of text. For each person, topic, or idea in every Discord message you receive, search for any memories you've saved about them.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The word, phrase, or sentence to search for, based on semantic similarity",
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "The max number of memories to return",
                                "default": 10,
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "save_memory",
                    "description": "Save a specific detail to your memory vector database. Make sure to save every detail you notice about other people and your interactions with them, along with anything you say about yourself.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "One or more sentences describing a specific detail to save, including any relevant context.",
                            }
                        },
                        "required": ["content"],
                    },
                },
            },
        ]

    async def _run_tool(
        self, tool_call: ChatCompletionMessageToolCall, functions: Dict[str, Any]
    ) -> None:
        if tool_call.function.name not in functions:
            raise ValueError(f"Unknown tool: {tool_call.function.name}")

        print(
            f"Calling tool {tool_call.function.name} with {tool_call.function.arguments}"
        )
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

    async def __call__(self, context: MessageContext) -> None:
        """
        Respond to recent messages in the provided conversation.

        Args:
            context: Conversation context.
        """

        functions = {
            "date_and_time": self._date_and_time,
            "search_web": self._search_web,
            "send_message": partial(
                self._send_message, social_media=context.social_media
            ),
            "react": partial(self._react, social_media=context.social_media),
            "read_messages": partial(
                self._read_messages, social_media=context.social_media
            ),
            "get_memories": self._get_memories,
            "save_memory": self._save_memory,
        }

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
