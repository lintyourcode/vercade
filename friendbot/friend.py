import os

from langchain.agents import AgentExecutor, ZeroShotAgent
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationSummaryMemory
from langchain.tools import GoogleSerperResults


_PREFIX = """{identity} Have a conversation with a human, answering the following questions as best you can. You have access to the following tools:"""
_SUFFIX = """Begin!"

{chat_history}
Question: {input}
{agent_scratchpad}"""


class Friend:
    def __init__(self, identity: str) -> None:
        if not identity:
            raise ValueError("identity must be a non-empty string")

        if os.getenv("SERPER_API_KEY") is None:
            raise ValueError("SERPER_API_KEY environment variable must be set")

        api_key = os.getenv("SERPER_API_KEY")
        tools = [GoogleSerperResults()]
        prompt = ZeroShotAgent.create_prompt(
            tools,
            prefix=_PREFIX,
            suffix=_SUFFIX,
            input_variables=["identity", "input", "chat_history", "agent_scratchpad"],
        ).partial(identity=identity)
        llm_chain = LLMChain(llm=ChatOpenAI(model="gpt-4"), prompt=prompt)
        agent = ZeroShotAgent(llm_chain=llm_chain, tools=tools, verbose=True)
        memory = ConversationSummaryMemory(
            llm=ChatOpenAI(), memory_key="chat_history", verbose=True
        )
        self._agent_chain = AgentExecutor.from_agent_and_tools(
            agent=agent,
            tools=tools,
            memory=memory,
            verbose=True,
        )

    def __call__(self, user_message: str) -> str:
        return self._agent_chain.run(input=user_message)
