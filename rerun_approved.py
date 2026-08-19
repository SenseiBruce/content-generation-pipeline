#!/usr/bin/env python3
"""
rerun_approved.py

A utility to rerun the production (images, voice, stitch) and publishing stages
for a specific approved script. Useful for tweaking stitching parameters
(like Ken Burns) without restarting the whole pipeline.

Usage: python3 rerun_approved.py <story_hash_or_filename> [--upload]
"""

import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from agents.imager import generate_images
from agents.publisher import upload_video
from agents.stitcher import stitch_video
from agents.voicer import synthesize_all
from pipeline.logger import get_logger

log = get_logger("rerun-tool")


def rerun(target: str, should_upload: bool = False):
    approved_dir = PROJECT_ROOT / "data" / "approved"

    # Resolve the script file
    script_file = None
    if target.endswith(".json"):
        script_file = approved_dir / target
    else:
        # Try finding by hash
        matches = list(approved_dir.glob(f"approved_{target}.json"))
        if matches:
            script_file = matches[0]

    if not script_file or not script_file.exists():
        log.error("Could not find approved script for: %s", target)
        return

    log.info("--- Rerunning Production for: %s ---", script_file.name)
    script = json.loads(script_file.read_text())

    # 1. Imager (Will skip if images exist)
    image_map = generate_images(script)

    # 2. Voicer (Will skip if audio exist)
    audio_map = synthesize_all(script)

    # 3. Stitcher (Will ALWAYS run and overwrite final .mp4)
    log.info("Stage: Stitching...")
    final_video_path = stitch_video(script, image_map, audio_map)

    if final_video_path:
        log.info("✅ Video rendered: %s", final_video_path)

        # 4. Publisher
        if should_upload:
            video_id = upload_video(final_video_path, script)
            if video_id:
                log.info("✅ Successfully uploaded: https://youtu.be/%s", video_id)
                # Archive on successful upload
                archive_dir = PROJECT_ROOT / "data" / "archive"
                archive_dir.mkdir(parents=True, exist_ok=True)
                if script_file.exists():
                    archive_file = archive_dir / script_file.name
                    script_file.rename(archive_file)
                    log.info("Archived script to: %s", archive_file.name)
        else:
            log.info("Skipping upload (use --upload to publish).")
    else:
        log.error("❌ Stitching failed.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 rerun_approved.py <story_hash_or_filename> [--upload]")
        sys.exit(1)

    target_arg = sys.argv[1]
    do_upload = "--upload" in sys.argv
    rerun(target_arg, do_upload)
