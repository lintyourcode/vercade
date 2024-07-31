from datetime import datetime
import json
import os
from typing import Any, Dict, List, Optional, Union

from litellm import ChatCompletionMessageToolCall, completion, moderation


_USER_MESSAGE = (
    "You just received a message in a Discord channel. How would you like to respond?"
)


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


class Action:
    def __init__(self, type: str, **kwargs) -> None:
        self._arguments = {**kwargs, "type": type}

    def __getattr__(self, name: str) -> Any:
        return self._arguments[name]

    def __getitem__(self, name: str) -> Any:
        return self._arguments[name]

    def __str__(self) -> str:
        return json.dumps(self._arguments)


class Friend:
    def __init__(self, identity: str, llm: Optional[str] = None) -> None:
        if not identity:
            raise ValueError("identity must be a non-empty string")

        if os.getenv("OPENAI_API_KEY") is None:
            raise ValueError("OPENAI_API_KEY environment variable must be set")

        self._identity = identity
        self._conversation = []
        self._llm = llm or os.getenv("LLM")
        self._functions = {
            "date_and_time": self._date_and_time,
            "send_message": self._send_message,
            "read_messages": self._read_messages,
        }

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

    def _read_messages(self, input: Any) -> str:
        if self._parse_input(input):
            return "Unexpected argument: {input}"
        if len(self._conversation) > 20:
            self._conversation = self._conversation[-20:]
        return json.dumps(
            [
                {
                    "author": self._format_author(message.author),
                    "content": message.content,
                }
                for message in self._conversation
                if not moderation(input=message.content).results[0].flagged
            ]
        )

    def _send_message(self, input: Union[str, Dict[str, Any]]) -> str:
        content = self._parse_input(input)["content"]
        if not content:
            return "content must be a non-empty string"
        message = Message(content=content, author=self._identity)
        self._conversation.append(message)

    @property
    def _tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "date_and_time",
                "description": "Get the current date and time",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            {
                "name": "send_message",
                "description": "Send a message in the current Discord channel",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The markdown content of the message",
                        },
                    },
                    "required": ["content"],
                },
            },
            {
                "name": "read_messages",
                "description": "Read the 20 most recent messages from the current Discord channel",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        ]

    def _run_tool(self, tool_call: ChatCompletionMessageToolCall) -> None:
        if tool_call.function.name not in self._functions:
            raise ValueError(f"Unknown tool: {tool_call.name}")

        result = self._functions[tool_call.function.name](tool_call.function.arguments)
        print(
            f"Tool {tool_call.function.name} called with {tool_call.function.arguments} returned {result}"
        )
        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_call.function.name,
            "content": result,
        }

    def __call__(self, message: Message) -> List[Message]:
        if not message:
            raise ValueError("message cannot be None")

        self._conversation.append(message)

        conversation_before = self._conversation[:]

        # Conversation with LLM
        chat_history = [
            {
                "role": "system",
                "content": self._identity,
            },
            {
                "role": "user",
                "content": _USER_MESSAGE,
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
            if not response.content:
                break
            tool_results = [
                self._run_tool(tool_call) for tool_call in response.tool_calls
            ]
            if not tool_results:
                if not ran_tools:
                    raise ValueError(f"No tools were called\n\n{response.content}")
                break
            chat_history += [
                response,
                *tool_results,
            ]
            ran_tools = True

        return self._conversation[len(conversation_before) :]
