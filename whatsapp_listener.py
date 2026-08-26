#!/usr/bin/env python3
"""
whatsapp_listener.py

This script provides a simple entry point for "WhatsApp Chat" interactions.
When a user (or a bot) sends a message like "REFRESH ANALYTICS",
this script can be invoked to trigger the autonomous feedback loop manually.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from agents.analyst import pull_and_analyze
from pipeline.health import inspect_health
from pipeline.logger import get_logger

log = get_logger("whatsapp-bridge")


def handle_message(message: str):
    message = message.upper().strip()

    if "REFRESH ANALYTICS" in message or "ANALYZE" in message:
        log.info("WhatsApp Command Received: REFRESH ANALYTICS")
        if pull_and_analyze():
            print("SUCCESS: Analytics loop complete. Winners updated.")
        else:
            print("ERROR: Failed to fetch analytics. Check logs/youtube_token.json.")

    elif "STATUS" in message:
        payload = inspect_health()
        label = "ok" if payload.get("ok") else "unhealthy"
        print(f"PIPELINE STATUS: {label}")
        print(f"last_run: {payload.get('last_run')}")
        print(f"age_hours: {payload.get('age_hours')}")
        print(f"stale: {payload.get('stale')}")
        if payload.get("abort_reason"):
            print(f"abort_reason: {payload['abort_reason']}")
        if payload.get("reason"):
            print(f"reason: {payload['reason']}")
        print("PIPELINE STATUS: Active (6-hourly cycle is enabled)")

    else:
        print(f"UNKNOWN COMMAND: {message}. Try 'REFRESH ANALYTICS' or 'STATUS'.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Simulate receiving a message via CLI argument
        handle_message(" ".join(sys.argv[1:]))
    else:
        print("Usage: python3 whatsapp_listener.py 'REFRESH ANALYTICS' or 'STATUS'")
        print("Usage: python3 whatsapp_listener.py 'REFRESH ANALYTICS'")
