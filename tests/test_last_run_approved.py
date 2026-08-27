import json
from pathlib import Path

from scripts.last_run_approved import last_run_approved, main


def test_reads_last_approved():
    payload = {
        "runs": [
            {"scripts_approved": 0, "timestamp": "t0"},
            {"scripts_approved": 3, "timestamp": "t1"},
        ]
    }
    assert last_run_approved(payload) == {"scripts_approved": 3, "timestamp": "t1"}


def test_empty_runs():
    assert last_run_approved({}) == {"scripts_approved": None, "timestamp": None}


def test_cli(tmp_path: Path, capsys):
    state = tmp_path / "pipeline_state.json"
    state.write_text(
        json.dumps({"runs": [{"scripts_approved": 1, "timestamp": "now"}]}),
        encoding="utf-8",
    )
    assert main(["--state-file", str(state)]) == 0
    assert json.loads(capsys.readouterr().out)["scripts_approved"] == 1


def test_cli_missing(tmp_path: Path):
    assert main(["--state-file", str(tmp_path / "missing.json")]) == 1
