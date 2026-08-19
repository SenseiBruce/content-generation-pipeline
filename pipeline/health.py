"""Read data/pipeline_state.json and exit non-zero when the last run looks unhealthy."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

STATE_FILE = Path(__file__).parent.parent / "data" / "pipeline_state.json"
DEFAULT_MAX_AGE_HOURS = 8.0


def inspect_health(
    state_file: Path | None = None,
    max_age_hours: float = DEFAULT_MAX_AGE_HOURS,
    now: datetime | None = None,
) -> dict[str, Any]:
    """
    Machine-readable last-run health.

    Always includes status, last_run, age_hours, stale, abort_reason, and ok.
    """
    path = state_file or STATE_FILE
    current = now or datetime.now()
    payload: dict[str, Any] = {
        "ok": False,
        "status": None,
        "last_run": None,
        "age_hours": None,
        "max_age_hours": max_age_hours,
        "stale": False,
        "abort_reason": None,
        "reason": "",
    }

    if not path.exists():
        payload["reason"] = f"missing state file: {path}"
        return payload

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        payload["reason"] = f"unreadable state file: {exc}"
        return payload

    last_run = data.get("last_run")
    if not last_run:
        payload["reason"] = "no last_run timestamp"
        return payload

    try:
        last_dt = datetime.fromisoformat(str(last_run))
    except ValueError:
        payload["reason"] = f"invalid last_run timestamp: {last_run}"
        return payload

    age_hours = (current - last_dt).total_seconds() / 3600
    runs = data.get("runs") or []
    last_entry = runs[-1] if runs else {}
    status = last_entry.get("status")
    abort_reason = last_entry.get("abort_reason")

    payload.update(
        {
            "status": status,
            "last_run": str(last_run),
            "age_hours": round(age_hours, 3),
            "abort_reason": abort_reason,
        }
    )

    if age_hours > max_age_hours:
        payload["stale"] = True
        payload["reason"] = f"stale last_run ({age_hours:.1f}h > {max_age_hours}h)"
        return payload

    if status == "aborted":
        payload["reason"] = f"last run aborted: {abort_reason or 'aborted'}"
        return payload

    payload["ok"] = True
    payload["reason"] = "ok"
    return payload


def check_health(
    state_file: Path | None = None,
    max_age_hours: float = DEFAULT_MAX_AGE_HOURS,
    now: datetime | None = None,
) -> tuple[int, str]:
    """
    Return (exit_code, reason).

    0 — state exists, last_run is within max_age_hours, last recorded status is not aborted.
    1 — missing, corrupt, stale, or last run aborted.
    """
    payload = inspect_health(state_file, max_age_hours, now)
    return (0 if payload["ok"] else 1, str(payload["reason"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Health-check the last pipeline run.")
    parser.add_argument(
        "--state-file",
        type=Path,
        default=STATE_FILE,
        help="Path to pipeline_state.json",
    )
    parser.add_argument(
        "--max-age-hours",
        type=float,
        default=DEFAULT_MAX_AGE_HOURS,
        help="Fail if last_run is older than this many hours (default: 8)",
    )
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="json (default, machine-readable) or text",
    )
    args = parser.parse_args(argv)
    payload = inspect_health(args.state_file, args.max_age_hours)
    code = 0 if payload["ok"] else 1
    stream = sys.stdout if code == 0 else sys.stderr
    if args.format == "json":
        print(json.dumps(payload, indent=2), file=sys.stdout)
    else:
        print(payload["reason"], file=stream)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
