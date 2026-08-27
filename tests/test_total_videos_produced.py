import json
from pathlib import Path

from scripts.total_videos_produced import main, total_videos_produced


def test_sums_produced_only():
    payload = {
        "runs": [
            {"videos_produced": 1, "videos_uploaded": 9},
            {"videos_produced": 2, "videos_uploaded": 0},
            {"status": "idle"},
        ]
    }
    assert total_videos_produced(payload) == 3


def test_missing_runs():
    assert total_videos_produced({}) == 0


def test_cli(tmp_path: Path, capsys):
    state = tmp_path / "pipeline_state.json"
    state.write_text(
        json.dumps({"runs": [{"videos_produced": 4, "videos_uploaded": 2}]}),
        encoding="utf-8",
    )
    assert main(["--state-file", str(state)]) == 0
    assert json.loads(capsys.readouterr().out) == {"videos_produced": 4}


def test_cli_missing(tmp_path: Path):
    assert main(["--state-file", str(tmp_path / "missing.json")]) == 1
