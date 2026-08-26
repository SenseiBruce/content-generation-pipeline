import json
from pathlib import Path

from scripts.last_run_videos import last_run_videos, main


def test_reads_last_videos():
    payload = {
        "runs": [
            {"videos_produced": 0, "timestamp": "t0"},
            {"videos_produced": 3, "timestamp": "t1"},
        ]
    }
    assert last_run_videos(payload) == {"videos_produced": 3, "timestamp": "t1"}


def test_empty_runs():
    assert last_run_videos({}) == {"videos_produced": None, "timestamp": None}


def test_cli(tmp_path: Path, capsys):
    state = tmp_path / "pipeline_state.json"
    state.write_text(
        json.dumps({"runs": [{"videos_produced": 2, "timestamp": "now"}]}),
        encoding="utf-8",
    )
    assert main(["--state-file", str(state)]) == 0
    assert json.loads(capsys.readouterr().out)["videos_produced"] == 2


def test_cli_missing(tmp_path: Path):
    assert main(["--state-file", str(tmp_path / "missing.json")]) == 1
