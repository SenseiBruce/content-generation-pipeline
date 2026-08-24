import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from export_last_run import last_run_from_state, main  # noqa: E402


def test_last_run_matches_timestamp():
    payload = {
        "last_run": "t2",
        "runs": [
            {"timestamp": "t1", "status": "idle"},
            {"timestamp": "t2", "status": "success"},
        ],
    }
    assert last_run_from_state(payload)["status"] == "success"


def test_last_run_falls_back_to_newest_entry():
    payload = {"runs": [{"timestamp": "a"}, {"timestamp": "b", "status": "ok"}]}
    assert last_run_from_state(payload)["timestamp"] == "b"


def test_cli_prints_last_run(tmp_path, capsys):
    state = tmp_path / "pipeline_state.json"
    state.write_text(
        json.dumps(
            {
                "last_run": "2026-01-01T00:00:00",
                "runs": [{"timestamp": "2026-01-01T00:00:00", "status": "success"}],
            }
        ),
        encoding="utf-8",
    )
    assert main(["--state-file", str(state)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "success"


def test_cli_missing_file(tmp_path):
    missing = tmp_path / "missing.json"
    assert main(["--state-file", str(missing)]) == 1
