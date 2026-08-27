import json
from pathlib import Path

from scripts.last_run_uploaded import last_run_uploaded, main


def test_reads_last_uploaded():
    payload = {
        "runs": [
            {"videos_uploaded": 0, "timestamp": "t0"},
            {"videos_uploaded": 2, "timestamp": "t1"},
        ]
    }
    assert last_run_uploaded(payload) == {"videos_uploaded": 2, "timestamp": "t1"}


def test_empty_runs():
    assert last_run_uploaded({}) == {"videos_uploaded": None, "timestamp": None}


def test_cli(tmp_path: Path, capsys):
    state = tmp_path / "pipeline_state.json"
    state.write_text(
        json.dumps({"runs": [{"videos_uploaded": 1, "timestamp": "now"}]}),
        encoding="utf-8",
    )
    assert main(["--state-file", str(state)]) == 0
    assert json.loads(capsys.readouterr().out)["videos_uploaded"] == 1


def test_cli_missing(tmp_path: Path):
    assert main(["--state-file", str(tmp_path / "missing.json")]) == 1
