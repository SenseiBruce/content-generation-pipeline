import json
from pathlib import Path

from scripts.last_run_failed import last_run_failed, main


def test_reads_last_failed():
    payload = {
        "runs": [
            {"status": "success", "timestamp": "t0"},
            {"status": "failed", "timestamp": "t1"},
        ]
    }
    assert last_run_failed(payload) == {
        "failed": True,
        "status": "failed",
        "timestamp": "t1",
    }


def test_empty_runs():
    assert last_run_failed({}) == {
        "failed": None,
        "status": None,
        "timestamp": None,
    }


def test_cli(tmp_path: Path, capsys):
    state = tmp_path / "pipeline_state.json"
    state.write_text(
        json.dumps({"runs": [{"status": "success", "timestamp": "now"}]}),
        encoding="utf-8",
    )
    assert main(["--state-file", str(state)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["failed"] is False
    assert out["status"] == "success"


def test_cli_missing(tmp_path: Path):
    assert main(["--state-file", str(tmp_path / "missing.json")]) == 1
