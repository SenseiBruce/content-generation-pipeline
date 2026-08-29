import json
from pathlib import Path

from scripts.last_run_max_stories import last_run_max_stories, main


def test_reads_last_max_stories():
    payload = {
        "runs": [
            {"max_stories": 2, "timestamp": "t0"},
            {"max_stories": 5, "timestamp": "t1"},
        ]
    }
    assert last_run_max_stories(payload) == {"max_stories": 5, "timestamp": "t1"}


def test_empty_runs():
    assert last_run_max_stories({}) == {"max_stories": None, "timestamp": None}


def test_cli(tmp_path: Path, capsys):
    state = tmp_path / "pipeline_state.json"
    state.write_text(
        json.dumps({"runs": [{"max_stories": 3, "timestamp": "now"}]}),
        encoding="utf-8",
    )
    assert main(["--state-file", str(state)]) == 0
    assert json.loads(capsys.readouterr().out)["max_stories"] == 3


def test_cli_missing(tmp_path: Path):
    assert main(["--state-file", str(tmp_path / "missing.json")]) == 1
