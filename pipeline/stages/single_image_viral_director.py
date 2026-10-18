"""
WORKHORSE Single-Image Viral Video Director (`single_image_viral_director.py`)
===============================================================================
Replaces mobile apps like PowerDirector's Single-Image-to-Video templates with a
100% local, zero-credit-cost, studio-grade pipeline powered by:
  1. ComfyUI `4. One Image, Many Edits.json` (`flux-2-klein-9b-fp8.safetensors` + `ReferenceLatent`, 4 steps)
     Generates brand-new, razor-sharp multi-angle keyframes, macro close-ups, side-profiles,
     and time-of-day relighting from a SINGLE input photo while locking 100% subject/wardrobe/jewelry identity.
  2. ComfyUI `2. Minimax FastH3 - FirstFrame to Video.json` & `3. Minimax FastH3 - First and Last Frame.json`
     Animates each multi-angle plate (or interpolates a continuous 3D camera pullback) into real 3D motion.
  3. DaVinci Resolve Studio 21.1.1 (`DaVinciResolveBridge`)
     Applies 33x33x33 `.cube` 3D LUT color grading, focus-lock reticles, optical lens flares,
     and mode-specific editorial pacing.

Supported Viral Video Modes (matching & exceeding PowerDirector):
  - `handheld_camera`: "Handheld camera motion with focus shifts. One photo becomes a heartfelt cinematic moment."
  - `micro_cinema`:    "Dreamy close-ups turn a single image into a poetic cinematic video."
  - `fast_cut`:        "Bold fast cuts and stylish pacing. Turn one photo into a modern, high-impact cinematic short."
  - `one_take_shot`:   "A seamless slow camera reveal. One photo becomes a smooth cinematic camera move."
  - `time_lapse`:      "Time-lapse motion captures the passage of time. Watch still moments come alive."
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from pipeline.stages.comfyui_bridge import comfy_bridge
from pipeline.stages.davinci_resolve_bridge import DaVinciResolveBridge


# Where viral reels are written (also the "viral_video_director" gallery category in shared/output_categories.py).
SHORTS_OUT_ROOT = Path(r"F:\WORKHORSE\workspace\shorts_out")

# Appended to EVERY Klein edit prompt. Flux 2 Klein will happily invent whatever the prompt names: the old Micro Cinema
# prompt said "the jewelry or sunlit glass/prop detail" and a photo with neither produced gold rings and glassware
# (2026-10-18 live test). Prompts below therefore describe detail TYPES that exist in any photo, and this guard
# forbids adding anything that is not already in the reference.
KLEIN_REALITY_GUARD = (
    "Use ONLY what is visible in the reference photo: do not add any new object, jewelry, glassware, prop, person, "
    "text or location, and keep the subject's identity, outfit and setting exactly the same."
)

VIRAL_MODES: Dict[str, Dict[str, Any]] = {
    "handheld_camera": {
        "name": "Handheld Camera",
        "tagline": "Handheld camera motion with focus shifts. One photo becomes a heartfelt cinematic moment.",
        "shot_durations_sec": [1.8, 1.8, 1.8, 2.2, 3.0],
        "transition": "focus_whip",
        "klein_angle_prompts": [
            "Extreme macro close-up, shot handheld, of the most striking REAL detail already visible in this photo (for example a hand, an accessory, hair strands, ink or a fabric edge), shallow depth of field, warm handheld lens bokeh.",
            "Macro close-up of a different REAL detail visible in this photo (clothing texture, the neckline or collar edge, or an object the subject is holding), soft natural lighting, shallow depth of field.",
            "Atmospheric close-up of the actual background and lighting visible in this photo with creamy foreground bokeh.",
            "Three-quarter side-profile portrait of this exact person turning slightly toward the camera with a warm natural expression, keeping exact facial identity, hair, and outfit.",
        ],
    },
    "micro_cinema": {
        "name": "Micro Cinema",
        "tagline": "Dreamy close-ups turn a single image into a poetic cinematic video.",
        "shot_durations_sec": [2.2, 2.2, 2.2, 3.4],
        "transition": "dreamy_dissolve",
        "klein_angle_prompts": [
            "Dreamy, poetic macro close-up of the most striking REAL detail already visible in this photo (a hand, an accessory, hair, ink or a fabric edge), soft warm highlights, shallow depth of field.",
            "Dreamy macro close-up of a different REAL detail in this photo - its fabric texture, a shoulder, or the edge of the setting - in the photo's own light, shallow depth of field.",
            "Intimate close-up of this exact person's face or profile exactly as it appears in this photo, poetic soft light, shallow depth of field.",
        ],
    },
    "fast_cut": {
        "name": "Fast Cut",
        "tagline": "Bold fast cuts and stylish pacing. Turn one photo into a modern, high-impact cinematic short.",
        "shot_durations_sec": [1.0, 0.9, 0.9, 1.0, 1.2, 2.4],
        "transition": "hard_flash_cut",
        "klein_angle_prompts": [
            "Bold low-angle close-up of the outfit styling and a garment or strap detail exactly as visible in this photo, high-impact editorial fashion photography.",
            "Extreme macro close-up of an accessory, eyewear or jewelry that is ALREADY visible on the subject in this photo (if there is none, her eyes), catching bright studio specular highlights.",
            "Tight close-up of the top fabric texture and shoulder/neckline styling exactly as visible in this photo, razor-sharp fashion editorial.",
            "Dynamic side-profile close-up of this exact person's face and hair in motion, keeping exact identity, hair, and styling.",
        ],
    },
    "one_take_shot": {
        "name": "One-Take Shot",
        "tagline": "A seamless slow camera reveal. One photo becomes a smooth cinematic camera move.",
        "shot_durations_sec": [5.0],
        "transition": "none",
        "klein_angle_prompts": [
            "Extreme close-up foreground detail of a REAL element of this exact scene and subject, shallow depth of field, ready to pull back into the full portrait.",
        ],
    },
    "time_lapse": {
        "name": "Time Lapse",
        "tagline": "Time-lapse motion captures the passage of time. Watch still moments come alive.",
        "shot_durations_sec": [3.5, 3.5],
        "transition": "dreamy_dissolve",
        "klein_angle_prompts": [
            "Relight this exact scene and subject with warm golden-hour sunlight and long soft shadows, keeping the subject, setting and composition identical.",
            "Relight this exact scene and subject at dusk with deep blue shadows and soft warm practical lights, keeping the subject, setting and composition identical.",
        ],
    },
}


class SingleImageViralDirector:
    """
    Orchestrates ComfyUI Flux 2 Klein 9B (`4. One Image, Many Edits.json`) +
    ComfyUI MiniMax FastH3 (`2. FirstFrame to Video.json` & `3. First and Last Frame.json`) +
    DaVinci Resolve Studio (`DaVinciResolveBridge`) to turn 1 photo into any of the 5 viral video modes.
    """

    def __init__(self, comfy_host: str = "192.168.1.74") -> None:
        self.comfy = comfy_bridge
        self.comfy.host = comfy_host
        self.resolve = DaVinciResolveBridge()
        self.template_klein = Path(
            r"F:\WORKHORSE\pipeline\stages\workflow_templates\automation\3. Many Prompts in One Run\4. One Image, Many Edits.json"
        )

    def generate_klein_multi_angle_edits(
        self,
        source_image_path: Path,
        edit_prompts: List[str],
        output_dir: Path,
        seed_base: int = 9001,
    ) -> List[Path]:
        """
        Runs ComfyUI `4. One Image, Many Edits.json` (`flux-2-klein-9b-fp8.safetensors` + `ReferenceLatent`)
        to generate multiple new camera angles/close-ups from `source_image_path`.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        self.comfy.remote_purge_vram()
        time.sleep(1.5)

        up_name = self.comfy.upload_image_to_comfy(source_image_path)
        wf_base = json.loads(self.template_klein.read_text(encoding="utf-8"))

        generated_paths: List[Path] = []
        for idx, ptxt in enumerate(edit_prompts):
            # Guard every prompt, and key the cached plate to the EXACT prompt text: with an index-only name,
            # editing a mode's prompt would silently keep serving plates generated from the old wording.
            ptxt = f"{ptxt} {KLEIN_REALITY_GUARD}"
            prompt_key = hashlib.sha1(ptxt.encode("utf-8")).hexdigest()[:8]
            out_path = output_dir / f"klein_angle_{idx+1:02d}_{prompt_key}.png"
            if out_path.exists() and out_path.stat().st_size > 100_000:
                generated_paths.append(out_path)
                continue

            wf = json.loads(json.dumps(wf_base))
            wf["1"]["inputs"]["unet_name"] = "flux-2-klein-9b-fp8.safetensors"
            wf["2"]["inputs"]["clip_name"] = "qwen_3_8b_fp8mixed.safetensors"
            wf["3"]["inputs"]["vae_name"] = "flux2-vae.safetensors"
            wf["4"]["inputs"]["image"] = up_name
            st = json.loads(wf["4"]["inputs"]["LoadImageMiniState"])
            st["orig_name"] = up_name
            wf["4"]["inputs"]["LoadImageMiniState"] = json.dumps(st)
            wf["5"]["inputs"]["LongestSideState"] = json.dumps(
                {"size": 1024, "ratio": "keep", "step": 16, "anchor": "center", "allow_upscale": True, "resample": "auto"}
            )
            wf["8"]["inputs"]["text"] = ptxt
            if "6" in wf:
                del wf["6"]
            seed_val = seed_base + idx
            wf["7"]["inputs"]["seed"] = seed_val
            wf["7"]["inputs"]["SeedState"] = json.dumps({"runSeed": seed_val})
            wf["16"]["inputs"]["filename_prefix"] = f"ViralDirector/angle_{idx+1:02d}"

            q = self.comfy.queue_prompt(wf)
            pid = q.get("prompt_id")
            if not pid:
                print(f"[ViralDirector] Klein plate {idx+1} was rejected by ComfyUI: {q.get('node_errors') or q}")
                continue
            imgs = self.comfy.wait_for_execution(pid, timeout_seconds=120)
            if imgs:
                dl = self.comfy.download_image(
                    imgs[0]["filename"], imgs[0].get("subfolder", ""), imgs[0].get("type", "output")
                )
                shutil.copy2(dl, out_path)
                generated_paths.append(out_path)

        return generated_paths

    def render_viral_mode_video(
        self,
        source_image_path: Path,
        mode: str = "handheld_camera",
        output_mp4_path: Optional[Path] = None,
        work_dir: Optional[Path] = None,
        super_scale: int = 3,
        width: int = 1080,
        height: int = 1920,
    ) -> Dict[str, Any]:
        """
        End-to-end execution of any of the 5 Single-Image-to-Viral-Video modes:
          `handheld_camera`, `micro_cinema`, `fast_cut`, `one_take_shot`, `time_lapse`.
        Automatically upscales the 480x864 ComfyUI MiniMax FastH3 clips in DaVinci Resolve
        Studio 21.1+ using Neural Engine `Super Scale` (`super_scale=3` -> 3x) + Optical Flow + 3D LUT.
        """
        if mode not in VIRAL_MODES:
            raise ValueError(f"Unknown mode '{mode}'. Choose from: {list(VIRAL_MODES.keys())}")

        spec = VIRAL_MODES[mode]
        # The work folder used to be shared per MODE and Klein plates were cached by file name only
        # (klein_angle_01.png). Running micro_cinema on a SECOND photo therefore silently re-used the FIRST
        # photo's plates and produced a video of the previous subject - and a fixed output name meant a stale
        # reel from an earlier run could even mask a failed render. Everything is now keyed to the photo's bytes.
        source_image_path = Path(source_image_path)
        src_hash = hashlib.sha1(source_image_path.read_bytes()).hexdigest()[:10]
        run_id = time.strftime("%Y%m%d_%H%M%S")
        work_dir = work_dir or (SHORTS_OUT_ROOT / f"mode_{mode}" / f"{source_image_path.stem}_{src_hash}")
        work_dir.mkdir(parents=True, exist_ok=True)
        output_mp4_path = output_mp4_path or (work_dir / f"{mode}_master_reel_{run_id}.mp4")

        # 1. Generate multi-angle / relit keyframes from the single photo via Flux 2 Klein 9B
        angle_plates = self.generate_klein_multi_angle_edits(
            source_image_path=source_image_path,
            edit_prompts=spec["klein_angle_prompts"],
            output_dir=work_dir / "plates",
        )

        # 2. Animate via ComfyUI MiniMax FastH3
        self.comfy.remote_purge_vram()
        time.sleep(1.5)
        clip_paths: List[Path] = []

        if mode == "one_take_shot" and angle_plates:
            # Use `3. Minimax FastH3 - First and Last Frame.json` from Close-Up Plate -> Full Original Photo!
            res = self.comfy.generate_video_fasth3(
                first_frame_path=angle_plates[0],
                last_frame_path=source_image_path,
                prompt=(
                    "Seamless continuous one-take camera pullback reveal. Starting from the extreme close-up detail in "
                    "<Picture 1>, the camera smoothly dollies backward in one unbroken shot to reveal the full moving portrait "
                    "in <Picture 2> with natural 3D parallax, subtle head movement, and warm expression."
                ),
                duration_seconds=5,
                longest_side=864,
            )
            if res.get("success") and res.get("file_path"):
                clip_paths.append(Path(res["file_path"]))
        else:
            all_plates = angle_plates + [source_image_path]
            for idx, plate in enumerate(all_plates):
                res = self.comfy.generate_video_fasth3(
                    first_frame_path=plate,
                    prompt=(
                        "For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.\n\n"
                        "integrated_multimodal_description: [Shot 1] Cinematic shallow depth of field, natural 3D camera parallax and "
                        "lifelike subject motion, smooth subtle movement and realistic lighting glints."
                    ),
                    duration_seconds=5,
                    longest_side=864,
                    seed=9500 + idx,
                )
                if res.get("success") and res.get("file_path"):
                    clip_paths.append(Path(res["file_path"]))

        if not clip_paths:
            return {
                "success": False,
                "mode": mode,
                "mode_name": spec["name"],
                "error": "No animated clips were produced - every ComfyUI Klein/FastH3 render failed or timed out, so there is nothing to master.",
                "angle_plates": [str(p) for p in angle_plates],
                "raw_clips": [],
                "output_mp4": str(output_mp4_path),
            }

        # 3. Upscale & Color-Grade in DaVinci Resolve Studio 21.1+ via Super Scale + 3D LUT
        # Clips come out of FastH3 in the PHOTO's aspect (e.g. 4:5). Resolve letterboxes any clip whose aspect differs from the
        # 9:16 timeline (black bars in the 2026-10-18 live test), so center-crop them to the reel aspect first - at NATIVE
        # resolution, no pre-scaling, so Super Scale still upscales real source pixels.
        clip_paths = self._conform_clips_to_aspect(clip_paths, width, height, work_dir / "conformed")
        lut_path = self.resolve.generate_cinematic_cube_lut()
        resolve_res = self.resolve.assemble_and_grade_timeline_in_resolve(
            project_name=f"WH_Viral_{mode}_{int(time.time())}",
            clip_paths=clip_paths,
            output_mp4_path=output_mp4_path,
            width=width,
            height=height,
            fps=24,
            lut_path=lut_path,
            super_scale=super_scale,
        )

        warnings: List[str] = []
        mastering = "davinci_resolve_super_scale"
        # The Resolve bridge reports used_resolve=False (it does not raise) when Resolve isn't running or the
        # render never appeared. This method used to ignore that and claim success for a file that didn't exist.
        if not resolve_res.get("used_resolve") or not self._is_real_video(output_mp4_path):
            warnings.append(
                "DaVinci Resolve wasn't available (" + str(resolve_res.get("reason", "render did not appear")) +
                ") - mastered with ffmpeg instead (Lanczos upscale + 3D LUT, NVENC). Open DaVinci Resolve Studio "
                "for the Neural Engine Super Scale."
            )
            fb = self._ffmpeg_master(clip_paths, output_mp4_path, width, height, 24, lut_path)
            resolve_res = {**resolve_res, "fallback": fb}
            mastering = "ffmpeg_fallback"

        ok = self._is_real_video(output_mp4_path)
        result: Dict[str, Any] = {
            "success": ok,
            "mode": mode,
            "mode_name": spec["name"],
            "tagline": spec["tagline"],
            "mastering": mastering,
            "warnings": warnings,
            "angle_plates": [str(p) for p in angle_plates],
            "raw_clips": [str(p) for p in clip_paths],
            "resolve_super_scale": resolve_res,
            "output_mp4": str(output_mp4_path),
        }
        if not ok:
            result["error"] = "Mastering failed: neither DaVinci Resolve nor the ffmpeg fallback produced a playable video."
        return result

    @staticmethod
    def _conform_clips_to_aspect(clip_paths: List[Path], width: int, height: int, out_dir: Path) -> List[Path]:
        """Center-crop each clip to width:height at its NATIVE resolution (even dimensions, high quality).

        Returns the cropped clip paths; any clip that can't be probed/cropped is passed through unchanged so a
        problem here can never lose a render."""
        target = width / height
        out_dir.mkdir(parents=True, exist_ok=True)
        conformed: List[Path] = []
        for clip in clip_paths:
            clip = Path(clip)
            try:
                probe = subprocess.run(
                    ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(clip)],
                    capture_output=True, text=True, timeout=30,
                ).stdout.strip()
                w, h = (int(x) for x in probe.split(",")[:2])
                if abs((w / h) - target) < 0.01:
                    conformed.append(clip)
                    continue
                if (w / h) > target:      # too wide -> trim the sides
                    cw, ch = int(h * target) // 2 * 2, h // 2 * 2
                else:                     # too tall -> trim top/bottom
                    cw, ch = w // 2 * 2, int(w / target) // 2 * 2
                dest = out_dir / f"{clip.stem}_{cw}x{ch}.mp4"
                proc = subprocess.run(
                    ["ffmpeg", "-y", "-v", "error", "-i", str(clip), "-vf", f"crop={cw}:{ch}", "-c:v", "libx264", "-crf", "12",
                     "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "copy", str(dest)],
                    capture_output=True, text=True, timeout=300,
                )
                if proc.returncode == 0 and dest.exists() and dest.stat().st_size > 10_000:
                    conformed.append(dest)
                else:
                    conformed.append(clip)
            except Exception as e:  # noqa: BLE001
                print(f"[ViralDirector] Could not conform {clip.name} to {width}x{height} ({e}); using it as-is.")
                conformed.append(clip)
        return conformed

    @staticmethod
    def _is_real_video(path: Path) -> bool:
        try:
            return Path(path).exists() and Path(path).stat().st_size > 50_000
        except OSError:
            return False

    @staticmethod
    def _has_audio_stream(path: Path) -> bool:
        try:
            out = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path)],
                capture_output=True, text=True, timeout=30,
            )
            return "audio" in (out.stdout or "")
        except Exception:
            return False

    def _ffmpeg_master(
        self,
        clip_paths: List[Path],
        output_mp4_path: Path,
        width: int,
        height: int,
        fps: int,
        lut_path: Optional[Path],
    ) -> Dict[str, Any]:
        """Resolve-free mastering: normalise every clip to WxH (cover-crop, Lanczos), concat, apply the .cube LUT, NVENC encode."""
        clips = [Path(p) for p in clip_paths if Path(p).exists()]
        if not clips:
            return {"success": False, "reason": "no clips on disk"}
        n = len(clips)
        keep_audio = all(self._has_audio_stream(c) for c in clips)
        chains: List[str] = []
        for i in range(n):
            chains.append(
                f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos,"
                f"crop={width}:{height},fps={fps},setsar=1,format=yuv420p[v{i}]"
            )
            if keep_audio:
                chains.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo[a{i}]")
        concat_in = "".join(f"[v{i}]" + (f"[a{i}]" if keep_audio else "") for i in range(n))
        chains.append(f"{concat_in}concat=n={n}:v=1:a={1 if keep_audio else 0}[vcat]" + ("[acat]" if keep_audio else ""))
        final_v = "[vcat]"
        if lut_path and Path(lut_path).exists():
            lut_arg = str(Path(lut_path).resolve()).replace("\\", "/").replace(":", "\\:")
            chains.append(f"[vcat]lut3d=file='{lut_arg}'[vout]")
            final_v = "[vout]"

        def build(video_codec: List[str]) -> List[str]:
            cmd = ["ffmpeg", "-y", "-v", "error"]
            for c in clips:
                cmd += ["-i", str(c)]
            cmd += ["-filter_complex", ";".join(chains), "-map", final_v]
            if keep_audio:
                cmd += ["-map", "[acat]"]
            cmd += video_codec + ["-pix_fmt", "yuv420p"]
            if keep_audio:
                cmd += ["-c:a", "aac", "-b:a", "192k"]
            return cmd + [str(output_mp4_path)]

        attempts = [
            ("h264_nvenc", ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "19", "-b:v", "0"]),
            ("libx264", ["-c:v", "libx264", "-preset", "medium", "-crf", "18"]),
        ]
        last_err = ""
        for name, codec_args in attempts:
            try:
                proc = subprocess.run(build(codec_args), capture_output=True, text=True, timeout=900)
            except Exception as e:  # noqa: BLE001
                last_err = str(e)
                continue
            if proc.returncode == 0 and self._is_real_video(output_mp4_path):
                return {"success": True, "encoder": name, "audio": keep_audio, "clips": n,
                        "size_bytes": Path(output_mp4_path).stat().st_size}
            last_err = (proc.stderr or "")[-400:]
        return {"success": False, "reason": last_err or "ffmpeg failed"}


