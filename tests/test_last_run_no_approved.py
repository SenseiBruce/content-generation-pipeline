import json
from pathlib import Path

from scripts.last_run_no_approved import last_run_no_approved, main


def test_reads_last_no_approved():
    payload = {
        "runs": [
            {"status": "success", "timestamp": "t0"},
            {"status": "no_approved", "timestamp": "t1"},
        ]
    }
    assert last_run_no_approved(payload) == {
        "no_approved": True,
        "status": "no_approved",
        "timestamp": "t1",
    }


def test_empty_runs():
    assert last_run_no_approved({}) == {
        "no_approved": None,
        "status": None,
        "timestamp": None,
    }


def test_cli(tmp_path: Path, capsys):
    state = tmp_path / "pipeline_state.json"
    state.write_text(
        json.dumps({"runs": [{"status": "idle", "timestamp": "now"}]}),
        encoding="utf-8",
    )
    assert main(["--state-file", str(state)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["no_approved"] is False
    assert out["status"] == "idle"


def test_cli_missing(tmp_path: Path):
    assert main(["--state-file", str(tmp_path / "missing.json")]) == 1
