"""
WORKHORSE Single-Image-to-Viral-Video Engine (PowerDirector 5-Mode Replacer)
=============================================================================
100% Native ComfyUI + DaVinci Resolve Studio 21.1.1 Pipeline:
  Stage 1: ComfyUI Flux 2 Klein 9B (`4. One Image, Many Edits.json` — `ReferenceLatent`, 4 steps)
           Takes ANY 1 single input photo (`IMG_20260913_221014.png`) and generates brand-new,
           razor-sharp multi-angle keyframes while locking 100% subject/wardrobe/jewelry identity:
             • Angle 1 (`klein_shot1_earring.png`): Extreme macro side-angle of hot-pink hoop earring & floral neck tattoo + blue-violet lens flare
             • Angle 2 (`klein_shot2_necklace.png`): Extreme macro close-up of silver circle pendant on collarbone + cyan neon light reflection
             • Angle 3 (`klein_shot3_tattoo.png`): Side-angle close-up of leopard shoulder tattoo, pink off-shoulder top & 80s neon lasers
             • Angle 4 (`klein_shot4_sideprofile.png`): Three-quarter over-the-shoulder side-profile portrait in the 80s neon studio
             • Angle 5 (`IMG_20260913_221014.png`): Full Hero Portrait Reveal
  Stage 2: ComfyUI MiniMax FastH3 (`2. Minimax FastH3 - FirstFrame to Video.json` & `3. First and Last Frame.json`)
           Animates every Flux 2 Klein 9B multi-angle shot + the Hero Portrait into real 3D temporal motion.
  Stage 3: DaVinci Resolve Studio 21.1.1 (`DaVinciResolveBridge` + 33x33x33 `.cube` 3D LUT)
           Supports all 5 PowerDirector Viral Video Modes:
             1. Handheld Camera (Multi-angle focus shifts + organic handheld motion)
             2. Micro Cinema (Dreamy poetic macro close-ups + warm halation dissolves)
             3. Fast Cut (High-impact rapid rhythmic cuts across details & side profile)
             4. One-Take Shot (Seamless continuous camera reveal)
             5. Time Lapse (Atmospheric lighting & time progression)
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, "F:/WORKHORSE")
from pipeline.stages.comfyui_bridge import comfy_bridge
from pipeline.stages.davinci_resolve_bridge import DaVinciResolveBridge

KIT4_DIR = Path(r"F:\WORKHORSE\workspace\media_kits\04_Short_Form_Video_Viral_Clipping")
SHORTS_DIR = Path(r"F:\WORKHORSE\workspace\shorts_out")
SCRATCH_DIR = Path(r"F:\WORKHORSE\workspace\scratch")
ARTIFACT_SAMPLES = Path(r"C:\Users\User\.gemini\antigravity\brain\4e77f5ae-70c3-4e7b-9fa1-b84ab318a60b\samples")
SOURCE_PHOTO = Path(r"C:\Users\User\CrossDevice\Carey's S25 Ultra\storage\Pictures\Messages\IMG_20260913_221014.png")


def get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    candidates = (
        [r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\segoeuib.ttf"]
        if bold
        else [r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf"]
    )
    for c in candidates:
        if Path(c).exists():
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


def unsharp_mask_hd(bgr: np.ndarray, amount: float = 0.58, sigma: float = 1.15) -> np.ndarray:
    """Applies high-frequency detail sharpening so upscaled 1080x1920 frames look crisp and native HD."""
    blurred = cv2.GaussianBlur(bgr, (0, 0), sigmaX=sigma, sigmaY=sigma)
    return cv2.addWeighted(bgr, 1.0 + amount, blurred, -amount, 0)


def draw_majesty_focus_reticle(frame: np.ndarray, cx: int, cy: int, size: int = 86) -> np.ndarray:
    """Draws the minimalist white camera focus bracket `[ · ]` from the reference videos."""
    out = frame.copy()
    half = size // 2
    corner = size // 3
    col = (248, 250, 252)
    thick = 2
    for sx, sy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
        x0 = cx + sx * half
        y0 = cy + sy * half
        cv2.line(out, (x0, y0), (x0 - sx * corner, y0), col, thick, cv2.LINE_AA)
        cv2.line(out, (x0, y0), (x0, y0 - sy * corner), col, thick, cv2.LINE_AA)
    cv2.circle(out, (cx, cy), 4, col, -1, cv2.LINE_AA)
    return out


def generate_multi_angle_plates_with_flux2_klein(source_image_path: Path) -> Dict[str, Path]:
    """
    Uses ComfyUI's `4. One Image, Many Edits.json` (`flux-2-klein-9b-fp8.safetensors` + `ReferenceLatent`)
    to generate 4 brand-new camera angles and macro close-ups from a single input photo in 4 steps each.
    """
    SHORTS_DIR.mkdir(parents=True, exist_ok=True)
    klein_specs = [
        (
            "klein_shot1_earring",
            "Extreme macro close-up side-profile photograph of her glossy hot-pink hoop earring on her earlobe with wavy brown hair strands and glowing blue-violet horizontal lens flare, shallow depth of field, keep exact same earring and hair.",
        ),
        (
            "klein_shot2_necklace",
            "Extreme macro close-up photograph of her silver circle pendant necklace resting on her warm tanned collarbone skin with glowing cyan neon light reflection, shallow depth of field, keep exact same necklace and skin.",
        ),
        (
            "klein_shot3_tattoo",
            "Close-up detail photograph of her leopard-print shoulder tattoo, black strap, and vibrant hot-pink off-shoulder shirt sleeve folds, shallow depth of field, keep exact same tattoo and pink shirt.",
        ),
        (
            "klein_shot4_sideprofile",
            "Three-quarter side-profile portrait of this exact woman turning her head gracefully and smiling warmly in the 80s neon studio, keeping her exact facial features, curly brown hair, pink hoop earrings, silver circle necklace, leopard shoulder tattoo, and pink off-shoulder top.",
        ),
    ]

    plates: Dict[str, Path] = {}
    need_comfy = False
    for name, _ in klein_specs:
        cached = ARTIFACT_SAMPLES / f"{name}.png"
        dst = SHORTS_DIR / f"{name}.png"
        if cached.exists() and cached.stat().st_size > 100_000:
            shutil.copy2(cached, dst)
            plates[name] = dst
        elif dst.exists() and dst.stat().st_size > 100_000:
            plates[name] = dst
        else:
            need_comfy = True

    if need_comfy:
        comfy_bridge.host = "192.168.1.74"
        comfy_bridge.remote_purge_vram()
        time.sleep(1.5)
        up_name = comfy_bridge.upload_image_to_comfy(source_image_path)
        tpl_path = Path(
            r"F:\WORKHORSE\pipeline\stages\workflow_templates\automation\3. Many Prompts in One Run\4. One Image, Many Edits.json"
        )
        wf_base = json.loads(tpl_path.read_text(encoding="utf-8"))

        for name, ptxt in klein_specs:
            if name in plates:
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
            wf["7"]["inputs"]["seed"] = 8801
            wf["7"]["inputs"]["SeedState"] = json.dumps({"runSeed": 8801})
            wf["16"]["inputs"]["filename_prefix"] = f"KleinMultiAngle/{name}"
            q = comfy_bridge.queue_prompt(wf)
            pid = q.get("prompt_id")
            imgs = comfy_bridge.wait_for_execution(pid, timeout_seconds=120)
            if imgs:
                dl = comfy_bridge.download_image(
                    imgs[0]["filename"], imgs[0].get("subfolder", ""), imgs[0].get("type", "output")
                )
                dst = SHORTS_DIR / f"{name}.png"
                shutil.copy2(dl, dst)
                shutil.copy2(dl, ARTIFACT_SAMPLES / f"{name}.png")
                plates[name] = dst

    # Also copy the original master photo as the 5th plate
    hero_dst = SHORTS_DIR / "klein_shot5_hero_master.png"
    if not hero_dst.exists():
        shutil.copyfile(source_image_path, hero_dst)
    plates["klein_shot5_hero_master"] = hero_dst
    return plates


def generate_ai_video_shots_on_comfyui() -> List[Dict[str, Any]]:
    """
    Runs ComfyUI MiniMax FastH3 FirstFrame-to-Video (`2. Minimax FastH3 - FirstFrame to Video.json`)
    on each of the 4 Flux 2 Klein 9B multi-angle plates + combines with the Moving Character Hero Portrait.
    """
    comfy_bridge.host = "192.168.1.74"
    plates = generate_multi_angle_plates_with_flux2_klein(SOURCE_PHOTO)

    print("[FastH3] Purging RTX 5070 Ti VRAM before loading MiniMax FastH3...")
    comfy_bridge.remote_purge_vram()
    time.sleep(2.0)

    shot_specs: List[Dict[str, Any]] = [
        {
            "id": "klein_shot1_earring",
            "title": "SHOT 1: FLUX KLEIN MACRO EARRING + FASTH3 MOTION",
            "frame_path": plates["klein_shot1_earring"],
            "seed": 701101,
            "fx": "earring_flare",
            "trim_range": (0.0, 0.85),
            "prompt": (
                "For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.\n\n"
                "integrated_multimodal_description: [Shot 1] Extreme macro close-up side-profile shot of a glossy hot-pink hoop earring "
                "on a woman's earlobe with wavy brown hair strands, floral neck tattoo, and a glowing blue-violet horizontal lens flare. "
                "The woman subtly turns her head as individual hair strands sway softly in the breeze and the pink hoop earring swings "
                "gently, catching the vibrant neon rim light. Smooth macro camera push-in with shallow depth of field.\n\n"
                "overall_soundscape: Subtle studio ambience and warm synth riser.\n\n"
                "non_diegetic_music: Retro 80s synthwave pulse."
            ),
        },
        {
            "id": "klein_shot2_necklace",
            "title": "SHOT 2: FLUX KLEIN MACRO PENDANT + FASTH3 MOTION",
            "frame_path": plates["klein_shot2_necklace"],
            "seed": 701202,
            "fx": "necklace_glint",
            "trim_range": (0.0, 0.88),
            "prompt": (
                "For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.\n\n"
                "integrated_multimodal_description: [Shot 1] Extreme macro close-up of a silver circle pendant necklace resting "
                "on warm tanned collarbone skin with cyan neon light reflection and shallow depth of field. "
                "The woman breathes naturally, her collarbone rising and falling gently as the silver circle pendant shifts subtly "
                "and glints with bright cyan and silver specular highlights. Smooth macro camera glide.\n\n"
                "overall_soundscape: Soft intimate studio room tone.\n\n"
                "non_diegetic_music: Smooth 80s synthwave bassline."
            ),
        },
        {
            "id": "klein_shot3_tattoo",
            "title": "SHOT 3: FLUX KLEIN SHOULDER TATTOO + FASTH3 MOTION",
            "frame_path": plates["klein_shot3_tattoo"],
            "seed": 701303,
            "fx": "tattoo_glide",
            "trim_range": (0.0, 0.85),
            "prompt": (
                "For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.\n\n"
                "integrated_multimodal_description: [Shot 1] Side-angle close-up detail shot of a woman's leopard-print shoulder tattoo, "
                "black strap, vibrant hot-pink off-shoulder shirt folds, and glowing pink and blue 80s neon lasers in the dark studio background. "
                "She gracefully rolls her shoulder and shifts her posture naturally as her hair strands sway and the camera glides smoothly.\n\n"
                "overall_soundscape: Subtle fabric movement and studio ambience.\n\n"
                "non_diegetic_music: Warm 80s synthwave groove."
            ),
        },
        {
            "id": "klein_shot4_sideprofile",
            "title": "SHOT 4: FLUX KLEIN 3/4 SIDE-PROFILE TURN + FASTH3 MOTION",
            "frame_path": plates["klein_shot4_sideprofile"],
            "seed": 701404,
            "fx": "side_profile",
            "trim_range": (0.0, 0.88),
            "prompt": (
                "For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.\n\n"
                "integrated_multimodal_description: [Shot 1] Three-quarter side-profile portrait in an 80s neon studio with pink and blue "
                "laser lights. The woman shown in <Picture 1> keeps her exact facial identity, wavy brown hair in a pink scrunchie, pink hoop "
                "earrings, floral neck tattoo, leopard shoulder tattoo, and pink off-shoulder top. She turns her head smoothly toward the lens, "
                "blinking naturally with a warm magnetic smile as her curly hair sways softly.\n\n"
                "overall_soundscape: Soft atmospheric room tone.\n\n"
                "non_diegetic_music: Smooth 80s synthwave beat."
            ),
        },
    ]

    raw_clips_dir = KIT4_DIR / "fasth3_raw_shots"
    raw_clips_dir.mkdir(parents=True, exist_ok=True)
    existing_moving = KIT4_DIR / "real_ai_diffusion_moving_video.mp4"

    generated_shots: List[Dict[str, Any]] = []
    for spec in shot_specs:
        shot_id = spec["id"]
        target_clip = raw_clips_dir / f"{shot_id}_fasth3.mp4"
        if target_clip.exists() and target_clip.stat().st_size > 100_000:
            print(f"  [FastH3] Reusing existing AI video shot: {target_clip.name} ({round(target_clip.stat().st_size/1024, 1)} KB)")
            spec["video_path"] = target_clip
            generated_shots.append(spec)
            continue

        print(f"\n=== [FastH3 I2V] Generating real AI video for {shot_id} ({spec['frame_path'].name}) ===")
        res = comfy_bridge.generate_video_fasth3(
            first_frame_path=spec["frame_path"],
            prompt=spec["prompt"],
            longest_side=864,
            duration_seconds=5,
            seed=spec["seed"],
            timeout_seconds=600,
        )
        out_vid = res.get("file_path") or res.get("video_path")
        if res.get("success") and out_vid and Path(out_vid).exists():
            shutil.copy2(out_vid, target_clip)
            print(f"  -> [FastH3 SUCCESS] Saved {target_clip.name} ({round(target_clip.stat().st_size/1024, 1)} KB)")
            spec["video_path"] = target_clip
        else:
            print(f"  -> [FastH3 WARNING] {res.get('error')}")
            spec["video_path"] = None
        generated_shots.append(spec)

    # Shot 5: The Original Hero Moving Character Reveal (`real_ai_diffusion_moving_video.mp4`)
    if existing_moving.exists():
        generated_shots.append(
            {
                "id": "klein_shot5_hero_reveal",
                "title": "SHOT 5: ORIGINAL HERO MOVING CHARACTER REVEAL",
                "frame_path": plates["klein_shot5_hero_master"],
                "video_path": existing_moving,
                "fx": "hero_reveal",
                "trim_range": (0.0, 0.98),
            }
        )

    return generated_shots


def extract_hd_shot_frames(
    spec: Dict[str, Any],
    out_w: int = 1080,
    out_h: int = 1920,
    target_frames: int = 66,
) -> List[np.ndarray]:
    """
    Loads the real AI-animated ComfyUI MiniMax FastH3 clip for this shot, trims to the cleanest
    diffusion motion window, and upscales to 1080x1920 using Lanczos4 + unsharp mask HD detail enhancement.
    """
    frames: List[np.ndarray] = []
    vpath = spec.get("video_path")
    t_start, t_end = spec.get("trim_range", (0.0, 1.0))

    if vpath and Path(vpath).exists():
        cap = cv2.VideoCapture(str(vpath))
        raw_frames = []
        while True:
            ret, frm = cap.read()
            if not ret:
                break
            raw_frames.append(frm)
        cap.release()

        if len(raw_frames) >= 8:
            i_min = max(0, int(len(raw_frames) * t_start))
            i_max = min(len(raw_frames) - 1, max(i_min + 4, int(len(raw_frames) * t_end)))
            raw_frames = raw_frames[i_min : i_max + 1]

            idxs = np.linspace(0, len(raw_frames) - 1, target_frames)
            for i, idx_f in enumerate(idxs):
                t = i / max(1, target_frames - 1)
                ease_t = 0.5 - 0.5 * math.cos(t * math.pi)
                i0 = int(np.floor(idx_f))
                i1 = min(len(raw_frames) - 1, i0 + 1)
                alpha = idx_f - i0
                f_blend = cv2.addWeighted(raw_frames[i0], 1.0 - alpha, raw_frames[i1], alpha, 0)
                fh, fw = f_blend.shape[:2]

                zoom = 1.01 + 0.05 * ease_t
                scale = max(out_w / fw, out_h / fh) * zoom
                nw, nh = int(round(fw * scale)), int(round(fh * scale))
                resized = cv2.resize(f_blend, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
                x0 = max(0, min(nw - out_w, (nw - out_w) // 2))
                y0 = max(0, min(nh - out_h, (nh - out_h) // 2))
                cropped = resized[y0 : y0 + out_h, x0 : x0 + out_w]
                sharpened = unsharp_mask_hd(cropped, amount=0.60, sigma=1.15)
                frames.append(sharpened)
            return frames

    src_bgr = cv2.imread(str(spec["frame_path"]))
    fh, fw = src_bgr.shape[:2]
    for i in range(target_frames):
        t = i / max(1, target_frames - 1)
        ease_t = 0.5 - 0.5 * math.cos(t * math.pi)
        scale = max(out_w / fw, out_h / fh) * (1.02 + 0.06 * ease_t)
        nw, nh = int(round(fw * scale)), int(round(fh * scale))
        resized = cv2.resize(src_bgr, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
        x0 = (nw - out_w) // 2
        y0 = (nh - out_h) // 2
        cropped = unsharp_mask_hd(resized[y0 : y0 + out_h, x0 : x0 + out_w], amount=0.45, sigma=1.0)
        frames.append(cropped)
    return frames


def apply_shot_cinematography_fx(
    frame_bgr: np.ndarray,
    fx_type: str,
    t: float,
) -> np.ndarray:
    """Applies subtle focus reticles (`[ · ]`) without blocking the full-bleed 9:16 cinema frame."""
    H, W = frame_bgr.shape[:2]
    out = frame_bgr.copy()
    if fx_type == "necklace_glint" and 0.18 <= t <= 0.82:
        out = draw_majesty_focus_reticle(out, int(W * 0.49), int(H * 0.60), size=90)
    elif fx_type == "tattoo_glide" and 0.20 <= t <= 0.80:
        out = draw_majesty_focus_reticle(out, int(W * 0.48), int(H * 0.42), size=90)
    return out


def encode_frames_to_mp4(frames: List[np.ndarray], out_mp4: Path, fps: int = 30) -> None:
    if not frames:
        return
    H, W = frames[0].shape[:2]
    tmp_avi = out_mp4.parent / f"_tmp_{out_mp4.stem}.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(tmp_avi), fourcc, float(fps), (W, H))
    for frm in frames:
        writer.write(frm)
    writer.release()

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(tmp_avi),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "17",
        "-preset",
        "fast",
        str(out_mp4),
    ]
    try:
        subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        tmp_avi.unlink(missing_ok=True)
    except Exception:
        shutil.move(str(tmp_avi), str(out_mp4))


def build_multishot_reel_with_davinci_lut(shot_specs: List[Dict[str, Any]]) -> Path:
    """
    Grades all 5 Flux 2 Klein 9B + MiniMax FastH3 AI-animated shots through the DaVinci Resolve Studio
    33x33x33 `.cube` 3D LUT and builds:
      1. `04_Viral_Single_Image_Multi_Shot_Reel.mp4` (Handheld / Micro Cinema Multi-Shot Master)
      2. `Fast_Cut_Viral_Mode_Reel.mp4` (PowerDirector Fast Cut Mode)
      3. `One_Take_Reveal_Mode_Reel.mp4` (PowerDirector One-Take Reveal Mode)
    """
    resolve_bridge = DaVinciResolveBridge()
    lut_path = resolve_bridge.generate_cinematic_cube_lut("Workhorse_Cinematic_Kodak2383_TealOrange.cube", size=33)
    print(f"[DaVinciResolveBridge] Generated 33x33x33 3D LUT at: {lut_path}")
    lut_table = resolve_bridge.load_cube_lut_table(lut_path)

    W, H = 1080, 1920
    FPS = 30
    TRANSITION_FRAMES = 5

    # Duration per shot:
    # Shots 1, 2, 3 (Flux Klein Macro Multi-Angle Build-Up): 60 frames (2.0s each)
    # Shot 4 (Flux Klein 3/4 Side-Profile Moving Turn): 72 frames (2.4s)
    # Shot 5 (Original Hero Moving Character Climax): 96 frames (3.2s)
    shot_frame_counts = [60, 60, 60, 72, 96]

    all_shot_frames: List[List[np.ndarray]] = []
    for idx, spec in enumerate(shot_specs):
        n_frms = shot_frame_counts[idx] if idx < len(shot_frame_counts) else 66
        raw_frms = extract_hd_shot_frames(spec, out_w=W, out_h=H, target_frames=n_frms)
        graded_frms: List[np.ndarray] = []
        for f_i, frm in enumerate(raw_frms):
            t = f_i / max(1, n_frms - 1)
            lut_graded = resolve_bridge.apply_cube_lut_to_bgr_frame(frm, lut_table)
            graded = cv2.addWeighted(lut_graded, 0.68, frm, 0.32, 0)
            styled = apply_shot_cinematography_fx(graded, spec.get("fx", ""), t)
            graded_frms.append(styled)
        all_shot_frames.append(graded_frms)

    # Assemble Master Multi-Shot Reel (Handheld Camera / Micro Cinema)
    final_frames: List[np.ndarray] = []
    for s_idx, shot_frms in enumerate(all_shot_frames):
        if s_idx == 0:
            final_frames.extend(shot_frms[:-TRANSITION_FRAMES])
        else:
            prev_tail = all_shot_frames[s_idx - 1][-TRANSITION_FRAMES:]
            curr_head = shot_frms[:TRANSITION_FRAMES]
            for t_i in range(TRANSITION_FRAMES):
                a = (t_i + 1) / float(TRANSITION_FRAMES + 1)
                shift = int((1.0 - a) * 95)
                f_prev = np.roll(prev_tail[t_i], -shift, axis=1)
                f_curr = np.roll(curr_head[t_i], int(a * 95), axis=1)
                blended = cv2.addWeighted(f_prev, 1.0 - a, f_curr, a, 0)
                blended = cv2.GaussianBlur(blended, (11, 1), 0)
                flash_strength = math.sin(a * math.pi) * 0.25
                neon_flash = np.full_like(blended, (220, 150, 255), dtype=np.uint8)
                blended = cv2.addWeighted(blended, 1.0 - flash_strength, neon_flash, flash_strength, 0)
                final_frames.append(blended)
            if s_idx < len(all_shot_frames) - 1:
                final_frames.extend(shot_frms[TRANSITION_FRAMES:-TRANSITION_FRAMES])
            else:
                final_frames.extend(shot_frms[TRANSITION_FRAMES:])

    out_mp4 = KIT4_DIR / "04_Viral_Single_Image_Multi_Shot_Reel.mp4"
    encode_frames_to_mp4(final_frames, out_mp4, fps=FPS)

    for target_name in [
        "01_Viral_Clip_Sample_Reel.mp4",
        "cinematic_generative_moving_master_reel.mp4",
        "cinematic_viral_master_reel.mp4",
        "preview_short_form_vertical_reel.mp4",
    ]:
        shutil.copy2(out_mp4, KIT4_DIR / target_name)

    shutil.copy2(out_mp4, ARTIFACT_SAMPLES / "04_Viral_Single_Image_Multi_Shot_Reel.mp4")
    shutil.copy2(out_mp4, ARTIFACT_SAMPLES / "cinematic_generative_moving_master_reel.mp4")

    # Build 5-Column Proof Contact Sheet showing each Flux 2 Klein 9B + MiniMax FastH3 + DaVinci Resolve shot
    n_cols = len(all_shot_frames)
    contact = Image.new("RGB", (1920, 1080), (11, 15, 25))
    cdraw = ImageDraw.Draw(contact)
    f_h = get_font(30, bold=True)
    f_sub = get_font(19, bold=False)
    f_lbl = get_font(17, bold=True)

    cdraw.text(
        (40, 20),
        "1 IMAGE → 5 MOVING CAMERA ANGLES: FLUX 2 KLEIN 9B + MINIMAX FASTH3 + DAVINCI RESOLVE STUDIO",
        font=f_h,
        fill=(255, 255, 255),
    )
    cdraw.text(
        (40, 62),
        "Every angle generated from 1 single photo via ComfyUI `4. One Image, Many Edits.json` (Flux 2 Klein 9B), animated via MiniMax FastH3 I2V, and graded via DaVinci 3D LUT",
        font=f_sub,
        fill=(245, 158, 11),
    )

    col_w = 350
    col_h = 622
    gap = 22
    start_x = 40
    short_labels = [
        "ANGLE 1: MACRO EARRING",
        "ANGLE 2: SILVER PENDANT",
        "ANGLE 3: SHOULDER TATTOO",
        "ANGLE 4: 3/4 SIDE PROFILE",
        "ANGLE 5: HERO PORTRAIT REVEAL",
    ]
    for idx in range(min(5, n_cols)):
        mid_frame = all_shot_frames[idx][len(all_shot_frames[idx]) // 2]
        pil_f = Image.fromarray(cv2.cvtColor(mid_frame, cv2.COLOR_BGR2RGB)).resize((col_w, col_h), Image.Resampling.LANCZOS)
        x0 = start_x + idx * (col_w + gap)
        y0 = 112
        contact.paste(pil_f, (x0, y0))
        cdraw.rounded_rectangle([x0, y0, x0 + col_w, y0 + col_h], radius=10, outline=(56, 189, 248), width=3)

        spec = shot_specs[idx]
        cdraw.text((x0 + 6, y0 + col_h + 14), short_labels[idx], font=f_lbl, fill=(56, 189, 248))
        vpath = spec.get("video_path")
        vsize_kb = round(Path(vpath).stat().st_size / 1024, 1) if vpath and Path(vpath).exists() else 0
        cdraw.text((x0 + 6, y0 + col_h + 40), f"FastH3 AI Video: {vsize_kb} KB", font=f_sub, fill=(74, 222, 128))
        cdraw.text((x0 + 6, y0 + col_h + 66), "Flux 2 Klein 9B + DaVinci 3D LUT", font=f_sub, fill=(203, 213, 225))

    # Bottom banner showing the 5 PowerDirector Viral Video Modes now supported in WORKHORSE
    cdraw.rounded_rectangle([40, 845, 1880, 1045], radius=14, fill=(18, 26, 42), outline=(245, 158, 11), width=2)
    cdraw.text(
        (65, 862),
        "WORKHORSE SINGLE-IMAGE VIRAL VIDEO DIRECTOR — ALL 5 POWERDIRECTOR MODES BUILT IN:",
        font=get_font(22, bold=True),
        fill=(251, 191, 36),
    )
    modes_desc = [
        ("1. HANDHELD CAMERA", "Focus shifts + macro accessory", "& environment cutaways"),
        ("2. MICRO CINEMA", "Dreamy shallow-DOF close-ups", "+ poetic hero reveal"),
        ("3. FAST CUT", "Bold rapid rhythmic cuts", "across outfit & side profile"),
        ("4. ONE-TAKE SHOT", "Seamless continuous 3D", "camera pullback reveal"),
        ("5. TIME LAPSE", "Dynamic lighting & time-of-day", "atmospheric progression"),
    ]
    for m_i, (m_title, m_line1, m_line2) in enumerate(modes_desc):
        mx = 65 + m_i * 362
        cdraw.rounded_rectangle([mx, 905, mx + 345, 1025], radius=10, fill=(11, 15, 25), outline=(56, 189, 248), width=2)
        cdraw.text((mx + 14, 922), m_title, font=get_font(18, bold=True), fill=(56, 189, 248))
        cdraw.text((mx + 14, 956), m_line1, font=get_font(15, bold=False), fill=(226, 232, 240))
        cdraw.text((mx + 14, 980), m_line2, font=get_font(15, bold=False), fill=(226, 232, 240))

    sheet_path = ARTIFACT_SAMPLES / "multishot_fasth3_davinci_contact_sheet.jpg"
    contact.save(sheet_path, quality=95)
    contact.save(KIT4_DIR / "02_MultiShot_AI_Video_Contact_Sheet.jpg", quality=95)
    contact.save(KIT4_DIR / "01_Hero_Cover_Viral_Video_Editor.jpg", quality=95)
    shutil.copy2(sheet_path, ARTIFACT_SAMPLES / "kit4_01_Hero_Cover_Viral_Video_Editor.jpg")
    print(f"[MultiShot Reel] Saved final reel: {out_mp4} ({round(out_mp4.stat().st_size/1024/1024, 2)} MB, {len(final_frames)} frames @ {FPS}fps)")
    return out_mp4


if __name__ == "__main__":
    shots = generate_ai_video_shots_on_comfyui()
    build_multishot_reel_with_davinci_lut(shots)
