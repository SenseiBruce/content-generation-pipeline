"""
agents/watchtower.py

Fetches India-focused finance news from multiple RSS sources.
Deduplicates using MD5 hash of (title + link).
Saves a timestamped batch JSON file to data/raw/.

Sources:
  - RBI Press Releases (via Google News geo-targeted RSS)
  - Economic Times Finance
  - Bloomberg Asia Finance (via Google News)
  - Government of India PIB
  - SEBI updates (via Google News)
  - India Personal Finance (via Google News)
  - India Stock Market (via Google News)
"""

import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import feedparser

from pipeline.logger import get_logger
from pipeline.state import is_seen

log = get_logger("watchtower")

# -----------------------------------------------------------------
# RSS sources — India finance only.
# Global news is included only via geo-restricted Google News queries.
# -----------------------------------------------------------------
RSS_SOURCES = [
    {
        "name": "RBI Press Releases",
        # RBI does not publish a standard RSS feed; using geo-targeted Google News instead
        "url": "https://news.google.com/rss/search?q=RBI+Reserve+Bank+India+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
    },
    {
        "name": "Economic Times Finance",
        "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    },
    {
        "name": "Bloomberg Asia Finance",
        "url": "https://news.google.com/rss/search?q=Bloomberg+india+finance+economy+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
    },
    {
        "name": "Government of India PIB",
        "url": "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3",
    },
    {
        "name": "SEBI Updates",
        "url": "https://news.google.com/rss/search?q=SEBI+india+regulation+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
    },
    {
        "name": "India Personal Finance",
        "url": "https://news.google.com/rss/search?q=income+tax+india+budget+inflation+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
    },
    {
        "name": "India Stock Market",
        "url": "https://news.google.com/rss/search?q=nifty+sensex+stock+market+india+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
    },
]

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"


def _story_hash(title: str, link: str) -> str:
    """Produce a stable MD5 fingerprint for a story to detect duplicates."""
    return hashlib.md5((title + link).encode("utf-8")).hexdigest()


def _fetch_single_source(source: dict) -> List[dict]:
    """
    Fetch one RSS feed and return a list of story dicts.
    Returns empty list on any network or parse error.
    """
    name = source["name"]
    url = source["url"]
    log.debug("Fetching: %s", name)

    try:
        feed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        log.warning("Feed fetch error [%s]: %s", name, e)
        return []

    if feed.bozo:
        log.debug("Feed parse warning [%s]: %s", name, feed.bozo_exception)

    stories = []
    for entry in feed.entries:
        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "").strip()
        pub_date = getattr(entry, "published", "")

        if not title or not link:
            continue

        h = _story_hash(title, link)

        # Skip if already processed in a prior run
        if is_seen(h):
            continue

        stories.append(
            {
                "hash": h,
                "title": title,
                "link": link,
                "pub_date": pub_date,
                "source": name,
                "fetched_at": datetime.now().isoformat(),
            }
        )

    log.info("[%s] fetched %d new stories", name, len(stories))
    return stories


def fetch_all_news() -> List[dict]:
    """
    Parallel-fetch all RSS sources and save a deduplicated batch.
    Returns the combined list of new stories.
    """
    log.info("=== Watchtower: fetching news from %d sources ===", len(RSS_SOURCES))
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    all_stories: List[dict] = []
    seen_in_batch = set()  # within-batch dedup

    with ThreadPoolExecutor(max_workers=len(RSS_SOURCES)) as pool:
        futures = {pool.submit(_fetch_single_source, src): src for src in RSS_SOURCES}
        for future in as_completed(futures):
            try:
                stories = future.result()
                for story in stories:
                    if story["hash"] not in seen_in_batch:
                        all_stories.append(story)
                        seen_in_batch.add(story["hash"])
            except Exception as e:
                log.error("Unexpected error in feed worker: %s", e)

    if not all_stories:
        log.warning("No new stories found across all sources.")
        return []

    # Persist batch
    batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_file = RAW_DIR / "batch_{}.json".format(batch_id)
    with open(batch_file, "w", encoding="utf-8") as f:
        json.dump(all_stories, f, indent=2, ensure_ascii=False)

    log.info("Saved %d stories to %s", len(all_stories), batch_file)
    return all_stories


if __name__ == "__main__":
    stories = fetch_all_news()
    print("Fetched {} new stories.".format(len(stories)))
