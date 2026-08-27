import json
from pathlib import Path

from scripts.last_run_generated import last_run_generated, main


def test_reads_last_generated():
    payload = {
        "runs": [
            {"scripts_generated": 0, "timestamp": "t0"},
            {"scripts_generated": 2, "timestamp": "t1"},
        ]
    }
    assert last_run_generated(payload) == {"scripts_generated": 2, "timestamp": "t1"}


def test_empty_runs():
    assert last_run_generated({}) == {"scripts_generated": None, "timestamp": None}


def test_cli(tmp_path: Path, capsys):
    state = tmp_path / "pipeline_state.json"
    state.write_text(
        json.dumps({"runs": [{"scripts_generated": 2, "timestamp": "now"}]}),
        encoding="utf-8",
    )
    assert main(["--state-file", str(state)]) == 0
    assert json.loads(capsys.readouterr().out)["scripts_generated"] == 2


def test_cli_missing(tmp_path: Path):
    assert main(["--state-file", str(tmp_path / "missing.json")]) == 1
