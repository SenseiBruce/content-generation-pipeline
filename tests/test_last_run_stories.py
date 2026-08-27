import json
from pathlib import Path

from scripts.last_run_stories import last_run_stories, main


def test_reads_last_stories():
    payload = {
        "runs": [
            {"stories_fetched": 10, "timestamp": "t0"},
            {"stories_fetched": 182, "timestamp": "t1"},
        ]
    }
    assert last_run_stories(payload) == {"stories_fetched": 182, "timestamp": "t1"}


def test_empty_runs():
    assert last_run_stories({}) == {"stories_fetched": None, "timestamp": None}


def test_cli(tmp_path: Path, capsys):
    state = tmp_path / "pipeline_state.json"
    state.write_text(
        json.dumps({"runs": [{"stories_fetched": 12, "timestamp": "now"}]}),
        encoding="utf-8",
    )
    assert main(["--state-file", str(state)]) == 0
    assert json.loads(capsys.readouterr().out)["stories_fetched"] == 12


def test_cli_missing(tmp_path: Path):
    assert main(["--state-file", str(tmp_path / "missing.json")]) == 1
