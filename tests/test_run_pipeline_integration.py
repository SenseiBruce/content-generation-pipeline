"""Offline integration test for run_pipeline with every agent mocked."""

from __future__ import annotations

import json
from pathlib import Path

import run_pipeline
from pipeline import metrics, state
from tests.helpers import make_valid_script


def _patch_state(monkeypatch, tmp_path: Path) -> Path:
    state_file = tmp_path / "pipeline_state.json"
    monkeypatch.setattr(state, "STATE_FILE", state_file)
    monkeypatch.setattr(metrics, "METRICS_JSON", tmp_path / "pipeline_metrics.json")
    monkeypatch.setattr(run_pipeline, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(run_pipeline, "_check_time_budget", lambda *args, **kwargs: True)
    monkeypatch.setattr(run_pipeline, "notify_failure", lambda *args, **kwargs: False)
    return state_file


def _last_run(state_file: Path) -> dict:
    return json.loads(state_file.read_text(encoding="utf-8"))["runs"][-1]


def test_run_pipeline_success_records_summary(monkeypatch, tmp_path: Path):
    state_file = _patch_state(monkeypatch, tmp_path)
    script = make_valid_script()
    scenes = script["scenes"]
    image_map = {scene["id"]: tmp_path / f"img_{scene['id']}.png" for scene in scenes}
    audio_map = {scene["id"]: tmp_path / f"aud_{scene['id']}.wav" for scene in scenes}
    story = {"hash": "abc123", "title": "RBI repo rate hike", "link": "https://example.com/rbi"}

    monkeypatch.setattr(run_pipeline, "fetch_all_news", lambda: [story])
    monkeypatch.setattr(run_pipeline, "prioritize", lambda stories: stories)
    monkeypatch.setattr(run_pipeline, "generate_all", lambda stories: [script])
    monkeypatch.setattr(run_pipeline, "judge_all", lambda scripts: ([script], []))
    monkeypatch.setattr(run_pipeline, "generate_images", lambda s: image_map)
    monkeypatch.setattr(run_pipeline, "synthesize_all", lambda s: audio_map)
    monkeypatch.setattr(
        run_pipeline, "stitch_video", lambda s, images, audio: tmp_path / "final.mp4"
    )
    monkeypatch.setattr(run_pipeline, "upload_video", lambda path, s: "ytid123")
    monkeypatch.setattr(run_pipeline, "pull_and_analyze", lambda: True)

    run_pipeline.run_pipeline()

    summary = _last_run(state_file)
    assert summary["status"] == "success"
    assert summary["stories_fetched"] == 1
    assert summary["stories_prioritized"] == 1
    assert summary["scripts_generated"] == 1
    assert summary["scripts_approved"] == 1
    assert summary["videos_produced"] == 1
    assert summary["videos_uploaded"] == 1


def test_run_pipeline_dry_run_skips_upload(monkeypatch, tmp_path: Path):
    state_file = _patch_state(monkeypatch, tmp_path)
    script = make_valid_script()
    scenes = script["scenes"]
    image_map = {scene["id"]: tmp_path / f"img_{scene['id']}.png" for scene in scenes}
    audio_map = {scene["id"]: tmp_path / f"aud_{scene['id']}.wav" for scene in scenes}
    story = {"hash": "dry123", "title": "SEBI circular", "link": "https://example.com/sebi"}

    monkeypatch.setattr(run_pipeline, "fetch_all_news", lambda: [story])
    monkeypatch.setattr(run_pipeline, "prioritize", lambda stories: stories)
    monkeypatch.setattr(run_pipeline, "generate_all", lambda stories: [script])
    monkeypatch.setattr(run_pipeline, "judge_all", lambda scripts: ([script], []))
    monkeypatch.setattr(run_pipeline, "generate_images", lambda s: image_map)
    monkeypatch.setattr(run_pipeline, "synthesize_all", lambda s: audio_map)
    monkeypatch.setattr(
        run_pipeline, "stitch_video", lambda s, images, audio: tmp_path / "final.mp4"
    )

    def _should_not_upload(*_args, **_kwargs):
        raise AssertionError("dry-run must not upload")

    monkeypatch.setattr(run_pipeline, "upload_video", _should_not_upload)

    run_pipeline.run_pipeline(dry_run=True)

    summary = _last_run(state_file)
    assert summary["status"] == "success"
    assert summary["videos_produced"] == 1
    assert summary["videos_uploaded"] == 0
    assert summary["dry_run"] is True


def test_run_pipeline_idle_when_watchtower_empty(monkeypatch, tmp_path: Path):
    """No new RSS items is a successful idle run, not an abort (no webhook)."""
    state_file = _patch_state(monkeypatch, tmp_path)
    monkeypatch.setattr(run_pipeline, "fetch_all_news", lambda: [])

    run_pipeline.run_pipeline()

    summary = _last_run(state_file)
    assert summary["status"] == "idle"
    assert summary["stories_fetched"] == 0


def test_run_pipeline_aborts_when_time_budget_exhausted(monkeypatch, tmp_path: Path):
    state_file = _patch_state(monkeypatch, tmp_path)
    monkeypatch.setattr(run_pipeline, "_check_time_budget", lambda *args, **kwargs: False)

    run_pipeline.run_pipeline()

    summary = _last_run(state_file)
    assert summary["status"] == "aborted"
    assert "Time exceeded" in summary["abort_reason"]
