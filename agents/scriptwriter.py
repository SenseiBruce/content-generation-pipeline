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

import requests
from dotenv import load_dotenv

from pipeline.logger import get_logger

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
            "voice_over": "15-22 words giving a SPECIFIC ACTIONABLE MOVE (e.g. check Section 80C, buy gold bond).",
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
    return "You are a professional Indian finance YouTube Shorts scriptwriter. Output only valid JSON."


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
            resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
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


def _validate_script(script: dict) -> List[str]:
    """
    Validate the generated script against the strict output schema.
    Returns a list of violation messages (empty = valid).
    """
    errors = []

    scenes = script.get("scenes", [])
    if len(scenes) != 5:
        errors.append(f"Expected 5 scenes for 30s+ length, got {len(scenes)}")

    for scene in scenes:
        vo = scene.get("voice_over", "")
        word_count = len(vo.split())
        if not (15 <= word_count <= 25):
            errors.append(f"Scene {scene.get('id', '?')}: voice_over has {word_count} words (need 15-22 for duration)")

        img = scene.get("image_prompt", "").lower()
        forbidden = ["text", "letter", "word", "caption", "watermark", "banner", "title", "label", "font"]
        for term in forbidden:
            if term in img:
                errors.append(f"Scene {scene.get('id', '?')}: image_prompt contains forbidden term '{term}'")

        caption_text = scene.get("caption", {}).get("text", "")
        cap_words = len(caption_text.split())
        if not (4 <= cap_words <= 10):
            errors.append(f"Scene {scene.get('id', '?')}: caption has {cap_words} words (need 5-8)")

    title = script.get("title", "")
    if len(title) > 70:
        errors.append(f"Title too long: {len(title)} chars (max 70 for SEO)")

    desc = script.get("description", "")
    word_count_desc = len(desc.split())
    if not (250 <= word_count_desc <= 400):
        errors.append(f"Description word count {word_count_desc} (need 250-350 for SEO weight)")

    if len(script.get("project_name", "")) > 30:
        errors.append("project_name exceeds 30 characters")

    return errors


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
    except Exception as e:
        log.error("Script generation failed for '%s': %s", title[:60], e)
        return None

    # Inject metadata in case LLM omitted them
    script.setdefault("metadata", {})
    script["metadata"]["story_hash"] = story.get("hash", "")
    script["metadata"]["source_url"] = story.get("link", "")
    script["metadata"]["original_title"] = story.get("title", "")
    script["metadata"]["fact_check_status"] = "pending"

    # Validate
    errors = _validate_script(script)
    if errors:
        log.warning("Script validation issues for '%s': %s", title[:60], errors)
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
    prioritized_file = Path(__file__).parent.parent / "data" / "prioritized" / "selected_stories.json"
    if not prioritized_file.exists():
        print("No prioritized stories found. Run prioritizer first.")
    else:
        with open(prioritized_file) as f:
            stories = json.load(f)
        scripts = generate_all(stories)
        print(f"Generated {len(scripts)} scripts.")
