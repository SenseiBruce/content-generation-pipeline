#!/usr/bin/env python3
"""Print recent pipeline run records from data/pipeline_state.json as JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline import state  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List recorded pipeline runs")
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of recent runs to print (default 20)",
    )
    parser.add_argument(
        "--state-file",
        default=None,
        help="Override path to pipeline_state.json",
    )
    args = parser.parse_args(argv)
    if args.state_file:
        state.STATE_FILE = Path(args.state_file)
    print(json.dumps(state.list_runs(args.limit), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
