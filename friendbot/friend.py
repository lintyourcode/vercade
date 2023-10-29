from operator import itemgetter
import os
from typing import Optional

from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationSummaryBufferMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.runnable import RunnableLambda, RunnablePassthrough


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
        return f"[{self.author}] {self.content}"

    @classmethod
    def parse(cls, message: str) -> "Message":
        if not message:
            raise ValueError("message cannot be None")

        if message.startswith("["):
            author, content = message[1:].split("] ", 1)
            return cls(content=content, author=author)
        else:
            return cls(content=message)


class Friend:
    def __init__(self, identity: str) -> None:
        if not identity:
            raise ValueError("identity must be a non-empty string")

        if os.getenv("SERPER_API_KEY") is None:
            raise ValueError("SERPER_API_KEY environment variable must be set")

        if os.getenv("OPENAI_API_KEY") is None:
            raise ValueError("OPENAI_API_KEY environment variable must be set")

        accurate_model = ChatOpenAI(
            model="gpt-4", temperature=0.9, presence_penalty=1.5
        )
        fast_model = ChatOpenAI(
            model="gpt-3.5-turbo", temperature=0.9, presence_penalty=1.5
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "{identity}"),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{input}"),
            ]
        )
        self._memory = ConversationSummaryBufferMemory(
            llm=fast_model, return_messages=True
        )
        self._runnable = (
            {
                "input": RunnablePassthrough(),
                "history": RunnableLambda(self._memory.load_memory_variables)
                | itemgetter("history"),
            }
            | prompt.partial(identity=identity)
            | accurate_model
        )

    def __call__(self, message: Message) -> Optional[Message]:
        if not message:
            raise ValueError("message cannot be None")

        inputs = {"input": str(message)}
        response = self._runnable.invoke(inputs).content
        self._memory.save_context(inputs, {"output": response})
        return Message.parse(response)
