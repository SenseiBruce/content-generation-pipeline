"""
agents/imager.py

Generates one image per scene using the Runware REST API (direct HTTP).
Enforces:
  - 1080x1920 (9:16 vertical for YouTube Shorts)
  - Negative prompt: no text, letters, watermark
  - Photorealistic / cinematic style

Uses the Runware v1 REST API directly via requests — no SDK required.
Works on Python 3.9+.
API docs: https://docs.runware.ai

Saves images to data/media/<story_hash>/img_<scene_id>.png
"""

import json
import os
import time
import uuid
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv
from pydantic import ValidationError

from pipeline import http_client
from pipeline.http_client import RequestException
from pipeline.logger import get_logger
from pipeline.schemas import RunwareResponse

log = get_logger("imager")

load_dotenv(Path(__file__).parent.parent / ".env")

RUNWARE_API_KEY: str = os.getenv("RUNWARE_API_KEY", "")
MEDIA_DIR = Path(__file__).parent.parent / "data" / "media"

RUNWARE_API_URL = "https://api.runware.ai/v1"

# Image generation parameters
IMAGE_MODEL = "runware:100@1"
IMAGE_WIDTH = 1088  # Must be a multiple of 64 for Runware API
IMAGE_HEIGHT = 1920  # 1920 is already a multiple of 64 (30 * 64)
NEGATIVE_PROMPT = (
    "text, letters, words, watermark, captions, subtitle, banner, label, "
    "title, font, number, symbol, logo, UI, interface, chart, graph, table"
)


def _enhance_prompt(raw_prompt: str) -> str:
    """Append consistent quality/style keywords to every image prompt."""
    style_suffix = (
        ", cinematic lighting, ultra-detailed, photorealistic, dramatic atmosphere, "
        "vertical 9:16 composition, subject centered, golden hour or dramatic overhead light, "
        "8K resolution, shallow depth of field"
    )
    return raw_prompt.strip() + style_suffix


def _image_url_from_runware(data: dict) -> str:
    """Validate a Runware JSON body and return the first image URL."""
    parsed = RunwareResponse.model_validate(data)
    return parsed.first_image_url()


def _generate_one_image(prompt: str, save_path: Path) -> bool:
    """
    Generate a single image via the Runware REST API.
    Uses the /imageInference endpoint with API key auth.
    Returns True on success.
    """
    if not RUNWARE_API_KEY:
        log.error("RUNWARE_API_KEY not set.")
        return False

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {RUNWARE_API_KEY}",
    }

    payload = [
        {
            "taskType": "imageInference",
            "taskUUID": str(uuid.uuid4()),
            "positivePrompt": _enhance_prompt(prompt),
            "negativePrompt": NEGATIVE_PROMPT,
            "model": IMAGE_MODEL,
            "width": IMAGE_WIDTH,
            "height": IMAGE_HEIGHT,
            "numberResults": 1,
            "outputType": "URL",
            "outputFormat": "PNG",
        }
    ]

    for attempt in range(3):
        try:
            resp = http_client.post(RUNWARE_API_URL, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()

            data = resp.json()
            image_url = _image_url_from_runware(data)

            img_resp = http_client.get(image_url, timeout=30)
            img_resp.raise_for_status()

            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_bytes(img_resp.content)
            log.info("Image saved: %s", save_path)
            return True

        except RequestException as e:
            err_text = ""
            if getattr(e, "response", None) is not None:
                err_text = e.response.text
            wait = 2 ** (attempt + 1)
            log.warning(
                "Image generation attempt %d/3 failed: %s | Responses: %s — retrying in %ds",
                attempt + 1,
                e,
                err_text,
                wait,
            )
            time.sleep(wait)

        except (json.JSONDecodeError, KeyError, RuntimeError, OSError, ValidationError) as e:
            wait = 2 ** (attempt + 1)
            log.warning(
                "Image generation attempt %d/3 failed: %s — retrying in %ds", attempt + 1, e, wait
            )
            time.sleep(wait)

    log.error("Image generation failed after 3 attempts for prompt: %.80s", prompt)
    return False


def generate_images(script: dict) -> Dict[int, Path]:
    """
    Generate images for all scenes in a script.
    Returns a mapping of scene_id -> image Path for successful generations.
    """
    story_hash = script.get("metadata", {}).get("story_hash", "unknown")
    scenes = script.get("scenes", [])
    project_name = script.get("project_name", "?")

    if not RUNWARE_API_KEY:
        log.error("RUNWARE_API_KEY not set — cannot generate images.")
        return {}

    log.info("=== Imager: generating %d images for '%s' ===", len(scenes), project_name)

    story_dir = MEDIA_DIR / story_hash
    story_dir.mkdir(parents=True, exist_ok=True)

    results: Dict[int, Path] = {}

    for scene in scenes:
        scene_id = scene.get("id", 0)
        prompt = scene.get("image_prompt", "").strip()

        if not prompt:
            log.warning("Scene %d has empty image_prompt — skipping.", scene_id)
            continue

        save_path = story_dir / f"img_{scene_id:02d}.png"

        # Skip re-generation if image already exists (useful for reruns)
        if save_path.exists() and save_path.stat().st_size > 1000:
            log.info("Reusing cached image for scene %d: %s", scene_id, save_path)
            results[scene_id] = save_path
            continue

        success = _generate_one_image(prompt, save_path)
        if success:
            results[scene_id] = save_path

    log.info("Imager: %d/%d images generated for '%s'", len(results), len(scenes), project_name)
    return results


if __name__ == "__main__":
    approved_dir = Path(__file__).parent.parent / "data" / "approved"
    scripts = list(approved_dir.glob("approved_*.json"))
    if not scripts:
        print("No approved scripts found.")
    else:
        import json as _json

        script = _json.loads(scripts[0].read_text())
        images = generate_images(script)
        print(f"Generated images: {images}")
