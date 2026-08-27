import json
from pathlib import Path

from scripts.last_run_prioritized import last_run_prioritized, main


def test_reads_last_prioritized():
    payload = {
        "runs": [
            {"stories_prioritized": 1, "timestamp": "t0"},
            {"stories_prioritized": 4, "timestamp": "t1"},
        ]
    }
    assert last_run_prioritized(payload) == {"stories_prioritized": 4, "timestamp": "t1"}


def test_empty_runs():
    assert last_run_prioritized({}) == {"stories_prioritized": None, "timestamp": None}


def test_cli(tmp_path: Path, capsys):
    state = tmp_path / "pipeline_state.json"
    state.write_text(
        json.dumps({"runs": [{"stories_prioritized": 2, "timestamp": "now"}]}),
        encoding="utf-8",
    )
    assert main(["--state-file", str(state)]) == 0
    assert json.loads(capsys.readouterr().out)["stories_prioritized"] == 2


def test_cli_missing(tmp_path: Path):
    assert main(["--state-file", str(tmp_path / "missing.json")]) == 1
