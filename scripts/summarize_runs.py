#!/usr/bin/env python3
"""Summarize pipeline run statuses from data/pipeline_state.json."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATE = PROJECT_ROOT / "data" / "pipeline_state.json"


def summarize_runs(payload: dict[str, Any]) -> dict[str, Any]:
    runs = payload.get("runs")
    counts: Counter[str] = Counter()
    if isinstance(runs, list):
        for run in runs:
            if not isinstance(run, dict):
                continue
            status = run.get("status")
            label = status if isinstance(status, str) and status.strip() else "unknown"
            counts[label] += 1
    return {"total": sum(counts.values()), "by_status": dict(counts)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize recorded pipeline run statuses")
    parser.add_argument(
        "--state-file", default=str(DEFAULT_STATE), help="Path to pipeline_state.json"
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
    print(json.dumps(summarize_runs(payload), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
