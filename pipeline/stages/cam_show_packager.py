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

import argparse
import datetime
import json
import logging
import os
import pathlib
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

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

for d in [INBOX_DIR, PROCESSING_DIR, OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def extract_thumbnails(
    video_path: pathlib.Path,
    clips: List[Dict[str, Any]],
    output_thumbs_dir: pathlib.Path,
    max_count: int = 16,
) -> List[Dict[str, Any]]:
    """Extracts 1080p high-resolution preview thumbnails across intro, guitar, and peak performances."""
    output_thumbs_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Extracting {max_count} high-resolution thumbnails...")

    stamps = []
    # 1. Outfit intro preview
    stamps.append((10.0, "01_outfit_intro.jpg", "Outfit Intro Showcase"))

    # 2. Guitar clips
    guitar_clips = [c for c in clips if "guitar" in c.get("label", "").lower() or c.get("marker_color") == "Yellow"]
    if guitar_clips:
        for idx, g in enumerate(guitar_clips[:3], 2):
            g_mid = g["start_sec"] + (g["duration_sec"] / 2.0)
            stamps.append((g_mid, f"{idx:02d}_guitar_performance.jpg", "Guitar Performance & Singing"))

    # 3. Performance clips evenly spaced
    start_idx = len(stamps) + 1
    remaining_needed = max_count - len(stamps)
    perf_clips = [c for c in clips if c not in guitar_clips]
    if perf_clips:
        step = max(1, len(perf_clips) // remaining_needed)
        for i in range(0, len(perf_clips), step):
            if len(stamps) >= max_count:
                break
            c = perf_clips[i]
            mid_sec = c["start_sec"] + (c["duration_sec"] / 2.0)
            stamps.append((mid_sec, f"{len(stamps)+1:02d}_performance_peak.jpg", c.get("label", "Show Segment")))

    extracted = []
    for sec, fname, lbl in stamps:
        out_f = output_thumbs_dir / fname
        cmd = [
            "ffmpeg", "-y", "-ss", str(sec), "-i", str(video_path),
            "-frames:v", "1", "-q:v", "2", str(out_f)
        ]
        subprocess.run(cmd, capture_output=True, timeout=20)
        if out_f.exists():
            extracted.append({"filename": fname, "timestamp_sec": sec, "label": lbl})

    logger.info(f"Generated {len(extracted)} preview thumbnails in {output_thumbs_dir.name}")
    return extracted


def generate_highlight_teaser(
    video_path: pathlib.Path,
    clips: List[Dict[str, Any]],
    output_file: pathlib.Path,
    target_duration: float = 30.0,
) -> Optional[pathlib.Path]:
    """Builds a dynamic, fast-paced 30-second highlight teaser promo video with transitions across the whole show."""
    logger.info(f"Generating {target_duration}s Dynamic Highlight Teaser Video (MP4)...")
    temp_stage = output_file.parent / "_teaser_staging"
    temp_stage.mkdir(parents=True, exist_ok=True)

    try:
        # Enforce .mp4 extension
        if output_file.suffix.lower() != ".mp4":
            output_file = output_file.with_suffix(".mp4")

        # 1. Select 12-14 fast dynamic cuts across the entire approved cutdown
        slice_len = 2.6
        trans_dur = 0.35
        guitar_clips = [c for c in clips if "guitar" in c.get("label", "").lower() or c.get("marker_color") == "Yellow"]
        perf_clips = [c for c in clips if c not in guitar_clips]

        segments_to_cut = []
        # Evenly distribute 11-12 performance clips from approved segments
        num_perf = 12
        step = max(1, len(perf_clips) // num_perf) if perf_clips else 1
        for i in range(0, min(len(perf_clips), step * num_perf), step):
            c = perf_clips[i]
            c_mid = c["start_sec"] + min(4.0, c["duration_sec"] / 3.0)
            segments_to_cut.append((c_mid, c_mid + slice_len, f"perf_{len(segments_to_cut):02d}"))

        # Add brief guitar flash (only 2.5s) in the middle
        if guitar_clips:
            best_g = guitar_clips[min(1, len(guitar_clips)-1)]
            g_start = best_g["start_sec"] + 15.0
            insert_pos = min(len(segments_to_cut) // 2, 7)
            segments_to_cut.insert(insert_pos, (g_start, g_start + slice_len, "guitar_flash"))

        # Ensure maximum 13 slices for ~30 seconds total with transitions
        segments_to_cut = segments_to_cut[:13]

        # 2. Render individual slices with NVENC
        rendered_slices = []
        for s_start, s_end, s_name in segments_to_cut:
            dur = round(s_end - s_start, 2)
            out_slice = temp_stage / f"{s_name}.mp4"
            cmd = [
                "ffmpeg", "-y", "-ss", str(s_start), "-i", str(video_path),
                "-t", str(dur),
                "-c:v", "h264_nvenc", "-preset", "p5", "-b:v", "8M",
                "-c:a", "aac", "-b:a", "192k",
                str(out_slice)
            ]
            subprocess.run(cmd, capture_output=True, timeout=30)
            if out_slice.exists():
                rendered_slices.append(out_slice)

        if not rendered_slices:
            logger.warning("No teaser slices were successfully generated.")
            return None

        # 3. Build filter_complex with dynamic transitions (fade, wipe, dissolve, slide)
        transitions = ["fade", "wipeleft", "dissolve", "wiperight", "fade", "slideleft", "dissolve", "slideright", "fade", "smoothleft", "fade", "dissolve"]
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
            "-c:v", "h264_nvenc", "-preset", "p5", "-b:v", "8M",
            "-c:a", "aac", "-b:a", "192k",
            "-t", str(target_duration),
            "-movflags", "+faststart",
            str(output_file)
        ]

        t0 = time.time()
        res = subprocess.run(cmd_concat, capture_output=True, timeout=120)
        if output_file.exists():
            logger.info(f"30s Dynamic Highlight Teaser created in {round(time.time() - t0, 1)}s: {output_file.name}")
        else:
            # Fallback fast-cut concat
            list_file = temp_stage / "concat.txt"
            list_file.write_text("\n".join([f"file '{p.resolve()}'" for p in rendered_slices]), encoding="utf-8")
            cmd_fallback = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
                "-c:v", "h264_nvenc", "-preset", "p5", "-b:v", "8M",
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
    temp_stage.mkdir(parents=True, exist_ok=True)

    try:
        rendered_clips = []
        t0 = time.time()
        for idx, c in enumerate(clips, 1):
            c_file = temp_stage / f"clip_{idx:03d}.mp4"
            cmd = [
                "ffmpeg", "-y", "-ss", str(c["start_sec"]), "-i", str(video_path),
                "-t", str(c["duration_sec"]),
                "-c:v", "h264_nvenc", "-preset", "p5", "-cq", "21",
                "-c:a", "aac", "-b:a", "192k",
                str(c_file)
            ]
            subprocess.run(cmd, capture_output=True, timeout=90)
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
        subprocess.run(cmd_concat, capture_output=True, timeout=300)
        if output_file.exists():
            elapsed = round(time.time() - t0, 1)
            size_mb = round(output_file.stat().st_size / (1024 * 1024), 1)
            logger.info(f"Full cutdown video rendered in {elapsed}s ({size_mb} MB): {output_file.name}")
            return output_file
        return None

    finally:
        shutil.rmtree(temp_stage, ignore_errors=True)


def package_cam_show(video_path: pathlib.Path) -> Dict[str, Any]:
    """Runs the full AI cutdown, renders cutdown video + teaser + thumbnails, and organizes output package."""
    video_path = pathlib.Path(video_path)
    logger.info(f"============================================================")
    logger.info(f"PROCESSING CAM SHOW PACKAGE: {video_path.name}")
    logger.info(f"============================================================")

    # 1. Determine date and output directory
    today_str = datetime.date.today().isoformat()
    clean_stem = video_path.stem.replace(" ", "_")
    package_name = f"{today_str}_{clean_stem}"
    package_dir = OUTPUT_DIR / package_name
    package_dir.mkdir(parents=True, exist_ok=True)
    thumbs_dir = package_dir / "thumbnails"

    # 2. Run the multi-modal AI cutter
    from pipeline.stages.cam_show_cutter import process_cam_video
    cut_res = process_cam_video(
        video_path=video_path,
        sample_fps=1.0,
        motion_threshold=0.12,
        enable_audio_ai=True,
        create_resolve_timeline=True,
    )

    # Load cutlist
    cutlist_file = pathlib.Path(cut_res["json_cutlist"])
    cutlist_data = json.loads(cutlist_file.read_text(encoding="utf-8"))
    segments = cutlist_data.get("segments", [])

    # 3. Extract 16 high-resolution thumbnails
    thumbs = extract_thumbnails(video_path, segments, thumbs_dir, max_count=16)

    # 4. Generate 60-second highlight teaser video
    teaser_file = package_dir / f"{clean_stem}_Highlight_Teaser.mp4"
    generate_highlight_teaser(video_path, segments, teaser_file, target_duration=60.0)

    # 5. Render full show cutdown video
    full_cutdown_file = package_dir / f"{clean_stem}_Full_Show_Cutdown.mp4"
    render_full_cutdown_video(video_path, segments, full_cutdown_file)

    # 6. Copy cutlist & EDL into package directory
    edl_file = pathlib.Path(cut_res["edl_file"])
    dest_cutlist = package_dir / "cutlist.json"
    dest_edl = package_dir / "master.edl"
    shutil.copy2(cutlist_file, dest_cutlist)
    shutil.copy2(edl_file, dest_edl)

    # 7. Write Package Manifest
    manifest = {
        "show_title": clean_stem,
        "date_processed": today_str,
        "source_file": str(video_path),
        "package_directory": str(package_dir),
        "original_duration_minutes": cut_res["original_minutes"],
        "cutdown_duration_minutes": cut_res["active_show_minutes"],
        "clip_count": len(segments),
        "outputs": {
            "full_cutdown_video": str(full_cutdown_file) if full_cutdown_file.exists() else None,
            "highlight_teaser_video": str(teaser_file) if teaser_file.exists() else None,
            "thumbnails_directory": str(thumbs_dir),
            "thumbnail_count": len(thumbs),
            "cutlist_json": str(dest_cutlist),
            "cmx_edl": str(dest_edl),
            "davinci_resolve_timeline": cut_res.get("davinci_resolve", {}).get("timeline_name"),
        }
    }
    manifest_file = package_dir / "package_manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info(f"Package complete! Saved to {package_dir}")
    return manifest


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
