import os
import json
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path("F:/WORKHORSE")))
from shared.ai_providers import AIProviderService

ADULT_CONTENT_KEYWORDS = [
    "adult", "boudoir", "nsfw", "onlyfans", "fansly", "glamour", "lingerie",
    "nude", "intimate", "sensual", "fetish", "cam", "fiverr_service_bot_adult"
]

class VisionAgent:
    def __init__(self, config_path: str = "F:/WORKHORSE/config.json"):
        self.ai = AIProviderService(config_path)

    def _detect_content_type(self, preset: str) -> str:
        """Auto-classifies a job preset as 'adult' or 'general', matching copy_synthesizer.py's detection."""
        preset_lower = (preset or "").lower()
        return "adult" if any(k in preset_lower for k in ADULT_CONTENT_KEYWORDS) else "general"

    def analyze_poses(self, pose_images: List[Path], progress_cb: Optional[Callable[[str, int], None]] = None) -> Dict[str, Any]:
        """Analyze the 6 extracted pose frames for visual aesthetics, mood, and tags."""
        if not pose_images:
            return {
                "visual_summary": "No pose frames provided.",
                "aesthetic_tags": [],
                "content_mood": "Unknown",
                "recommended_cover_index": 1
            }

        if progress_cb:
            progress_cb("Iris Agent: Scanning pose frames with Qwen-VL...", 30)

        prompt = """You are Iris, the elite visual scout agent for a high-end photography & adult/creator content production studio.
Analyze these preview frames captured from a shoot. Provide a structured analysis:
1. Setting & Lighting (e.g. Studio, boudoir, neon, natural light, mood)
2. Subject Styling & Aesthetics (e.g. Glamour, lingerie, casual, provocative, artistic)
3. Best Cover Pose (Pick which pose 1-6 is the strongest thumbnail cover and explain why in 1 sentence)
4. Key Visual Tags (Provide 8-12 comma-separated tags describing the visual elements, attire, and poses)

Respond in clean format."""

        try:
            # We send up to 3 selected representative poses (e.g. pose 1, 3, 5) to keep inference fast
            sample_poses = [pose_images[0], pose_images[min(2, len(pose_images)-1)], pose_images[min(4, len(pose_images)-1)]]
            response = self.ai.call_ollama_vision(prompt, sample_poses)

            if progress_cb:
                progress_cb("Iris Agent: Vision analysis completed!", 95)

            return {
                "visual_summary": response,
                "pose_count": len(pose_images),
                "cover_recommendation": self._extract_cover_recommendation(response),
                "sample_poses_inspected": [p.name for p in sample_poses]
            }
        except Exception as e:
            return {
                "visual_summary": f"Visual analysis fallback: {e}",
                "pose_count": len(pose_images),
                "cover_recommendation": "Pose 1"
            }

    def _extract_cover_recommendation(self, response_text: str) -> str:
        """Parse the model's actual named cover-pose pick out of its free-text response."""
        import re
        match = re.search(r"pose\s*#?\s*(\d)", response_text, re.IGNORECASE)
        if match:
            return f"Pose {match.group(1)}"
        return "Pose 1"

    def extract_forensic_scene(
        self,
        pose_images: List[Path],
        preset: str = "Adult Creator Shoot",
        content_type: str = "auto",
        progress_cb: Optional[Callable[[str, int], None]] = None
    ) -> Dict[str, Any]:
        """Clinical, literal scene extraction (hair, outfit/fabric, pose anatomy, lighting,
        setting, visible text) - grounds Scribe's copywriting and Muse's AI-prompt generation
        in what's actually visible, instead of a loose aesthetic summary."""
        if not pose_images:
            return {"scene_description": "No pose frames provided.", "pose_count": 0}

        resolved_type = self._detect_content_type(preset) if content_type == "auto" else content_type

        if progress_cb:
            progress_cb("Iris Agent: Running forensic scene extraction...", 40)

        if resolved_type == "adult":
            prompt = """You are Iris, a forensic visual analyst for adult/glamour creator content production.
Examine these photos with clinical precision and describe EXACTLY what is visible - do not guess or embellish beyond what's shown:

1. SUBJECT: Hair (exact color, length, texture, style, parting), visible skin tone, build, facial expression.
2. OUTFIT & FABRIC: Top and bottom garments described separately - exact cut, fabric type (sheer/lace/mesh/leather/satin/velvet/latex/denim/cotton), color, how it fits/drapes.
3. POSE & BODY LANGUAGE: Camera framing (frontal/three-quarter/profile), weight distribution, hip/shoulder tilt, arm and hand positions, head direction, gaze.
4. SETTING & PROPS: Exact wall/floor/furniture materials and colors visible - no inferred location.
5. LIGHTING: Direction, hardness (soft/hard), color temperature, key light source type.
6. VISIBLE TEXT: Any readable text on clothing, signs, or props (quote exactly, or state "none").

Output as a clean labeled list. Be precise and literal, not creative."""
        else:
            prompt = """You are Iris, a forensic visual analyst for a professional content studio.
Examine these photos with clinical precision and describe EXACTLY what is visible - do not guess or embellish beyond what's shown:

1. SUBJECT: Hair, visible skin tone, build, facial expression (or main subject if non-human).
2. WARDROBE/OBJECT DETAILS: Garments or product details - exact colors, materials, textures, branding.
3. POSE & COMPOSITION: Camera framing, body/object orientation, composition style.
4. SETTING & PROPS: Exact wall/floor/furniture/background materials and colors visible.
5. LIGHTING: Direction, hardness, color temperature, key light source type.
6. VISIBLE TEXT: Any readable text on clothing, signs, products, or props (quote exactly, or state "none").

Output as a clean labeled list. Be precise and literal, not creative."""

        try:
            sample_poses = [pose_images[0], pose_images[min(2, len(pose_images)-1)], pose_images[min(4, len(pose_images)-1)]]
            response = self.ai.call_ollama_vision(prompt, sample_poses, num_predict=700)

            if progress_cb:
                progress_cb("Iris Agent: Forensic scene extraction complete!", 60)

            return {
                "scene_description": response,
                "pose_count": len(pose_images),
                "content_type": resolved_type
            }
        except Exception as e:
            return {
                "scene_description": f"Scene extraction fallback: {e}",
                "pose_count": len(pose_images),
                "content_type": resolved_type
            }

if __name__ == "__main__":
    v_agent = VisionAgent()
    print("Vision Agent (Iris) initialized.")
