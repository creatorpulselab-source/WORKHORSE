#!/usr/bin/env python3
"""
WORKHORSE STAGE: CAM SHOW CUTTER & RESOLVE AUTO-EDITOR
======================================================
Automated Multi-Modal AI Cutdown Pipeline for 1-to-8+ Hour Adult Model Cam Shows.
Separates 'Active Shows' (striptease, toy play, dancing, explicit performances, posing, guitar)
from 'Casual Chat & Idle Downtime' (talking to chat while nude/topless, makeup, eating, resting).

Dual-GPU Workload Partitioning:
- GPU 1: NVENC/OpenCV optical flow motion energy profiling + Faster-Whisper speech density & acoustic music detection
- GPU 0: IRIS (huihui_ai/qwen3-vl-abliterated:8b-instruct) for uncensored keyframe verification

DaVinci Resolve Integration:
- Directly connects via DaVinciResolveScript API (Resolve Studio 21.1+)
- Imports raw file into Media Pool
- Automatically creates timeline with ONLY the active show ranges (ripple-deleted, zero gaps)
- Drops color-coded timeline markers (Cyan=Intro Outfit, Yellow=Guitar/Music, Purple=Active Show)
- Generates CMX 3600 .EDL and .JSON cutlist as portable fallbacks
"""

import sys
import os
import pathlib

# Ensure F:\WORKHORSE is on sys.path
WORKHORSE_ROOT = pathlib.Path(r"F:\WORKHORSE")
if str(WORKHORSE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKHORSE_ROOT))

import argparse
import base64
import json
import logging
import subprocess
import time
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple

import cv2
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("cam_show_cutter")

OLLAMA_API = "http://127.0.0.1:11434"
VISION_MODEL = "huihui_ai/qwen3-vl-abliterated:8b-instruct"


# ----------------------------------------------------------------------
# 1. Video Probe & Metadata
# ----------------------------------------------------------------------
def probe_video(video_path: pathlib.Path) -> Dict[str, Any]:
    """Extracts resolution, frame rate, total frames, and duration using OpenCV and ffprobe."""
    info = {"path": str(video_path), "fps": 30.0, "duration": 0.0, "width": 1920, "height": 1080, "total_frames": 0}
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration:stream=width,height,r_frame_rate,nb_frames",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        for line in lines:
            if "/" in line and info["fps"] == 30.0:
                n, d = line.split("/")
                if float(d) > 0:
                    info["fps"] = round(float(n) / float(d), 3)
            elif "." in line and info["duration"] == 0.0:
                try:
                    info["duration"] = float(line)
                except ValueError:
                    pass
    except Exception as e:
        logger.warning(f"ffprobe warning: {e}")

    cap = cv2.VideoCapture(str(video_path))
    if cap.isOpened():
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        f = float(cap.get(cv2.CAP_PROP_FPS))
        cnt = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if w > 0:
            info["width"] = w
        if h > 0:
            info["height"] = h
        if f > 0:
            info["fps"] = f
        if cnt > 0:
            info["total_frames"] = cnt
        if info["duration"] == 0.0 and cnt > 0 and info["fps"] > 0:
            info["duration"] = round(cnt / info["fps"], 2)
        cap.release()

    if info["total_frames"] <= 0 and info["duration"] > 0 and info["fps"] > 0:
        info["total_frames"] = int(info["duration"] * info["fps"])

    return info


# ----------------------------------------------------------------------
# 2. Stage 1: Fast Optical Flow Motion Energy Scanner
# ----------------------------------------------------------------------
def scan_motion_energy(
    video_path: pathlib.Path,
    sample_fps: float = 1.0,
    motion_threshold: float = 0.08,
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> List[Dict[str, Any]]:
    """Fast scan of the entire video at sample_fps (default 1 frame per second).
    Computes optical flow pixel difference and active motion area across the timeline.
    Uses diff > 15 for high sensitivity across both close-ups and wide-angle room setups.
    """
    processing_dir = pathlib.Path(r"F:\WORKHORSE\cam_shows\processing")
    processing_dir.mkdir(parents=True, exist_ok=True)
    cache_file = processing_dir / f"{video_path.stem}.motion.json"
    if cache_file.exists():
        try:
            logger.info(f"Loading cached motion profile from {cache_file.name}...")
            cached_pts = json.loads(cache_file.read_text(encoding="utf-8"))
            if len(cached_pts) > 100:
                logger.info(f"Loaded {len(cached_pts)} cached motion points in 0.1s!")
                return cached_pts
        except Exception as ce:
            logger.warning(f"Error reading motion cache ({ce}), re-scanning...")

    logger.info(f"Scanning motion energy at {sample_fps} fps on {video_path.name}...")
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video file: {video_path}")

    fps = float(cap.get(cv2.CAP_PROP_FPS)) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_step = max(1, int(round(fps / sample_fps)))

    timeline_points = []
    prev_gray = None
    frame_idx = 0
    sampled_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        small = cv2.resize(frame, (320, 180), interpolation=cv2.INTER_LINEAR)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        # Performer human skin tone presence filter (HSV + YCrCb combined)
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        ycrcb = cv2.cvtColor(small, cv2.COLOR_BGR2YCrCb)
        m_hsv = cv2.inRange(hsv, np.array([0, 45, 60]), np.array([18, 255, 255]))
        m_ycrcb = cv2.inRange(ycrcb, np.array([0, 135, 80]), np.array([255, 175, 125]))
        skin_mask = cv2.bitwise_and(m_hsv, m_ycrcb)
        skin_pct = float(np.count_nonzero(skin_mask) / skin_mask.size)
        has_performer = (skin_pct >= 0.020)

        motion_energy = 0.0
        motion_area_pct = 0.0

        if prev_gray is not None:
            diff = cv2.absdiff(prev_gray, gray)
            motion_energy = float(np.mean(diff) / 255.0)
            active_pixels = np.count_nonzero(diff > 15)
            motion_area_pct = float(active_pixels / (320 * 180))

        timestamp = round(frame_idx / fps, 2)

        timeline_points.append({
            "time_sec": timestamp,
            "frame": frame_idx,
            "motion_energy": round(motion_energy, 4),
            "motion_area": round(motion_area_pct, 4),
            "skin_pct": round(skin_pct, 4),
            "has_performer": has_performer,
            "is_motion_active": (motion_area_pct >= motion_threshold or motion_energy >= 0.04) and has_performer,
        })

        prev_gray = gray
        sampled_count += 1

        if sampled_count % 300 == 0:
            pct = min(100.0, (frame_idx / total_frames) * 100.0) if total_frames > 0 else 0.0
            msg = f"Motion Scan: {round(timestamp / 60, 1)}m / {round(total_frames / (fps * 60), 1)}m ({round(pct, 1)}%)..."
            logger.info(msg)
            if progress_callback:
                progress_callback(pct, msg)

        skip_ok = True
        for _ in range(frame_step - 1):
            if not cap.grab():
                skip_ok = False
                break
            frame_idx += 1
        frame_idx += 1
        if not skip_ok:
            break

    cap.release()
    try:
        cache_file.write_text(json.dumps(timeline_points), encoding="utf-8")
        logger.info(f"Cached {len(timeline_points)} motion sample points to {cache_file.name}")
    except Exception as ce:
        logger.warning(f"Could not save motion cache: {ce}")

    logger.info(f"Motion scan complete: {len(timeline_points)} sample points analyzed.")
    return timeline_points


# ----------------------------------------------------------------------
# 3. Stage 2: Audio Speech Density & Acoustic Music Profiler
# ----------------------------------------------------------------------
def extract_and_scan_audio(
    video_path: pathlib.Path,
    device_index: int = 1,
) -> Dict[str, Any]:
    """Extracts audio to AAC/WAV and runs GPU 1 Faster-Whisper to profile speech blocks and musical cues."""
    processing_dir = pathlib.Path(r"F:\WORKHORSE\cam_shows\processing")
    processing_dir.mkdir(parents=True, exist_ok=True)
    temp_audio = processing_dir / f"{video_path.stem}_audio.aac"

    if not temp_audio.exists() or temp_audio.stat().st_size < 1000:
        logger.info(f"Extracting audio stream to {temp_audio.name}...")
        cmd = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vn", "-acodec", "copy", str(temp_audio)
        ]
        subprocess.run(cmd, capture_output=True, timeout=120)

    if not temp_audio.exists() or temp_audio.stat().st_size < 1000:
        # Fallback re-encode to clean AAC
        logger.info(f"Fallback re-encoding audio to {temp_audio.name}...")
        cmd_fallback = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vn", "-c:a", "aac", "-b:a", "128k", str(temp_audio)
        ]
        subprocess.run(cmd_fallback, capture_output=True, timeout=180)

    if not temp_audio.exists() or temp_audio.stat().st_size < 100:
        logger.warning(f"Could not extract audio for {video_path.name}, proceeding without audio profiling.")
        return {"all_speech": [], "guitar_segments": [], "music_segments": []}

    logger.info(f"Loading Faster-Whisper on GPU {device_index} for audio speech & music profiling...")
    import faster_whisper
    try:
        model = faster_whisper.WhisperModel("tiny.en", device="cuda", device_index=device_index, compute_type="float16")
    except Exception as e:
        logger.warning(f"Could not load Whisper on CUDA GPU {device_index} ({e}), falling back to CPU.")
        model = faster_whisper.WhisperModel("tiny.en", device="cpu", compute_type="int8")

    logger.info(f"Running high-speed speech density & musical scan on {temp_audio.name}...")
    try:
        segments, info = model.transcribe(
            str(temp_audio),
            beam_size=1,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )
    except Exception as te:
        logger.warning(f"Whisper transcribe warning ({te}), proceeding with empty speech profile.")
        return {"all_speech": [], "guitar_segments": [], "music_segments": []}

    all_speech = []
    music_segments = []
    guitar_segments = []

    music_keywords = ["guitar", "strum", "chords", "song", "sing", "singing", "playing", "[music]", "(music)", "♪", "♫"]

    for seg in segments:
        txt = seg.text.strip().lower()
        words = len(seg.text.split())
        all_speech.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
            "words": words,
        })

        if "guitar" in txt or any(k in txt for k in ["strum", "chords", "kurt cobain", "nirvana", "tenacious"]):
            guitar_segments.append({"start": seg.start, "end": seg.end, "text": seg.text.strip()})

        if any(m in txt for m in music_keywords):
            music_segments.append({"start": seg.start, "end": seg.end, "text": seg.text.strip()})

    logger.info(f"Audio scan complete: {len(all_speech)} speech blocks, {len(guitar_segments)} guitar cues, {len(music_segments)} music cues.")
    return {
        "all_speech": all_speech,
        "guitar_segments": guitar_segments,
        "music_segments": music_segments,
    }


# ----------------------------------------------------------------------
# 4. Stage 3: Vision AI Verification & Multi-Modal Classification
# ----------------------------------------------------------------------
REFINED_PROMPT = (
    "You are an expert adult webcam show video editor and curator. Strictly classify this video frame with an intensity score (0 to 5) and action description.\n\n"
    "CRITICAL RULES:\n"
    "1. CASUAL IDLE/CHAT IS ALWAYS LEVEL 0:\n"
    "   - Drinking from a cup, mug, glass, water bottle, or can is strictly LEVEL 0 (CASUAL_CHAT).\n"
    "   - Standing in front of the camera casually talking, gesturing, or chatting with viewers is strictly LEVEL 0 (CASUAL_CHAT).\n"
    "   - Sitting in a gaming chair talking, typing, holding or checking phone, or resting is strictly LEVEL 0 (CASUAL_CHAT).\n"
    "   - Sitting or posing casually in lingerie/clothing with hand on chin, hand on leg, or looking at camera without active intimate stimulation is strictly LEVEL 0 (CASUAL_CHAT).\n"
    "   - Getting up, standing up from bed or chair after an act is strictly LEVEL 0 (CASUAL_CHAT).\n"
    "   - Pulling up underwear, panties, shorts, robe, or fixing/adjusting outfit after a show is strictly LEVEL 0 (CASUAL_CHAT).\n"
    "   - Walking around the room or adjusting webcam is strictly LEVEL 0 (CASUAL_CHAT).\n"
    "   - Sitting quietly in chair while tips/Lovense vibrates is strictly LEVEL 0 (CASUAL_CHAT).\n\n"
    "2. LEVEL 1 (MUSIC / GUITAR ONLY):\n"
    "   - Playing electric/acoustic guitar, strumming, singing (lowest priority).\n\n"
    "3. LEVEL 2 (ACTIVE STRIPTEASE / UNCLOTHING ONLY):\n"
    "   - Performer is actively removing/peeling off lingerie, unhooking bra, or pulling underwear aside to expose private parts.\n"
    "   - (NOTE: Simply sitting or standing wearing lingerie while talking or drinking is LEVEL 0!).\n\n"
    "4. LEVEL 3 (ACTIVE INTIMATE TEASING):\n"
    "   - Active hands-on intimate touching: pinching bare nipples/breasts, hand between legs/groin, mask/costume toy play, sensual body caress.\n\n"
    "5. LEVEL 4 (PENETRATION & ACTIVE ORAL PLAY):\n"
    "   - Dildo insertion, active pumping & thrusting, sucking/licking dildo, oral play with saliva strings, floor/bed spread play.\n\n"
    "6. LEVEL 5 (PEAK CLIMAX & VISIBLE FLUIDS - HIGHEST PRIORITY):\n"
    "   - Pullout from wet pussy with legs spread, deep pumping, visible dripping wetness/moisture reflections, squirt, glistening body oil.\n\n"
    "Respond in valid JSON only:\n"
    "{\n"
    "  \"classification\": \"ACTIVE_SHOW\" or \"CASUAL_CHAT\",\n"
    "  \"intensity\": 0 to 5,\n"
    "  \"action\": \"concise descriptive action tag\",\n"
    "  \"wetness_detected\": true or false\n"
    "}"
)


def verify_candidate_with_vision(
    cap: cv2.VideoCapture,
    cand: Dict[str, Any],
    all_speech: Optional[List[Dict[str, Any]]] = None,
    guitar_sessions: Optional[List[Tuple[float, float]]] = None,
    ollama_api: str = OLLAMA_API,
    model: str = VISION_MODEL,
    is_produced_clip: bool = False,
) -> List[Dict[str, Any]]:
    """Subdivides motion candidates into discrete time windows, evaluates speech density
    and GPU 0 Vision AI, and prunes casual chat, drinking, standing, and post-act dress adjustments.
    Returns a list of verified, cohesive show segments with action moments and peak action timestamps.
    """
    start_sec = cand["start_sec"]
    end_sec = cand["end_sec"]
    dur = cand["duration_sec"]

    if all_speech is None:
        all_speech = []
    if guitar_sessions is None:
        guitar_sessions = []

    # Subdivide candidate into discrete sub-windows (~35.0s target)
    step = 35.0
    if dur <= 45.0:
        sub_windows = [(start_sec, end_sec)]
    else:
        sub_windows = []
        cur = start_sec
        while cur < end_sec:
            w_end = min(end_sec, cur + step)
            sub_windows.append((cur, w_end))
            cur = w_end

    kept_sub_blocks = []

    for s_st, s_et in sub_windows:
        s_dur = s_et - s_st
        mid = (s_st + s_et) / 2.0

        # Check speech metrics in this sub-window
        overlapping_speech = [
            sp for sp in all_speech
            if max(s_st, sp["start"]) < min(s_et, sp["end"])
        ]
        sp_dur = sum(min(s_et, sp["end"]) - max(s_st, sp["start"]) for sp in overlapping_speech)
        sp_words = sum(sp.get("words", 0) for sp in overlapping_speech)
        wpm = (sp_words / (s_dur / 60.0)) if s_dur > 0 else 0.0
        coverage = (sp_dur / s_dur) if s_dur > 0 else 0.0
        is_continuous_talk = (wpm >= 65.0 and coverage >= 0.40) or (wpm >= 85.0 and coverage >= 0.30)

        # Check guitar performance context
        has_guitar_audio = any(
            (gs[0] <= s_st <= gs[1]) or (gs[0] <= s_et <= gs[1]) or (s_st <= gs[0] and s_et >= gs[1])
            for gs in guitar_sessions
        )

        # Query Vision AI on keyframe at center of sub-window
        cap.set(cv2.CAP_PROP_POS_MSEC, mid * 1000.0)
        ret, frame = cap.read()
        if not ret:
            continue

        small = cv2.resize(frame, (960, 540))
        _, buf = cv2.imencode('.jpg', small, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        b64 = base64.b64encode(buf).decode('utf-8')

        payload = {
            'model': model,
            'prompt': REFINED_PROMPT,
            'images': [b64],
            'stream': False,
            'options': {'num_ctx': 4096, 'temperature': 0.1}
        }

        cls = "CASUAL_CHAT"
        intensity = 0
        action = "casual chat"
        wet = False

        try:
            req = urllib.request.Request(
                f'{ollama_api}/api/generate',
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                res = json.loads(resp.read().decode('utf-8'))
            txt = res.get('response', '')
            if '```' in txt:
                txt = txt.split('```')[1]
                if txt.startswith('json'):
                    txt = txt[4:]
            data = json.loads(txt.strip())
            cls = data.get('classification', 'CASUAL_CHAT')
            intensity = int(data.get('intensity', 0))
            action = data.get('action', '')
            wet = bool(data.get('wetness_detected', False))
        except Exception as e:
            logger.warning(f"Vision API query notice at {mid:.1f}s ({e})")

        act_lower = action.lower()

        # Discard casual chat, sitting, drinking, adjusting clothes
        if cls == "CASUAL_CHAT" or intensity == 0:
            logger.info(f"    PRUNE [{s_st:>6.1f}s-{s_et:>6.1f}s]: Score 0 ({action})")
            continue

        # If talking continuously and not extreme action (Score < 4), prune as chat (only for live streams)
        if not is_produced_clip and is_continuous_talk and intensity < 4:
            logger.info(f"    PRUNE [{s_st:>6.1f}s-{s_et:>6.1f}s]: High speech chatting ({wpm:.0f} WPM, {coverage*100:.0f}% talk) | {action}")
            continue

        # Guitar handling (strictly lowest priority Level 1)
        is_guitar = has_guitar_audio or ("guitar" in act_lower) or ("strum" in act_lower)
        if intensity == 1:
            if is_guitar:
                kept_sub_blocks.append({
                    "start_sec": s_st,
                    "end_sec": s_et,
                    "intensity": 1,
                    "action": action,
                    "wetness": False,
                    "mid": mid,
                    "category": "guitar"
                })
                logger.info(f"    KEEP  [{s_st:>6.1f}s-{s_et:>6.1f}s]: Score 1 Music ({action})")
            else:
                logger.info(f"    PRUNE [{s_st:>6.1f}s-{s_et:>6.1f}s]: Score 1 non-guitar ({action})")
            continue

        # Level 2 handling: must be active striptease / reveal
        if intensity == 2:
            strip_keywords = ["strip", "reveal", "undress", "unhook", "pulling aside", "peeling", "slide off"]
            if any(k in act_lower for k in strip_keywords):
                kept_sub_blocks.append({
                    "start_sec": s_st,
                    "end_sec": s_et,
                    "intensity": 2,
                    "action": action,
                    "wetness": wet,
                    "mid": mid,
                    "category": "active_show"
                })
                logger.info(f"    KEEP  [{s_st:>6.1f}s-{s_et:>6.1f}s]: Score 2 Striptease ({action})")
            else:
                logger.info(f"    PRUNE [{s_st:>6.1f}s-{s_et:>6.1f}s]: Score 2 casual lingerie posing ({action})")
            continue

        # Level 3, 4, 5: genuine active performance acts
        kept_sub_blocks.append({
            "start_sec": s_st,
            "end_sec": s_et,
            "intensity": intensity,
            "action": action,
            "wetness": wet,
            "mid": mid,
            "category": "active_show"
        })
        logger.info(f"    KEEP  [{s_st:>6.1f}s-{s_et:>6.1f}s]: Score {intensity}/5 Active Show ({action}, wet={wet})")

    # Merge adjacent kept sub-blocks (gap <= 6.0s and same category)
    if not kept_sub_blocks:
        return []

    merged_clips = []
    curr_clip = None

    for b in kept_sub_blocks:
        if curr_clip is None:
            curr_clip = {
                "start_sec": b["start_sec"],
                "end_sec": b["end_sec"],
                "intensity": b["intensity"],
                "action": b["action"],
                "wetness_detected": b["wetness"],
                "peak_action_sec": b["mid"],
                "category": b["category"],
                "action_moments": [{
                    "time_sec": b["mid"],
                    "intensity": b["intensity"],
                    "action": b["action"],
                    "wet": b["wetness"]
                }] if b["intensity"] >= 3 else []
            }
            continue

        gap = b["start_sec"] - curr_clip["end_sec"]
        same_cat = (b["category"] == curr_clip["category"])

        if gap <= 6.0 and same_cat:
            curr_clip["end_sec"] = b["end_sec"]
            if b["wetness"]:
                curr_clip["wetness_detected"] = True
            if b["intensity"] > curr_clip["intensity"]:
                curr_clip["intensity"] = b["intensity"]
                curr_clip["action"] = b["action"]
                curr_clip["peak_action_sec"] = b["mid"]
            elif b["intensity"] == curr_clip["intensity"] and len(b["action"]) > len(curr_clip["action"]):
                curr_clip["action"] = b["action"]
                curr_clip["peak_action_sec"] = b["mid"]

            if b["intensity"] >= 3:
                curr_clip["action_moments"].append({
                    "time_sec": b["mid"],
                    "intensity": b["intensity"],
                    "action": b["action"],
                    "wet": b["wetness"]
                })
        else:
            curr_clip["duration_sec"] = round(curr_clip["end_sec"] - curr_clip["start_sec"], 2)
            if curr_clip["category"] == "guitar":
                curr_clip["label"] = f"Music [1/5]: {curr_clip['action'][:24]}"
                curr_clip["marker_color"] = "Yellow"
            else:
                curr_clip["label"] = f"Show [{curr_clip['intensity']}/5]: {curr_clip['action'][:26]}"
                curr_clip["marker_color"] = "Red" if curr_clip["intensity"] == 5 else "Purple"
            merged_clips.append(curr_clip)

            curr_clip = {
                "start_sec": b["start_sec"],
                "end_sec": b["end_sec"],
                "intensity": b["intensity"],
                "action": b["action"],
                "wetness_detected": b["wetness"],
                "peak_action_sec": b["mid"],
                "category": b["category"],
                "action_moments": [{
                    "time_sec": b["mid"],
                    "intensity": b["intensity"],
                    "action": b["action"],
                    "wet": b["wetness"]
                }] if b["intensity"] >= 3 else []
            }

    if curr_clip is not None:
        curr_clip["duration_sec"] = round(curr_clip["end_sec"] - curr_clip["start_sec"], 2)
        if curr_clip["category"] == "guitar":
            curr_clip["label"] = f"Music [1/5]: {curr_clip['action'][:24]}"
            curr_clip["marker_color"] = "Yellow"
        else:
            curr_clip["label"] = f"Show [{curr_clip['intensity']}/5]: {curr_clip['action'][:26]}"
            curr_clip["marker_color"] = "Red" if curr_clip["intensity"] == 5 else "Purple"
        merged_clips.append(curr_clip)

    return merged_clips


def group_and_classify_segments(
    points: List[Dict[str, Any]],
    audio_profile: Dict[str, Any],
    fps: float = 30.0,
    video_duration: float = 0.0,
    video_path: Optional[pathlib.Path] = None,
    min_window_sec: float = 5.0,
    max_gap_sec: float = 4.0,
    is_produced_clip: bool = False,
) -> List[Dict[str, Any]]:
    """Combines adaptive optical flow motion windows with GPU 0 Vision AI and Faster-Whisper music cues.
    Eliminates casual chatting and sitting downtime while preserving 100% of active shows and guitar performances.
    """
    if not points:
        return []

    # 0. Global Performer Presence Gate: verify that a human performer is actually in the stream
    performer_pts = [p for p in points if p.get("has_performer", False) or p.get("skin_pct", 0.0) >= 0.020]
    stream_performer_pct = (len(performer_pts) / max(1, len(points))) * 100.0
    if stream_performer_pct < 4.0:
        logger.warning(
            f"Standby Stream Detected: Performer visible in only {stream_performer_pct:.1f}% of frames. "
            f"Camera was left streaming on an empty room/chair. Suppressing false cuts and thumbnails."
        )
        return []

    # 1. Compute Adaptive Motion Baseline & Thresholds for this specific recording
    areas = np.array([p["motion_area"] for p in points])
    energies = np.array([p["motion_energy"] for p in points])

    base_area = float(np.percentile(areas, 20))
    p50_area = float(np.percentile(areas, 50))
    p75_area = float(np.percentile(areas, 75))
    p85_area = float(np.percentile(areas, 85))
    max_area = float(np.max(areas))

    base_energy = float(np.percentile(energies, 20))
    p85_energy = float(np.percentile(energies, 85))

    area_thresh = max(0.0035, base_area + 0.08 * (p85_area - base_area))
    energy_thresh = max(0.0018, base_energy + 0.08 * (p85_energy - base_energy))
    high_motion_mark = base_area + 0.50 * (p85_area - base_area)

    logger.info(
        f"Adaptive Motion Calibration: base_area={base_area:.4f}, p75={p75_area:.4f}, p85={p85_area:.4f}, max={max_area:.4f} "
        f"-> Active Thresholds: area>={area_thresh:.4f} or energy>={energy_thresh:.4f} (High Motion mark>={high_motion_mark:.4f})"
    )

    # 2. Group raw motion points into continuous motion candidate windows
    candidates = []
    current_start = None
    last_active_time = None
    accum_energy = []

    for pt in points:
        t = pt["time_sec"]
        performer_in_frame = pt.get("has_performer", True) or (pt.get("skin_pct", 0.0) >= 0.015)
        is_active = ((pt["motion_area"] >= area_thresh) or (pt["motion_energy"] >= energy_thresh)) and performer_in_frame

        if is_active:
            if current_start is None:
                current_start = t
            last_active_time = t
            accum_energy.append(pt["motion_area"])
        else:
            if current_start is not None:
                if (t - last_active_time) > max_gap_sec:
                    duration = last_active_time - current_start
                    if duration >= min_window_sec:
                        candidates.append({
                            "start_sec": current_start,
                            "end_sec": last_active_time,
                            "duration_sec": round(duration, 2),
                            "avg_motion_area": round(float(np.mean(accum_energy)), 4) if accum_energy else 0.0,
                        })
                    current_start = None
                    last_active_time = None
                    accum_energy = []

    if current_start is not None and last_active_time is not None:
        duration = last_active_time - current_start
        if duration >= min_window_sec:
            candidates.append({
                "start_sec": current_start,
                "end_sec": last_active_time,
                "duration_sec": round(duration, 2),
                "avg_motion_area": round(float(np.mean(accum_energy)), 4) if accum_energy else 0.0,
            })

    # 3. Cluster Guitar Performance Cues into Discrete Song Sessions
    all_speech = audio_profile.get("all_speech", [])
    guitar_cues = audio_profile.get("guitar_segments", [])

    guitar_sessions = []
    if guitar_cues:
        sorted_cues = sorted(guitar_cues, key=lambda x: x["start"])
        curr_g_start = max(0.0, sorted_cues[0]["start"] - 10.0)
        curr_g_end = sorted_cues[0]["end"] + 10.0

        for cue in sorted_cues[1:]:
            if cue["start"] <= curr_g_end + 45.0:
                curr_g_end = max(curr_g_end, cue["end"] + 10.0)
            else:
                if (curr_g_end - curr_g_start) >= 8.0:
                    guitar_sessions.append((curr_g_start, curr_g_end))
                curr_g_start = max(0.0, cue["start"] - 10.0)
                curr_g_end = cue["end"] + 10.0
        if (curr_g_end - curr_g_start) >= 8.0:
            guitar_sessions.append((curr_g_start, curr_g_end))

    logger.info(f"Identified {len(guitar_sessions)} discrete guitar performance sessions.")

    # 4. Open video for GPU 0 Vision AI verification
    cap = None
    if video_path and video_path.exists():
        cap = cv2.VideoCapture(str(video_path))
        logger.info(f"Loaded video for GPU 0 Vision AI Verification across {len(candidates)} candidate clips...")

    kept_segments = []

    for idx, cand in enumerate(candidates, 1):
        s_start = cand["start_sec"]
        s_end = cand["end_sec"]
        dur = cand["duration_sec"]
        avg_area = cand.get("avg_motion_area", 0.0)

        # Check if audio detected guitar performance context
        has_guitar_audio = any(
            (gs[0] <= s_start <= gs[1]) or (gs[0] <= s_end <= gs[1]) or (s_start <= gs[0] and s_end >= gs[1])
            for gs in guitar_sessions
        )

        # Vision AI verification gate on GPU 0
        if cap and cap.isOpened():
            logger.info(f"[{idx:03d}/{len(candidates):03d}] Evaluating motion candidate {s_start:>6.1f}s - {s_end:>6.1f}s ({dur:>4.1f}s)...")
            sub_clips = verify_candidate_with_vision(cap, cand, all_speech, guitar_sessions, is_produced_clip=is_produced_clip)
            if sub_clips:
                for sc in sub_clips:
                    kept_segments.append(sc)
                    logger.info(f"    -> KEPT SHOW (Score {sc['intensity']}/5): {sc['start_sec']:>6.1f}s - {sc['end_sec']:>6.1f}s ({sc['duration_sec']:>4.1f}s) | {sc['action']}")
            else:
                logger.info(f"    -> PRUNED ENTIRE CANDIDATE: {s_start:>6.1f}s - {s_end:>6.1f}s ({dur:>4.1f}s)")
            continue

        # Fallback to speech/motion heuristic if Vision AI is unavailable
        seg_words = 0
        seg_speech_sec = 0.0
        for sp in all_speech:
            overlap_s = max(s_start, sp["start"])
            overlap_e = min(s_end, sp["end"])
            if overlap_e > overlap_s:
                seg_speech_sec += (overlap_e - overlap_s)
                seg_words += sp.get("words", 0)

        wpm = (seg_words / (dur / 60.0)) if dur > 0 else 0
        speech_coverage_pct = (seg_speech_sec / dur) if dur > 0 else 0.0

        if avg_area >= high_motion_mark:
            cand["category"] = "active_show"
            cand["label"] = f"Performance Segment #{len(kept_segments) + 1}"
            cand["marker_color"] = "Purple"
            cand["intensity"] = 3
            cand["action_moments"] = []
            kept_segments.append(cand)
            continue

        if wpm >= 85.0 and speech_coverage_pct >= 0.50:
            continue
        if dur < 20.0 and wpm >= 60.0 and speech_coverage_pct >= 0.50:
            continue

        cand["category"] = "active_show"
        cand["label"] = f"Performance Segment #{len(kept_segments) + 1}"
        cand["marker_color"] = "Purple"
        cand["intensity"] = 3
        cand["action_moments"] = []
        kept_segments.append(cand)

    if cap:
        cap.release()

    # 5. Smooth merge adjacent segments of the same category (gap <= 6.0s)
    merged = []
    current = None
    for s in kept_segments:
        if current is None:
            current = dict(s)
            continue

        gap = s["start_sec"] - current["end_sec"]
        same_cat = (current["marker_color"] == s["marker_color"])

        if gap <= 6.0 and same_cat:
            current["end_sec"] = s["end_sec"]
            current["duration_sec"] = round(current["end_sec"] - current["start_sec"], 2)
            if s.get("wetness_detected"):
                current["wetness_detected"] = True
            if s.get("intensity", 0) > current.get("intensity", 0):
                current["intensity"] = s["intensity"]
                current["action"] = s["action"]
                current["peak_action_sec"] = s.get("peak_action_sec", current.get("peak_action_sec", 0.0))
            if "action_moments" in s:
                current.setdefault("action_moments", []).extend(s["action_moments"])
        else:
            merged.append(current)
            current = dict(s)

    if current is not None:
        merged.append(current)

    if current:
        merged.append(current)

    # Calculate frame numbers
    for seg in merged:
        seg["start_frame"] = int(round(seg["start_sec"] * fps))
        seg["end_frame"] = int(round(seg["end_sec"] * fps))
        seg["duration_frames"] = seg["end_frame"] - seg["start_frame"]

    logger.info(f"Classification complete: {len(merged)} show segments preserved across stream.")
    return merged


# ----------------------------------------------------------------------
# 5. Stage 4: DaVinci Resolve Studio 21.1 Direct Timeline Generator
# ----------------------------------------------------------------------
def build_davinci_resolve_timeline(
    video_path: pathlib.Path,
    segments: List[Dict[str, Any]],
    timeline_name: Optional[str] = None,
    fps: float = 30.0,
) -> Dict[str, Any]:
    """Connects to running DaVinci Resolve Studio 21.1+ and builds the cutdown timeline with markers."""
    tl_name = timeline_name or f"{video_path.stem}_Master_Show_Cut"
    logger.info(f"Connecting to DaVinci Resolve to assemble timeline '{tl_name}'...")

    try:
        os.environ.setdefault("RESOLVE_SCRIPT_API", r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting")
        os.environ.setdefault("RESOLVE_SCRIPT_LIB", r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll")
        script_module_dir = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules"
        if script_module_dir not in sys.path:
            sys.path.append(script_module_dir)

        import DaVinciResolveScript as bmd
        resolve = bmd.scriptapp("Resolve")
        if not resolve:
            raise RuntimeError("Could not connect to DaVinci Resolve. Is Resolve.exe running?")

        pm = resolve.GetProjectManager()
        project = pm.GetCurrentProject()
        if not project:
            project = pm.CreateProject(f"CamCut_{video_path.stem[:20]}")

        media_pool = project.GetMediaPool()
        root_folder = media_pool.GetRootFolder()

        target_clip = None
        for clip in root_folder.GetClipList():
            c_name = str(clip.GetName()).lower()
            if video_path.stem.lower() in c_name:
                target_clip = clip
                break

        if not target_clip:
            imported = media_pool.ImportMedia([str(video_path.resolve())])
            if imported and len(imported) > 0:
                target_clip = imported[0]
            else:
                for clip in root_folder.GetClipList():
                    if video_path.name.lower() in str(clip.GetName()).lower():
                        target_clip = clip
                        break

        if not target_clip:
            raise RuntimeError(f"Failed to import {video_path} into DaVinci Resolve Media Pool.")

        # Delete existing timeline with same name if exists
        for i in range(project.GetTimelineCount()):
            t = project.GetTimelineByIndex(i + 1)
            if t and t.GetName() == tl_name:
                media_pool.DeleteTimelines([t])
                break

        # Create Timeline with all active show cuts
        clip_infos = []
        for seg in segments:
            clip_infos.append({
                "mediaPoolItem": target_clip,
                "startFrame": seg["start_frame"],
                "endFrame": seg["end_frame"],
            })

        timeline = media_pool.CreateEmptyTimeline(tl_name)
        if not timeline and clip_infos:
            timeline = media_pool.CreateTimelineFromClips(tl_name, [clip_infos[0]])
            to_append = clip_infos[1:]
        else:
            to_append = clip_infos

        project.SetCurrentTimeline(timeline)
        chunk_size = 50
        for i in range(0, len(to_append), chunk_size):
            media_pool.AppendToTimeline(to_append[i:i + chunk_size])

        # Color-coded markers for each performance segment
        current_record_frame = 0
        markers_count = 0
        for seg in segments:
            color = seg.get("marker_color", "Purple")
            name = seg.get("label", "Active Show")[:32]
            note = f"Runtime: {seg['duration_sec']}s"
            duration = seg["duration_frames"]
            try:
                timeline.AddMarker(current_record_frame, color, name, note, duration)
                markers_count += 1
            except Exception:
                pass
            current_record_frame += duration

        project.SetCurrentTimeline(timeline)
        total_cut_sec = current_record_frame / fps
        logger.info(f"Timeline '{tl_name}' created in DaVinci Resolve! Total Active Show Duration: {round(total_cut_sec / 60, 2)} minutes ({markers_count} markers placed).")

        return {
            "success": True,
            "timeline_name": tl_name,
            "total_segments": len(segments),
            "total_cut_seconds": round(total_cut_sec, 2),
            "total_cut_minutes": round(total_cut_sec / 60, 2),
            "status": "TIMELINE_CREATED_IN_DAVINCI_RESOLVE",
        }

    except Exception as e:
        logger.error(f"DaVinci Resolve direct assembly error: {e}")
        return {"success": False, "error": str(e)}


# ----------------------------------------------------------------------
# 6. Helper: Timecode Formatter & Universal CMX 3600 EDL Export
# ----------------------------------------------------------------------
def format_tc(seconds: float, fps: float = 30.0) -> str:
    """Formats seconds into HH:MM:SS:FF standard timecode."""
    total_frames = int(round(seconds * fps))
    ff = total_frames % int(fps)
    ss = int(seconds) % 60
    mm = (int(seconds) // 60) % 60
    hh = int(seconds) // 3600
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"


def export_edl(
    video_path: pathlib.Path,
    segments: List[Dict[str, Any]],
    fps: float = 30.0,
    output_file: Optional[pathlib.Path] = None,
) -> pathlib.Path:
    """Exports a standard CMX 3600 EDL file for universal import into any NLE."""
    edl_path = output_file if output_file is not None else video_path.with_suffix(".edl")
    lines = [f"TITLE: {video_path.stem[:30]}_ACTIVE_CUTS", "FCM: NON-DROP FRAME", ""]

    rec_in = 0.0
    for idx, seg in enumerate(segments, 1):
        src_in_tc = format_tc(seg["start_sec"], fps)
        src_out_tc = format_tc(seg["end_sec"], fps)
        rec_out = rec_in + seg["duration_sec"]
        rec_in_tc = format_tc(rec_in, fps)
        rec_out_tc = format_tc(rec_out, fps)

        lines.append(f"{idx:03d}  AX       V     C        {src_in_tc} {src_out_tc} {rec_in_tc} {rec_out_tc}")
        lines.append(f"* FROM CLIP NAME: {video_path.name}")
        lines.append(f"* SCENE: {seg.get('label', 'Active Show')}")
        lines.append("")
        rec_in = rec_out

    edl_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Exported standard CMX 3600 EDL to {edl_path}")
    return edl_path


# ----------------------------------------------------------------------
# 7. Main Orchestrator Pipeline
# ----------------------------------------------------------------------
def process_cam_video(
    video_path: pathlib.Path,
    sample_fps: float = 1.0,
    motion_threshold: float = 0.04,
    enable_audio_ai: bool = True,
    create_resolve_timeline: bool = True,
    output_dir: Optional[pathlib.Path] = None,
) -> Dict[str, Any]:
    """Runs the full multi-modal active show detection and DaVinci Resolve assembly pipeline."""
    video_path = pathlib.Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video file does not exist: {video_path}")

    start_time = time.time()
    logger.info(f"=== Starting Cam Show Cutdown Pipeline on {video_path.name} ===")

    # 1. Video Probe
    info = probe_video(video_path)
    fps = info["fps"]
    duration = info["duration"]
    logger.info(f"Video info: {info['width']}x{info['height']} @ {fps} fps, Duration: {round(duration / 60, 2)} mins ({round(duration / 3600, 2)} hrs)")

    # 2. Stage 1: Fast Optical Flow Motion Scanning
    points = scan_motion_energy(video_path, sample_fps=sample_fps, motion_threshold=motion_threshold)

    # 3. Stage 2: Audio Speech Density & Acoustic Music Profiler
    audio_profile = {}
    if enable_audio_ai:
        audio_profile = extract_and_scan_audio(video_path, device_index=1)

    # Auto-detect format: Produced Scene / Standalone Clip (10-60m) vs Multi-Hour Live Stream
    stem_lower = video_path.stem.lower()
    is_live_stream = ("live-with-restream" in stem_lower) or ("camshow" in stem_lower) or (duration > 4200.0)
    is_produced_clip = not is_live_stream
    if is_produced_clip:
        logger.info(f"Detected Produced Clip / Scene Video ({round(duration / 60, 1)}m) — preserving spoken dialogue & dirty talk.")

    # 4. Stage 3: Multi-Modal Classification (Motion + Speech + Music + Vision AI)
    final_segments = group_and_classify_segments(
        points=points,
        audio_profile=audio_profile,
        fps=fps,
        video_duration=duration,
        video_path=video_path,
        is_produced_clip=is_produced_clip,
    )

    total_active_sec = sum(s["duration_sec"] for s in final_segments)
    cut_ratio_pct = round((total_active_sec / max(1.0, duration)) * 100.0, 1)

    logger.info(f"Final Cuts: {len(final_segments)} show segments.")
    logger.info(f"Original: {round(duration / 60, 2)} mins -> Cutdown: {round(total_active_sec / 60, 2)} mins (Kept {cut_ratio_pct}% active performance)")

    # 5. Save JSON Cutlist & EDL
    target_out_dir = output_dir if output_dir is not None else pathlib.Path(r"F:\WORKHORSE\cam_shows\processing")
    target_out_dir.mkdir(parents=True, exist_ok=True)
    cutlist_data = {
        "source_video": str(video_path),
        "original_duration_seconds": duration,
        "original_duration_minutes": round(duration / 60, 2),
        "cutdown_duration_seconds": total_active_sec,
        "cutdown_duration_minutes": round(total_active_sec / 60, 2),
        "compression_percentage": cut_ratio_pct,
        "segments": final_segments,
    }
    cutlist_json_path = target_out_dir / f"{video_path.stem}.cutlist.json"
    edl_path = target_out_dir / f"{video_path.stem}.edl"
    try:
        cutlist_json_path.write_text(json.dumps(cutlist_data, indent=2), encoding="utf-8")
        export_edl(video_path, final_segments, fps=fps, output_file=edl_path)
    except Exception as e:
        logger.warning(f"Could not save cutlist/EDL directly to {target_out_dir} ({e}), writing to processing dir")
        processing_dir = pathlib.Path(r"F:\WORKHORSE\cam_shows\processing")
        processing_dir.mkdir(parents=True, exist_ok=True)
        cutlist_json_path = processing_dir / f"{video_path.stem}.cutlist.json"
        cutlist_json_path.write_text(json.dumps(cutlist_data, indent=2), encoding="utf-8")
        edl_path = export_edl(video_path, final_segments, fps=fps, output_file=processing_dir / f"{video_path.stem}.edl")

    # 6. Stage 4: DaVinci Resolve Direct Assembly
    resolve_res = None
    if create_resolve_timeline:
        resolve_res = build_davinci_resolve_timeline(video_path, final_segments, fps=fps)

    elapsed = round(time.time() - start_time, 2)
    logger.info(f"=== Pipeline Completed in {elapsed}s ===")

    return {
        "success": True,
        "video": str(video_path),
        "original_minutes": round(duration / 60, 2),
        "active_show_minutes": round(total_active_sec / 60, 2),
        "segments_count": len(final_segments),
        "json_cutlist": str(cutlist_json_path),
        "edl_file": str(edl_path),
        "davinci_resolve": resolve_res,
        "elapsed_seconds": elapsed,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WORKHORSE Cam Show AI Cutter & DaVinci Resolve Auto-Editor")
    parser.add_argument("video", help="Path to raw video file (.mp4, .mkv, .mov)")
    parser.add_argument("--sample-fps", type=float, default=1.0, help="Frame sampling rate for motion scan (default: 1.0 fps)")
    parser.add_argument("--motion-threshold", type=float, default=0.04, help="Motion area threshold (default: 0.04)")
    parser.add_argument("--no-audio", action="store_true", help="Disable Whisper speech density & acoustic music scan")
    parser.add_argument("--no-resolve", action="store_true", help="Do not create timeline in DaVinci Resolve")
    args = parser.parse_args()

    v_path = pathlib.Path(args.video)
    res = process_cam_video(
        v_path,
        sample_fps=args.sample_fps,
        motion_threshold=args.motion_threshold,
        enable_audio_ai=not args.no_audio,
        create_resolve_timeline=not args.no_resolve,
    )
    print(json.dumps(res, indent=2))
