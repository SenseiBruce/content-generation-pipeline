"""CLI for listing recent pipeline runs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import list_runs as list_runs_cli  # noqa: E402

from pipeline import state  # noqa: E402


def test_list_runs_returns_tail(monkeypatch, tmp_path: Path) -> None:
    state_file = tmp_path / "pipeline_state.json"
    monkeypatch.setattr(state, "STATE_FILE", state_file)
    state_file.write_text(
        json.dumps(
            {
                "seen_hashes": [],
                "last_run": "3",
                "runs": [
                    {"timestamp": "1", "status": "ok"},
                    {"timestamp": "2", "status": "ok"},
                    {"timestamp": "3", "status": "aborted"},
                ],
            }
        ),
        encoding="utf-8",
    )
    assert [row["timestamp"] for row in state.list_runs(2)] == ["2", "3"]


def test_list_runs_cli(monkeypatch, tmp_path: Path, capsys) -> None:
    path = tmp_path / "pipeline_state.json"
    path.write_text(
        json.dumps({"runs": [{"timestamp": "t1", "status": "success"}]}),
        encoding="utf-8",
    )
    assert list_runs_cli.main(["--state-file", str(path), "--limit", "5"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["status"] == "success"
