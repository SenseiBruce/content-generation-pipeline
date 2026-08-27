#!/usr/bin/env python3
"""Count winning keywords in data/analytics_feedback.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FEEDBACK = PROJECT_ROOT / "data" / "analytics_feedback.json"


def count_winning_keywords(payload: dict[str, Any]) -> int:
    winners = payload.get("winning_keywords")
    if not isinstance(winners, list):
        return 0
    return len(winners)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Count winning keywords")
    parser.add_argument(
        "--feedback-file",
        default=str(DEFAULT_FEEDBACK),
        help="Path to analytics_feedback.json",
    )
    args = parser.parse_args(argv)
    path = Path(args.feedback_file)
    if not path.exists():
        print(f"Feedback file not found: {path}", file=sys.stderr)
        return 1
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON in {path}: {exc}", file=sys.stderr)
        return 1
    if not isinstance(payload, dict):
        print("Feedback file must contain a JSON object", file=sys.stderr)
        return 1
    print(json.dumps({"winning_keywords": count_winning_keywords(payload)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
