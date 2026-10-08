"""
WORKHORSE AUTONOMOUS AI MODEL CONTENT ENGINE (PIPE 3)
Chains four already-named WORKHORSE agents into one scheduled, hands-off content
drop - no new bot persona is needed, every step already has an owner:
  Cipher  [Market Scout]  -> trend_researcher.py   : supplies today's trend theme
  (RTX 5070 Ti)           -> comfyui_bridge.py      : renders base image + animates it
  Forge   [Video Cuts]    -> scene_extractor.py     : teaser cut + 9:16/1:1 social crops
  Scribe  [Copywriter]    -> copy_synthesizer.py     : multi-platform caption/copy kit
NOTE: the user's roadmap diagram said "Aura Writes Copy", but in this codebase Aura
owns photo retouching/color-grading (PhotoRetoucher) - copywriting is Scribe's job
(CopySynthesizer.generate_release_kit), so that's the function wired in here.
Output is staged to disk for human review before posting anywhere - this engine does
NOT auto-publish to any platform (see Pipe 4 risk discussion).
"""
import json
import random
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

sys.path.insert(0, "F:/WORKHORSE")
from pipeline.stages.trend_researcher import trend_researcher
from pipeline.stages.copy_synthesizer import CopySynthesizer
from pipeline.stages import scene_extractor

OUTPUT_ROOT = Path("F:/WORKHORSE/workspace/output/content_engine")
STATE_FILE = Path("F:/WORKHORSE/workspace/content_engine_state.json")

# On-brand aesthetic presets (same vibe as Herald's BRAND_VIBES) blended with
# whatever Cipher's daily radar sweep most recently surfaced as trending.
BRAND_AESTHETIC_POOL = [
    "boudoir mood, provocative pose, studio lighting, lingerie attire, luxury glamour",
    "luxury velvet boudoir, warm candlelit glow, silk drapery, confident alluring gaze",
    "golden hour glamour, sun-kissed glowing skin, intimate close framing, editorial"
]

NEGATIVE_PROMPT = (
    "extra limbs, deformed hands, mutated fingers, bad anatomy, blurry, low quality, "
    "watermark, text, cartoon, illustration"
)


class ContentEngine:
    def __init__(self):
        self.copy_synth = CopySynthesizer()

    def _build_prompt_from_trends(self) -> str:
        """Cipher's hand-off: blend today's already-synthesized trend theme (if the
        morning radar sweep has run) with a brand-safe aesthetic preset."""
        vault = trend_researcher.load_vault()
        themes = vault.get("daily_synthesis", {}).get("top_themes_today", [])
        theme_hint = random.choice(themes) if themes else "high-end creator monetization content"
        aesthetic = random.choice(BRAND_AESTHETIC_POOL)
        return (
            f"Photorealistic portrait, {aesthetic}, inspired by today's trend theme: "
            f"'{theme_hint}', 85mm lens, shallow depth of field, high-end editorial glamour, "
            f"photorealistic"
        )

    def run_autonomous_cycle(self) -> Dict[str, Any]:
        """Runs one full hands-off content drop. On failure, returns a 'stage' field
        naming exactly where it stopped so the watchdog/incident log is specific."""
        from pipeline.stages.comfyui_bridge import comfy_bridge

        cycle_dir = OUTPUT_ROOT / datetime.now().strftime("%Y%m%d_%H%M%S")
        cycle_dir.mkdir(parents=True, exist_ok=True)

        prompt = self._build_prompt_from_trends()

        # STAGE 1 (RTX 5070 Ti): base image render, Iris QC-gated inside generate_and_audit
        img_res = comfy_bridge.generate_and_audit(
            positive_prompt=prompt,
            negative_prompt=NEGATIVE_PROMPT,
            width=832,
            height=1216,
            style_preset="photorealism",
            auto_qc=True
        )
        if not img_res.get("success"):
            return {"success": False, "stage": "image_generation", "error": img_res.get("error"), "prompt": prompt}

        # STAGE 2 (RTX 5070 Ti): image-to-video animation of the approved base image
        vid_res = comfy_bridge.generate_image_to_video(
            source_image_path=img_res["file_path"],
            prompt=prompt,
            negative_prompt=NEGATIVE_PROMPT,
            width=720,
            height=1280,
            num_frames=240,
            fps=30,
            timeout_seconds=900
        )
        if not vid_res.get("success"):
            return {
                "success": False, "stage": "video_generation", "error": vid_res.get("error"),
                "prompt": prompt, "base_image": img_res["file_path"]
            }

        video_path = Path(vid_res["file_path"])

        # STAGE 3 (Forge): teaser cut + 9:16/1:1 social crops
        preview_path = scene_extractor.cut_preview_video(video_path, cycle_dir, target_duration=30)
        if not preview_path:
            return {"success": False, "stage": "forge_preview_cut", "error": "Forge failed to cut preview video", "video": str(video_path)}

        crops = scene_extractor.generate_social_crops(preview_path, cycle_dir)
        if not crops:
            return {"success": False, "stage": "forge_social_crops", "error": "Forge failed to generate social crops", "preview": str(preview_path)}

        # STAGE 4 (Scribe): multi-platform copy kit
        copy_kit = self.copy_synth.generate_release_kit(
            video_name=video_path.stem,
            visual_analysis=prompt,
            transcript_text="",
            spoken_hooks=[],
            preset="Adult Creator Shoot",
            content_type="adult",
            caption_styles=["Hook", "Story", "Question"]
        )

        manifest = {
            "success": True,
            "generated_at": datetime.now().isoformat(),
            "prompt_used": prompt,
            "base_image": img_res["file_path"],
            "qc_audit": img_res.get("qc_audit"),
            "raw_video": str(video_path),
            "preview_video": str(preview_path),
            "social_crops": {k: str(v) for k, v in crops.items()},
            "copy_kit": copy_kit,
            "output_dir": str(cycle_dir),
            "status": "awaiting_manual_review_and_posting"
        }
        try:
            with open(cycle_dir / "manifest.json", "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, default=str)
        except Exception:
            pass

        self._save_last_result(manifest)
        return manifest

    def _save_last_result(self, result: Dict[str, Any]):
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, default=str)
        except Exception:
            pass

    def get_last_result(self) -> Dict[str, Any]:
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"success": None, "message": "No content engine cycle has run yet."}


# Global singleton instance export
content_engine = ContentEngine()
