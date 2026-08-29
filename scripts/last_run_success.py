#!/usr/bin/env python3
"""Print whether the most recent pipeline run succeeded."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATE = PROJECT_ROOT / "data" / "pipeline_state.json"


def last_run_success(payload: dict[str, Any]) -> dict[str, Any]:
    runs = payload.get("runs")
    if not isinstance(runs, list) or not runs:
        return {"success": None, "status": None, "timestamp": None}
    last = runs[-1]
    if not isinstance(last, dict):
        return {"success": None, "status": None, "timestamp": None}
    status = last.get("status")
    timestamp = last.get("timestamp")
    status_text = status if isinstance(status, str) else None
    return {
        "success": status_text == "success" if status_text is not None else None,
        "status": status_text,
        "timestamp": timestamp if isinstance(timestamp, str) else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print whether last pipeline run succeeded")
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
    print(json.dumps(last_run_success(payload)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
