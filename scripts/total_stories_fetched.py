#!/usr/bin/env python3
"""Sum stories_fetched across recorded pipeline runs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "pipeline_state.json"


def total_stories_fetched(state: dict[str, Any]) -> int:
    runs = state.get("runs") or []
    total = 0
    for run in runs:
        if not isinstance(run, dict):
            continue
        try:
            total += int(run.get("stories_fetched") or 0)
        except (TypeError, ValueError):
            continue
    return total


def load_state(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Unable to read state file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"State file {path} must contain a JSON object")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state-file",
        type=Path,
        default=DEFAULT_STATE_FILE,
        help="Path to pipeline_state.json",
    )
    args = parser.parse_args(argv)
    total = total_stories_fetched(load_state(args.state_file))
    json.dump({"stories_fetched": total}, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
