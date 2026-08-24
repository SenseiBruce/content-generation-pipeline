#!/usr/bin/env python3
"""Print the most recent pipeline run from data/pipeline_state.json as JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATE = PROJECT_ROOT / "data" / "pipeline_state.json"


def last_run_from_state(payload: dict[str, Any]) -> dict[str, Any] | None:
    runs = payload.get("runs")
    if not isinstance(runs, list) or not runs:
        return None
    last_ts = payload.get("last_run")
    if isinstance(last_ts, str):
        for run in reversed(runs):
            if isinstance(run, dict) and run.get("timestamp") == last_ts:
                return run
    last = runs[-1]
    return last if isinstance(last, dict) else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export the last recorded pipeline run as JSON"
    )
    parser.add_argument(
        "--state-file",
        default=str(DEFAULT_STATE),
        help="Path to pipeline_state.json",
    )
    args = parser.parse_args(argv)
    path = Path(args.state_file)
    if not path.exists():
        print(f"State file not found: {path}", file=sys.stderr)
        return 1
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON in {path}: {exc}", file=sys.stderr)
        return 1
    if not isinstance(payload, dict):
        print("State file must contain a JSON object", file=sys.stderr)
        return 1
    run = last_run_from_state(payload)
    if run is None:
        print("No pipeline runs recorded", file=sys.stderr)
        return 1
    print(json.dumps(run, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
