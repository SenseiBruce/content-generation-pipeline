#!/usr/bin/env python3
"""List losing keywords in data/analytics_feedback.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FEEDBACK = PROJECT_ROOT / "data" / "analytics_feedback.json"


def list_losing_keywords(payload: dict[str, Any]) -> list[str]:
    losers = payload.get("losing_keywords")
    if not isinstance(losers, list):
        return []
    return [item.strip() for item in losers if isinstance(item, str) and item.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List losing keywords")
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
    print(json.dumps({"losing_keywords": list_losing_keywords(payload)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
