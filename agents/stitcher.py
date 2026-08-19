"""
agents/stitcher.py

Assembles the final YouTube Short using FFmpeg only.

Per-scene processing:
  1. Scale image to 1080×1920 (pad with black if aspect differs)
  2. Overlay caption text with fade-in/fade-out
  3. Mix with WAV audio track
  4. Trim video to audio duration (scene clip length = voice duration)

Final assembly:
  - Concatenate all scene clips
  - Export as MP4: H.264 video + AAC audio, optimized for Shorts

Output: data/output/<story_hash>_final.mp4
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from pipeline.logger import get_logger

log = get_logger("stitcher")

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "output"
MEDIA_DIR = Path(__file__).parent.parent / "data" / "media"

# Caption font settings (rendered via ffmpeg drawtext filter)
CAPTION_FONT = "Arial"
CAPTION_FONT_SIZE = 56
CAPTION_COLOR = "white"
CAPTION_SHADOW_COLOR = "black@0.8"
CAPTION_SHADOW_X = 3
CAPTION_SHADOW_Y = 3
CAPTION_BG_COLOR = "black@0.45"

# Final encode settings — optimized for YouTube Shorts
VIDEO_CODEC = "libx264"
AUDIO_CODEC = "aac"
VIDEO_PRESET = "fast"
CRF = "23"
AUDIO_BITRATE = "192k"


def _ffprobe_duration(audio_path: Path) -> float:
    """Return the duration of an audio file in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", str(audio_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "audio":
                return float(stream.get("duration", 3.0))
    except (
        subprocess.CalledProcessError,
        json.JSONDecodeError,
        ValueError,
        TypeError,
        FileNotFoundError,
    ) as e:
        log.warning("ffprobe failed for %s: %s — using 3.0s default", audio_path, e)
    return 3.0


def _create_caption_image(text: str, out_path: Path):
    """Use Pillow to draw wrapped text onto a transparent 1080x1920 canvas."""
    try:
        import textwrap

        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        log.error("Pillow not installed. Run: pip install Pillow")
        return False

    W, H = 1080, 1920
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", CAPTION_FONT_SIZE)
    except (OSError, IOError):
        font = ImageFont.load_default()

    lines = textwrap.wrap(text, width=28)
    line_spacing = int(CAPTION_FONT_SIZE * 1.5)
    total_height = len(lines) * line_spacing

    y = int(H * 0.83) - total_height // 2

    max_w = 0
    for line in lines:
        try:
            left, top, right, bottom = d.textbbox((0, 0), line, font=font)
        except AttributeError:
            w, h = d.textsize(line, font=font)
            right, left = w, 0
        max_w = max(max_w, right - left)

    padding = 30
    box_x0 = (W - max_w) // 2 - padding
    box_y0 = y - padding
    box_x1 = (W + max_w) // 2 + padding
    box_y1 = y + total_height + padding

    if text.strip():
        # Draw translucent background box
        d.rectangle([box_x0, box_y0, box_x1, box_y1], fill=(0, 0, 0, 160))

        current_y = y
        for line in lines:
            try:
                left, top, right, bottom = d.textbbox((0, 0), line, font=font)
                w = right - left
            except AttributeError:
                w, h = d.textsize(line, font=font)

            x = (W - w) // 2
            # Drop shadow
            d.text((x + 3, current_y + 3), line, font=font, fill=(0, 0, 0, 255))
            # Text
            d.text((x, current_y), line, font=font, fill=(255, 255, 255, 255))
            current_y += line_spacing

    img.save(out_path)
    return True


def _render_scene_clip(
    scene: dict,
    image_path: Path,
    audio_path: Path,
    clip_output: Path,
) -> bool:
    """
    Render one scene into a short MP4 clip:
     - Prompts Pillow to generate a transparent PNG with text.
     - Streams image as video source.
     - Overlays caption image.
     - Trim video to audio duration.
    """
    duration = _ffprobe_duration(audio_path)
    caption = scene.get("caption", {}).get("text", "")

    caption_path = clip_output.with_suffix(".png")
    if not _create_caption_image(caption, caption_path):
        return False

    # Subtle Ken Burns effect: Alternate zoom in/out per scene
    scene_id = scene.get("id", 1)
    if scene_id % 2 == 1:
        # Zoom In: starts at 1.0, grows
        zoom_expr = "min(zoom+0.0012,1.5)"
    else:
        # Zoom Out: starts at 1.15, shrinks
        zoom_expr = "if(eq(on,0),1.15,max(zoom-0.0012,1.0))"

    # To avoid jitter, scale image to a fixed large size before zoompan
    scale_filter = (
        "scale=1280:2276:force_original_aspect_ratio=increase,crop=1280:2276"
    )
    zoom_filter = (
        f"zoompan=z='{zoom_expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920"
    )

    fade_in = "fade=t=in:st=0:d=0.3:alpha=1"
    fade_out = f"fade=t=out:st={duration-0.3:.2f}:d=0.3:alpha=1"

    filter_complex = (
        f"[0:v]{scale_filter},{zoom_filter}[bg];"
        f"[1:v]format=rgba,{fade_in},{fade_out}[ov];"
        f"[bg][ov]overlay=x=0:y=0:shortest=1[vid]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", "30", "-t", str(duration), "-i", str(image_path),
        "-loop", "1", "-framerate", "30", "-t", str(duration), "-i", str(caption_path),
        "-i", str(audio_path),
        "-filter_complex", filter_complex,
        "-map", "[vid]",
        "-map", "2:a",
        "-c:v", VIDEO_CODEC,
        "-preset", VIDEO_PRESET,
        "-crf", CRF,
        "-c:a", AUDIO_CODEC,
        "-b:a", AUDIO_BITRATE,
        "-shortest",
        "-pix_fmt", "yuv420p",
        str(clip_output),
    ]

    log.debug("Rendering scene %d → %s", scene.get("id"), clip_output.name)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        caption_path.unlink(missing_ok=True)
        if result.returncode != 0:
            log.error("FFmpeg error for scene %d:\n%s", scene.get("id"), result.stderr[-800:])
            return False
        return True
    except FileNotFoundError:
        log.error("ffmpeg not found — please install FFmpeg.")
        return False
    except (OSError, ValueError) as e:
        log.error("Scene render error: %s", e)
        return False


def _concatenate_clips(clip_paths: List[Path], output_path: Path) -> bool:
    """
    Concatenate all scene clips into a single final MP4 using ffmpeg concat demuxer.
    Returns True on success.
    """
    # Write a concat list file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
        for clip in clip_paths:
            tmp.write(f"file '{clip.resolve()}'\n")
        concat_file = tmp.name

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-c:v", VIDEO_CODEC,
        "-preset", VIDEO_PRESET,
        "-crf", CRF,
        "-c:a", AUDIO_CODEC,
        "-b:a", AUDIO_BITRATE,
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",       # Web-optimized MP4 (moov atom first)
        str(output_path),
    ]

    log.info("Concatenating %d clips → %s", len(clip_paths), output_path.name)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        os.unlink(concat_file)
        if result.returncode != 0:
            log.error("FFmpeg concat error:\n%s", result.stderr[-800:])
            return False
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
        log.error("Concat error: %s", e)
        return False


def stitch_video(
    script: dict,
    image_map: Dict[int, Path],
    audio_map: Dict[int, Path],
) -> Optional[Path]:
    """
    Assemble a complete YouTube Short from per-scene images and audio.

    Args:
        script:    Approved script dict (with scenes[])
        image_map: {scene_id: image_path}
        audio_map: {scene_id: audio_path}

    Returns:
        Path to final MP4, or None on failure.
    """
    story_hash = script.get("metadata", {}).get("story_hash", "unknown")
    project_name = script.get("project_name", "video")
    scenes = script.get("scenes", [])

    log.info("=== Stitcher: assembling '%s' ===", project_name)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    working_dir = MEDIA_DIR / story_hash / "clips"
    working_dir.mkdir(parents=True, exist_ok=True)

    scene_clips: List[Path] = []

    for scene in scenes:
        sid = scene.get("id")
        image_path = image_map.get(sid)
        audio_path = audio_map.get(sid)

        if not image_path or not audio_path:
            log.error(
                "Missing asset for scene %d (image=%s, audio=%s)",
                sid,
                image_path,
                audio_path,
            )
            return None

        clip_path = working_dir / f"clip_{sid:02d}.mp4"
        success = _render_scene_clip(scene, image_path, audio_path, clip_path)

        if not success:
            log.error("Scene %d render failed — aborting stitch.", sid)
            return None

        scene_clips.append(clip_path)

    if not scene_clips:
        log.error("No clips rendered — cannot assemble final video.")
        return None

    # Sanitize project name for filesystem use
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in project_name)[:40]
    final_path = OUTPUT_DIR / f"{story_hash}_{safe_name}_final.mp4"

    success = _concatenate_clips(scene_clips, final_path)
    if not success:
        return None

    log.info("Final video ready: %s (%.1f MB)", final_path, final_path.stat().st_size / 1_048_576)
    return final_path


if __name__ == "__main__":
    # Quick test harness
    import json
    approved_dir = Path(__file__).parent.parent / "data" / "approved"
    scripts = list(approved_dir.glob("approved_*.json"))
    if not scripts:
        print("No approved scripts.")
    else:
        script = json.loads(scripts[0].read_text())
        h = script["metadata"]["story_hash"]
        media = MEDIA_DIR / h
        image_map = {int(p.stem.split("_")[1]): p for p in media.glob("img_*.png")}
        audio_map = {int(p.stem.split("_")[1]): p for p in media.glob("voice_*.wav")}
        out = stitch_video(script, image_map, audio_map)
        print(f"Output: {out}")
