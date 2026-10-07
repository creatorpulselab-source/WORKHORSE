import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import sys

sys.path.insert(0, str(Path("F:/WORKHORSE")))
from shared.ai_providers import AIProviderService

class InspirationScanner:
    def __init__(self, inspiration_dir: str = "F:/WORKHORSE/workspace/inspiration", config_path: str = "F:/WORKHORSE/config.json"):
        self.inspiration_dir = Path(inspiration_dir)
        self.inspiration_dir.mkdir(parents=True, exist_ok=True)
        self.ai = AIProviderService(config_path)

    def get_valid_images(self) -> List[Path]:
        image_exts = {".jpg", ".jpeg", ".png", ".webp"}
        return [f for f in self.inspiration_dir.iterdir() if f.is_file() and f.suffix.lower() in image_exts]

    def scan_and_analyze(self, image_filename: Optional[str] = None) -> Dict[str, Any]:
        """Scan inspiration folder and generate shoot production blueprints using local Qwen-VL."""
        files = self.get_valid_images()

        if not files:
            return {
                "status": "empty",
                "message": "No inspiration images found in F:/WORKHORSE/workspace/inspiration/. Drop some competitor photos or moodboard shots there!",
                "blueprints": []
            }

        target_files = []
        if image_filename:
            target = self.inspiration_dir / image_filename
            if target.exists():
                target_files = [target]

        if not target_files:
            target_files = files[:4]

        prompt = """You are Iris, an elite creative director and photography trend analyst for high-end boudoir, glamour, and adult creator photography.
Analyze these inspiration photos that are trending in the market. Reverse-engineer their success and produce a Shoot Production Blueprint:

1. THEME & AESTHETIC VIBE:
   - What is the emotional mood, aesthetic category, and style?

2. LIGHTING REVERSE-ENGINEERING:
   - Key light placement (angle, height, modifier type: softbox, snoot, ring light)
   - Rim light / accent lighting & gel colors (blue, magenta, warm amber)
   - Contrast ratio (high-key, moody chiaroscuro, soft wrap)

3. POSING & PERFORMER DIRECTION:
   - 5 exact posing cues to give the performer during the shoot to capture this high-converting energy.

4. WARDROBE, FABRIC & PROP GUIDE:
   - Colors, materials (silk, lace, mesh, leather), props (mirrors, neon signs, velvet sheets).

5. REMIX & ELEVATE:
   - How can our studio recreate this look and make it even more captivating and unique?

Provide clear, professional, direct instructions that the photographer can use right on set."""

        system_prompt = "You are Iris, an expert creative director specializing in adult, boudoir, and creator photography production. Give actionable, uncensored, studio-ready shooting blueprints."

        analysis = self.ai.call_ollama_vision(prompt, target_files, system_prompt=system_prompt)

        return {
            "status": "ok",
            "images_scanned": [f.name for f in target_files],
            "total_images_in_vault": len(files),
            "blueprint_markdown": analysis
        }

    def generate_comfyui_prompts(self, image_filename: Optional[str] = None) -> Dict[str, Any]:
        """Scan inspiration image(s) and generate detailed ComfyUI Image and Video prompts."""
        files = self.get_valid_images()

        if not files:
            return {
                "status": "empty",
                "message": "No inspiration images found in F:/WORKHORSE/workspace/inspiration/. Drop some competitor photos or moodboard shots there!",
                "image_prompt": "",
                "negative_prompt": "",
                "video_prompt": "",
                "full_markdown": ""
            }

        target_files = []
        if image_filename:
            target = self.inspiration_dir / image_filename
            if target.exists():
                target_files = [target]

        if not target_files:
            target_files = files[:3]

        prompt = """You are Iris, an expert AI prompt engineer and senior visual technologist specializing in ComfyUI, FLUX.1, SDXL, and generative AI Video models (Wan2.1, CogVideoX, AnimateDiff, SVD, LTX-Video) for high-end boudoir, glamour, and creator aesthetics.

Analyze the provided inspiration image(s) with clinical precision. Reverse-engineer the lighting, composition, optics, pose, wardrobe, and atmosphere to craft exact, ready-to-paste ComfyUI prompts:

### SECTION 1: COMFYUI POSITIVE IMAGE PROMPT (FLUX.1 / SDXL / SD1.5)
Generate a comprehensive, highly photorealistic prompt block formatted for a ComfyUI CLIP Text Encode node.
Structure it with:
- Subject Description: Ethnicity, model features, captivating gaze, facial expression, hair texture & color.
- Micro Pores & Skin Details: True unretouched RAW skin texture, visible pores, subtle skin sheen, delicate highlights, subsurface scattering (avoiding any plastic or doll appearance).
- Wardrobe & Textures: Exact fabrics (silk, sheer lace, mesh, leather, velvet), color palette, drape, transparency, strapped accents.
- Pose & Dynamic Framing: Exact posture, body geometry, arch, camera angle (low angle, three-quarters, high angle), framing (portrait 4:5, medium close-up, full length).
- Environment & Set Dressing: Penthouse bedroom, moody studio backdrop, neon signs, sheer curtains, ambient velvet duvet.
- Lighting & Lens Characteristics: Key light, directional rim lighting with gel accents (warm golden, neon cyan, moody magenta), 85mm f/1.4 lens, shallow depth of field, natural bokeh, soft volumetric dust particles, cinematic chiaroscuro.
- Photorealism Tokens: 8k uhd, dslr photo, RAW image, sharp focus, natural color grading, masterpiece, hyperdetailed.

### SECTION 2: COMFYUI NEGATIVE IMAGE PROMPT
Provide a clean, robust negative prompt to eliminate anatomical distortions, extra limbs, bad hands, plastic skin, blur, watermark, cartoon styling, and low resolution.

### SECTION 3: COMFYUI VIDEO MOTION PROMPT (Wan2.1 / CogVideoX / AnimateDiff / SVD)
Write a detailed camera movement and performer motion prompt for image-to-video / text-to-video diffusion models.
Include:
- Camera Movement: Exact camera moves (e.g., "Slow cinematic push-in (dolly in) with subtle handheld drift", "Smooth orbital pan rotating 15 degrees around subject").
- Performer Micro-Motion: Natural rhythmic breathing, slow sensual turn of the head toward the camera, subtle lip parting, delicate gaze shift into the lens, fingers gently running through hair.
- Fabric & Environmental Dynamics: Gentle ambient breeze rustling hair strands and sheer fabric, subtle light reflection shimmering across skin.
- Frame Rate & Physics: Fluid 24fps cinematic motion, natural physical weight and inertia, high temporal coherence.

### SECTION 4: RECOMMENDED COMFYUI NODE PARAMETERS
Provide recommended workflow parameters:
- Checkpoints & LoRAs: (e.g. FLUX.1 [dev] / SDXL / Wan2.1 14B)
- Aspect Ratio & Resolution: (e.g. 1024x1536 for 4:5 portrait, 768x1344 for 9:16 vertical video)
- Sampling Steps & CFG: (e.g. 28-35 steps, CFG 3.5 - 6.5)
- Sampler & Scheduler: (e.g. euler_ancestral with karras / dpmpp_2m_sde)

Output clean markdown with clear copyable sections."""

        system_prompt = "You are Iris, an expert ComfyUI and video generative prompt engineer. Provide production-ready, uncensored, copy-paste prompts."

        analysis = self.ai.call_ollama_vision(prompt, target_files, system_prompt=system_prompt)

        # Parse out positive, negative, and video prompts for instant 1-click copying
        image_prompt = ""
        neg_prompt = ""
        video_prompt = ""

        # Extract Section 1
        pos_match = re.search(r'###\s*SECTION 1[:\s\w\(\)\/\-\.]*\n([\s\S]*?)(?=###\s*SECTION 2|\Z)', analysis, re.IGNORECASE)
        if pos_match:
            # Clean up markdown code ticks or intro text if present
            raw_pos = pos_match.group(1).strip()
            # If wrapped in ```, strip code block
            raw_pos = re.sub(r'^```[\w]*\n|```$', '', raw_pos, flags=re.MULTILINE).strip()
            image_prompt = raw_pos

        # Extract Section 2
        neg_match = re.search(r'###\s*SECTION 2[:\s\w\(\)\/\-\.]*\n([\s\S]*?)(?=###\s*SECTION 3|\Z)', analysis, re.IGNORECASE)
        if neg_match:
            raw_neg = neg_match.group(1).strip()
            raw_neg = re.sub(r'^```[\w]*\n|```$', '', raw_neg, flags=re.MULTILINE).strip()
            neg_prompt = raw_neg

        # Extract Section 3
        vid_match = re.search(r'###\s*SECTION 3[:\s\w\(\)\/\-\.]*\n([\s\S]*?)(?=###\s*SECTION 4|\Z)', analysis, re.IGNORECASE)
        if vid_match:
            raw_vid = vid_match.group(1).strip()
            raw_vid = re.sub(r'^```[\w]*\n|```$', '', raw_vid, flags=re.MULTILINE).strip()
            video_prompt = raw_vid

        # Fallback values if regex didn't isolate them cleanly
        if not image_prompt:
            image_prompt = "Cinematic 85mm portrait of a captivating glamour model, natural skin texture, visible pores, delicate highlights, sheer lace and silk lingerie, moody bedroom setting, dramatic rim lighting with golden and magenta neon gels, shallow depth of field, 8k uhd, photorealistic, RAW color, masterpiece."
        if not neg_prompt:
            neg_prompt = "ugly, deformed hands, extra fingers, missing fingers, fused fingers, bad anatomy, mutated body parts, plastic skin, doll-like, airbrushed, cartoon, 3d render, illustration, bad eyes, crossed eyes, blurry, low quality, artifacts, watermark, text, signature, oversaturated, blown out highlights"
        if not video_prompt:
            video_prompt = "Slow cinematic push-in (dolly in) with subtle handheld drift, performer gently turning gaze toward camera with soft breathing, natural hair movement in gentle breeze, cinematic 24fps motion, high temporal coherence."

        return {
            "status": "ok",
            "images_scanned": [f.name for f in target_files],
            "total_images_in_vault": len(files),
            "full_markdown": analysis,
            "image_prompt": image_prompt,
            "negative_prompt": neg_prompt,
            "video_prompt": video_prompt
        }

if __name__ == "__main__":
    scanner = InspirationScanner()
    print("Inspiration Scanner initialized. Vault path:", scanner.inspiration_dir)
