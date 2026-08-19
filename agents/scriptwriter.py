"""
agents/scriptwriter.py

Generates structured YouTube Shorts scripts for each prioritized story.
Uses GPT-4o via OpenRouter API (OPENROUTER_MODEL=openai/gpt-4o).

Output per story: strict JSON matching the Capital Architects schema.
Saved to data/scripts/draft_<story_hash>.json
"""

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import ValidationError

from pipeline import http_client
from pipeline.errors import PipelineValidationError
from pipeline.http_client import RequestException
from pipeline.logger import get_logger
from pipeline.schemas import ScriptSchema

log = get_logger("scriptwriter")

load_dotenv(Path(__file__).parent.parent / ".env")

OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
SCRIPT_MODEL: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "script_system.txt"
SCRIPTS_DIR = Path(__file__).parent.parent / "data" / "scripts"

SCHEMA_TEMPLATE = {
    "project_name": "30 chars max",
    "series_color": "#FF6B35",
    "title": "SEO focus keywords here",
    "description": "250-350 words + hashtags + specific CTA",
    "tags": ["15-20 SEO high-volume financial keywords"],
    "scenes": [
        {
            "id": 1,
            "voice_over": "15-22 word energetic hook narration here using specific numbers/facts.",
            "image_prompt": "Cinematic metaphorical scene, no text, vertical 9:16",
            "caption": {"text": "5-8 word bold caption"},
        },
        {
            "id": 2,
            "voice_over": "15-22 words explaining the context and depth of the news.",
            "image_prompt": "Metaphorical visual, no text",
            "caption": {"text": "5-8 word bold caption"},
        },
        {
            "id": 3,
            "voice_over": "15-22 words explaining exact impact on Indian taxes or savings.",
            "image_prompt": "Metaphorical visual, no text",
            "caption": {"text": "5-8 word bold caption"},
        },
        {
            "id": 4,
            "voice_over": (
                "15-22 words giving a SPECIFIC ACTIONABLE MOVE "
                "(e.g. check Section 80C, buy gold bond)."
            ),
            "image_prompt": "Metaphorical visual, no text",
            "caption": {"text": "5-8 word actionable caption"},
        },
        {
            "id": 5,
            "voice_over": "15-22 words for recap and urgent Capital Architects subscription push.",
            "image_prompt": "Metaphorical visual, no text",
            "caption": {"text": "5-8 word CTA caption"},
        },
    ],
    "metadata": {
        "source_url": "",
        "original_title": "",
        "fact_check_status": "pending",
        "story_hash": "",
        "categories": {"topics": [], "emotions": [], "audience": []},
    },
}


def _load_system_prompt() -> str:
    """Load the script generation system prompt from disk."""
    if SYSTEM_PROMPT_FILE.exists():
        return SYSTEM_PROMPT_FILE.read_text(encoding="utf-8").strip()
    log.warning("System prompt file missing; using inline fallback.")
    return (
        "You are a professional Indian finance YouTube Shorts scriptwriter. "
        "Output only valid JSON."
    )


def _call_openrouter(system: str, user: str) -> str:
    """
    Send a chat completion request to OpenRouter.
    Returns raw response text.
    Raises on persistent failure after 3 retries.
    """
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set.")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/capital-architects",
        "X-Title": "Capital Architects Script Pipeline",
    }
    payload = {
        "model": SCRIPT_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.7,
        "max_tokens": 1200,
    }

    for attempt in range(3):
        try:
            resp = http_client.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except (RequestException, KeyError, IndexError, TypeError, ValueError) as e:
            log.warning("OpenRouter attempt %d failed: %s", attempt + 1, e)
            if attempt < 2:
                time.sleep(2 ** (attempt + 1))

    raise RuntimeError("OpenRouter failed after 3 attempts.")


def _extract_json(raw: str) -> dict:
    """
    Extract JSON object from raw LLM response.
    Handles markdown code fences and trailing noise.
    """
    # Strip markdown fences if present
    clean = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

    # Try direct parse first
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass

    # Try extracting first {...} block
    match = re.search(r"\{.*\}", clean, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from LLM output:\n{raw[:300]}")


def _build_user_prompt(story: dict) -> str:
    """Compose the user-facing prompt for a single story."""
    return (
        f"Generate a YouTube Shorts script for this India finance news story.\n\n"
        f"News Title: {story.get('title', '')}\n"
        f"Source: {story.get('source', 'Unknown')}\n"
        f"News URL: {story.get('link', '')}\n\n"
        f"Priority Score: {story.get('priority_score', 0)}/100\n\n"
        f"Follow the schema exactly:\n{json.dumps(SCHEMA_TEMPLATE, indent=2)}\n\n"
        f"Fill story_hash with: {story.get('hash', '')}\n"
        f"Fill source_url with: {story.get('link', '')}\n"
        f"Fill original_title with: {story.get('title', '')}\n\n"
        f"Return ONLY the JSON object. No explanation, no markdown fences."
    )


def _validate_script(script: dict) -> ScriptSchema:
    """
    Validate the generated script against ScriptSchema.
    Raises PipelineValidationError on structural or content-rule failures.
    """
    try:
        return ScriptSchema.model_validate(script)
    except ValidationError as exc:
        raise PipelineValidationError(str(exc)) from exc


def generate_script(story: dict) -> Optional[dict]:
    """
    Generate a Shorts script for a single story.
    Returns the parsed script dict, or None on unrecoverable failure.
    """
    title = story.get("title", "?")
    log.info("Generating script for: %s", title[:70])

    system = _load_system_prompt()
    user = _build_user_prompt(story)

    try:
        raw = _call_openrouter(system, user)
        script = _extract_json(raw)
    except (RuntimeError, ValueError, json.JSONDecodeError) as e:
        log.error("Script generation failed for '%s': %s", title[:60], e)
        return None

    # Inject metadata in case LLM omitted them
    script.setdefault("metadata", {})
    script["metadata"]["story_hash"] = story.get("hash", "")
    script["metadata"]["source_url"] = story.get("link", "")
    script["metadata"]["original_title"] = story.get("title", "")
    script["metadata"]["fact_check_status"] = "pending"

    try:
        _validate_script(script)
    except PipelineValidationError as e:
        log.warning("Script validation issues for '%s': %s", title[:60], e)
        # Attach validation notes but still return — the judge will decide

    # Save draft
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    h = story.get("hash", hashlib.md5(title.encode()).hexdigest())
    draft_file = SCRIPTS_DIR / f"draft_{h}.json"
    with open(draft_file, "w", encoding="utf-8") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)

    log.info("Draft saved: %s", draft_file)
    return script


def generate_all(stories: List[dict]) -> List[dict]:
    """Generate scripts for a list of prioritized stories. Returns successful scripts."""
    log.info("=== Scriptwriter: generating %d scripts ===", len(stories))
    results = []
    for story in stories:
        script = generate_script(story)
        if script:
            results.append(script)
    log.info("Scriptwriter: %d/%d scripts generated successfully", len(results), len(stories))
    return results


if __name__ == "__main__":
    prioritized_file = (
        Path(__file__).parent.parent / "data" / "prioritized" / "selected_stories.json"
    )
    if not prioritized_file.exists():
        print("No prioritized stories found. Run prioritizer first.")
    else:
        with open(prioritized_file) as f:
            stories = json.load(f)
        scripts = generate_all(stories)
        print(f"Generated {len(scripts)} scripts.")
