"""
agents/analyst.py

Autonomous Analyst: Pulls YouTube stats, identifies winning/losing topics,
and updates analytics_feedback.json to guide the next pipeline run.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

from pipeline.logger import get_logger

log = get_logger("analyst")

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

FEEDBACK_FILE = PROJECT_ROOT / "data" / "analytics_feedback.json"
TOKEN_FILE = PROJECT_ROOT / "youtube_token.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]


def _get_youtube_client():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    if not TOKEN_FILE.exists():
        log.warning("YouTube token missing; cannot auto-pull analytics.")
        return None

    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def pull_and_analyze():
    """
    1. Fetch statistics for the last 20 videos.
    2. Rank them by views/engagement.
    3. Extract winning vs. losing keywords.
    4. Update analytics_feedback.json.
    """
    log.info("=== Analyst: Pulling latest YouTube performance data ===")

    youtube = _get_youtube_client()
    if not youtube:
        return False

    try:
        # 1. Get channel's uploads playlist
        ch_resp = youtube.channels().list(part="contentDetails", mine=True).execute()
        uploads_id = ch_resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

        # 2. Get last 20 videos
        v_resp = (
            youtube.playlistItems()
            .list(part="snippet,contentDetails", playlistId=uploads_id, maxResults=20)
            .execute()
        )

        video_items = v_resp.get("items", [])
        if not video_items:
            log.info("No videos found on channel yet.")
            return False

        vids_data = []
        for item in video_items:
            v_id = item["contentDetails"]["videoId"]
            title = item["snippet"]["title"]

            # Fetch stats for each video
            s_resp = youtube.videos().list(part="statistics,snippet", id=v_id).execute()
            if not s_resp["items"]:
                continue

            stats = s_resp["items"][0]["statistics"]
            tags = s_resp["items"][0]["snippet"].get("tags", [])

            views = int(stats.get("viewCount", 0))
            likes = int(stats.get("likeCount", 0))
            engagement = views + (likes * 5)  # Weight likes 5x views

            vids_data.append(
                {
                    "title": title,
                    "tags": [t.lower() for t in tags],
                    "score": engagement,
                    "views": views,
                }
            )

        if not vids_data:
            return False

        # Sort by engagement score
        vids_data.sort(key=lambda x: x["score"], reverse=True)

        # Split into top 5 (winners) and bottom 5 (losers)
        winner_vids = vids_data[:5]
        loser_vids = vids_data[-5:] if len(vids_data) > 10 else []

        winners = []
        for v in winner_vids:
            # Pick tags that appear in high-performing videos
            winners.extend(v["tags"][:3])
            # Also extract keywords from title (naive)
            for word in v["title"].split():
                if len(word) > 3:
                    winners.append(word.lower())

        losers = []
        for v in loser_vids:
            losers.extend(v["tags"][:2])

        # De-duplicate and filter
        winners = list(set([w for w in winners if len(w) > 2]))[:10]
        losers = list(set([kw for kw in losers if len(kw) > 2]))[:10]

        # Final set logic: Winners minus Losers (just in case)
        winners = [w for w in winners if w not in losers]

        # Update the file
        update_feedback(winners=winners, losers=losers)
        log.info("Analytics loop complete. Winners: %s", ", ".join(winners))
        return True

    except (OSError, ValueError, KeyError, TypeError) as e:
        log.error("Autonomous analysis failed: %s", e)
        return False


def update_feedback(
    winners: Optional[list] = None,
    losers: Optional[list] = None,
    insights: Optional[list] = None,
):
    """Update the analytics feedback file."""
    if not FEEDBACK_FILE.exists():
        data: dict[str, Any] = {
            "performance_insights": [],
            "winning_keywords": [],
            "losing_keywords": [],
        }
    else:
        with open(FEEDBACK_FILE, "r") as f:
            data = json.load(f)

    if winners:
        # Use more recent data primarily, but keep a rolling history
        data["winning_keywords"] = winners

    if losers:
        data["losing_keywords"] = losers

    data["last_updated"] = datetime.now().isoformat()
    # Basic static insight based on findings
    if winners:
        data["performance_insights"] = [
            (
                "Currently, topics related to "
                f"{', '.join(winners[:3])} are driving the highest engagement."
            )
        ]

    with open(FEEDBACK_FILE, "w") as f:
        json.dump(data, f, indent=2)
    return True


if __name__ == "__main__":
    pull_and_analyze()
