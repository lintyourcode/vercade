import asyncio
from datetime import datetime, timezone

from vercade.social_media import Channel, Message, MessageContext, Server, SocialMedia
from vercade.trigger import Trigger


def _message() -> Message:
    return Message(
        content="hello",
        author="alice",
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


async def _run_read_message(
    context: MessageContext, *, hang: bool = False
) -> tuple[Trigger, list[str], asyncio.Event]:
    events: list[str] = []
    called = asyncio.Event()
    release = asyncio.Event()

    async def fake_agent(event: str) -> None:
        events.append(event)
        called.set()
        if hang:
            await release.wait()

    trigger = Trigger(SocialMedia(), fake_agent)
    await trigger.read_message(context, _message())
    await asyncio.wait_for(called.wait(), timeout=1)
    if not hang:
        pending = [
            task
            for bucket in trigger._response_tasks.values()
            for task in bucket.values()
        ]
        if pending:
            await asyncio.gather(*pending)
    return trigger, events, release


async def test_read_message_guild_event_includes_server_and_channel():
    context = MessageContext(
        social_media=SocialMedia(),
        server=Server(id=1, name="Vercade"),
        channel=Channel(id=2, name="general"),
    )
    _, events, _ = await _run_read_message(context)
    assert events == [
        (
            "You received a message in the Discord server Vercade (with id 1) "
            "and channel general (with id 2)."
        )
    ]


async def test_read_message_direct_message_event_has_no_server():
    context = MessageContext(
        social_media=SocialMedia(),
        server=None,
        channel=Channel(id=99, name="alice"),
    )
    trigger, events, release = await _run_read_message(context, hang=True)
    task = trigger._response_tasks[None][99]
    try:
        assert len(events) == 1
        event = events[0]
        assert "direct message" in event.lower()
        assert "alice" in event
        assert "99" in event
        assert "no Discord server" in event
        assert task is trigger._response_tasks[None][99]
    finally:
        release.set()
        await task
