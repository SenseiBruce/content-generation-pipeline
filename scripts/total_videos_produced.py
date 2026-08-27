#!/usr/bin/env python3
"""Sum videos_produced across pipeline runs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATE = PROJECT_ROOT / "data" / "pipeline_state.json"


def total_videos_produced(payload: dict[str, Any]) -> int:
    runs = payload.get("runs")
    if not isinstance(runs, list):
        return 0
    total = 0
    for run in runs:
        if not isinstance(run, dict):
            continue
        produced = run.get("videos_produced")
        if isinstance(produced, int):
            total += produced
    return total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sum videos_produced across pipeline runs")
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
    print(json.dumps({"videos_produced": total_videos_produced(payload)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
