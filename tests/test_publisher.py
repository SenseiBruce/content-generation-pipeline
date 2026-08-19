from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from agents.publisher import _ist_slot_to_utc, _video_id_from_upload_response
from pipeline.schemas import YouTubeUploadResponse


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


def test_youtube_upload_schema_accepts_id():
    assert (
        _video_id_from_upload_response({"id": "abc123xyz", "kind": "youtube#video"}) == "abc123xyz"
    )


def test_youtube_upload_schema_rejects_malformed():
    with pytest.raises(ValidationError):
        YouTubeUploadResponse.model_validate({"kind": "youtube#video"})
    with pytest.raises(ValidationError):
        _video_id_from_upload_response({})
