import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from pipeline.health import check_health, main


def _write_state(tmp_path: Path, last_run: str, status: str = "success") -> Path:
    path = tmp_path / "pipeline_state.json"
    path.write_text(
        json.dumps(
            {
                "seen_hashes": [],
                "last_run": last_run,
                "runs": [{"timestamp": last_run, "status": status}],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_check_health_ok(tmp_path: Path):
    now = datetime(2026, 8, 19, 21, 0, 0)
    path = _write_state(tmp_path, now.isoformat(), "success")
    code, reason = check_health(path, max_age_hours=8, now=now)
    assert code == 0
    assert reason == "ok"


def test_check_health_missing(tmp_path: Path):
    code, reason = check_health(tmp_path / "missing.json")
    assert code == 1
    assert "missing" in reason


def test_check_health_corrupt(tmp_path: Path):
    path = tmp_path / "pipeline_state.json"
    path.write_text("{not-json", encoding="utf-8")
    code, reason = check_health(path)
    assert code == 1
    assert "unreadable" in reason


def test_check_health_invalid_timestamp(tmp_path: Path):
    path = tmp_path / "pipeline_state.json"
    path.write_text(
        json.dumps({"seen_hashes": [], "last_run": "not-a-date", "runs": []}),
        encoding="utf-8",
    )
    code, reason = check_health(path)
    assert code == 1
    assert "invalid last_run" in reason
    now = datetime(2026, 8, 19, 21, 0, 0)
    last = (now - timedelta(hours=9)).isoformat()
    path = _write_state(tmp_path, last, "success")
    code, reason = check_health(path, max_age_hours=8, now=now)
    assert code == 1
    assert "stale" in reason


def test_check_health_aborted(tmp_path: Path):
    now = datetime(2026, 8, 19, 21, 0, 0)
    path = _write_state(tmp_path, now.isoformat(), "aborted")
    code, reason = check_health(path, max_age_hours=8, now=now)
    assert code == 1
    assert "aborted" in reason


def test_main_exit_code(tmp_path: Path, capsys):
    now = datetime.now()
    path = _write_state(tmp_path, now.isoformat(), "success")
    assert main(["--state-file", str(path), "--max-age-hours", "8"]) == 0
    assert capsys.readouterr().out.strip() == "ok"


def test_health_check_script_exit_code(tmp_path: Path):
    now = datetime.now()
    path = _write_state(tmp_path, now.isoformat(), "success")
    script = Path(__file__).resolve().parent.parent / "scripts" / "health_check.sh"
    result = subprocess.run(
        ["bash", str(script), "--state-file", str(path), "--max-age-hours", "8"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "ok"
