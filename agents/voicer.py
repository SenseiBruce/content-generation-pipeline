"""
agents/voicer.py

Generates male Indian accent TTS voiceover audio using Coqui TTS (local, free).
One WAV file per scene, saved to data/media/<story_hash>/voice_<scene_id>.wav

Voice Engine: Jamie Pine's "Voicebox" (Qwen3-TTS)
Requires the standalone Voicebox server running at http://localhost:8000
Set VOICEBOX_PROFILE_ID in your .env file to target your custom voice profile.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv

from pipeline import http_client
from pipeline.http_client import RequestException
from pipeline.logger import get_logger

log = get_logger("voicer")

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

VOICEBOX_API_URL = os.getenv("VOICEBOX_API_URL", "http://localhost:8000")
VOICEBOX_PROFILE_ID = os.getenv("VOICEBOX_PROFILE_ID", "")

MEDIA_DIR = Path(__file__).parent.parent / "data" / "media"


def _synthesize_with_voicebox(text: str, output_path: Path) -> bool:
    """
    Send generation request to the standalone Voicebox API.
    Voicebox handles all MLX/GPU model loading internally.
    Returns True on success.
    """
    if not VOICEBOX_PROFILE_ID:
        log.error("VOICEBOX_PROFILE_ID is not set in .env")
        log.error("Please create a profile in the Voicebox Web UI and add its ID to .env")
        return False

    try:
        url = f"{VOICEBOX_API_URL}/generate"
        payload = {
            "profile_id": VOICEBOX_PROFILE_ID,
            "text": text,
            "language": "en",
        }

        response = http_client.post(url, json=payload, timeout=120)

        if response.status_code == 202:
            log.warning("Voicebox model is currently downloading. We need to wait and retry.")
            return False

        response.raise_for_status()

        gen_data = response.json()
        generation_id = gen_data.get("id")

        if not generation_id:
            log.error("Voicebox API did not return a generation ID: %s", gen_data)
            return False

        download_url = f"{VOICEBOX_API_URL}/audio/{generation_id}"
        audio_response = http_client.get(download_url, timeout=60)
        audio_response.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in audio_response.iter_content(chunk_size=8192):
                f.write(chunk)

        log.debug("Voicebox generated: %s", output_path)
        return True

    except RequestException as e:
        log.error("Could not reach Voicebox server at %s: %s", VOICEBOX_API_URL, e)
        return False
    except (json.JSONDecodeError, OSError, ValueError, KeyError) as e:
        log.error("Voicebox API error: %s", e)
        return False


def _sanitize_text(text: str) -> str:
    """
    Remove characters that TTS engines choke on (emojis, special punctuation).
    Keep commas and periods for natural pacing.
    """
    # Remove emoji and non-ASCII
    clean = re.sub(r"[^\x00-\x7F]+", "", text)
    # Collapse multiple spaces
    clean = re.sub(r"\s{2,}", " ", clean).strip()
    return clean


def synthesize_scene(scene: dict, story_hash: str) -> Optional[Path]:
    """
    Synthesize audio for one scene's voice_over text.
    Returns the WAV file Path on success, None on failure.
    """
    scene_id = scene.get("id", 0)
    text = scene.get("voice_over", "").strip()

    if not text:
        log.warning("Scene %d has empty voice_over — skipping.", scene_id)
        return None

    text = _sanitize_text(text)

    story_dir = MEDIA_DIR / story_hash
    story_dir.mkdir(parents=True, exist_ok=True)
    wav_path = story_dir / f"voice_{scene_id:02d}.wav"

    # Reuse existing audio if present
    if wav_path.exists() and wav_path.stat().st_size > 100:
        log.info("Reusing cached audio for scene %d: %s", scene_id, wav_path)
        return wav_path

    log.info("Synthesizing scene %d: '%s...'", scene_id, text[:50])

    # Use Voicebox directly as the primary engine
    if _synthesize_with_voicebox(text, wav_path):
        return wav_path

    log.error("Voicebox generation failed for scene %d.", scene_id)
    return None


def synthesize_all(script: dict) -> Dict[int, Path]:
    """
    Synthesize audio for every scene in the script.
    Returns mapping of scene_id → WAV path (successful scenes only).
    """
    story_hash = script.get("metadata", {}).get("story_hash", "unknown")
    scenes = script.get("scenes", [])
    project_name = script.get("project_name", "?")

    log.info("=== Voicer: synthesizing %d scenes for '%s' ===", len(scenes), project_name)

    audio_map: Dict[int, Path] = {}
    for scene in scenes:
        wav = synthesize_scene(scene, story_hash)
        if wav:
            audio_map[scene.get("id", 0)] = wav

    log.info("Voicer: %d/%d scenes synthesized for %s", len(audio_map), len(scenes), project_name)
    return audio_map


if __name__ == "__main__":
    import json

    approved_dir = Path(__file__).parent.parent / "data" / "approved"
    scripts = list(approved_dir.glob("approved_*.json"))
    if not scripts:
        print("No approved scripts found.")
    else:
        script = json.loads(scripts[0].read_text())
        audio_map = synthesize_all(script)
        print("Audio files:", audio_map)
