import json
from pathlib import Path

from scripts.last_run_abort import last_run_abort, main


def test_reads_last_abort_reason():
    payload = {
        "runs": [
            {"abort_reason": None, "timestamp": "t0"},
            {"abort_reason": "Time exceeded before watchtower", "timestamp": "t1"},
        ]
    }
    assert last_run_abort(payload) == {
        "abort_reason": "Time exceeded before watchtower",
        "timestamp": "t1",
    }


def test_empty_runs():
    assert last_run_abort({}) == {"abort_reason": None, "timestamp": None}


def test_cli(tmp_path: Path, capsys):
    state = tmp_path / "pipeline_state.json"
    state.write_text(
        json.dumps({"runs": [{"abort_reason": "stopped", "timestamp": "now"}]}),
        encoding="utf-8",
    )
    assert main(["--state-file", str(state)]) == 0
    assert json.loads(capsys.readouterr().out)["abort_reason"] == "stopped"


def test_cli_missing(tmp_path: Path):
    assert main(["--state-file", str(tmp_path / "missing.json")]) == 1
