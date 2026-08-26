import json
from pathlib import Path

from scripts.last_run_elapsed import last_run_elapsed, main


def test_reads_last_elapsed():
    payload = {
        "runs": [
            {"elapsed_seconds": 10, "timestamp": "t0"},
            {"elapsed_seconds": 171.7, "timestamp": "t1"},
        ]
    }
    assert last_run_elapsed(payload) == {"elapsed_seconds": 171.7, "timestamp": "t1"}


def test_empty_runs():
    assert last_run_elapsed({}) == {"elapsed_seconds": None, "timestamp": None}


def test_cli(tmp_path: Path, capsys):
    state = tmp_path / "pipeline_state.json"
    state.write_text(
        json.dumps({"runs": [{"elapsed_seconds": 12, "timestamp": "now"}]}),
        encoding="utf-8",
    )
    assert main(["--state-file", str(state)]) == 0
    assert json.loads(capsys.readouterr().out)["elapsed_seconds"] == 12


def test_cli_missing(tmp_path: Path):
    assert main(["--state-file", str(tmp_path / "missing.json")]) == 1
