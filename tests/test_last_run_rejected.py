import json
from pathlib import Path

from scripts.last_run_rejected import last_run_rejected, main


def test_reads_last_rejected():
    payload = {
        "runs": [
            {"scripts_rejected": 1, "timestamp": "t0"},
            {"scripts_rejected": 4, "timestamp": "t1"},
        ]
    }
    assert last_run_rejected(payload) == {"scripts_rejected": 4, "timestamp": "t1"}


def test_empty_runs():
    assert last_run_rejected({}) == {"scripts_rejected": None, "timestamp": None}


def test_cli(tmp_path: Path, capsys):
    state = tmp_path / "pipeline_state.json"
    state.write_text(
        json.dumps({"runs": [{"scripts_rejected": 2, "timestamp": "now"}]}),
        encoding="utf-8",
    )
    assert main(["--state-file", str(state)]) == 0
    assert json.loads(capsys.readouterr().out)["scripts_rejected"] == 2


def test_cli_missing(tmp_path: Path):
    assert main(["--state-file", str(tmp_path / "missing.json")]) == 1
