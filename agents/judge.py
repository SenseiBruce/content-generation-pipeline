"""
agents/judge.py

Weighted script judge for Capital Architects.

Scoring (out of 100):
  Hook Strength      30 pts
  Search Intent      25 pts
  Practical Value    25 pts
  Retention          10 pts
  Emotional Trigger  10 pts

Flow:
  - score >= 85  →  APPROVED  →  write to data/approved/
  - 60 <= score < 85  →  IMPROVE  →  LLM rewrites script, re-score (up to 3 loops)
  - score < 60  →  REJECT  →  write to data/rejected/
  - After 3 loops with score still < 85  →  REJECT for human review

Uses GPT-4o via OpenRouter for both scoring and rewriting.
"""

import json
import os
import re
import time
from pathlib import Path
from typing import List, Optional, Tuple

from dotenv import load_dotenv

from pipeline import http_client
from pipeline.http_client import RequestException
from pipeline.logger import get_logger

log = get_logger("judge")

load_dotenv(Path(__file__).parent.parent / ".env")

OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
JUDGE_MODEL: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

JUDGE_SYSTEM_FILE = Path(__file__).parent.parent / "prompts" / "judge_system.txt"
SCRIPTS_DIR = Path(__file__).parent.parent / "data" / "scripts"
APPROVED_DIR = Path(__file__).parent.parent / "data" / "approved"
REJECTED_DIR = Path(__file__).parent.parent / "data" / "rejected"

APPROVAL_THRESHOLD = 85
IMPROVE_THRESHOLD = 60
MAX_LOOPS = 3


def _load_judge_prompt() -> str:
    if JUDGE_SYSTEM_FILE.exists():
        return JUDGE_SYSTEM_FILE.read_text(encoding="utf-8").strip()
    return "You are a strict YouTube Shorts editorial judge for Indian finance content."


def _call_judge_llm(system: str, user: str) -> str:
    """Call OpenRouter and return raw text response."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set.")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/capital-architects",
    }
    payload = {
        "model": JUDGE_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.4,
        "max_tokens": 2000,
    }

    for attempt in range(3):
        try:
            resp = http_client.post(OPENROUTER_URL, headers=headers, json=payload, timeout=90)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except (RequestException, KeyError, IndexError, TypeError, ValueError) as e:
            log.warning("Judge LLM attempt %d failed: %s", attempt + 1, e)
            if attempt < 2:
                time.sleep(2 ** (attempt + 1))

    raise RuntimeError("Judge LLM failed after 3 attempts.")


def _parse_score(response_text: str) -> Tuple[int, str, str]:
    """
    Parse scoring block from judge response.
    Returns (total_score, verdict, feedback).
    """

    def extract_int(pattern: str, text: str, default: int = 0) -> int:
        m = re.search(pattern, text, re.I)
        return int(m.group(1)) if m else default

    hook = extract_int(r"HOOK_STRENGTH:\s*(\d+)", response_text)
    search = extract_int(r"SEARCH_INTENT:\s*(\d+)", response_text)
    practical = extract_int(r"PRACTICAL_VALUE:\s*(\d+)", response_text)
    retention = extract_int(r"RETENTION:\s*(\d+)", response_text)
    emotional = extract_int(r"EMOTIONAL_TRIGGER:\s*(\d+)", response_text)

    # Try to get the explicit TOTAL if LLM provided it, else compute it
    stated_total = extract_int(r"TOTAL:\s*(\d+)", response_text, default=-1)
    computed = hook + search + practical + retention + emotional
    total = stated_total if stated_total >= 0 else computed

    verdict_match = re.search(r"VERDICT:\s*(APPROVED|IMPROVE|REJECT)", response_text, re.I)
    verdict = (
        verdict_match.group(1).upper()
        if verdict_match
        else (
            "APPROVED"
            if total >= APPROVAL_THRESHOLD
            else "IMPROVE"
            if total >= IMPROVE_THRESHOLD
            else "REJECT"
        )
    )

    feedback_match = re.search(
        r"FEEDBACK:\s*(.+?)(?=IMPROVED_SCRIPT:|$)",
        response_text,
        re.DOTALL | re.I,
    )
    feedback = feedback_match.group(1).strip() if feedback_match else ""

    log.debug(
        "Scores — Hook:%d Search:%d Practical:%d Retention:%d Emotional:%d → Total:%d (%s)",
        hook,
        search,
        practical,
        retention,
        emotional,
        total,
        verdict,
    )
    return total, verdict, feedback


def _extract_improved_script(response_text: str) -> Optional[dict]:
    """
    If the judge included an IMPROVED_SCRIPT block, parse and return it.
    Returns None if not present or unparseable.
    """
    match = re.search(r"IMPROVED_SCRIPT:\s*(\{.*\})", response_text, re.DOTALL | re.I)
    if not match:
        return None
    try:
        raw = match.group(1).strip()
        return json.loads(raw)
    except json.JSONDecodeError:
        # Attempt to extract first {...} block from the remaining text
        sub_match = re.search(r"\{.*\}", match.group(1), re.DOTALL)
        if sub_match:
            try:
                return json.loads(sub_match.group())
            except json.JSONDecodeError:
                pass
    log.warning("Found IMPROVED_SCRIPT marker but could not parse JSON.")
    return None


def _build_judge_prompt(script: dict, loop: int, prior_feedback: str = "") -> str:
    """Compose the user-facing prompt for a judge call."""
    context = ""
    if loop > 1 and prior_feedback:
        context = (
            f"\n\nThis is loop {loop}/3. Prior feedback was:\n{prior_feedback}\n"
            "The script has been updated. Score it again.\n"
        )

    return (
        f"Score and judge the following YouTube Shorts script.{context}\n\n"
        f"```json\n{json.dumps(script, indent=2)}\n```\n\n"
        "Follow the scoring format exactly as defined in your system prompt.\n"
        "If verdict is IMPROVE, provide the full improved script JSON after IMPROVED_SCRIPT:."
    )


def judge_script(script: dict) -> Tuple[str, dict, int]:
    """
    Run the judge loop on a single script.

    Returns:
      (decision, final_script, final_score)
      decision: "APPROVED" | "REJECTED"
    """
    project_name = script.get("project_name", "unknown")
    log.info("Judging: %s", project_name)

    system = _load_judge_prompt()
    current_script = script
    prior_feedback = ""

    for loop in range(1, MAX_LOOPS + 1):
        log.info("  Judge loop %d/%d for: %s", loop, MAX_LOOPS, project_name)

        try:
            response = _call_judge_llm(
                system, _build_judge_prompt(current_script, loop, prior_feedback)
            )
        except RuntimeError as e:
            log.error("Judge call failed: %s — marking as REJECTED", e)
            return "REJECTED", current_script, 0

        score, verdict, feedback = _parse_score(response)
        log.info("  Loop %d score: %d — %s", loop, score, verdict)

        if verdict == "APPROVED" or score >= APPROVAL_THRESHOLD:
            log.info("  ✅ APPROVED (score=%d)", score)
            return "APPROVED", current_script, score

        if verdict == "REJECT" or score < IMPROVE_THRESHOLD:
            log.info("  ❌ REJECTED (score=%d, below threshold)", score)
            return "REJECTED", current_script, score

        # IMPROVE path: try to use the rewritten script
        if loop < MAX_LOOPS:
            improved = _extract_improved_script(response)
            if improved:
                log.info("  ♻️  Applying improved script for next loop")
                # Preserve metadata from original
                improved.setdefault("metadata", current_script.get("metadata", {}))
                current_script = improved
            else:
                log.warning("  Judge said IMPROVE but gave no new script; retrying same script")
            prior_feedback = feedback

    # After MAX_LOOPS without reaching 85
    log.warning("  ❌ Max loops reached — score < 85. Sending to rejected/human_review.")
    return "REJECTED", current_script, score


def judge_all(scripts: List[dict]) -> Tuple[List[dict], List[dict]]:
    """
    Judge all generated scripts.
    Returns (approved_scripts, rejected_scripts).
    """
    APPROVED_DIR.mkdir(parents=True, exist_ok=True)
    REJECTED_DIR.mkdir(parents=True, exist_ok=True)

    approved = []
    rejected = []

    for script in scripts:
        h = script.get("metadata", {}).get("story_hash", "unknown")
        decision, final_script, score = judge_script(script)

        final_script["judge_score"] = score
        final_script["judge_decision"] = decision

        if decision == "APPROVED":
            out_file = APPROVED_DIR / f"approved_{h}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(final_script, f, indent=2, ensure_ascii=False)
            approved.append(final_script)
        else:
            out_file = REJECTED_DIR / f"rejected_{h}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(final_script, f, indent=2, ensure_ascii=False)
            rejected.append(final_script)

    log.info(
        "=== Judge complete: %d approved, %d rejected ===",
        len(approved),
        len(rejected),
    )
    return approved, rejected


if __name__ == "__main__":
    scripts_dir = Path(__file__).parent.parent / "data" / "scripts"
    drafts = list(scripts_dir.glob("draft_*.json"))
    if not drafts:
        print("No draft scripts found.")
    else:
        scripts = [json.loads(p.read_text()) for p in drafts]
        approved, rejected = judge_all(scripts)
        print(f"Approved: {len(approved)} | Rejected: {len(rejected)}")
