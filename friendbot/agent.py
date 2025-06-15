import asyncio
from functools import partial
from datetime import datetime, timezone
import json
import re
from typing import Any, Dict, List, Optional

import fastmcp
from litellm import ChatCompletionMessageToolCall, completion, embedding
import pinecone

from friendbot.social_media import SocialMedia


# TODO: Make social media-specific
_USER_MESSAGE_TEMPLATE = "{event} The current date and time is {date_time}. You may use any tools available to you, or do nothing at all. The user cannot see your responses directly, so you must use the tools if you would like to respond to the user. Take your time and think carefully before responding."


class Agent:
    """
    Social media AI agent.
    """

    def __init__(
        self,
        name: str,
        identity: str,
        pinecone_index: pinecone.Index,
        llm: Optional[str] = None,
        fast_llm: Optional[str] = None,
        embedding_model: Optional[str] = None,
        temperature: Optional[float] = None,
        reasoning_effort: Optional[str] = None,
        mcp_client: Optional[fastmcp.Client] = None,
    ) -> None:
        """
        Initialize the agent.

        Args:
            name: Human-readable name of the agent.
            identity: Natural language description of the agent.
            pinecone_index: Pinecone index for storing memories.
            llm: LLM to use for the agent.
            fast_llm: Smaller, faster LLM to use for simple tasks.
            embedding_model: Embedding model to use for the agent.
            temperature: Temperature to use for the agent's LLM.
            reasoning_effort: LiteLLM reasoning effort for the agent (e.g. "low", "medium", "high").
            mcp_client: FastMCP client with user-provided tools.
        """

        if not identity:
            raise ValueError("identity must be a non-empty string")

        self.name = name
        self._identity = identity
        self._pinecone_index = pinecone_index
        self._llm = llm
        self._fast_llm = fast_llm
        self._embedding_model = embedding_model
        self._temperature = temperature
        self._mcp_client = mcp_client
        self._tools = None
        self._reasoning_effort = reasoning_effort

    async def _mcp_tool(self, tool_name: str, input: str) -> str:
        if not self._mcp_client:
            raise ValueError("No MCP client provided")
        input = self._parse_input(input)
        try:
            result = await self._mcp_client.call_tool(tool_name, input)
        except Exception as e:
            return f"Error calling tool {tool_name}: {e}"
        return "\n".join([block.text for block in result])

    def _parse_input(self, input: str) -> Dict[str, Any]:
        try:
            return json.loads(input)
        except json.JSONDecodeError:
            return {"content": input}

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
        if existing_memories and existing_memories[0]["score"] > 0.75:
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

    async def _get_tools(self) -> List[Dict[str, Any]]:
        if self._tools is not None:
            return self._tools
        self._tools = []
        if self._mcp_client:
            self._tools.extend(
                [
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.inputSchema,
                        },
                    }
                    for tool in await self._mcp_client.list_tools()
                ]
            )
        self._tools.extend(
            [
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
        )
        return self._tools

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

    async def __call__(self, event: str, social_media: SocialMedia) -> None:
        """
        Respond to recent messages in the provided conversation.

        Args:
            context: Conversation context.
        """

        functions = {}
        if self._mcp_client:
            functions.update(
                {
                    tool.name: partial(self._mcp_tool, tool.name)
                    for tool in await self._mcp_client.list_tools()
                }
            )
        functions.update(
            {
                "get_memories": self._get_memories,
                "save_memory": self._save_memory,
            }
        )

        # Conversation with LLM
        chat_history = [
            {
                "role": "system",
                "content": self._identity,
            },
            {
                "role": "user",
                "content": _USER_MESSAGE_TEMPLATE.format(
                    event=event,
                    date_time=datetime.now(tz=timezone.utc).strftime(
                        "%Y-%m-%d %H:%M:%S %Z"
                    ),
                ),
            },
        ]
        ran_tools = False
        while True:
            response = (
                completion(
                    model=self._llm,
                    temperature=self._temperature,
                    messages=chat_history,
                    tools=await self._get_tools(),
                    reasoning_effort=self._reasoning_effort,
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
