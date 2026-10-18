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


VIRAL_MODES: Dict[str, Dict[str, Any]] = {
    "handheld_camera": {
        "name": "Handheld Camera",
        "tagline": "Handheld camera motion with focus shifts. One photo becomes a heartfelt cinematic moment.",
        "shot_durations_sec": [1.8, 1.8, 1.8, 2.2, 3.0],
        "transition": "focus_whip",
        "klein_angle_prompts": [
            "Extreme macro close-up side-profile photograph of the subject's signature earring or accessory and hair strands from this exact photo, shallow depth of field, warm handheld lens bokeh, keep exact same subject details.",
            "Macro close-up photograph of the subject's necklace, collar, or handheld prop from this exact photo with soft natural lighting and shallow depth of field, keep exact same details.",
            "Atmospheric close-up detail shot of the background environment and lighting from this exact photo with creamy foreground bokeh.",
            "Three-quarter side-profile portrait of this exact person turning slightly toward the camera with a warm natural expression, keeping exact facial identity, hair, and outfit.",
        ],
    },
    "micro_cinema": {
        "name": "Micro Cinema",
        "tagline": "Dreamy close-ups turn a single image into a poetic cinematic video.",
        "shot_durations_sec": [2.2, 2.2, 2.2, 3.4],
        "transition": "dreamy_dissolve",
        "klein_angle_prompts": [
            "Dreamy poetic macro close-up of the jewelry or sunlit glass/prop detail from this exact photo casting soft golden reflections, shallow depth of field, keep exact same details.",
            "Dreamy macro close-up of the fabric texture, shoulder detail, or flowers/environment from this exact photo in warm golden rim light, shallow depth of field.",
            "Intimate close-up of the subject's hands, neckline, or profile silhouette from this exact photo bathed in warm poetic light, shallow depth of field.",
        ],
    },
    "fast_cut": {
        "name": "Fast Cut",
        "tagline": "Bold fast cuts and stylish pacing. Turn one photo into a modern, high-impact cinematic short.",
        "shot_durations_sec": [1.0, 0.9, 0.9, 1.0, 1.2, 2.4],
        "transition": "hard_flash_cut",
        "klein_angle_prompts": [
            "Bold low-angle close-up shot of the outfit styling and lower garment/strap detail from this exact photo, high-impact editorial fashion photography.",
            "Extreme macro close-up of the signature earring or eyewear from this exact photo catching bright studio specular highlights.",
            "Tight close-up of the top fabric texture and shoulder/neckline styling from this exact photo, razor-sharp fashion editorial.",
            "Dynamic side-profile close-up of this exact person's face and hair in motion, keeping exact identity, hair, and styling.",
        ],
    },
    "one_take_shot": {
        "name": "One-Take Shot",
        "tagline": "A seamless slow camera reveal. One photo becomes a smooth cinematic camera move.",
        "shot_durations_sec": [5.0],
        "transition": "none",
        "klein_angle_prompts": [
            "Extreme close-up foreground detail shot from this exact scene and subject, shallow depth of field, ready to pull back into the full portrait.",
        ],
    },
    "time_lapse": {
        "name": "Time Lapse",
        "tagline": "Time-lapse motion captures the passage of time. Watch still moments come alive.",
        "shot_durations_sec": [3.5, 3.5],
        "transition": "dreamy_dissolve",
        "klein_angle_prompts": [
            "Relight this exact scene and subject in warm golden-hour sunset lighting with glowing amber sky and long dramatic shadows, keeping the subject and composition identical.",
            "Relight this exact scene and subject at twilight night with glowing neon city/studio lights and deep atmospheric blue shadows, keeping the subject and composition identical.",
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
            out_path = output_dir / f"klein_angle_{idx+1:02d}.png"
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
        work_dir = work_dir or (Path(r"F:\WORKHORSE\workspace\shorts_out") / f"mode_{mode}")
        work_dir.mkdir(parents=True, exist_ok=True)
        output_mp4_path = output_mp4_path or (work_dir / f"{mode}_master_reel.mp4")

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

        # 3. Upscale & Color-Grade in DaVinci Resolve Studio 21.1+ via Super Scale + 3D LUT
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

        return {
            "success": True,
            "mode": mode,
            "mode_name": spec["name"],
            "tagline": spec["tagline"],
            "angle_plates": [str(p) for p in angle_plates],
            "raw_clips": [str(p) for p in clip_paths],
            "resolve_super_scale": resolve_res,
            "output_mp4": str(output_mp4_path),
        }

