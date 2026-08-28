import json
from pathlib import Path

from scripts.last_run_started import last_run_started, main


def test_reads_last_run():
    payload = {
        "runs": [
            {"started_at": "t0", "timestamp": "2026-01-01T00:00:00"},
            {"started_at": "t1", "timestamp": "2026-01-02T00:00:00"},
        ]
    }
    assert last_run_started(payload) == {
        "started_at": "t1",
        "timestamp": "2026-01-02T00:00:00",
    }


def test_empty_runs():
    assert last_run_started({}) == {"started_at": None, "timestamp": None}


def test_cli(tmp_path: Path, capsys):
    state = tmp_path / "pipeline_state.json"
    state.write_text(
        json.dumps({"runs": [{"started_at": "now", "timestamp": "t1"}]}),
        encoding="utf-8",
    )
    assert main(["--state-file", str(state)]) == 0
    assert json.loads(capsys.readouterr().out)["started_at"] == "now"


def test_cli_missing(tmp_path: Path):
    assert main(["--state-file", str(tmp_path / "missing.json")]) == 1
