#!/usr/bin/env python3
"""Count seen_hashes in data/pipeline_state.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATE = PROJECT_ROOT / "data" / "pipeline_state.json"


def count_seen_hashes(payload: dict[str, Any]) -> int:
    hashes = payload.get("seen_hashes")
    if not isinstance(hashes, list):
        return 0
    return len(hashes)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Count seen story hashes in pipeline_state.json")
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
    print(json.dumps({"seen_hashes": count_seen_hashes(payload)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
