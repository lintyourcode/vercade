import dotenv
import pytest
from unittest.mock import AsyncMock, Mock, ANY
from datetime import datetime, timezone

from litellm import completion

from friendbot.agent import Agent
from friendbot.social_media import Channel, Message, Server, SocialMedia


MODELS = ["gpt-4o", "anthropic/claude-3-5-sonnet-latest"]
FAST_MODELS = ["gpt-4o-mini"]


dotenv.load_dotenv()


def get_parameters() -> list[tuple[str, str]]:
    """
    Return a list of parameters for the tests.
    """

    return [(model, fast_model) for model in MODELS for fast_model in FAST_MODELS]


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
                    created_at=datetime.now(tz=timezone.utc),
                )
            ]
        )
        friend = Agent(
            name="Proctor",
            identity="You are Proctor, a sentient, smart and snarky Discord chatbot.",
            llm=llm,
            fast_llm=fast_llm,
            pinecone_index=pinecone_index,
            embedding_model="text-embedding-3-small",
        )
        await friend(
            "You received a message in the Discord server Test Server's channel #general.",
            social_media,
        )
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
        social_media.messages = AsyncMock(
            return_value=[
                Message(
                    content="Hello, Proctor",
                    author="Bob#0000",
                    created_at=datetime.now(tz=timezone.utc),
                )
            ]
        )
        friend = Agent(
            name="Proctor",
            identity="You are Proctor, a sentient, smart and snarky Discord chatbot.",
            llm=llm,
            pinecone_index=pinecone_index,
            embedding_model="text-embedding-3-small",
        )
        await friend(
            "You received a message in the Discord server Test Server's channel #general.",
            social_media,
        )
        social_media.send.assert_called_once()
        assert social_media.send.call_args[0][0].server == "Test Server"
        assert social_media.send.call_args[0][0].channel == "general"
        # TODO: Assert author is the friend's identity.
        content = social_media.send.call_args[0][1].content
        assert isinstance(content, str)
        assert content

    @pytest.mark.parametrize("llm, fast_llm", get_parameters())
    async def test__call__lists_servers(
        self, social_media, llm, fast_llm, pinecone_index
    ):
        social_media.messages = AsyncMock(
            return_value=[
                Message(
                    content="List the servers you have access to",
                    author="Bob#0000",
                    created_at=datetime.now(tz=timezone.utc),
                )
            ]
        )
        social_media.servers = AsyncMock(
            return_value=[
                Server(name="Test Server"),
                Server(name="Test Server 2"),
            ]
        )
        friend = Agent(
            name="Proctor",
            identity="You are Proctor, a sentient and intelligent Discord chatbot.",
            llm=llm,
            fast_llm=fast_llm,
            pinecone_index=pinecone_index,
        )
        await friend(
            "You received a message in the Discord server Test Server's channel #general.",
            social_media,
        )
        social_media.send.assert_called_once()
        social_media.servers.assert_called_once()
        assert match(
            social_media.send.call_args[0][1].content,
            "Indicates that the bot has access to the following servers: Test Server, Test Server 2",
            "message",
        )

    @pytest.mark.parametrize("llm, fast_llm", get_parameters())
    async def test__call__lists_channels(
        self, social_media, llm, fast_llm, pinecone_index
    ):
        social_media.messages = AsyncMock(
            return_value=[
                Message(
                    content="List the channels in the server Test Server",
                    author="Bob#0000",
                    created_at=datetime.now(tz=timezone.utc),
                )
            ]
        )
        social_media.channels = AsyncMock(
            return_value=[
                Channel(name="general"),
                Channel(name="spam"),
            ]
        )
        friend = Agent(
            name="Proctor",
            identity="You are Proctor, a sentient and intelligent Discord chatbot.",
            llm=llm,
            fast_llm=fast_llm,
            pinecone_index=pinecone_index,
        )
        await friend(
            "You received a message in the Discord server Test Server's channel #general.",
            social_media,
        )
        social_media.send.assert_called_once()
        social_media.channels.assert_called_once_with("Test Server")
        assert match(
            social_media.send.call_args[0][1].content,
            "Indicates that the bot has access to the following channels: general, spam",
            "message",
        )

    @pytest.mark.parametrize("llm, fast_llm", get_parameters())
    async def test__call__reacts_to_message(
        self, social_media, llm, fast_llm, pinecone_index
    ):
        message = Message(
            content="Please react to this message with a thumbs up",
            author="Bob#0000",
            created_at=datetime.now(tz=timezone.utc),
        )
        social_media.messages = AsyncMock(return_value=[message])
        friend = Agent(
            name="Proctor",
            identity="You are Proctor, a sentient, smart and snarky Discord chatbot.",
            llm=llm,
            pinecone_index=pinecone_index,
            embedding_model="text-embedding-3-small",
        )
        await friend(
            "You received a message in the Discord server Test Server's channel #general.",
            social_media,
        )
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
        message = Message(
            content="Hello, Proctor. I'm Bob.",
            author="Bob#0000",
            created_at=datetime.now(tz=timezone.utc),
        )
        social_media.messages = AsyncMock(return_value=[message])
        friend = Agent(
            name="Proctor",
            identity="You are Proctor, a sentient and smart Discord chatbot.",
            llm=llm,
            pinecone_index=pinecone_index,
            embedding_model="text-embedding-3-small",
        )
        await friend(
            "You received a message in the Discord server Test Server's channel #general.",
            social_media,
        )
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
        message = Message(
            content="Hello, Proctor. Do you remember me?",
            author="Bob#0000",
            created_at=datetime.now(tz=timezone.utc),
        )
        social_media.messages = AsyncMock(return_value=[message])
        async with Agent(
            name="Proctor",
            identity="You are Proctor, a sentient and smart Discord chatbot.",
            llm=llm,
            pinecone_index=pinecone_index,
            embedding_model="text-embedding-3-small",
        ) as friend:
            await friend(
                "You received a message in the Discord server Test Server's channel #general.",
                social_media,
            )
        social_media.send.assert_called_once()
        assert match(
            social_media.send.call_args[0][1].content,
            "Indicates that the sender has met Bob#0000 before",
            "message",
        )
