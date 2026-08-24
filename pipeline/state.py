"""
pipeline/state.py

Manages persistent pipeline state across runs.
Tracks:
  - story hashes already processed (deduplication)
  - per-run results for audit
  - current pipeline status
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from pipeline.logger import get_logger
from pipeline.metrics import write_run_metrics

log = get_logger("state")

STATE_FILE = Path(__file__).parent.parent / "data" / "pipeline_state.json"


def _load() -> dict:
    """Load state file from disk; return empty skeleton on first run."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log.warning("State file corrupt, starting fresh: %s", e)
    return {
        "seen_hashes": [],
        "runs": [],
        "last_run": None,
    }


def _save(state: dict) -> None:
    """Persist state to disk atomically using a temp file."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, STATE_FILE)


def is_seen(story_hash: str) -> bool:
    """Return True if this story hash was already processed previously."""
    state = _load()
    return story_hash in state["seen_hashes"]


def mark_seen(story_hash: str) -> None:
    """Mark a story hash as processed so it is skipped on the next run."""
    state = _load()
    if story_hash not in state["seen_hashes"]:
        state["seen_hashes"].append(story_hash)
        _save(state)


def record_run(summary: Dict[str, Any]) -> None:
    """Append a pipeline run summary entry (timestamp + summary) to the history."""
    state = _load()
    entry = {
        "timestamp": datetime.now().isoformat(),
        **summary,
    }
    state["runs"].append(entry)
    # Keep only the last 100 run records to avoid unbounded growth
    state["runs"] = state["runs"][-100:]
    state["last_run"] = entry["timestamp"]
    _save(state)
    write_run_metrics(entry)
    log.info("Run recorded: %s", entry)


def list_runs(limit: int = 20) -> list[dict[str, Any]]:
    """Return the most recent pipeline run records (newest last)."""
    runs = _load().get("runs") or []
    if limit <= 0:
        return []
    return list(runs[-limit:])
