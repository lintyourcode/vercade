from datetime import datetime
import dotenv
import pytest

from friendbot.friend import Friend


dotenv.load_dotenv()


@pytest.fixture
def friend():
    return Friend(
        identity="You are Proctor, a sentient, smart and snarky Discord chatbot.",
    )


class TestFriend:
    def test__call__with_greeting_responds_with_nonempty_string(self, friend: Friend):
        response = friend("Hello!")
        assert isinstance(response, str)
        assert len(response) > 0

    def test__call__multiple_times_remembers_previous_messages(self, friend: Friend):
        friend("My name is Mark")
        response = friend("What is my name?")
        assert "Mark" in response

    def test__call__can_search_web(self, friend: Friend):
        year = datetime.now().year
        response = friend("Can you search online to find out what the current date is?")
        assert str(year) in response
