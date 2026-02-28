"""
pipeline/logger.py

Structured, production-safe logger for the Capital Architects pipeline.
Writes to logs/pipeline_YYYYMMDD.log with per-day rotation and console output.
"""

import logging
import os
from datetime import datetime
from pathlib import Path

_LOG_DIR = Path(__file__).parent.parent / "logs"


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger that simultaneously writes to:
      - logs/pipeline_YYYYMMDD.log  (DEBUG and above)
      - stdout console               (INFO and above)

    Idempotent: safe to call multiple times with the same name.
    """
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    log_file = _LOG_DIR / f"pipeline_{datetime.now().strftime('%Y%m%d')}.log"
    logger = logging.getLogger(name)

    # Guard against duplicate handlers on repeated imports
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # --- File handler ---
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)-8s] %(name)-20s — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    # --- Console handler ---
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
