"""
WORKHORSE Catalog Teaser & Thumbnail Auto-Generator
Extracts 3-5 HD snapshot stills and a 15-30s teaser clip from any catalog video using FFmpeg.
Author: Antigravity / WORKHORSE Pipeline
"""

import os
import sys
import json
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

WORKHORSE_ROOT = Path("F:/WORKHORSE")
FFMPEG_PATH = shutil.which("ffmpeg") or r"C:\ffmpeg\bin\ffmpeg.exe" or "ffmpeg"


def get_video_duration(video_url_or_path: str) -> float:
    """Uses ffprobe to get video duration in seconds."""
    ffprobe = shutil.which("ffprobe") or "ffprobe"
    cmd = [
        ffprobe, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_url_or_path
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if res.returncode == 0 and res.stdout.strip():
            return float(res.stdout.strip())
    except Exception:
        pass
    return 600.0  # Fallback: assume 10 minutes


def extract_stills_and_teaser(
    video_url_or_path: str,
    output_dir: Path,
    video_id: str = "video",
    num_stills: int = 4,
    teaser_duration: int = 15
) -> Dict[str, Any]:
    """
    Extracts high-resolution keyframe stills and a dynamic teaser cutdown from video.
    Returns dictionary with paths to generated assets.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    duration = get_video_duration(video_url_or_path)

    # 1. Extract Stills at 20%, 40%, 60%, 80% marks
    stills = []
    ratios = [0.20, 0.40, 0.60, 0.80][:num_stills]
    for i, ratio in enumerate(ratios):
        timestamp = max(5.0, duration * ratio)
        still_path = output_dir / f"still_{i+1}.jpg"
        cmd = [
            FFMPEG_PATH, "-y",
            "-ss", str(timestamp),
            "-i", video_url_or_path,
            "-vframes", "1",
            "-q:v", "2",
            str(still_path)
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=20)
            if still_path.exists() and still_path.stat().st_size > 5000:
                stills.append(str(still_path))
        except Exception as e:
            pass

    # 2. Extract 15s Teaser Cutdown (take 15 seconds from active 40% mark)
    teaser_path = output_dir / "teaser_15s.mp4"
    teaser_start = max(10.0, duration * 0.35)
    teaser_cmd = [
        FFMPEG_PATH, "-y",
        "-ss", str(teaser_start),
        "-i", video_url_or_path,
        "-t", str(teaser_duration),
        "-vf", "scale=-2:720",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
        "-c:a", "aac", "-b:a", "128k",
        str(teaser_path)
    ]
    try:
        subprocess.run(teaser_cmd, capture_output=True, timeout=30)
    except Exception:
        pass

    return {
        "video_id": video_id,
        "stills": stills,
        "teaser": str(teaser_path) if teaser_path.exists() else None,
        "duration": duration
    }


if __name__ == "__main__":
    print("Catalog Teaser & Thumbnail Engine ready.")
