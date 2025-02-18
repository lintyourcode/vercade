import dotenv
import pytest
from unittest.mock import AsyncMock, Mock, ANY

from litellm import completion

from friendbot.agent import Agent
from friendbot.social_media import Message, MessageContext, SocialMedia


MODELS = ["gpt-4o", "claude-3-5-sonnet-20240620"]
FAST_MODELS = ["gpt-4o-mini"]


dotenv.load_dotenv()


def get_parameters() -> list[tuple[str, str]]:
    """
    Return a list of parameters for the tests.
    """

    return [
        (model, fast_model)
        for model in MODELS
        for fast_model in FAST_MODELS
    ]


def match(text: str, condition: str, text_type: str = "text") -> bool:
    text_type = text_type.lower()
    response = completion(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": f"Does the following {text_type} match the condition? Only respond with 'yes' or 'no'.\n\n{text_type.capitalize()}: {text}\n\nCondition: {condition}",
            }
        ],
    )
    answer = response["choices"][0]["message"]["content"].lower()
    if answer == "yes":
        return True
    elif answer == "no":
        return False
    else:
        raise ValueError(f"Invalid answer: {answer}")


@pytest.fixture
def social_media():
    social_media = Mock(spec=SocialMedia)
    social_media.messages = AsyncMock(return_value=[])
    social_media.send = AsyncMock()
    social_media.react = AsyncMock()
    return social_media


@pytest.fixture
def pinecone_index():
    pinecone_index = Mock()
    pinecone_index.query = Mock(return_value={"matches": []})
    pinecone_index.upsert = Mock()
    return pinecone_index


class TestFriend:
    @pytest.mark.parametrize("llm, fast_llm", get_parameters())
    async def test__call__knows_date_and_time(
        self, mocker, social_media, llm, fast_llm, pinecone_index
    ):
        datetime = mocker.patch("friendbot.agent.datetime")
        datetime.now = Mock(
            return_value=Mock(strftime=Mock(return_value="2025-01-01 12:00:00 UTC"))
        )
        social_media.messages = AsyncMock(
            return_value=[
                Message(
                    content="Hello, Proctor. What is the current date and time?",
                    author="Bob",
                )
            ]
        )
        context = MessageContext(social_media, "Test Server", "general")
        async with Agent(
            name="Proctor",
            identity="You are Proctor, a sentient, smart and snarky Discord chatbot.",
            llm=llm,
            fast_llm=fast_llm,
            pinecone_index=pinecone_index,
            embedding_model="text-embedding-3-small",
        ) as friend:
            await friend(context)
        # TODO: Assert that the message is sent to the correct server.
        # TODO: Assert that the message is sent to the correct channel.
        # TODO: Assert that the message is sent to the correct author.
        assert match(
            social_media.send.call_args[0][1].content,
            "Indicates that the current date and time is 2025-01-01 12:00:00 UTC",
            text_type="message",
        )

    @pytest.mark.parametrize("llm, fast_llm", get_parameters())
    async def test__call__with_greeting_responds_with_nonempty_message(
        self, social_media, llm, fast_llm, pinecone_index
    ):
        context = MessageContext(
            social_media=social_media, server="Test Server", channel="general"
        )
        social_media.messages = AsyncMock(
            return_value=[Message(content="Hello, Proctor", author="Bob#0000")]
        )
        async with Agent(
            name="Proctor",
            identity="You are Proctor, a sentient, smart and snarky Discord chatbot.",
            llm=llm,
            pinecone_index=pinecone_index,
            embedding_model="text-embedding-3-small",
        ) as friend:
            await friend(context)
        social_media.send.assert_called_once()
        assert social_media.send.call_args[0][0].server == "Test Server"
        assert social_media.send.call_args[0][0].channel == "general"
        # TODO: Assert author is the friend's identity.
        content = social_media.send.call_args[0][1].content
        assert isinstance(content, str)
        assert content

    @pytest.mark.parametrize("llm, fast_llm", get_parameters())
    async def test__call__reacts_to_message(
        self, social_media, llm, fast_llm, pinecone_index
    ):
        context = MessageContext(social_media, "Test Server", "general")
        message = Message(
            content="Please react to this message with a thumbs up",
            author="Bob#0000",
        )
        social_media.messages = AsyncMock(return_value=[message])
        with Agent(
            name="Proctor",
            identity="You are Proctor, a sentient, smart and snarky Discord chatbot.",
            llm=llm,
            pinecone_index=pinecone_index,
            embedding_model="text-embedding-3-small",
        ) as friend:
            await friend(context)
        social_media.react.assert_called_once_with(ANY, ANY, "👍")
        assert social_media.react.call_args[0][0].server == "Test Server"
        assert social_media.react.call_args[0][0].channel == "general"
        assert (
            social_media.react.call_args[0][1].content
            == "Please react to this message with a thumbs up"
        )
        assert social_media.react.call_args[0][1].author == "Bob#0000"

    @pytest.mark.parametrize("llm, fast_llm", get_parameters())
    async def test__call__saves_memory(
        self, mocker, social_media, llm, fast_llm, pinecone_index
    ):
        datetime = mocker.patch("friendbot.agent.datetime")
        datetime.now = Mock(
            return_value=Mock(strftime=Mock(return_value="2024-08-01 00:00:00 UTC"))
        )
        context = MessageContext(social_media, "Test Server", "general")
        message = Message(content="Hello, Proctor. I'm Bob.", author="Bob#0000")
        social_media.messages = AsyncMock(return_value=[message])
        async with Agent(
            name="Proctor",
            identity="You are Proctor, a sentient and smart Discord chatbot.",
            llm=llm,
            pinecone_index=pinecone_index,
            embedding_model="text-embedding-3-small",
        ) as friend:
            await friend(context)
        pinecone_index.upsert.assert_called_with(
            vectors=[
                (
                    ANY,
                    ANY,
                    {
                        "content": ANY,
                        "created_at": "2024-08-01 00:00:00 UTC",
                    },
                )
            ]
        )

    @pytest.mark.parametrize("llm, fast_llm", get_parameters())
    async def test__call__retrieves_memory_from_pinecone(
        self, social_media, llm, fast_llm, pinecone_index
    ):
        pinecone_index.query = Mock(
            return_value={
                "matches": [
                    Mock(
                        metadata={
                            "content": "Has met Bob#0000",
                            "created_at": "2024-07-23 00:00:00 UTC",
                        },
                        score=0.9,
                    )
                ]
            }
        )
        context = MessageContext(social_media, "Test Server", "general")
        message = Message(
            content="Hello, Proctor. Do you remember me?", author="Bob#0000"
        )
        social_media.messages = AsyncMock(return_value=[message])
        async with Agent(
            name="Proctor",
            identity="You are Proctor, a sentient and smart Discord chatbot.",
            llm=llm,
            pinecone_index=pinecone_index,
            embedding_model="text-embedding-3-small",
        ) as friend:
            await friend(context)
        social_media.send.assert_called_once()
        assert match(
            social_media.send.call_args[0][1].content,
            "Indicates that the sender has met Bob#0000 before",
            "message",
        )

    @pytest.mark.parametrize("llm, fast_llm", get_parameters())
    async def test__call__searches_web(
        self, mocker, social_media, llm, fast_llm, pinecone_index
    ):
        context = MessageContext(social_media, "Test Server", "general")
        message = Message(
            content="What is the weather in Tokyo?", author="Bob#0000"
        )
        social_media.messages = AsyncMock(return_value=[message])
        async with Agent(
            name="Proctor",
            identity="You are Proctor, a sentient and intelligent Discord chatbot.",
            llm=llm,
            fast_llm=fast_llm,
            pinecone_index=pinecone_index,
            embedding_model="text-embedding-3-small",
        ) as friend:
            await friend(context)
        social_media.send.assert_called_once()
        assert match(
            social_media.send.call_args[0][1].content,
            "Includes information about the weather in Tokyo",
            "message",
        )
