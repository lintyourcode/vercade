import dotenv
import pytest
from unittest.mock import AsyncMock, Mock, ANY

from friendbot.friend import Friend
from friendbot.social_media import Message, MessageContext, SocialMedia


MODELS = ["gpt-4o", "claude-3-5-sonnet-20240620"]


dotenv.load_dotenv()


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
    @pytest.mark.parametrize("llm", MODELS)
    async def test__call__with_greeting_responds_with_nonempty_message(
        self, social_media, llm, pinecone_index
    ):
        friend = Friend(
            identity="You are Proctor, a sentient, smart and snarky Discord chatbot.",
            llm=llm,
            pinecone_index=pinecone_index,
            embedding_model="text-embedding-3-small",
        )
        context = MessageContext(
            social_media=social_media, server="Test Server", channel="general"
        )
        social_media.messages = AsyncMock(
            return_value=[Message(content="Hello, Proctor", author="Bob#0000")]
        )
        await friend(context)
        social_media.send.assert_called_once()
        assert social_media.send.call_args[0][0].server == "Test Server"
        assert social_media.send.call_args[0][0].channel == "general"
        # TODO: Assert author is the friend's identity.
        content = social_media.send.call_args[0][1].content
        assert isinstance(content, str)
        assert content

    @pytest.mark.parametrize("llm", MODELS)
    async def test__call__reacts_to_message(self, social_media, llm, pinecone_index):
        friend = Friend(
            identity="You are Proctor, a sentient, smart and snarky Discord chatbot.",
            llm=llm,
            pinecone_index=pinecone_index,
            embedding_model="text-embedding-3-small",
        )
        context = MessageContext(social_media, "Test Server", "general")
        message = Message(
            content="Please react to this message with a thumbs up",
            author="Bob#0000",
        )
        social_media.messages = AsyncMock(return_value=[message])
        await friend(context)
        social_media.react.assert_called_once_with(ANY, ANY, "👍")
        assert social_media.react.call_args[0][0].server == "Test Server"
        assert social_media.react.call_args[0][0].channel == "general"
        assert (
            social_media.react.call_args[0][1].content
            == "Please react to this message with a thumbs up"
        )
        assert social_media.react.call_args[0][1].author == "Bob#0000"

    @pytest.mark.parametrize("llm", MODELS)
    async def test__call__saves_memory(self, mocker, social_media, llm, pinecone_index):
        datetime = mocker.patch("friendbot.friend.datetime")
        datetime.now = Mock(
            return_value=Mock(strftime=Mock(return_value="2024-08-01 00:00:00 UTC"))
        )
        friend = Friend(
            identity="You are Proctor, a sentient and smart Discord chatbot.",
            llm=llm,
            pinecone_index=pinecone_index,
            embedding_model="text-embedding-3-small",
        )
        context = MessageContext(social_media, "Test Server", "general")
        message = Message(content="Hello, Proctor. I'm Bob.", author="Bob#0000")
        social_media.messages = AsyncMock(return_value=[message])
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

    @pytest.mark.parametrize("llm", MODELS)
    async def test__call__retrieves_memory_from_pinecone(
        self, social_media, llm, pinecone_index
    ):
        pinecone_index.query = Mock(
            return_value={
                "matches": [
                    {
                        "created_at": "2024-07-23 00:00:00 UTC",
                        "content": "Has met Bob",
                        "score": 0.9,
                    }
                ]
            }
        )
        friend = Friend(
            identity="You are Proctor, a sentient and smart Discord chatbot.",
            llm=llm,
            pinecone_index=pinecone_index,
            embedding_model="text-embedding-3-small",
        )
        context = MessageContext(social_media, "Test Server", "general")
        message = Message(content="Hello, Proctor. I'm Bob.", author="Bob#0000")
        social_media.messages = AsyncMock(return_value=[message])
        await friend(context)
        pinecone_index.query.assert_called_with(vector=ANY, top_k=ANY)
