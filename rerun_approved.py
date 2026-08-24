#!/usr/bin/env python3
"""
rerun_approved.py

A utility to rerun the production (images, voice, stitch) and publishing stages
for a specific approved script. Useful for tweaking stitching parameters
(like Ken Burns) without restarting the whole pipeline.

Usage:
    python3 rerun_approved.py --list
    python3 rerun_approved.py <story_hash_or_filename> [--upload]
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.resolve()
APPROVED_DIR = PROJECT_ROOT / "data" / "approved"


def _story_hash(filename: str, payload: dict[str, Any]) -> str:
    meta = payload.get("metadata")
    if isinstance(meta, dict) and meta.get("story_hash"):
        return str(meta["story_hash"])
    stem = filename.removeprefix("approved_").removesuffix(".json")
    return stem


def list_approved(approved_dir: Path | None = None) -> list[dict[str, Any]]:
    """Return a JSON-serializable catalog of approved scripts."""
    directory = approved_dir or APPROVED_DIR
    if not directory.is_dir():
        return []

    entries: list[dict[str, Any]] = []
    for path in sorted(directory.glob("approved_*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        scenes = payload.get("scenes")
        scene_count = len(scenes) if isinstance(scenes, list) else 0
        modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
        entries.append(
            {
                "filename": path.name,
                "story_hash": _story_hash(path.name, payload),
                "title": payload.get("title") or "",
                "project_name": payload.get("project_name") or "",
                "judge_score": payload.get("judge_score"),
                "scene_count": scene_count,
                "modified_at": modified_at,
            }
        )

    entries.sort(key=lambda row: (row["modified_at"], row["filename"]), reverse=True)
    return entries


def rerun(target: str, should_upload: bool = False) -> None:
    # Heavy production imports stay lazy so --list works without agent deps.
    sys.path.insert(0, str(PROJECT_ROOT))
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")

    from agents.imager import generate_images
    from agents.publisher import upload_video
    from agents.stitcher import stitch_video
    from agents.voicer import synthesize_all
    from pipeline.logger import get_logger

    log = get_logger("rerun-tool")
    approved_dir = PROJECT_ROOT / "data" / "approved"

    script_file = None
    if target.endswith(".json"):
        script_file = approved_dir / target
    else:
        matches = list(approved_dir.glob(f"approved_{target}.json"))
        if matches:
            script_file = matches[0]

    if not script_file or not script_file.exists():
        log.error("Could not find approved script for: %s", target)
        return

    log.info("--- Rerunning Production for: %s ---", script_file.name)
    script = json.loads(script_file.read_text())

    image_map = generate_images(script)
    audio_map = synthesize_all(script)

    log.info("Stage: Stitching...")
    final_video_path = stitch_video(script, image_map, audio_map)

    if final_video_path:
        log.info("✅ Video rendered: %s", final_video_path)

        if should_upload:
            video_id = upload_video(final_video_path, script)
            if video_id:
                log.info("✅ Successfully uploaded: https://youtu.be/%s", video_id)
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


USAGE = "Usage: python3 rerun_approved.py [--list] | <story_hash_or_filename> [--upload]"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(USAGE)
        return 0 if args else 1
    if "--list" in args or args[0] == "-l":
        print(json.dumps(list_approved(), indent=2, ensure_ascii=False))
        return 0

    target_arg = next((arg for arg in args if not arg.startswith("-")), None)
    if not target_arg:
        print(USAGE)
        return 1
    rerun(target_arg, should_upload="--upload" in args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
