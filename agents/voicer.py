"""
agents/voicer.py

Generates male Indian accent TTS voiceover audio using Coqui TTS (local, free).
One WAV file per scene, saved to data/media/<story_hash>/voice_<scene_id>.wav

Model: tts_models/en/vctk/vits
Speaker: p326 (male, neutral, energetic — best match for Indian accent in VCTK)

Falls back to a basic gTTS Google Cloud call if Coqui is not installed,
but Coqui is strongly preferred for offline / private operation.
"""

import os
import time
from pathlib import Path
from typing import Dict, Optional

from pipeline.logger import get_logger

log = get_logger("voicer")

MEDIA_DIR = Path(__file__).parent.parent / "data" / "media"

# Coqui VCTK male speaker — closest to Indian-neutral accent available locally
COQUI_MODEL = "tts_models/en/vctk/vits"
COQUI_SPEAKER = "p326"

# Speed-up ratio for high-energy finance news tone
SPEED = 1.1


def _synthesize_with_coqui(text: str, output_path: Path) -> bool:
    """
    Use Coqui TTS to synthesize a single voice line.
    Returns True on success.
    """
    try:
        from TTS.api import TTS  # type: ignore

        tts = TTS(model_name=COQUI_MODEL, progress_bar=False)
        tts.tts_to_file(
            text=text,
            speaker=COQUI_SPEAKER,
            file_path=str(output_path),
            speed=SPEED,
        )
        log.debug("Coqui TTS saved: %s", output_path)
        return True
    except (ImportError, TypeError):
        log.warning("Coqui TTS not installed or incompatible (Python 3.9). Falling back to gTTS.")
        return False
    except Exception as e:
        log.error("Coqui TTS error: %s", e)
        return False


def _synthesize_with_gtts(text: str, output_path: Path) -> bool:
    """
    Fallback: Use gTTS to generate MP3 and convert to WAV via ffmpeg.
    Returns True on success.
    """
    try:
        from gtts import gTTS  # type: ignore
        import subprocess

        mp3_path = output_path.with_suffix(".mp3")
        tts = gTTS(text=text, lang="en", tld="co.in", slow=False)
        tts.save(str(mp3_path))

        # Convert MP3 → WAV (required downstream for ffmpeg scene stitching)
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(mp3_path), str(output_path)],
            check=True,
            capture_output=True,
        )
        mp3_path.unlink(missing_ok=True)
        log.debug("gTTS WAV saved: %s", output_path)
        return True
    except Exception as e:
        log.error("gTTS fallback error: %s", e)
        return False


def _sanitize_text(text: str) -> str:
    """
    Remove characters that TTS engines choke on (emojis, special punctuation).
    Keep commas and periods for natural pacing.
    """
    import re
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

    # Try Coqui first, gTTS as fallback
    if _synthesize_with_coqui(text, wav_path):
        return wav_path
    if _synthesize_with_gtts(text, wav_path):
        return wav_path

    log.error("All TTS methods failed for scene %d.", scene_id)
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
