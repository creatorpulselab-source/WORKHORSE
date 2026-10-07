import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import sys

sys.path.insert(0, str(Path("F:/WORKHORSE")))
from shared.ai_providers import AIProviderService

ADULT_CONTENT_KEYWORDS = [
    "adult", "boudoir", "nsfw", "onlyfans", "fansly", "glamour", "lingerie",
    "nude", "intimate", "sensual", "fetish", "cam", "fiverr_service_bot_adult"
]


class PromptSynthesizer:
    """MUSE [34 Se] (Selenium) - AI Image/Video Prompt Engineer.
    Converts Iris's real, grounded scene description into reusable FLUX.1/SDXL image
    prompts, WAN2.1/2.2 video motion prompts, and a 6-variation pose series - so the
    creator can generate NEW AI content faithful to the real shoot, not just reuse the
    raw screenshots."""

    def __init__(self, config_path: str = "F:/WORKHORSE/config.json"):
        self.ai = AIProviderService(config_path)

    def _detect_content_type(self, preset: str) -> str:
        """Auto-classifies a job preset as 'adult' or 'general', matching copy_synthesizer.py's detection."""
        preset_lower = (preset or "").lower()
        return "adult" if any(k in preset_lower for k in ADULT_CONTENT_KEYWORDS) else "general"

    def generate_prompt_kit(
        self,
        scene_description: str,
        preset: str = "Adult Creator Shoot",
        content_type: str = "auto",
        progress_cb: Optional[Callable[[str, int], None]] = None
    ) -> Dict[str, Any]:
        """Generate a Flux image prompt, a WAN video motion prompt, and 6 pose-series
        prompt variations - all grounded in Iris's real forensic scene description."""
        resolved_type = self._detect_content_type(preset) if content_type == "auto" else content_type

        explicit_note = (
            "Use direct, explicit adult-content vocabulary where appropriate - this is for "
            "private, consenting adult creator content and must not be censored or softened."
            if resolved_type == "adult" else
            "Keep all vocabulary tasteful and brand-safe for mainstream platforms."
        )

        base_context = f"""GROUND-TRUTH SCENE DESCRIPTION (from real reference photos - stay faithful to this, do not invent new details):
{scene_description}

{explicit_note}"""

        if progress_cb:
            progress_cb("Muse Agent: Crafting Flux image generation prompt...", 10)

        flux_request = f"""You are Muse, an expert AI prompt engineer specializing in ComfyUI, FLUX.1, and SDXL image generation.
{base_context}

Using ONLY the ground-truth scene description above, write ONE single-paragraph, highly detailed FLUX.1/SDXL image generation prompt that could recreate this exact subject, outfit, pose, setting, and lighting. Include subject description, outfit & fabric details, pose & camera framing, setting/props, and lighting exactly as described, ending with photorealism tokens: 8k uhd, RAW photo, sharp focus, natural skin texture, cinematic lighting, masterpiece.

Output ONLY the prompt paragraph, no headers or explanation."""

        flux_prompt = self._clean_response(self.ai.call_ollama_text(flux_request, system_prompt="You are Muse, an expert AI image-prompt engineer for FLUX.1/SDXL."))

        if progress_cb:
            progress_cb("Muse Agent: Crafting WAN video motion prompt...", 40)

        wan_request = f"""You are Muse, an expert AI video-prompt engineer specializing in WAN2.1/2.2 and CogVideoX image-to-video generation.
{base_context}

Using ONLY the ground-truth scene description above, write ONE cinematic camera-movement + subject-motion prompt (under 90 words) suitable for turning a still photo of this subject into a short video clip. Include camera movement (push-in, orbital pan, handheld drift, etc.) and natural subject micro-motion (breathing, gaze shift, hair movement, fabric sway).

Output ONLY the prompt, no headers or explanation."""

        wan_prompt = self._clean_response(self.ai.call_ollama_text(wan_request, system_prompt="You are Muse, an expert AI video-prompt engineer for WAN2.1/2.2."))

        if progress_cb:
            progress_cb("Muse Agent: Crafting 6-pose variation series...", 70)

        pose_request = f"""You are Muse, an expert AI prompt engineer creating a 6-pose variation series for FLUX.1/SDXL.
{base_context}

Using ONLY the ground-truth scene description above (keep subject, outfit, and setting IDENTICAL across all 6), write 6 numbered single-paragraph FLUX.1-compatible prompts, each describing a DIFFERENT pose/camera-angle variation (vary: framing, weight distribution, hip/shoulder tilt, arm position, gaze direction).

Format strictly as:
1. <prompt text>
2. <prompt text>
...through 6.
No extra commentary before, between, or after the 6 entries."""

        pose_series_raw = self._clean_response(self.ai.call_ollama_text(pose_request, system_prompt="You are Muse, an expert AI prompt engineer creating pose-series variations."))
        pose_variations = self._parse_pose_series(pose_series_raw)

        if progress_cb:
            progress_cb("Muse Agent: Prompt kit complete!", 100)

        return {
            "flux_image_prompt": flux_prompt,
            "wan_video_prompt": wan_prompt,
            "pose_series": pose_variations,
            "content_type": resolved_type
        }

    def _clean_response(self, text: str) -> str:
        """Strip <think>...</think> reasoning leakage some local thinking models emit before the real answer."""
        cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        if "</think>" in cleaned:
            cleaned = cleaned.split("</think>")[-1].strip()
        cleaned = re.sub(r"^```[\w]*\n|```$", "", cleaned, flags=re.MULTILINE).strip()
        return cleaned

    def _parse_pose_series(self, raw_text: str) -> List[Dict[str, Any]]:
        """Split Muse's numbered 6-pose response into individual prompt entries."""
        matches = re.findall(r"(?:^|\n)\s*(\d)\.\s*(.+?)(?=\n\s*\d\.\s|\Z)", raw_text, re.DOTALL)
        poses = [{"pose_number": int(num), "prompt": text.strip()} for num, text in matches]
        if not poses:
            poses = [{"pose_number": 1, "prompt": raw_text.strip()}]
        return poses


if __name__ == "__main__":
    synthesizer = PromptSynthesizer()
    print("Prompt Synthesizer (Muse) initialized.")
