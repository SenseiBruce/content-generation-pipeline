"""Optional failure webhook so a silent 6-hour OpenClaw miss can still alert."""

from __future__ import annotations

import os
from typing import Any

from pipeline import http_client
from pipeline.http_client import RequestException
from pipeline.logger import get_logger

log = get_logger("alerts")


def notify_failure(reason: str, summary: dict[str, Any]) -> bool:
    """
    POST a JSON payload to ERROR_WEBHOOK_URL when the pipeline aborts.

    Returns True if a webhook was configured and the POST succeeded.
    No-ops (False) when ERROR_WEBHOOK_URL is unset so local/offline runs stay quiet.
    """
    url = os.getenv("ERROR_WEBHOOK_URL", "").strip()
    if not url:
        log.debug("ERROR_WEBHOOK_URL unset — skipping abort webhook.")
        return False

    payload = {"event": "pipeline_aborted", "reason": reason, "summary": summary}
    try:
        resp = http_client.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        log.info("Abort webhook delivered to %s", url)
        return True
    except RequestException as exc:
        log.warning("Abort webhook failed: %s", exc)
        return False
