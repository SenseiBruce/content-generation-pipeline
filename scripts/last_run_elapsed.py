#!/usr/bin/env python3
"""Print elapsed_seconds for the most recent pipeline run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATE = PROJECT_ROOT / "data" / "pipeline_state.json"


def last_run_elapsed(payload: dict[str, Any]) -> dict[str, Any]:
    runs = payload.get("runs")
    if not isinstance(runs, list) or not runs:
        return {"elapsed_seconds": None, "timestamp": None}
    last = runs[-1]
    if not isinstance(last, dict):
        return {"elapsed_seconds": None, "timestamp": None}
    elapsed = last.get("elapsed_seconds")
    timestamp = last.get("timestamp")
    return {
        "elapsed_seconds": elapsed if isinstance(elapsed, (int, float)) else None,
        "timestamp": timestamp if isinstance(timestamp, str) else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print last pipeline run elapsed_seconds")
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
    print(json.dumps(last_run_elapsed(payload)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
