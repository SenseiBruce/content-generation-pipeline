#!/usr/bin/env python3
"""
auth_youtube.py

One-time YouTube OAuth2 authentication script.
Run this ONCE locally to generate youtube_token.json.

After running, youtube_token.json is used by the publisher agent
for all future uploads without re-authentication.

Usage:
    python3 auth_youtube.py

Prerequisites:
  1. Download your OAuth2 client credentials from Google Cloud Console
     (APIs & Services → Credentials → OAuth 2.0 Client IDs)
  2. Save the file as client_secret.json in the project root
  3. Enable the YouTube Data API v3 in Google Cloud Console
"""

import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

PROJECT_ROOT = Path(__file__).parent
CLIENT_SECRETS_FILE = PROJECT_ROOT / "client_secret.json"
TOKEN_FILE = PROJECT_ROOT / "youtube_token.json"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def authenticate() -> None:
    if not CLIENT_SECRETS_FILE.exists():
        print(f"❌ client_secret.json not found at: {CLIENT_SECRETS_FILE}")
        print("   Download it from Google Cloud Console → APIs → Credentials")
        return

    print("🔐 Starting OAuth2 flow — a browser window will open...")
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS_FILE), SCOPES)
    credentials = flow.run_local_server(port=0, prompt="consent")

    # Save credentials for reuse by the publisher agent
    token_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": list(credentials.scopes or SCOPES),
    }

    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    print(f"✅ Token saved to: {TOKEN_FILE}")
    print("   The pipeline will now use this token for all YouTube uploads.")
    print("   Refresh tokens are long-lived — you should not need to re-auth.")


if __name__ == "__main__":
    authenticate()
