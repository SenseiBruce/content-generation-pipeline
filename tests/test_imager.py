import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from agents.imager import _generate_one_image, _image_url_from_runware
from pipeline.schemas import RunwareResponse


def test_generate_one_image_uses_runware_fixture(monkeypatch, tmp_path: Path, fixture_dir: Path):
    payload = json.loads((fixture_dir / "runware_response.json").read_text(encoding="utf-8"))
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"fake-image-bytes"

    class FakeJsonResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return payload

    class FakeImageResponse:
        content = png_bytes

        def raise_for_status(self) -> None:
            return None

    def fake_post(*args, **kwargs):
        return FakeJsonResponse()

    def fake_get(*args, **kwargs):
        return FakeImageResponse()

    monkeypatch.setattr("pipeline.http_client.post", fake_post)
    monkeypatch.setattr("pipeline.http_client.get", fake_get)
    monkeypatch.setattr("agents.imager.RUNWARE_API_KEY", "test-key")

    save_path = tmp_path / "img_01.png"
    assert _generate_one_image("Cinematic vault of gold coins", save_path) is True
    assert save_path.exists()
    assert save_path.read_bytes() == png_bytes


def test_runware_schema_rejects_malformed_fixture(fixture_dir: Path):
    payload = json.loads(
        (fixture_dir / "runware_response_malformed.json").read_text(encoding="utf-8")
    )
    with pytest.raises(ValidationError):
        RunwareResponse.model_validate(payload)
    with pytest.raises(ValidationError):
        _image_url_from_runware(payload)
