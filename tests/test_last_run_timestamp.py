import json
from pathlib import Path

from scripts.last_run_timestamp import last_run_timestamp, main


def test_reads_last_run():
    payload = {
        "runs": [
            {"timestamp": "2026-01-01T00:00:00"},
            {"timestamp": "2026-01-02T00:00:00"},
        ]
    }
    assert last_run_timestamp(payload) == {"timestamp": "2026-01-02T00:00:00"}


def test_empty_runs():
    assert last_run_timestamp({}) == {"timestamp": None}


def test_cli(tmp_path: Path, capsys):
    state = tmp_path / "pipeline_state.json"
    state.write_text(
        json.dumps({"runs": [{"timestamp": "t1"}]}),
        encoding="utf-8",
    )
    assert main(["--state-file", str(state)]) == 0
    assert json.loads(capsys.readouterr().out)["timestamp"] == "t1"


def test_cli_missing(tmp_path: Path):
    assert main(["--state-file", str(tmp_path / "missing.json")]) == 1
