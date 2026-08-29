import json
from pathlib import Path

from scripts.last_run_idle import last_run_idle, main


def test_reads_last_idle():
    payload = {
        "runs": [
            {"status": "success", "timestamp": "t0"},
            {"status": "idle", "timestamp": "t1"},
        ]
    }
    assert last_run_idle(payload) == {
        "idle": True,
        "status": "idle",
        "timestamp": "t1",
    }


def test_empty_runs():
    assert last_run_idle({}) == {
        "idle": None,
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
    assert out["idle"] is False
    assert out["status"] == "success"


def test_cli_missing(tmp_path: Path):
    assert main(["--state-file", str(tmp_path / "missing.json")]) == 1
