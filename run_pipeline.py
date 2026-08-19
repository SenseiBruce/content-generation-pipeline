#!/usr/bin/env python3
"""
run_pipeline.py

Capital Architects — YouTube Shorts Automation Pipeline
Channel: Capital Architects | Audience: India | Topic: Finance

Orchestrates the following agent sequence:
  1. Watchtower    → Fetch RSS finance news (7 sources)
  2. Prioritizer   → Score & pick top 5 stories (LLM)
  3. Scriptwriter  → Generate structured JSON scripts (GPT-4o)
  4. Judge         → Score scripts (weighted), auto-improve up to 3x
  5. Imager        → Generate scene images (Runware API)
  6. Voicer        → Synthesize TTS audio (Coqui local / gTTS fallback)
  7. Stitcher      → Assemble final MP4 (FFmpeg)
  8. Publisher     → Upload & schedule to YouTube at India traffic peaks

Security:
  - All API keys from .env (never hardcoded)
  - File access restricted to project directory (sandbox)
  - No arbitrary shell access

Runtime target: < 25 minutes per full run (enforced by OpenClaw task config)
"""

import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to sys.path so all agents and pipeline modules resolve
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from agents.analyst import pull_and_analyze
from agents.imager import generate_images
from agents.judge import judge_all
from agents.prioritizer import prioritize
from agents.publisher import upload_video
from agents.scriptwriter import generate_all
from agents.stitcher import stitch_video
from agents.voicer import synthesize_all
from agents.watchtower import fetch_all_news
from pipeline.logger import get_logger
from pipeline.state import mark_seen, record_run

log = get_logger("orchestrator")

# ─────────────────────────────────────────────────────────────────────────────
# Hard runtime limit guard (OpenClaw enforces 25 min — we self-check at 23 min)
# ─────────────────────────────────────────────────────────────────────────────
PIPELINE_START = time.monotonic()
RUNTIME_LIMIT_SECONDS = 23 * 60  # 23 minutes


def _check_time_budget(stage: str) -> bool:
    """Return False (and log warning) if the pipeline is running over budget."""
    elapsed = time.monotonic() - PIPELINE_START
    remaining = RUNTIME_LIMIT_SECONDS - elapsed
    if remaining < 60:
        log.warning(
            "⏰ Time budget nearly exhausted at stage '%s' (elapsed %.0fs). Stopping pipeline.",
            stage, elapsed,
        )
        return False
    log.debug("Stage '%s' — elapsed %.0fs, remaining %.0fs", stage, elapsed, remaining)
    return True


def _abort(reason: str, summary: dict) -> None:
    """Log a clean abort and record the failed run."""
    log.error("Pipeline aborted: %s", reason)
    summary["status"] = "aborted"
    summary["abort_reason"] = reason
    record_run(summary)


# ─────────────────────────────────────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────────────────────────────────────
def run_pipeline() -> None:
    log.info("=" * 70)
    log.info("🚀 Capital Architects pipeline starting — %s", datetime.now().isoformat())
    log.info("=" * 70)

    summary: dict = {
        "started_at": datetime.now().isoformat(),
        "stories_fetched": 0,
        "stories_prioritized": 0,
        "scripts_generated": 0,
        "scripts_approved": 0,
        "scripts_rejected": 0,
        "videos_produced": 0,
        "videos_uploaded": 0,
        "status": "running",
    }

    # ── STAGE 1: Fetch News ─────────────────────────────────────────────────
    log.info("── Stage 1: Watchtower (RSS fetch) ──")
    if not _check_time_budget("watchtower"):
        return _abort("Time exceeded before watchtower", summary)

    stories = fetch_all_news()
    summary["stories_fetched"] = len(stories)

    if not stories:
        log.info("No new stories this run. Pipeline complete (nothing to do).")
        summary["status"] = "idle"
        record_run(summary)
        return

    log.info("Fetched %d new stories.", len(stories))

    # ── STAGE 2: Prioritize ─────────────────────────────────────────────────
    log.info("── Stage 2: Prioritizer (top-5 selection) ──")
    if not _check_time_budget("prioritizer"):
        return _abort("Time exceeded before prioritizer", summary)

    top_stories = prioritize(stories)
    summary["stories_prioritized"] = len(top_stories)

    if not top_stories:
        log.info("No stories passed the relevance threshold. Exiting.")
        summary["status"] = "idle"
        record_run(summary)
        return

    log.info("Top %d stories selected.", len(top_stories))

    # ── STAGE 3: Generate Scripts ───────────────────────────────────────────
    log.info("── Stage 3: Scriptwriter (GPT-4o) ──")
    if not _check_time_budget("scriptwriter"):
        return _abort("Time exceeded before scriptwriter", summary)

    scripts = generate_all(top_stories)
    summary["scripts_generated"] = len(scripts)

    if not scripts:
        log.warning("No scripts generated. Check OpenRouter API key and model.")
        summary["status"] = "failed"
        record_run(summary)
        return

    # ── STAGE 4: Judge & Auto-Improve ──────────────────────────────────────
    log.info("── Stage 4: Judge (score + auto-improve, max 3 loops) ──")
    if not _check_time_budget("judge"):
        return _abort("Time exceeded before judge", summary)

    approved_scripts, rejected_scripts = judge_all(scripts)
    summary["scripts_approved"] = len(approved_scripts)
    summary["scripts_rejected"] = len(rejected_scripts)

    if not approved_scripts:
        log.warning("No scripts approved by judge (all scored < 85 after 3 loops).")
        # Mark all stories as seen so they're not reprocessed next run
        for story in top_stories:
            mark_seen(story.get("hash", ""))
        summary["status"] = "no_approved"
        record_run(summary)
        return

    log.info("%d script(s) approved.", len(approved_scripts))

    # ── STAGE 5-7: Produce Videos (per approved script) ────────────────────
    for idx, script in enumerate(approved_scripts, start=1):
        project_name = script.get("project_name", f"video_{idx}")
        story_hash = script.get("metadata", {}).get("story_hash", f"hash_{idx}")

        log.info("── Producing video %d/%d: %s ──", idx, len(approved_scripts), project_name)

        # ── STAGE 5: Generate Images ────────────────────────────────────────
        if not _check_time_budget(f"imager [{project_name}]"):
            _abort("Time exceeded during image generation", summary)
            break

        log.info("Stage 5: Imager")
        image_map = generate_images(script)
        if len(image_map) != len(script.get("scenes", [])):
            log.error("Image generation incomplete for '%s' — skipping this video.", project_name)
            continue

        # ── STAGE 6: Generate Voice ─────────────────────────────────────────
        if not _check_time_budget(f"voicer [{project_name}]"):
            _abort("Time exceeded during voice synthesis", summary)
            break

        log.info("Stage 6: Voicer")
        audio_map = synthesize_all(script)
        if len(audio_map) != len(script.get("scenes", [])):
            log.error("Audio synthesis incomplete for '%s' — skipping this video.", project_name)
            continue

        # ── STAGE 7: Stitch Video ───────────────────────────────────────────
        if not _check_time_budget(f"stitcher [{project_name}]"):
            _abort("Time exceeded during video stitching", summary)
            break

        log.info("Stage 7: Stitcher")
        final_video_path = stitch_video(script, image_map, audio_map)
        if not final_video_path:
            log.error("Video stitching failed for '%s' — skipping.", project_name)
            continue

        summary["videos_produced"] += 1

        # ── STAGE 8: Upload to YouTube ──────────────────────────────────────
        if not _check_time_budget(f"publisher [{project_name}]"):
            _abort("Time exceeded before upload", summary)
            break

        log.info("Stage 8: Publisher")
        video_id = upload_video(final_video_path, script)
        if video_id:
            log.info("✅ Video live: https://youtu.be/%s", video_id)
            summary["videos_uploaded"] += 1

            # --- NEW: Autonomous Feedback Loop ---
            log.info("Stage 9: Analyst (Autonomous Feedback Loop)")
            if pull_and_analyze():
                log.info("Feedback loop complete: prioritizer now optimized for current winners.")

            # --- NEW: Archive Scripture ---
            archive_dir = PROJECT_ROOT / "data" / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)
            approved_file = PROJECT_ROOT / "data" / "approved" / f"approved_{story_hash}.json"
            if approved_file.exists():
                archive_file = archive_dir / approved_file.name
                approved_file.rename(archive_file)
                log.info("Archived script to: %s", archive_file.name)
        else:
            log.warning(
                "Upload failed for '%s'. Video saved locally at: %s",
                project_name,
                final_video_path,
            )

        # Mark story as seen regardless of upload success (to avoid duplicate scripts)
        mark_seen(story_hash)

    # ── Final Summary ────────────────────────────────────────────────────────
    elapsed = time.monotonic() - PIPELINE_START
    summary["status"] = "success"
    summary["elapsed_seconds"] = round(elapsed, 1)

    log.info("=" * 70)
    log.info("✅ Pipeline complete in %.0fs", elapsed)
    log.info("   Stories fetched    : %d", summary["stories_fetched"])
    log.info("   Stories prioritized: %d", summary["stories_prioritized"])
    log.info("   Scripts generated  : %d", summary["scripts_generated"])
    log.info("   Scripts approved   : %d", summary["scripts_approved"])
    log.info("   Scripts rejected   : %d", summary["scripts_rejected"])
    log.info("   Videos produced    : %d", summary["videos_produced"])
    log.info("   Videos uploaded    : %d", summary["videos_uploaded"])
    log.info("=" * 70)

    record_run(summary)


if __name__ == "__main__":
    try:
        run_pipeline()
    except KeyboardInterrupt:
        log.warning("Pipeline interrupted by user.")
        sys.exit(0)
    except Exception as exc:
        log.exception("Unhandled pipeline error: %s", exc)
        sys.exit(1)
