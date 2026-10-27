#!/usr/bin/env python3
"""
WORKHORSE STAGE: CAM SHOW COMPLETE CONTENT PACKAGER & WATCH FOLDER
==================================================================
Monitors F:\\WORKHORSE\\cam_shows\\inbox for new adult model cam show recordings.
Automatically produces a complete, organized content package for every show:
1. Full 1080p gapless show cutdown MP4 (NVENC accelerated)
2. 60-second fast-paced highlight teaser MP4 (for Twitter/X, Telegram, OnlyFans promo)
3. 16 high-resolution 1080p JPEG preview thumbnails (outfit, guitar, performance peaks)
4. Master CMX 3600 EDL and JSON cutlist
5. Automatic timeline assembly in DaVinci Resolve Studio 21.1
6. Organized into F:\\WORKHORSE\\cam_shows\\output\\<YYYY-MM-DD_Show_Name>\\
"""

import sys
import os
import pathlib

# Ensure F:\WORKHORSE is on sys.path
WORKHORSE_ROOT = pathlib.Path(r"F:\WORKHORSE")
if str(WORKHORSE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKHORSE_ROOT))

import argparse
import datetime
import json
import logging
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("cam_show_packager")

BASE_DIR = pathlib.Path(r"F:\WORKHORSE\cam_shows")
INBOX_DIR = BASE_DIR / "inbox"
PROCESSING_DIR = BASE_DIR / "processing"
OUTPUT_DIR = BASE_DIR / "output"
ARCHIVE_DIR = BASE_DIR / "archive"

for d in [INBOX_DIR, PROCESSING_DIR, OUTPUT_DIR, ARCHIVE_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def extract_thumbnails(
    video_path: pathlib.Path,
    clips: List[Dict[str, Any]],
    output_thumbs_dir: pathlib.Path,
    motion_points: Optional[List[Dict[str, Any]]] = None,
    cutdown_video_path: Optional[pathlib.Path] = None,
    target_count: int = 36,
) -> List[Dict[str, Any]]:
    """Extracts curated peak highlight preview thumbnails (30-40 total) directly from the final edited video.
    Captures the best action climaxes, top teaser moments, and performance highlights without image bloat.
    """
    output_thumbs_dir.mkdir(parents=True, exist_ok=True)
    for old_thumb in output_thumbs_dir.glob("*.jpg"):
        try:
            old_thumb.unlink()
        except Exception:
            pass

    # Load motion points for peak action detection if not provided
    if not motion_points:
        motion_cache = PROCESSING_DIR / f"{video_path.stem}.motion.json"
        if motion_cache.exists():
            try:
                motion_points = json.loads(motion_cache.read_text(encoding="utf-8"))
            except Exception:
                motion_points = []
        else:
            motion_points = []

    def find_peak_action_sec(t_start: float, t_end: float) -> float:
        """Finds the timestamp within [t_start, t_end] with the highest motion energy and area."""
        pad = min(1.0, (t_end - t_start) * 0.10)
        candidates = [p for p in motion_points if (t_start + pad) <= p.get("time_sec", 0) <= (t_end - pad)]
        if candidates:
            best = max(candidates, key=lambda p: (p.get("motion_energy", 0.0) * 0.6 + p.get("motion_area", 0.0) * 0.4))
            return round(best["time_sec"], 2)
        return round((t_start + t_end) / 2.0, 2)

    def get_action_priority(act_text: str) -> int:
        txt = act_text.lower()
        if any(k in txt for k in ["pullout", "pulling", "massive dildo", "giant dildo", "penetration", "pumping", "thrusting", "thrust", "riding", "deepthroat", "deep throat", "gagging", "anal"]):
            return 100
        if any(k in txt for k in ["wet fingering", "dripping", "spread-legged", "spread legs", "masturbat", "drool", "spit", "saliva"]):
            return 90
        if any(k in txt for k in ["sucking dildo", "sucking", "licking", "mouth", "oral", "toy play", "toy engagement"]):
            return 85
        if any(k in txt for k in ["breast", "fishnet", "teas", "pinch", "caress", "mask", "spider", "bed show", "floor show", "reveal"]):
            return 75
        if "guitar" in txt:
            return 10
        return 40

    logger.info(f"Selecting ~{target_count} curated peak highlight thumbnails directly from the final edited video...")

    use_cutdown = cutdown_video_path is not None and cutdown_video_path.exists()
    source_video = cutdown_video_path if use_cutdown else video_path

    # Process all clips in chronological order - 100% focused on performance and action highlights
    sorted_clips = sorted(clips, key=lambda c: c["start_sec"])
    candidate_stamps = []
    elapsed_cutdown = 0.0

    step = 75.0
    for c in sorted_clips:
        dur = c["duration_sec"]
        c_start = c["start_sec"]
        c_end = c["end_sec"]
        action_desc = c.get("action", c.get("label", "Show Performance"))
        moments = c.get("action_moments", [])

        if moments:
            for m in moments:
                m_time = m.get("time_sec", c_start)
                m_score = m.get("intensity", c.get("intensity", 3))
                m_act = m.get("action", action_desc)

                # Skip gross movement (standing up, pulling clothes)
                pts_around = [p for p in motion_points if abs(p.get("time_sec", 0) - m_time) <= 1.0]
                max_area = max([p.get("motion_area", 0) for p in pts_around], default=0.0)
                if max_area > 0.28:
                    continue

                offset = max(0.0, min(dur - 0.5, m_time - c_start))
                stamp_time = (elapsed_cutdown + offset) if use_cutdown else (c_start + offset)
                pri = 100 if m_score >= 5 else (90 if m_score == 4 else (80 if m_score == 3 else 40))
                candidate_stamps.append((stamp_time, "highlight", m_act[:32], pri))
        else:
            if dur <= step:
                v_peak_raw = c.get("peak_action_sec") or find_peak_action_sec(c_start, c_end)
                v_offset = max(0.0, min(dur - 0.5, v_peak_raw - c_start))
                stamp_time = (elapsed_cutdown + v_offset) if use_cutdown else v_peak_raw
                priority = get_action_priority(action_desc)
                candidate_stamps.append((stamp_time, "highlight", action_desc[:32], priority))
            else:
                curr = c_start
                while curr < (c_end - 5.0):
                    w_end = min(c_end, curr + step)
                    sub_peak_raw = find_peak_action_sec(curr, w_end)
                    sub_offset = max(0.0, min(dur - 0.5, sub_peak_raw - c_start))
                    sub_stamp_time = (elapsed_cutdown + sub_offset) if use_cutdown else sub_peak_raw
                    priority = get_action_priority(action_desc)
                    candidate_stamps.append((sub_stamp_time, "highlight", action_desc[:32], priority))
                    curr += step

        elapsed_cutdown += dur

    # Select target_count evenly distributed across candidate stamps, prioritizing highest-action moments
    needed_thumbs = target_count
    selected_stamps = []
    if candidate_stamps:
        chunk_size = max(1, len(candidate_stamps) // needed_thumbs)
        for i in range(0, len(candidate_stamps), chunk_size):
            chunk = candidate_stamps[i:i + chunk_size]
            if chunk:
                best_pt = max(chunk, key=lambda s: s[3])
                selected_stamps.append(best_pt)
            if len(selected_stamps) >= needed_thumbs:
                break

    # Sort chronologically and deduplicate closer than 20.0s
    selected_stamps.sort(key=lambda s: s[0])
    deduped = []
    for t, tag, desc, pri in selected_stamps:
        if not deduped:
            deduped.append((t, tag, desc))
            continue
        if (t - deduped[-1][0]) >= 20.0:
            deduped.append((t, tag, desc))

    stamps = []
    for idx, (t, tag, desc) in enumerate(deduped, 1):
        mm = int(t // 60)
        ss = int(t % 60)
        clean_desc = desc.replace(" ", "_").replace(":", "").replace("/", "_").replace(",", "")[:24]
        fname = f"{idx:02d}_{tag}_{mm:02d}m{ss:02d}s_{clean_desc}.jpg"
        stamps.append((t, fname, desc))

    # Extract all high-res frames directly from the final edited cutdown video
    extracted = []
    for sec, fname, lbl in stamps:
        out_f = output_thumbs_dir / fname
        cmd = [
            "ffmpeg", "-y", "-ss", f"{sec:.2f}", "-i", str(source_video),
            "-frames:v", "1", "-q:v", "2", str(out_f)
        ]
        subprocess.run(cmd, capture_output=True, timeout=20)
        if out_f.exists() and out_f.stat().st_size > 5000:
            # Verify thumbnail has actual human performer (not empty chair or background light)
            t_img = cv2.imread(str(out_f))
            if t_img is not None:
                h_img = cv2.cvtColor(t_img, cv2.COLOR_BGR2HSV)
                y_img = cv2.cvtColor(t_img, cv2.COLOR_BGR2YCrCb)
                mh = cv2.inRange(h_img, np.array([0, 45, 60]), np.array([18, 255, 255]))
                my = cv2.inRange(y_img, np.array([0, 135, 80]), np.array([255, 175, 125]))
                skin_test = cv2.bitwise_and(mh, my)
                skin_pct = (np.count_nonzero(skin_test) / skin_test.size) * 100.0
                if skin_pct < 1.5 and not fname.startswith("01_outfit"):
                    # Discard empty room thumbnail
                    try:
                        out_f.unlink()
                    except Exception:
                        pass
                    continue
            extracted.append({"filename": fname, "timestamp_sec": sec, "label": lbl})

    logger.info(f"Generated {len(extracted)} curated peak highlight preview thumbnails in {output_thumbs_dir.name}")
    return extracted


def generate_highlight_teaser(
    video_path: pathlib.Path,
    clips: List[Dict[str, Any]],
    output_file: pathlib.Path,
    target_duration: float = 30.0,
    cutdown_video_path: Optional[pathlib.Path] = None,
) -> Optional[pathlib.Path]:
    """Builds an ultra-fast-paced, high-octane 30-second highlight teaser promo video with transitions across the whole show.
    Features 20-22 rapid-fire cuts (1.35s net visible each) centered on peak optical flow motion energy and action climaxes.
    """
    logger.info(f"Generating {target_duration}s Dynamic High-Octane Highlight Teaser Video (MP4)...")
    temp_stage = output_file.parent / "_teaser_staging"
    temp_stage.mkdir(parents=True, exist_ok=True)

    try:
        # Enforce .mp4 extension
        if output_file.suffix.lower() != ".mp4":
            output_file = output_file.with_suffix(".mp4")

        use_cutdown = cutdown_video_path is not None and cutdown_video_path.exists()
        source_video = cutdown_video_path if use_cutdown else video_path

        slice_len = 1.65
        trans_dur = 0.30
        target_slices_count = 22

        # 1. Filter active performance clips
        perf_clips = [
            c for c in clips
            if (c.get("category") == "active_show" or c.get("marker_color") == "Purple")
            and c.get("category") != "outfit_intro"
        ]
        if not perf_clips:
            perf_clips = [c for c in clips if c.get("category") != "outfit_intro"]

        # Compute cutdown timeline offsets for each clip
        clip_offsets = []
        elapsed = 0.0
        for c in clips:
            clip_offsets.append({
                "clip": c,
                "cutdown_start": elapsed,
                "cutdown_end": elapsed + c["duration_sec"],
            })
            elapsed += c["duration_sec"]

        # Load motion points for peak motion selection
        motion_cache = PROCESSING_DIR / f"{video_path.stem}.motion.json"
        motion_points = []
        if motion_cache.exists():
            try:
                motion_points = json.loads(motion_cache.read_text(encoding="utf-8"))
            except Exception:
                motion_points = []

        def get_best_motion_sec(t_start: float, t_end: float) -> float:
            pad = min(1.0, (t_end - t_start) * 0.15)
            candidates = [p for p in motion_points if (t_start + pad) <= p.get("time_sec", 0) <= (t_end - pad)]
            if candidates:
                best = max(candidates, key=lambda p: (p.get("motion_energy", 0.0) * 0.6 + p.get("motion_area", 0.0) * 0.4))
                return round(best["time_sec"], 2)
            return round((t_start + t_end) / 2.0, 2)

        # Action Priority Weighting: Prioritizes explicit peak action shots, climaxes, and toy play
        def get_action_priority(act_text: str) -> int:
            txt = act_text.lower()
            # Tier 1: Highest impact climax action shots (pullout, penetration, pumping, deepthroat, anal, gagging)
            if any(k in txt for k in [
                "pullout", "pulling", "massive dildo", "giant dildo", "penetration", "pumping",
                "thrusting", "thrust", "riding", "deepthroat", "deep throat", "gagging", "anal"
            ]):
                return 100
            # Tier 2: Wet fingering, spread masturbation, drool/spit/saliva, intense body play
            if any(k in txt for k in [
                "wet fingering", "dripping", "spread-legged", "spread legs", "masturbat",
                "drool", "spit", "saliva"
            ]):
                return 90
            # Tier 3: Oral & Toy play (sucking dildo, licking, toy in mouth, oral)
            if any(k in txt for k in [
                "sucking dildo", "sucking", "licking", "mouth", "oral", "toy play", "toy engagement"
            ]):
                return 85
            # Tier 4: Breast teasing, fishnets, caress, spider mask, bed/floor shows
            if any(k in txt for k in [
                "breast", "fishnet", "teas", "pinch", "caress", "mask", "spider", "bed show", "floor show", "reveal"
            ]):
                return 75
            if "guitar" in txt:
                return 10
            return 40

        # Collect candidate slices directly from Vision AI verified action moments
        candidate_slices = []
        for info in clip_offsets:
            c = info["clip"]
            if c not in perf_clips:
                continue
            c_start = c["start_sec"]
            c_end = c["end_sec"]
            dur = c["duration_sec"]
            moments = c.get("action_moments", [])

            if moments:
                for m in moments:
                    m_time = m.get("time_sec", c_start)
                    m_score = m.get("intensity", c.get("intensity", 3))
                    m_act = m.get("action", c.get("action", "perf"))

                    # Skip gross movement (standing up, pulling clothes, walking)
                    pts_around = [p for p in motion_points if abs(p.get("time_sec", 0) - m_time) <= 1.0]
                    max_area = max([p.get("motion_area", 0) for p in pts_around], default=0.0)
                    if max_area > 0.28:
                        continue

                    offset = max(0.0, min(dur - slice_len, m_time - c_start - 0.7))
                    slice_start = (info["cutdown_start"] + offset) if use_cutdown else (c_start + offset)
                    pri = 100 if m_score >= 5 else (90 if m_score == 4 else (75 if m_score == 3 else 30))
                    candidate_slices.append((slice_start, m_act, pri))
            else:
                raw_peak = c.get("peak_action_sec") or get_best_motion_sec(c_start, c_end)
                offset = max(0.0, min(dur - slice_len, raw_peak - c_start - 0.7))
                slice_start = (info["cutdown_start"] + offset) if use_cutdown else (c_start + offset)
                pri = get_action_priority(c.get("action", "perf"))
                candidate_slices.append((slice_start, c.get("action", "perf"), pri))

        # Select cuts distributed across active show, picking highest-action moment in each section
        needed_perf = target_slices_count
        selected = []
        if candidate_slices:
            candidate_slices.sort(key=lambda s: s[0])
            chunk_size = max(1, len(candidate_slices) // needed_perf)
            for i in range(0, len(candidate_slices), chunk_size):
                chunk = candidate_slices[i:i + chunk_size]
                if chunk:
                    # Pick slice with highest action priority (or motion)
                    best_slice = max(chunk, key=lambda s: s[2])
                    selected.append((best_slice[0], best_slice[1]))
                if len(selected) >= needed_perf:
                    break

        # Render individual slices with NVENC
        rendered_slices = []
        for idx, (s_start, s_name) in enumerate(selected, 1):
            out_slice = temp_stage / f"slice_{idx:02d}.mp4"
            cmd = [
                "ffmpeg", "-y", "-ss", f"{s_start:.2f}", "-i", str(source_video),
                "-t", f"{slice_len:.2f}",
                "-map", "0:v:0", "-map", "0:a:0?",
                "-c:v", "h264_nvenc", "-gpu", "1", "-preset", "p5", "-b:v", "8M",
                "-c:a", "aac", "-b:a", "192k",
                str(out_slice)
            ]
            subprocess.run(cmd, capture_output=True, timeout=25)
            if out_slice.exists() and out_slice.stat().st_size > 5000:
                rendered_slices.append(out_slice)

        if not rendered_slices:
            logger.warning("No teaser slices were successfully generated.")
            return None

        # Build dynamic xfade filter complex (fast 0.3s transitions)
        transitions = [
            "circlecrop", "wipeleft", "dissolve", "smoothleft", "wiperight",
            "fade", "smoothright", "circleopen", "dissolve", "wipeleft",
            "fade", "smoothleft", "wiperight", "dissolve", "circlecrop",
            "fade", "smoothleft", "dissolve", "wipeleft", "smoothright", "fade"
        ]
        filter_str = ""
        prev_v = "[0:v]"
        current_offset = slice_len - trans_dur

        for idx in range(1, len(rendered_slices)):
            out_v = f"[v{idx}]" if idx < len(rendered_slices) - 1 else "[v_out]"
            trans = transitions[(idx - 1) % len(transitions)]
            filter_str += f"{prev_v}[{idx}:v]xfade=transition={trans}:duration={trans_dur}:offset={current_offset:.2f}{out_v}; "
            prev_v = out_v
            current_offset += (slice_len - trans_dur)

        prev_a = "[0:a]"
        for idx in range(1, len(rendered_slices)):
            out_a = f"[a{idx}]" if idx < len(rendered_slices) - 1 else "[a_out]"
            filter_str += f"{prev_a}[{idx}:a]acrossfade=d={trans_dur}:c1=tri:c2=tri{out_a}; "
            prev_a = out_a

        filter_str = filter_str.rstrip("; ")
        inputs = []
        for f in rendered_slices:
            inputs.extend(["-i", str(f)])

        cmd_concat = [
            "ffmpeg", "-y"
        ] + inputs + [
            "-filter_complex", filter_str,
            "-map", "[v_out]",
            "-map", "[a_out]",
            "-c:v", "h264_nvenc", "-gpu", "1", "-preset", "p5", "-b:v", "8M",
            "-c:a", "aac", "-b:a", "192k",
            "-t", str(target_duration),
            "-movflags", "+faststart",
            str(output_file)
        ]

        t0 = time.time()
        res = subprocess.run(cmd_concat, capture_output=True, timeout=120)
        if output_file.exists():
            logger.info(f"30s High-Octane Highlight Teaser created in {round(time.time() - t0, 1)}s: {output_file.name}")
        else:
            # Fallback fast-cut concat
            list_file = temp_stage / "concat.txt"
            list_file.write_text("\n".join([f"file '{p.resolve()}'" for p in rendered_slices]), encoding="utf-8")
            cmd_fallback = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
                "-c:v", "h264_nvenc", "-gpu", "1", "-preset", "p5", "-b:v", "8M",
                "-c:a", "aac", "-b:a", "192k",
                "-t", str(target_duration),
                "-movflags", "+faststart",
                str(output_file)
            ]
            subprocess.run(cmd_fallback, capture_output=True, timeout=60)
            logger.info(f"Fast-cut highlight teaser created: {output_file.name}")

        return output_file

    finally:
        shutil.rmtree(temp_stage, ignore_errors=True)


def render_full_cutdown_video(
    video_path: pathlib.Path,
    clips: List[Dict[str, Any]],
    output_file: pathlib.Path,
) -> Optional[pathlib.Path]:
    """Renders the complete 1080p gapless show cutdown MP4 via GPU 1 NVENC acceleration."""
    logger.info(f"Rendering Full Show Cutdown Video ({len(clips)} clips)...")
    temp_stage = output_file.parent / "_cutdown_staging"
    shutil.rmtree(temp_stage, ignore_errors=True)
    temp_stage.mkdir(parents=True, exist_ok=True)

    try:
        rendered_clips = []
        t0 = time.time()
        for idx, c in enumerate(clips, 1):
            c_file = temp_stage / f"clip_{idx:03d}.mp4"
            if c_file.exists() and c_file.stat().st_size > 1000:
                rendered_clips.append(c_file)
                continue
            dur = c["duration_sec"]
            cmd = [
                "ffmpeg", "-y", "-ss", str(c["start_sec"]), "-i", str(video_path),
                "-t", str(dur),
                "-map", "0:v:0", "-map", "0:a:0?",
                "-c:v", "h264_nvenc", "-gpu", "1", "-preset", "p4", "-cq", "21",
                "-c:a", "aac", "-b:a", "192k",
                str(c_file)
            ]
            clip_timeout = max(300, int(dur + 120))
            subprocess.run(cmd, capture_output=True, timeout=clip_timeout)
            if c_file.exists():
                rendered_clips.append(c_file)

        if not rendered_clips:
            logger.error("Failed to render individual cutdown segments.")
            return None

        # Concat all segments into master video
        concat_txt = temp_stage / "concat.txt"
        concat_txt.write_text("\n".join([f"file '{p.resolve()}'" for p in rendered_clips]), encoding="utf-8")

        cmd_concat = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
            "-c", "copy",
            "-movflags", "+faststart",
            str(output_file)
        ]
        concat_timeout = max(600, len(rendered_clips) * 5)
        subprocess.run(cmd_concat, capture_output=True, timeout=concat_timeout)
        if output_file.exists():
            elapsed = round(time.time() - t0, 1)
            size_mb = round(output_file.stat().st_size / (1024 * 1024), 1)
            logger.info(f"Full cutdown video rendered in {elapsed}s ({size_mb} MB): {output_file.name}")
            return output_file
        return None

    finally:
        shutil.rmtree(temp_stage, ignore_errors=True)


def package_cam_show(video_path: pathlib.Path) -> Dict[str, Any]:
    """Runs the full AI cutdown, renders cutdown video + teaser + thumbnails, and organizes output package.
    Reports real-time agent telemetry to WORKHORSE active_task_tracker (Vanguard, Echo, Iris, Aura, Forge, Apex)."""
    video_path = pathlib.Path(video_path)
    logger.info(f"============================================================")
    logger.info(f"PROCESSING CAM SHOW PACKAGE: {video_path.name}")
    logger.info(f"============================================================")

    from pipeline.stages.ai_operator import active_task_tracker
    sz_gb = round(video_path.stat().st_size / (1024**3), 2)

    # 1. Vanguard: Video Intake Sentinel
    active_task_tracker.start_task(
        agent="vanguard",
        sub_agent="synapse",
        task_desc=f"Vanguard [23 V]: Ingesting {video_path.name} ({sz_gb} GB) for AI performance cutdown...",
        task_id="cam_show_active",
        progress=10
    )

    # 2. Determine date and output directory
    today_str = datetime.date.today().isoformat()
    clean_stem = video_path.stem.replace(" ", "_")
    package_name = f"{today_str}_{clean_stem}"
    package_dir = OUTPUT_DIR / package_name
    package_dir.mkdir(parents=True, exist_ok=True)
    thumbs_dir = package_dir / "thumbnails"

    # 3. Iris & Echo: Multi-Modal Analysis
    active_task_tracker.start_task(
        agent="iris",
        sub_agent="echo",
        task_desc=f"Iris [77 Ir] & Echo [83 Bi]: Scanning motion energy & Whisper speech density on GPU 1 ({video_path.name})...",
        task_id="cam_show_active",
        progress=35
    )

    from pipeline.stages.cam_show_cutter import process_cam_video
    cut_res = process_cam_video(
        video_path=video_path,
        sample_fps=1.0,
        motion_threshold=0.04,
        enable_audio_ai=True,
        create_resolve_timeline=True,
        output_dir=package_dir,
    )

    # Load cutlist
    cutlist_file = pathlib.Path(cut_res["json_cutlist"])
    cutlist_data = json.loads(cutlist_file.read_text(encoding="utf-8"))
    segments = cutlist_data.get("segments", [])

    # If stream is an empty room standby recording with no performer, exit cleanly
    if not segments:
        logger.warning(f"Standby Stream: No active show detected in {video_path.name} (empty room). Skipping false cuts and thumbnails.")
        dest_cutlist = package_dir / "cutlist.json"
        dest_edl = package_dir / "master.edl"
        if cutlist_file.resolve() != dest_cutlist.resolve():
            shutil.copy2(cutlist_file, dest_cutlist)
        if pathlib.Path(cut_res["edl_file"]).resolve() != dest_edl.resolve():
            shutil.copy2(pathlib.Path(cut_res["edl_file"]), dest_edl)

        manifest = {
            "show_title": clean_stem,
            "date_processed": today_str,
            "source_file": str(video_path),
            "package_directory": str(package_dir),
            "status": "EMPTY_ROOM_STANDBY",
            "message": "No performer detected in stream recording. Camera was streaming on an empty room/chair.",
            "original_duration_minutes": cut_res["original_minutes"],
            "cutdown_duration_minutes": 0.0,
            "clip_count": 0,
            "outputs": {
                "full_cutdown_video": None,
                "highlight_teaser_video": None,
                "thumbnails_directory": None,
                "thumbnail_count": 0,
                "cutlist_json": str(dest_cutlist.name),
                "cmx_edl": str(dest_edl.name),
            }
        }
        manifest_file = package_dir / "package_manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        active_task_tracker.finish_task("cam_show_active")
        return manifest

    # 4. Aura: DaVinci Resolve Studio Assembly
    active_task_tracker.start_task(
        agent="aura",
        sub_agent="iris",
        task_desc=f"Aura [79 Au]: DaVinci Resolve Studio timeline assembled with {len(segments)} show cuts...",
        task_id="cam_show_active",
        progress=60
    )

    # 5. Forge: Render full show cutdown video (MP4) via NVENC
    active_task_tracker.start_task(
        agent="forge",
        sub_agent="apex",
        task_desc=f"Forge [26 Fe]: Rendering full {cut_res['active_show_minutes']:.1f}m show cutdown MP4 via NVENC on GPU 1...",
        task_id="cam_show_active",
        progress=75
    )
    full_cutdown_file = package_dir / f"{clean_stem}_Full_Show_Cutdown.mp4"
    render_full_cutdown_video(video_path, segments, full_cutdown_file)

    # 6. Apex: Extract dynamic content-driven preview thumbnails
    active_task_tracker.start_task(
        agent="apex",
        sub_agent="aura",
        task_desc=f"Apex [78 Pt]: Extracting dynamic content-driven preview thumbnails from peak show highlights...",
        task_id="cam_show_active",
        progress=85
    )
    thumbs = extract_thumbnails(video_path, segments, thumbs_dir, cutdown_video_path=full_cutdown_file)

    # 7. Forge: Generate 30-second dynamic high-octane highlight teaser video (MP4)
    active_task_tracker.start_task(
        agent="forge",
        sub_agent="aura",
        task_desc=f"Forge [26 Fe]: Rendering 30s dynamic high-octane highlight teaser MP4 with transitions on GPU 1...",
        task_id="cam_show_active",
        progress=92
    )
    teaser_file = package_dir / f"{clean_stem}_Highlight_Teaser.mp4"
    generate_highlight_teaser(video_path, segments, teaser_file, target_duration=30.0, cutdown_video_path=full_cutdown_file)

    # 8. Copy cutlist & EDL into standard names in package directory
    edl_file = pathlib.Path(cut_res["edl_file"])
    dest_cutlist = package_dir / "cutlist.json"
    dest_edl = package_dir / "master.edl"
    if cutlist_file.resolve() != dest_cutlist.resolve():
        shutil.copy2(cutlist_file, dest_cutlist)
    if edl_file.resolve() != dest_edl.resolve():
        shutil.copy2(edl_file, dest_edl)

    # 9. Write Package Manifest
    manifest = {
        "show_title": clean_stem,
        "date_processed": today_str,
        "source_file": str(video_path),
        "package_directory": str(package_dir),
        "original_duration_minutes": cut_res["original_minutes"],
        "cutdown_duration_minutes": cut_res["active_show_minutes"],
        "clip_count": len(segments),
        "outputs": {
            "full_cutdown_video": str(full_cutdown_file.name) if full_cutdown_file.exists() else None,
            "highlight_teaser_video": str(teaser_file.name) if teaser_file.exists() else None,
            "thumbnails_directory": str(thumbs_dir.name),
            "thumbnail_count": len(thumbs),
            "cutlist_json": str(dest_cutlist.name),
            "cmx_edl": str(dest_edl.name),
            "davinci_resolve_timeline": cut_res.get("davinci_resolve", {}).get("timeline_name"),
        }
    }
    manifest_file = package_dir / "package_manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info(f"Package complete! Saved to {package_dir}")

    active_task_tracker.finish_task("cam_show_active")
    return manifest


def get_cam_show_queue_status() -> Dict[str, Any]:
    """Returns current inbox, processing, and completed package status for dashboard UI."""
    inbox_files = []
    for f in sorted(INBOX_DIR.glob("*.mp4")):
        inbox_files.append({"name": f.name, "size_gb": round(f.stat().st_size / (1024**3), 2)})

    proc_files = []
    for f in sorted(PROCESSING_DIR.glob("*.mp4")):
        proc_files.append({"name": f.name, "size_gb": round(f.stat().st_size / (1024**3), 2)})

    completed = []
    for d in sorted(OUTPUT_DIR.iterdir(), reverse=True):
        if d.is_dir():
            mf = d / "package_manifest.json"
            if mf.exists():
                try:
                    data = json.loads(mf.read_text(encoding="utf-8"))
                    completed.append({
                        "name": d.name,
                        "title": data.get("show_title", d.name),
                        "original_minutes": data.get("original_duration_minutes", 0),
                        "cutdown_minutes": data.get("cutdown_duration_minutes", 0),
                        "clip_count": data.get("clip_count", 0),
                    })
                except Exception:
                    completed.append({"name": d.name})

    return {
        "inbox_count": len(inbox_files),
        "inbox_files": inbox_files,
        "processing_file": proc_files[0] if proc_files else None,
        "completed_count": len(completed),
        "completed_packages": completed[:10],
    }


def watch_inbox_loop():
    """Continuously monitors INBOX_DIR for new video files and automatically packages them."""
    logger.info(f"Starting WORKHORSE Cam Show Watcher on {INBOX_DIR}...")
    logger.info("Drop any .mp4, .mkv, or .mov recording into inbox to process automatically.")

    seen_sizes = {}
    while True:
        try:
            for item in INBOX_DIR.iterdir():
                if item.suffix.lower() in [".mp4", ".mkv", ".mov"] and not item.name.startswith("."):
                    current_size = item.stat().st_size
                    # Check if file has finished writing (size stable for 10 seconds)
                    if item.name in seen_sizes and seen_sizes[item.name] == current_size:
                        logger.info(f"New video detected and verified stable: {item.name}")
                        # Move to processing
                        target_proc = PROCESSING_DIR / item.name
                        shutil.move(item, target_proc)
                        seen_sizes.pop(item.name, None)

                        # Package show
                        try:
                            package_cam_show(target_proc)
                            # Move raw file to archive upon success
                            dest_arch = ARCHIVE_DIR / item.name
                            shutil.move(target_proc, dest_arch)
                            logger.info(f"Moved raw video to archive: {dest_arch.name}")
                        except Exception as e:
                            logger.error(f"Error packaging {target_proc.name}: {e}")
                    else:
                        seen_sizes[item.name] = current_size
                        logger.info(f"Incoming file writing in progress: {item.name} ({round(current_size/(1024*1024), 1)} MB)...")

            time.sleep(5)
        except KeyboardInterrupt:
            logger.info("Watcher stopped by user.")
            break
        except Exception as e:
            logger.error(f"Watcher error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WORKHORSE Cam Show Content Packager & Watch Folder")
    parser.add_argument("video", nargs="?", help="Optional path to video file to process directly")
    parser.add_argument("--watch", action="store_true", help="Run in continuous watch folder mode")
    args = parser.parse_args()

    if args.watch or not args.video:
        watch_inbox_loop()
    else:
        package_cam_show(pathlib.Path(args.video))
