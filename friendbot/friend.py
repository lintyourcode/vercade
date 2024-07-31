import json
import os
from typing import Any, Dict, List, Optional

import openai


_USER_MESSAGE_TEMPLATE = """
Please read the following conversation and respond in either of the following JSON formats:

- Use this format if you want to send a message in the conversation:
  {{
      "type": "Send Message",
      "message": {{message}}
  }}
- Use this format if you don't want to send a message in the conversation:
  {{
      "type": "None",
  }}

Conversation:
{conversation}
""".strip()


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
    def __init__(self, identity: str) -> None:
        if not identity:
            raise ValueError("identity must be a non-empty string")

        if os.getenv("OPENAI_API_KEY") is None:
            raise ValueError("OPENAI_API_KEY environment variable must be set")
        self.openai = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))

        self._identity = identity
        self._conversation = []

    def _format_author(self, author: str) -> str:
        if author == self._identity:
            return "You"
        else:
            return author

    @property
    def _system_message(self) -> Dict[str, str]:
        return {
            "role": "system",
            "content": self._identity,
        }

    @property
    def _user_message(self) -> Dict[str, str]:
        formatted_conversation = "\n".join(
            [f"{message.author}: {message.content}" for message in self._conversation]
        )
        content = _USER_MESSAGE_TEMPLATE.format(conversation=formatted_conversation)
        return {"role": "user", "content": content}

    @property
    def _messages(self) -> List[Dict[str, str]]:
        return [
            self._system_message,
            self._user_message,
        ]

    def _decide_action(self) -> Action:
        messages = self._messages
        print(f"Messages: {messages}")
        for message in messages:
            moderation = self.openai.moderations.create(input=message["content"])
            if moderation.results[0].flagged:
                print(f"Message flagged: {message} ({moderation})")
                return {
                    "type": "None",
                }

        completion = self.openai.chat.completions.create(
            model="gpt-4",
            temperature=0.9,
            presence_penalty=1.5,
            messages=messages,
        )
        raw_action = json.loads(completion.choices[0].message.content)
        return Action(**raw_action)

    def _perform_action(self, action: Action) -> Any:
        if action.type == "Send Message":
            message = Message(action["message"], author=self._identity)
            self._conversation.append(message)
            return message
        elif action.type == "None":
            pass
        else:
            raise ValueError(f"Unknown action type: {action.type}")

    def __call__(self, message: Message) -> Optional[Message]:
        if not message:
            raise ValueError("message cannot be None")

        self._conversation.append(message)
        action = self._decide_action()
        print(f"Action: {action}")
        if len(self._conversation) > 20:
            self._conversation = self._conversation[-20:]
        return self._perform_action(action)
