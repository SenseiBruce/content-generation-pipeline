import json
from pathlib import Path

from scripts.last_run_success import last_run_success, main


def test_reads_last_success():
    payload = {
        "runs": [
            {"status": "idle", "timestamp": "t0"},
            {"status": "success", "timestamp": "t1"},
        ]
    }
    assert last_run_success(payload) == {
        "success": True,
        "status": "success",
        "timestamp": "t1",
    }


def test_empty_runs():
    assert last_run_success({}) == {
        "success": None,
        "status": None,
        "timestamp": None,
    }


def test_cli(tmp_path: Path, capsys):
    state = tmp_path / "pipeline_state.json"
    state.write_text(
        json.dumps({"runs": [{"status": "idle", "timestamp": "now"}]}),
        encoding="utf-8",
    )
    assert main(["--state-file", str(state)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["success"] is False
    assert out["status"] == "idle"


def test_cli_missing(tmp_path: Path):
    assert main(["--state-file", str(tmp_path / "missing.json")]) == 1
