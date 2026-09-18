import pytest

from vercade.trigger import parse_schedule_interval_seconds


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("", None),
        ("  ", None),
        ("45s", 45.0),
        ("15m", 900.0),
        ("2h", 7200.0),
        ("1.5h", 5400.0),
        ("1h30m", 5400.0),
        (" 15m ", 900.0),
        ("0s", 0.0),
    ],
)
def test_parse_schedule_interval_seconds(value: str | None, expected: float | None):
    assert parse_schedule_interval_seconds(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "disabled",
        "DISABLED",
        "300",
        "300.5",
        "0",
        "+0",
        "not-a-duration",
        "15x",
        "m15",
        "1h30",
        "15M",
    ],
)
def test_parse_schedule_interval_seconds_rejects_invalid_values(value: str):
    with pytest.raises(ValueError, match="VERCADE_SCHEDULE_INTERVAL"):
        parse_schedule_interval_seconds(value)
