"""Read data/pipeline_state.json and exit non-zero when the last run looks unhealthy."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

STATE_FILE = Path(__file__).parent.parent / "data" / "pipeline_state.json"
DEFAULT_MAX_AGE_HOURS = 8.0


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
    path = state_file or STATE_FILE
    if not path.exists():
        return 1, f"missing state file: {path}"

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return 1, f"unreadable state file: {exc}"

    last_run = data.get("last_run")
    if not last_run:
        return 1, "no last_run timestamp"

    try:
        last_dt = datetime.fromisoformat(str(last_run))
    except ValueError:
        return 1, f"invalid last_run timestamp: {last_run}"

    current = now or datetime.now()
    age_hours = (current - last_dt).total_seconds() / 3600
    if age_hours > max_age_hours:
        return 1, f"stale last_run ({age_hours:.1f}h > {max_age_hours}h)"

    runs = data.get("runs") or []
    if runs and runs[-1].get("status") == "aborted":
        reason = runs[-1].get("abort_reason", "aborted")
        return 1, f"last run aborted: {reason}"

    return 0, "ok"


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
    args = parser.parse_args(argv)
    code, reason = check_health(args.state_file, args.max_age_hours)
    stream = sys.stdout if code == 0 else sys.stderr
    print(reason, file=stream)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
