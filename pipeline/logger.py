"""
pipeline/logger.py

JSON-structured logger for the Capital Architects pipeline.
File records include timestamp, level, message, stage, run_id, duration_ms.
Console output stays human-readable for local runs.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOG_DIR = Path(__file__).parent.parent / "logs"


class JsonLogFormatter(logging.Formatter):
    """Emit one JSON object per log record for scheduled-pipeline debugging."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "stage": getattr(record, "stage", None),
            "run_id": getattr(record, "run_id", None),
            "duration_ms": getattr(record, "duration_ms", None),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps({k: v for k, v in payload.items() if v is not None})


def extra_fields(
    stage: str,
    run_id: str,
    duration_ms: int | None = None,
) -> dict[str, Any]:
    """Build logging extra= context for orchestrator stage transitions."""
    payload: dict[str, Any] = {"stage": stage, "run_id": run_id}
    if duration_ms is not None:
        payload["duration_ms"] = duration_ms
    return payload


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger that simultaneously writes to:
      - logs/pipeline_YYYYMMDD.log  (DEBUG and above, JSON lines)
      - stdout console               (INFO and above, human-readable)

    Idempotent: safe to call multiple times with the same name.
    """
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    log_file = _LOG_DIR / f"pipeline_{datetime.now().strftime('%Y%m%d')}.log"
    logger = logging.getLogger(name)

    # Guard against duplicate handlers on repeated imports
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(JsonLogFormatter())

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
            datefmt="%H:%M:%S",
        )
    )

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
