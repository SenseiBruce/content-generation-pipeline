#!/usr/bin/env python3
"""Sum videos produced/uploaded across pipeline runs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATE = PROJECT_ROOT / "data" / "pipeline_state.json"


def totals(payload: dict[str, Any]) -> dict[str, int]:
    runs = payload.get("runs")
    if not isinstance(runs, list):
        return {"videos_produced": 0, "videos_uploaded": 0, "runs_with_uploads": 0}
    produced = 0
    uploaded = 0
    runs_with_uploads = 0
    for run in runs:
        if not isinstance(run, dict):
            continue
        p = run.get("videos_produced")
        u = run.get("videos_uploaded")
        produced += int(p) if isinstance(p, int) else 0
        if isinstance(u, int) and u > 0:
            uploaded += u
            runs_with_uploads += 1
        elif isinstance(u, int):
            uploaded += u
    return {
        "videos_produced": produced,
        "videos_uploaded": uploaded,
        "runs_with_uploads": runs_with_uploads,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sum videos produced and uploaded")
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
    print(json.dumps(totals(payload)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
