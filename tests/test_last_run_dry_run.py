import json
from pathlib import Path

from scripts.last_run_dry_run import last_run_dry_run, main


def test_reads_last_dry_run():
    payload = {
        "runs": [
            {"dry_run": False, "timestamp": "t0"},
            {"dry_run": True, "timestamp": "t1"},
        ]
    }
    assert last_run_dry_run(payload) == {"dry_run": True, "timestamp": "t1"}


def test_empty_runs():
    assert last_run_dry_run({}) == {"dry_run": None, "timestamp": None}


def test_cli(tmp_path: Path, capsys):
    state = tmp_path / "pipeline_state.json"
    state.write_text(
        json.dumps({"runs": [{"dry_run": True, "timestamp": "now"}]}),
        encoding="utf-8",
    )
    assert main(["--state-file", str(state)]) == 0
    assert json.loads(capsys.readouterr().out)["dry_run"] is True


def test_cli_missing(tmp_path: Path):
    assert main(["--state-file", str(tmp_path / "missing.json")]) == 1
