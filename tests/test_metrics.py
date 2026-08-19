import json
from datetime import datetime
from pathlib import Path

from pipeline.metrics import write_run_metrics


def test_write_run_metrics_accumulates_counters(tmp_path: Path):
    path = tmp_path / "pipeline_metrics.json"
    first = {
        "timestamp": datetime(2026, 8, 19, 12, 0, 0).isoformat(),
        "status": "success",
        "videos_uploaded": 1,
    }
    second = {
        "timestamp": datetime(2026, 8, 19, 18, 0, 0).isoformat(),
        "status": "aborted",
        "abort_reason": "Time exceeded before watchtower",
        "videos_uploaded": 0,
    }

    write_run_metrics(first, metrics_json=path)
    snapshot = write_run_metrics(second, metrics_json=path)
    data = json.loads(snapshot.read_text(encoding="utf-8"))
    assert data["runs_total"]["success"] == 1
    assert data["runs_total"]["aborted"] == 1
    assert data["last_status"] == "aborted"
    assert data["abort_reason"] == "Time exceeded before watchtower"
    assert data["last_run_healthy"] == 0

    prom = path.with_suffix(".prom").read_text(encoding="utf-8")
    assert 'pipeline_runs_total{status="success"} 1' in prom
    assert 'pipeline_runs_total{status="aborted"} 1' in prom
    assert "pipeline_last_run_healthy 0" in prom
    assert "pipeline_videos_uploaded 0" in prom
