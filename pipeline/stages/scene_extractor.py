from shared.gpu1_arbiter import gpu1_arbiter
import os
import cv2
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable

def detect_ffmpeg_encoder() -> str:
    """Detect if NVENC hardware encoder is available."""
    try:
        res = subprocess.run(["nvidia-smi"], capture_output=True, timeout=2)
        if res.returncode == 0:
            return "h264_nvenc"
    except Exception:
        pass
    return "libx264"

def get_nvenc_flags() -> List[str]:
    """
    Selects GPU 1 for NVENC hardware encoding to isolate video processing
    from Synapse and Iris (running Ollama on GPU 0).
    """
    return ["-gpu", "1"]

def get_nvenc_quality_flags() -> List[str]:
    """High-quality constant-quality NVENC settings for cinematic-grade output (vs default low-bitrate NVENC)."""
    return ["-preset", "p7", "-tune", "hq", "-rc", "vbr", "-cq", "19", "-b:v", "0"]

def get_cpu_quality_flags() -> List[str]:
    """High-quality constant-rate-factor libx264 settings for cinematic-grade output."""
    return ["-preset", "slow", "-crf", "18"]

def get_video_info(video_path: Path) -> Dict[str, Any]:
    """Get video duration, resolution, fps using ffprobe and cv2."""
    duration = 0.0
    width = 0
    height = 0
    fps = 0.0

    try:
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration:stream=width,height,r_frame_rate",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=5)
        lines = result.stdout.strip().splitlines()
        for line in lines:
            line = line.strip()
            if "/" in line:
                num, den = line.split("/")
                fps = round(float(num) / float(den), 2) if float(den) > 0 else 30.0
            elif "." in line and duration == 0:
                duration = round(float(line), 2)
    except Exception:
        pass

    if duration == 0 or width == 0:
        cap = cv2.VideoCapture(str(video_path))
        if cap.isOpened():
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = float(cap.get(cv2.CAP_PROP_FPS)) or 30.0
            count = float(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = round(count / fps, 2) if fps > 0 else 0.0
            cap.release()

    return {
        "duration": duration,
        "width": width,
        "height": height,
        "fps": fps
    }

def extract_6_poses(video_path: Path, output_dir: Path, progress_cb: Optional[Callable[[str, int], None]] = None) -> List[Path]:
    """Extract 6 evenly spaced high-resolution pose screenshots."""
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_images = []

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames < 6:
        indices = list(range(max(1, total_frames)))
    else:
        # Avoid first 2% and last 2% to skip intro/outro black frames
        start_frame = int(total_frames * 0.03)
        end_frame = int(total_frames * 0.97)
        step = (end_frame - start_frame) / 5
        indices = [int(start_frame + i * step) for i in range(6)]

    for idx, f_idx in enumerate(indices):
        if progress_cb:
            progress_cb(f"Extracting pose screenshot {idx + 1}/6...", int(10 + (idx / 6) * 40))
        cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
        ret, frame = cap.read()
        if ret and frame is not None:
            img_path = output_dir / f"pose_{idx + 1}.jpg"
            cv2.imwrite(str(img_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            saved_images.append(img_path)

    cap.release()
    return saved_images

def cut_preview_video(video_path: Path, output_dir: Path, target_duration: int = 60, progress_cb: Optional[Callable[[str, int], None]] = None) -> Optional[Path]:
    """Cut a max 60s teaser preview using NVENC pinned to GPU 1."""
    output_dir.mkdir(parents=True, exist_ok=True)
    encoder = detect_ffmpeg_encoder()
    preview_file = output_dir / f"preview_60s_{video_path.name}"

    if progress_cb:
        progress_cb(f"Forge Agent: Cutting {target_duration}s teaser preview ({encoder} on GPU 1)...", 60)

    gpu_flags = get_nvenc_flags() if encoder == "h264_nvenc" else []
    quality_flags = get_nvenc_quality_flags() if encoder == "h264_nvenc" else get_cpu_quality_flags()
    cmd = [
        "ffmpeg", "-y",
        "-ss", "0",
        "-t", str(target_duration),
        "-i", str(video_path),
        "-c:v", encoder
    ] + gpu_flags + quality_flags + [
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        str(preview_file)
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, timeout=120)
        if res.returncode != 0 and encoder == "h264_nvenc":
            # Retry on GPU 0
            cmd_gpu0 = [
                "ffmpeg", "-y",
                "-ss", "0",
                "-t", str(target_duration),
                "-i", str(video_path),
                "-c:v", "h264_nvenc",
                "-gpu", "0"
            ] + get_nvenc_quality_flags() + [
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                str(preview_file)
            ]
            res2 = subprocess.run(cmd_gpu0, capture_output=True, timeout=120)
            if res2.returncode != 0:
                # Retry with CPU libx264
                cmd_cpu = [
                    "ffmpeg", "-y",
                    "-ss", "0",
                    "-t", str(target_duration),
                    "-i", str(video_path),
                    "-c:v", "libx264"
                ] + get_cpu_quality_flags() + [
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    str(preview_file)
                ]
                subprocess.run(cmd_cpu, capture_output=True, timeout=180)
    except Exception as e:
        print(f"Error cutting preview: {e}")

    return preview_file if preview_file.exists() else None

def generate_social_crops(preview_video: Path, output_dir: Path, progress_cb: Optional[Callable[[str, int], None]] = None) -> Dict[str, Path]:
    """Generate 9:16 vertical crop (TikTok/Reels/Shorts) and 1:1 square crop (Feed) pinned to GPU 1."""
    output_dir.mkdir(parents=True, exist_ok=True)
    encoder = detect_ffmpeg_encoder()
    crops = {}

    v_path = output_dir / f"vertical_9x16_{preview_video.name}"
    s_path = output_dir / f"square_1x1_{preview_video.name}"

    if progress_cb:
        progress_cb(f"Forge Agent: Generating 9:16 vertical social cut ({encoder} on GPU 1)...", 75)

    gpu_flags = get_nvenc_flags() if encoder == "h264_nvenc" else []
    quality_flags = get_nvenc_quality_flags() if encoder == "h264_nvenc" else get_cpu_quality_flags()

    # 9:16 crop filter (center crop), lanczos scaling for crisp cinematic resize
    cmd_vertical = [
        "ffmpeg", "-y",
        "-i", str(preview_video),
        "-vf", "crop=ih*(9/16):ih,scale=1080:1920:flags=lanczos",
        "-c:v", encoder
    ] + gpu_flags + quality_flags + [
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        str(v_path)
    ]
    try:
        res = subprocess.run(cmd_vertical, capture_output=True, timeout=120)
        if res.returncode != 0 and encoder == "h264_nvenc":
            # Fallback to CPU
            cmd_vertical_cpu = [
                "ffmpeg", "-y",
                "-i", str(preview_video),
                "-vf", "crop=ih*(9/16):ih,scale=1080:1920:flags=lanczos",
                "-c:v", "libx264"
            ] + get_cpu_quality_flags() + [
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                str(v_path)
            ]
            subprocess.run(cmd_vertical_cpu, capture_output=True, timeout=180)
        if v_path.exists():
            crops["vertical_9x16"] = v_path
    except Exception:
        pass

    if progress_cb:
        progress_cb(f"Forge Agent: Generating 1:1 square feed cut ({encoder} on GPU 1)...", 85)

    # 1:1 square crop, lanczos scaling for crisp cinematic resize
    cmd_square = [
        "ffmpeg", "-y",
        "-i", str(preview_video),
        "-vf", "crop=min(iw\\,ih):min(iw\\,ih),scale=1080:1080:flags=lanczos",
        "-c:v", encoder
    ] + gpu_flags + quality_flags + [
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        str(s_path)
    ]
    try:
        res = subprocess.run(cmd_square, capture_output=True, timeout=120)
        if res.returncode != 0 and encoder == "h264_nvenc":
            cmd_square_cpu = [
                "ffmpeg", "-y",
                "-i", str(preview_video),
                "-vf", "crop=min(iw\\,ih):min(iw\\,ih),scale=1080:1080:flags=lanczos",
                "-c:v", "libx264"
            ] + get_cpu_quality_flags() + [
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                str(s_path)
            ]
            subprocess.run(cmd_square_cpu, capture_output=True, timeout=180)
        if s_path.exists():
            crops["square_1x1"] = s_path
    except Exception:
        pass

    return crops

if __name__ == "__main__":
    print(f"Scene Extractor Stage initialized. NVENC encoder: {detect_ffmpeg_encoder()} (GPU flags: {get_nvenc_flags()}).")
