from pathlib import Path

from pipeline import state


def test_mark_seen_and_is_seen(monkeypatch, tmp_path: Path):
    state_file = tmp_path / "pipeline_state.json"
    monkeypatch.setattr(state, "STATE_FILE", state_file)

    assert state.is_seen("abc") is False
    state.mark_seen("abc")
    assert state.is_seen("abc") is True
    state.mark_seen("abc")
    saved = state_file.read_text(encoding="utf-8")
    assert saved.count("abc") == 1


def test_record_run(monkeypatch, tmp_path: Path):
    state_file = tmp_path / "pipeline_state.json"
    monkeypatch.setattr(state, "STATE_FILE", state_file)

    state.record_run({"status": "success", "videos_uploaded": 1})
    data = state._load()
    assert data["last_run"] is not None
    assert data["runs"][0]["status"] == "success"
    assert data["runs"][0]["videos_uploaded"] == 1
