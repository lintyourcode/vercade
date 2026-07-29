import pytest

from tests.e2e.conftest import E2EChannel, E2EServer, UserStub, VercadeProcess
from tests.judge import match

pytestmark = pytest.mark.e2e


def test_greeting_reciprocated(
    e2e_server: E2EServer,
    e2e_channel: E2EChannel,
    vercade_process: VercadeProcess,
    user_stub: UserStub,
) -> None:
    user_stub.send_message(e2e_channel.id, "Hello!")
    reply = user_stub.wait_for_message(
        author_id=e2e_server.vercade_user_id,
        channel_id=e2e_channel.id,
        timeout=120,
    )
    assert reply is not None, (
        "Vercade did not respond to the greeting within 120s. "
        f"Captured output:\n{vercade_process.dump_output()}"
    )
    assert match(
        reply.content,
        "a friendly greeting in response to a user saying hello",
        "Discord message",
    )
