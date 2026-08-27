import json
from pathlib import Path

from scripts.last_run_status import last_run_status, main


def test_reads_last_run():
    payload = {
        "runs": [
            {"status": "idle", "timestamp": "2026-01-01T00:00:00"},
            {"status": "success", "timestamp": "2026-01-02T00:00:00"},
        ]
    }
    assert last_run_status(payload) == {
        "status": "success",
        "timestamp": "2026-01-02T00:00:00",
    }


def test_empty_runs():
    assert last_run_status({}) == {"status": None, "timestamp": None}


def test_cli(tmp_path: Path, capsys):
    state = tmp_path / "pipeline_state.json"
    state.write_text(
        json.dumps({"runs": [{"status": "aborted", "timestamp": "t1"}]}),
        encoding="utf-8",
    )
    assert main(["--state-file", str(state)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "aborted"


def test_cli_missing(tmp_path: Path):
    assert main(["--state-file", str(tmp_path / "missing.json")]) == 1
