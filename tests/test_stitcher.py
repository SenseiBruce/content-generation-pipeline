from pathlib import Path

from agents.stitcher import _create_caption_image, _ffprobe_duration


def test_create_caption_image_writes_nonzero_file(tmp_path: Path):
    out = tmp_path / "caption.png"
    ok = _create_caption_image("RBI hikes repo rate today", out)
    assert ok is True
    assert out.exists()
    assert out.stat().st_size > 0


def test_ffprobe_duration_defaults_when_file_missing(tmp_path: Path):
    missing = tmp_path / "missing.wav"
    assert _ffprobe_duration(missing) == 3.0
