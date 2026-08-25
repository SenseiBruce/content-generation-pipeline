import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from total_videos_uploaded import main, totals  # noqa: E402


def test_sums_runs():
    payload = {
        "runs": [
            {"videos_produced": 1, "videos_uploaded": 1},
            {"videos_produced": 2, "videos_uploaded": 0},
            {"status": "idle"},
        ]
    }
    assert totals(payload) == {
        "videos_produced": 3,
        "videos_uploaded": 1,
        "runs_with_uploads": 1,
    }


def test_missing_runs():
    assert totals({})["videos_produced"] == 0


def test_cli(tmp_path, capsys):
    state = tmp_path / "pipeline_state.json"
    state.write_text(
        json.dumps({"runs": [{"videos_produced": 4, "videos_uploaded": 2}]}), encoding="utf-8"
    )
    assert main(["--state-file", str(state)]) == 0
    assert json.loads(capsys.readouterr().out)["videos_uploaded"] == 2


def test_cli_missing(tmp_path):
    assert main(["--state-file", str(tmp_path / "missing.json")]) == 1
