"""
agents/publisher.py

Uploads finished videos to YouTube via the Data API v3.
Schedules at India high-traffic time slots:
  7:30 AM IST | 12:30 PM IST | 6:30 PM IST | 9:00 PM IST

Slot collision detection: checks existing scheduled videos before assigning.
Looks up to LOOKAHEAD_DAYS ahead to find an open slot.

Authentication: uses youtube_token.json (OAuth2 offline credentials).
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import ValidationError

from pipeline.logger import get_logger
from pipeline.schemas import YouTubeUploadResponse

log = get_logger("publisher")

load_dotenv(Path(__file__).parent.parent / ".env")

TOKEN_FILE = Path(__file__).parent.parent / "youtube_token.json"
CLIENT_SECRETS_FILE = Path(__file__).parent.parent / "client_secret.json"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

# India high-traffic publish slots (IST hours/minutes)
PREFERRED_SLOTS_IST = [
    (7, 30),    # 7:30 AM IST
    (12, 30),   # 12:30 PM IST
    (18, 30),   # 6:30 PM IST
    (21, 0),    # 9:00 PM IST
]

# How many days ahead to search for an open slot
LOOKAHEAD_DAYS = 4

# Tags added to every upload for discoverability
DEFAULT_TAGS = [
    "#Shorts", "finance", "money", "india", "tax", "rbi", "sebi",
    "investment", "stockmarket", "personalfinance", "capitalarchitects",
]


def _get_youtube_client():
    """
    Build and return an authenticated YouTube API client.
    Requires youtube_token.json to already exist (run auth_youtube.py first).
    """
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        raise RuntimeError(
            "google-api-python-client not installed. "
            "Run: pip install google-api-python-client google-auth-oauthlib"
        )

    if not TOKEN_FILE.exists():
        raise RuntimeError(
            f"YouTube token not found at {TOKEN_FILE}. "
            "Run auth_youtube.py to authenticate."
        )

    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def _ist_slot_to_utc(date: datetime, hour: int, minute: int) -> datetime:
    """
    Convert an IST hour:minute on a given date to timezone-aware UTC datetime.
    IST = UTC + 5:30
    """
    ist_dt = date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    utc_dt = ist_dt - timedelta(hours=5, minutes=30)
    return utc_dt.replace(tzinfo=timezone.utc)


def _fetch_occupied_slots(youtube) -> set[datetime]:
    """
    Retrieve all videos currently marked as scheduled (private + publishAt set).
    Returns a set of their publishAt datetimes (UTC, minute-precision).
    """
    occupied: set[datetime] = set()

    try:
        # Get uploads playlist
        channel_resp = youtube.channels().list(part="contentDetails", mine=True).execute()
        playlist_id = channel_resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

        request = youtube.playlistItems().list(
            part="contentDetails", playlistId=playlist_id, maxResults=50
        )
        while request:
            resp = request.execute()
            video_ids = [item["contentDetails"]["videoId"] for item in resp.get("items", [])]

            if video_ids:
                status_resp = youtube.videos().list(
                    part="status", id=",".join(video_ids)
                ).execute()
                for item in status_resp.get("items", []):
                    status = item.get("status", {})
                    if status.get("privacyStatus") == "private" and status.get("publishAt"):
                        dt = datetime.fromisoformat(status["publishAt"].replace("Z", "+00:00"))
                        occupied.add(dt.replace(second=0, microsecond=0, tzinfo=timezone.utc))

            request = youtube.playlistItems().list_next(request, resp)

    except (OSError, ValueError, KeyError, json.JSONDecodeError) as e:
        log.warning("Could not fetch scheduled videos for collision check: %s", e)

    return occupied


def _find_next_slot(youtube, start_from: datetime) -> str:
    """
    Find the next available India-friendly publish slot after start_from.
    Returns ISO 8601 UTC string (e.g. 2026-03-01T02:00:00Z).
    """
    occupied = _fetch_occupied_slots(youtube)
    log.debug("Found %d occupied slots", len(occupied))

    if start_from.tzinfo is None:
        search_base = start_from.replace(tzinfo=timezone.utc)
    else:
        search_base = start_from

    for day_offset in range(LOOKAHEAD_DAYS + 1):
        candidate_day = (search_base + timedelta(days=day_offset)).date()
        base = datetime(candidate_day.year, candidate_day.month, candidate_day.day)

        for hour, minute in PREFERRED_SLOTS_IST:
            utc_slot = _ist_slot_to_utc(base, hour, minute)
            # Must be at least 30 minutes in the future
            if utc_slot <= (datetime.now(timezone.utc) + timedelta(minutes=30)):
                continue
            # Check collision (within same hour bucket)
            slot_rounded = utc_slot.replace(second=0, microsecond=0)
            if slot_rounded not in occupied:
                log.info(
                    "Scheduled slot: %02d:%02d IST on %s (UTC: %s)",
                    hour, minute, candidate_day, utc_slot.isoformat(),
                )
                return utc_slot.strftime("%Y-%m-%dT%H:%M:%S") + "Z"

    # Fallback: 9 PM IST next day
    fallback_day = datetime.now() + timedelta(days=1)
    fallback_utc = _ist_slot_to_utc(fallback_day, 21, 0)
    log.warning("No free slot found in %d days — using fallback 9 PM IST next day", LOOKAHEAD_DAYS)
    return fallback_utc.strftime("%Y-%m-%dT%H:%M:%S") + "Z"


def _video_id_from_upload_response(response: dict) -> str:
    """Validate a YouTube videos.insert payload and return the video id."""
    return YouTubeUploadResponse.model_validate(response).id


def upload_video(video_path: Path, script: dict) -> Optional[str]:
    """
    Upload a finished video to the Capital Architects YouTube channel.

    Args:
        video_path: Path to the final MP4 file.
        script:     Approved script dict (provides title, description, tags).

    Returns:
        YouTube video ID string on success, None on failure.
    """
    from googleapiclient.http import MediaFileUpload

    title = script.get("title", "Finance News Short")[:100]
    description = script.get("description", "#Shorts #Finance #India")
    project_name = script.get("project_name", "")

    log.info("=== Publisher: uploading '%s' ===", project_name)

    try:
        youtube = _get_youtube_client()
    except RuntimeError as e:
        log.error("YouTube auth error: %s", e)
        return None

    # Schedule 1 day ahead (earliest free slot)
    start_from = datetime.now(timezone.utc) + timedelta(days=1)
    publish_at = _find_next_slot(youtube, start_from)

    ist_display = (
        datetime.fromisoformat(publish_at.replace("Z", "+00:00"))
        + timedelta(hours=5, minutes=30)
    ).strftime("%Y-%m-%d %H:%M IST")
    log.info("Publishing at: %s (%s)", publish_at, ist_display)

    # Tags: Use script-specific tags if available, else fallback to defaults
    script_tags = script.get("tags", [])
    if not isinstance(script_tags, list):
        script_tags = []

    # Merge script tags with defaults, set limit to ~20 total
    tags = (script_tags + DEFAULT_TAGS)[:25]

    # Build the upload metadata body
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "27",          # Education
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": {
            "privacyStatus": "private",  # Private until scheduled time
            "publishAt": publish_at,
            "selfDeclaredMadeForKids": False,
            "madeForKids": False,
        },
    }

    media = MediaFileUpload(str(video_path), chunksize=1024 * 1024, resumable=True)

    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    video_id = None
    try:
        from googleapiclient.errors import HttpError

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                log.debug("Upload progress: %d%%", int(status.progress() * 100))

        video_id = _video_id_from_upload_response(response)
        log.info("✅ Uploaded: https://youtu.be/%s (scheduled %s)", video_id, ist_display)

    except HttpError as e:
        log.error("Upload failed for '%s': %s", project_name, e)
        return None
    except (OSError, ValueError, KeyError, ValidationError) as e:
        log.error("Upload failed for '%s': %s", project_name, e)
        return None

    return video_id


if __name__ == "__main__":
    # Manual test: upload the first video in data/output/
    output_dir = Path(__file__).parent.parent / "data" / "output"
    videos = list(output_dir.glob("*_final.mp4"))
    if not videos:
        print("No videos in data/output/")
    else:
        # Load matching script from approved
        v = videos[0]
        story_hash = v.stem.split("_")[0]
        approved_dir = Path(__file__).parent.parent / "data" / "approved"
        script_file = approved_dir / f"approved_{story_hash}.json"
        if script_file.exists():
            script = json.loads(script_file.read_text())
            vid_id = upload_video(v, script)
            print(f"Uploaded: {vid_id}")
        else:
            print(f"No script found for hash {story_hash}")
