from datetime import datetime, timezone

from agents.publisher import _ist_slot_to_utc


def test_ist_slot_to_utc_morning():
    base = datetime(2026, 3, 1)
    utc = _ist_slot_to_utc(base, 7, 30)
    assert utc.tzinfo == timezone.utc
    assert utc.hour == 2
    assert utc.minute == 0
    assert utc.day == 1


def test_ist_slot_to_utc_evening():
    base = datetime(2026, 3, 1)
    utc = _ist_slot_to_utc(base, 21, 0)
    assert utc.hour == 15
    assert utc.minute == 30
