"""
agents/prioritizer.py

Scores and ranks raw news stories using the OpenRouter API (stepfun-3.5-flash:free).
Applies a weighted dual-score (pocket impact + search intent) to each story.
Selects the top 5 stories and writes selected_stories.json to data/prioritized/.

Scoring rubric passed to the LLM:
  - Pocket Impact (0-60): Does this directly affect an Indian's money?
  - Search Intent (0-40): Would an Indian actively search for this right now?

Combined score: pocket_impact + search_intent (max 100).
Only stories scoring >= 60 are eligible for te top-5.
"""

import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv

from pipeline import http_client
from pipeline.http_client import RequestException
from pipeline.logger import get_logger

log = get_logger("prioritizer")

load_dotenv(Path(__file__).parent.parent / ".env")

OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
# Provide a reliable, cheap model for ranking (Gemini 2.0 Flash Lite handles format well)
RANKING_MODEL = "google/gemini-2.0-flash-lite-001"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

PRIORITIZED_DIR = Path(__file__).parent.parent / "data" / "prioritized"
TOP_N = 5
MIN_SCORE = 60           # Stories below this are discarded
MAX_WORKERS = 2          # Reduced to avoid 429 Too Many Requests
MAX_CANDIDATES = 25      # Cap the number of stories scored per run
ANALYTICS_FEEDBACK_FILE = Path(__file__).parent.parent / "data" / "analytics_feedback.json"


def _load_analytics_insights() -> str:
    """Load insights from past video performance (winning/losing topics)."""
    if not ANALYTICS_FEEDBACK_FILE.exists():
        return "No specific analytics yet."
    try:
        with open(ANALYTICS_FEEDBACK_FILE, "r") as f:
            data = json.load(f)
        insights = data.get("performance_insights", [])
        winners = data.get("winning_keywords", [])
        losers = data.get("losing_keywords", [])

        prompt_block = (
            "--- Recent Analytics Insights ---\n"
            "Winning Topics/Keywords: {}\n"
            "Losing Topics/Keywords: {}\n"
            "Performance Trends: {}\n"
            "-------------------------------"
        ).format(", ".join(winners), ", ".join(losers), ". ".join(insights))
        return prompt_block
    except (json.JSONDecodeError, OSError, TypeError, KeyError) as e:
        log.warning("Could not load analytics feedback: %s", e)
        return "No insights available."


def _score_story_via_llm(story: dict) -> Tuple[int, dict]:
    """
    Call OpenRouter with a structured prompt asking for two sub-scores.
    Returns (combined_score, story).
    """
    title = story.get("title", "")
    source = story.get("source", "Unknown")

    if not title:
        return 0, story

    insights = _load_analytics_insights()

    prompt = (
        "You are a content strategist for 'Capital Architects', "
        "an Indian finance YouTube Shorts channel.\n"
        "Audience: Common Indian people (salaried class, investors, small business owners).\n\n"
        "{}\n\n"
        "News Title: {}\n"
        "Source: {}\n\n"
        "Score this story on TWO dimensions:\n"
        "1. POCKET_IMPACT (0-60): How directly does this affect an Indian person's money "
        "(taxes, loans, savings, inflation, RBI policy, SEBI rules)?\n"
        "2. SEARCH_INTENT (0-40): Would ordinary Indians be actively searching "
        "for this topic today?\n\n"
        "MANDATORY RULE: If the story is about the SHARE MARKET, STOCK TRADING, "
        "NIFTY, SENSEX or IPOs, "
        "give it a TOTAL SCORE of 0. We avoid these topics.\n\n"
        "GUIDANCE: If a story aligns with the Winning Topics/Keywords in the insights above, "
        "boost its Search Intent score by +10 (max 40). If it matches Losing Topics, "
        "reduce both scores significantly.\n\n"
        "IMPORTANT: If the story has NO financial relevance to India, both scores MUST be 0.\n\n"
        "Respond in EXACTLY this format (no extra text):\n"
        "POCKET_IMPACT: <number>\n"
        "SEARCH_INTENT: <number>\n"
        "REASON: <one sentence>"
    ).format(insights, title, source)

    headers = {
        "Authorization": "Bearer {}".format(OPENROUTER_API_KEY),
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/capital-architects",
    }
    payload = {
        "model": RANKING_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 120,
        "temperature": 0.2,
    }

    for attempt in range(3):
        try:
            resp = http_client.post(OPENROUTER_BASE_URL, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"].strip()

            pocket_match = re.search(r"POCKET_IMPACT:\s*(\d+)", text, re.I)
            search_match = re.search(r"SEARCH_INTENT:\s*(\d+)", text, re.I)

            if not pocket_match or not search_match:
                raise ValueError(f"Could not parse scores. Raw response: {text[:150]!r}")

            pocket = max(0, min(60, int(pocket_match.group(1))))
            search = max(0, min(40, int(search_match.group(1))))
            combined = pocket + search

            reason_match = re.search(r"REASON:\s*(.+)", text, re.I)
            reason = reason_match.group(1).strip() if reason_match else ""

            log.debug("Score %d | %.60s | %s", combined, title, reason)
            return combined, story

        except (RequestException, AttributeError, KeyError, ValueError) as e:
            log.warning("Scoring attempt %d failed for '%.50s': %s", attempt + 1, title, e)
            time.sleep(2 ** attempt)

    log.error("All scoring attempts failed for: %.60s", title)
    return 0, story


def prioritize(stories: List[dict]) -> List[dict]:
    """
    Score all candidate stories in parallel and return the top 5.
    """
    if not OPENROUTER_API_KEY:
        log.error("OPENROUTER_API_KEY not set; cannot score stories.")
        return []

    # Cap to MAX_CANDIDATES to control API usage and runtime
    candidates = stories[:MAX_CANDIDATES]
    log.info("Scoring %d candidate stories (top %d cap)", len(candidates), MAX_CANDIDATES)

    scored: List[Tuple[int, dict]] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_score_story_via_llm, s): s for s in candidates}
        for future in as_completed(futures):
            try:
                score, story = future.result()
                if score >= MIN_SCORE:
                    scored.append((score, story))
            except (RuntimeError, ValueError, OSError) as e:
                log.error("Worker error: %s", e)

    # Sort descending, take top N
    scored.sort(key=lambda x: x[0], reverse=True)
    top = []
    for score, story in scored[:TOP_N]:
        story["priority_score"] = score
        top.append(story)

    # Persist for downstream agents
    PRIORITIZED_DIR.mkdir(parents=True, exist_ok=True)
    out_file = PRIORITIZED_DIR / "selected_stories.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(top, f, indent=2, ensure_ascii=False)

    log.info("Selected top %d stories -> %s", len(top), out_file)
    return top


if __name__ == "__main__":
    raw_dir = Path(__file__).parent.parent / "data" / "raw"
    batches = sorted(raw_dir.glob("batch_*.json"), reverse=True)
    if not batches:
        print("No raw batches found. Run watchtower first.")
    else:
        with open(batches[0]) as f:
            stories = json.load(f)
        top = prioritize(stories)
        print("Top {} stories selected.".format(len(top)))
        for s in top:
            print("  [{}] {:.80s}".format(s["priority_score"], s["title"]))
