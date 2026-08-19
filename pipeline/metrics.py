"""Prometheus-style last-run metrics for OpenClaw / local polling."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

METRICS_JSON = Path(__file__).parent.parent / "data" / "pipeline_metrics.json"
METRICS_PROM = Path(__file__).parent.parent / "data" / "pipeline_metrics.prom"

_HEALTHY_STATUSES = {"success", "idle"}


def _load_counts(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    raw = data.get("runs_total") or {}
    return {str(k): int(v) for k, v in raw.items()}


def write_run_metrics(entry: dict[str, Any], metrics_json: Path | None = None) -> Path:
    """
    Update counters from a record_run entry and write JSON + Prometheus text.

    Gauges reflect the latest run; counters accumulate across runs in this file.
    """
    json_path = metrics_json or METRICS_JSON
    prom_path = json_path.with_suffix(".prom")
    json_path.parent.mkdir(parents=True, exist_ok=True)

    status = str(entry.get("status") or "unknown")
    counts = _load_counts(json_path)
    counts[status] = counts.get(status, 0) + 1

    timestamp = entry.get("timestamp") or datetime.now().isoformat()
    try:
        unix_ts = datetime.fromisoformat(str(timestamp)).timestamp()
    except ValueError:
        unix_ts = datetime.now().timestamp()

    snapshot = {
        "runs_total": counts,
        "last_status": status,
        "last_run": timestamp,
        "abort_reason": entry.get("abort_reason"),
        "videos_uploaded": int(entry.get("videos_uploaded") or 0),
        "last_run_healthy": 1 if status in _HEALTHY_STATUSES else 0,
        "last_run_timestamp_seconds": unix_ts,
    }
    json_path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# HELP pipeline_runs_total Pipeline runs recorded by status",
        "# TYPE pipeline_runs_total counter",
    ]
    for key, value in sorted(counts.items()):
        lines.append(f'pipeline_runs_total{{status="{key}"}} {value}')
    lines.extend(
        [
            "# HELP pipeline_last_run_timestamp_seconds Unix time of the last recorded run",
            "# TYPE pipeline_last_run_timestamp_seconds gauge",
            f"pipeline_last_run_timestamp_seconds {unix_ts:.0f}",
            "# HELP pipeline_last_run_healthy 1 if last status is success or idle",
            "# TYPE pipeline_last_run_healthy gauge",
            f"pipeline_last_run_healthy {snapshot['last_run_healthy']}",
            "# HELP pipeline_videos_uploaded Videos uploaded in the last run",
            "# TYPE pipeline_videos_uploaded gauge",
            f"pipeline_videos_uploaded {snapshot['videos_uploaded']}",
        ]
    )
    prom_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path
