import os
import json
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path("F:/WORKHORSE")))
from shared.ai_providers import AIProviderService

class VisionAgent:
    def __init__(self, config_path: str = "F:/WORKHORSE/config.json"):
        self.ai = AIProviderService(config_path)

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
                "cover_recommendation": "Pose 2 or Pose 3",
                "sample_poses_inspected": [p.name for p in sample_poses]
            }
        except Exception as e:
            return {
                "visual_summary": f"Visual analysis fallback: {e}",
                "pose_count": len(pose_images),
                "cover_recommendation": "Pose 1"
            }

if __name__ == "__main__":
    v_agent = VisionAgent()
    print("Vision Agent (Iris) initialized.")
