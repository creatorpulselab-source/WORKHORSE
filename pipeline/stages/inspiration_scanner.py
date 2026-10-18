import os
import json
import re
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import sys

sys.path.insert(0, str(Path("F:/WORKHORSE")))
from shared.ai_providers import AIProviderService, is_ai_error_response, VISION_NUM_CTX
from shared.comfyui_knowledge import get_comfyui_context

VAULT_CACHE_FILE = Path("F:/WORKHORSE/workspace/inspiration_vault_cache.json")
MAX_VAULT_CACHE_ENTRIES = 50

# --- Vision budget -----------------------------------------------------------------
# Root causes of the "Style & Pose Lab writes no prompts from images" bug (2026-10-18):
#   1. call_ollama_vision() was invoked with its defaults: num_ctx=4096 and num_predict=350.
#      The Iris system prompt (~3.7K tokens) + instructions (~0.9K) + one 768px image (~1.2K)
#      is ~5.9K tokens -> HTTP 400 "exceeds the available context size" on EVERY call, and even
#      a call that fit could only emit 350 tokens (the 4-section answer needs ~1,200+).
#   2. The failure string was then cached and the regex parse "fell back" to a hard-coded
#      glamour-model prompt, which the UI showed as if it had been written from the photo.
# Fixes: a window/outputs sized for the real prompt, a trimmed knowledge slice, strict
# validation, no caching of failures, and NO canned prompt masquerading as image output.
VISION_KNOWLEDGE_CHARS = 6500     # keeps Module 6 (prompt writing) whole; ~1.2K tokens
COMFY_PROMPT_NUM_PREDICT = 1600
BLUEPRINT_NUM_PREDICT = 1400
SINGLE_IMAGE_MAX_DIM = 896        # one image: keep fine detail (pose, wardrobe, lens cues)
MULTI_IMAGE_MAX_DIM = 640         # several images: ~0.7K tokens each instead of ~1.2K
MIN_ANALYSIS_CHARS = 40
# Long list-style output at temperature 0.1 with no penalty is what produced the
# "oversaturated, oversharpened, oversmoothed" x400 loop that ate the whole token budget.
VISION_TEMPERATURE = 0.45
VISION_REPEAT_PENALTY = 1.2

# The old hard-coded fallbacks. Cache entries that contain them (or a stored failure
# string) were produced by the bug above and must never be served again.
_LEGACY_CANNED_IMAGE_PROMPT_PREFIX = "Cinematic 85mm portrait of a captivating glamour model"
_BAD_CACHE_MARKERS = (
    "blocked a real network connection",
    "exceeds the available context size",
    "Vision QC timed out",
)

# Generic anti-artifact negative prompt. Unlike the positive/video prompts this is not
# image-specific, so a default is legitimate - but the result says when it was used.
DEFAULT_NEGATIVE_PROMPT = (
    "ugly, deformed hands, extra fingers, missing fingers, fused fingers, bad anatomy, mutated body parts, "
    "plastic skin, doll-like, airbrushed, cartoon, 3d render, illustration, bad eyes, crossed eyes, blurry, "
    "low quality, artifacts, watermark, text, signature, oversaturated, blown out highlights"
)

_SECTION_HEADER_RE = re.compile(
    r"^[ \t]*(?:#{1,6}[ \t]*|\*{2}[ \t]*)?(?:SECTION|Section)[ \t]*(\d)\b[^\n]*", re.MULTILINE
)
_LEGACY_SECTION_KEYS = {0: "description", 1: "image", 2: "negative", 3: "video", 4: "params"}


def _classify_section(header_line: str, number: int) -> str:
    """Name-aware: 'COMFYUI VIDEO MOTION PROMPT' is the video section whatever number the model gave it."""
    h = header_line.lower()
    if "what you see" in h:
        return "description"
    if "negative" in h:
        return "negative"
    if "video" in h or "motion" in h:
        return "video"
    if "positive" in h or "image prompt" in h:
        return "image"
    if "param" in h or "setting" in h:
        return "params"
    return _LEGACY_SECTION_KEYS.get(number, f"section_{number}")


def _split_sections(text: str) -> Dict[str, str]:
    """Tolerant section splitter returning {'description'|'image'|'negative'|'video'|'params': body}.

    Accepts '### SECTION 1: ...', '**Section 1 -**', '## Section 1', etc. The first occurrence of
    each section wins. Code fences/stray bold markers are stripped."""
    matches = list(_SECTION_HEADER_RE.finditer(text or ""))
    sections: Dict[str, str] = {}
    for i, m in enumerate(matches):
        key = _classify_section(m.group(0), int(m.group(1)))
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end():end].strip()
        body = re.sub(r"^```[\w]*[ \t]*\n", "", body, flags=re.MULTILINE)
        body = re.sub(r"\n?[ \t]*```[ \t]*$", "", body, flags=re.MULTILINE).strip()
        body = body.strip("*").strip()
        # Models end sections with a '---' horizontal rule; it must not end up inside a copy-paste prompt.
        body = re.sub(r"(?:[ \t]*\n)?[ \t]*(?:-{3,}|\*{3,}|_{3,})[ \t]*$", "", body).strip()
        body = re.sub(r"[ \t]+(?:-{3,})[ \t]*$", "", body).strip()
        if body and key not in sections:
            sections[key] = body
    return sections


def _collapse_repetition(text: str, max_terms: int = 60) -> str:
    """Undo degenerate generation loops (e.g. 'oversaturated, oversharpened, oversmoothed' x400).

    Comma lists are de-duplicated (case-insensitive, order preserved, capped at max_terms); prose drops
    any sentence that repeats an earlier one verbatim. Clean text passes through unchanged."""
    text = (text or "").strip()
    if not text:
        return text
    if text.count(",") >= 8 and "\n" not in text.strip():
        seen, terms = set(), []
        for raw in text.split(","):
            term = raw.strip()
            key = term.lower()
            if term and key not in seen:
                seen.add(key)
                terms.append(term)
        return ", ".join(terms[:max_terms])
    seen_sent, out = set(), []
    for sent in re.split(r"(?<=[.!?])\s+", text):
        key = sent.strip().lower()
        if key and key in seen_sent:
            continue
        seen_sent.add(key)
        out.append(sent)
    return " ".join(out)


class InspirationScanner:
    def __init__(self, inspiration_dir: str = "F:/WORKHORSE/workspace/inspiration", config_path: str = "F:/WORKHORSE/config.json"):
        self.inspiration_dir = Path(inspiration_dir)
        self.inspiration_dir.mkdir(parents=True, exist_ok=True)
        self.ai = AIProviderService(config_path)

    def get_valid_images(self) -> List[Path]:
        """Returns vault images sorted newest-first, so the default "scan the vault" selection
        always analyzes the most recently added photos rather than an arbitrary filesystem order."""
        image_exts = {".jpg", ".jpeg", ".png", ".webp"}
        files = [f for f in self.inspiration_dir.iterdir() if f.is_file() and f.suffix.lower() in image_exts]
        return sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)

    def _cache_key_for(self, target_files: List[Path]) -> str:
        """Fingerprints the exact set of files (name + modified time) being analyzed, so the
        same selection of images always maps to the same cache entry, and adding/removing/
        replacing any image in the set naturally invalidates it."""
        parts = sorted(f"{f.name}:{int(f.stat().st_mtime)}" for f in target_files)
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()

    @staticmethod
    def _is_bad_cache_entry(entry: Any) -> bool:
        """True for entries written by the old buggy code: a stored failure string, a test-suite
        network-block message, or the canned glamour prompt that was shown instead of real output."""
        if not isinstance(entry, dict):
            return True
        for field in ("full_markdown", "blueprint_markdown"):
            value = entry.get(field)
            if isinstance(value, str):
                if is_ai_error_response(value) or any(marker in value for marker in _BAD_CACHE_MARKERS):
                    return True
        if str(entry.get("image_prompt", "")).startswith(_LEGACY_CANNED_IMAGE_PROMPT_PREFIX):
            return True
        return False

    def _load_vault_cache(self) -> Dict[str, Any]:
        try:
            if VAULT_CACHE_FILE.exists():
                with open(VAULT_CACHE_FILE, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                clean = {k: v for k, v in cache.items() if not self._is_bad_cache_entry(v)}
                if len(clean) != len(cache):
                    print(f"[Inspiration Scanner] Purged {len(cache) - len(clean)} poisoned cache entr(ies) from earlier failed/canned analyses.")
                    self._save_vault_cache(clean)
                return clean
        except Exception:
            pass
        return {}

    def _save_vault_cache(self, cache: Dict[str, Any]) -> None:
        try:
            if len(cache) > MAX_VAULT_CACHE_ENTRIES:
                items = sorted(cache.items(), key=lambda kv: kv[1].get("cached_at", 0))
                cache = dict(items[-MAX_VAULT_CACHE_ENTRIES:])
            with open(VAULT_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2)
        except Exception as e:
            print(f"[Inspiration Scanner] Failed to save vault cache: {e}")

    def _select_targets(self, files: List[Path], image_filename: Optional[str], default_count: int):
        """Returns (target_files, warnings). A selected-but-missing image is reported instead of silently swapped."""
        warnings: List[str] = []
        if image_filename:
            target = self.inspiration_dir / Path(image_filename).name
            if target.exists():
                return [target], warnings
            warnings.append(f"Selected image '{image_filename}' was not found in the vault - used the newest photo(s) instead.")
        return files[:default_count], warnings

    @staticmethod
    def _error_result(message: str, raw: str, files: List[Path], images: List[Path], extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        result = {
            "status": "error",
            "message": message,
            "error": (raw or "")[:400],
            "images_scanned": [f.name for f in images],
            "total_images_in_vault": len(files),
            "cache_hit": False,
        }
        if extra:
            result.update(extra)
        return result

    def scan_and_analyze(self, image_filename: Optional[str] = None) -> Dict[str, Any]:
        """Scan inspiration folder and generate shoot production blueprints using local Qwen-VL."""
        files = self.get_valid_images()

        if not files:
            return {
                "status": "empty",
                "message": "No inspiration images found in F:/WORKHORSE/workspace/inspiration/. Drop some competitor photos or moodboard shots there!",
                "blueprints": []
            }

        target_files, warnings = self._select_targets(files, image_filename, default_count=4)

        cache = self._load_vault_cache()
        cache_key = "blueprint:" + self._cache_key_for(target_files)
        cached = cache.get(cache_key)
        if cached:
            print(f"[Inspiration Scanner] Cache hit for blueprint scan ({len(target_files)} image(s) unchanged since last analysis) - skipping vision call.")
            return {
                "status": "ok",
                "images_scanned": cached["images_scanned"],
                "total_images_in_vault": len(files),
                "blueprint_markdown": cached["blueprint_markdown"],
                "cache_hit": True,
                "warnings": warnings,
            }

        prompt = """You are Iris, an elite creative director and photography trend analyst for high-end boudoir, glamour, and adult creator photography.
Analyze these inspiration photos that are trending in the market. Reverse-engineer their success and produce a Shoot Production Blueprint.
Base EVERYTHING on what is actually visible in the provided photo(s) - do not invent details that are not in the image.

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

        analysis = self.ai.call_ollama_vision(
            prompt, target_files, system_prompt=system_prompt, timeout=240,
            num_predict=BLUEPRINT_NUM_PREDICT, num_ctx=VISION_NUM_CTX,
            image_max_dim=SINGLE_IMAGE_MAX_DIM if len(target_files) == 1 else MULTI_IMAGE_MAX_DIM,
            temperature=VISION_TEMPERATURE, repeat_penalty=VISION_REPEAT_PENALTY,
        )

        if is_ai_error_response(analysis) or len((analysis or "").strip()) < MIN_ANALYSIS_CHARS:
            print(f"[Inspiration Scanner] Blueprint analysis failed (not cached): {(analysis or '')[:200]}")
            return self._error_result(
                "Iris could not analyse the photo(s) this time (vision model error). Nothing was saved - click again to retry.",
                analysis, files, target_files, {"warnings": warnings},
            )

        images_scanned = [f.name for f in target_files]
        cache[cache_key] = {
            "images_scanned": images_scanned,
            "blueprint_markdown": analysis,
            "cached_at": time.time()
        }
        self._save_vault_cache(cache)

        return {
            "status": "ok",
            "images_scanned": images_scanned,
            "total_images_in_vault": len(files),
            "blueprint_markdown": analysis,
            "cache_hit": False,
            "warnings": warnings,
        }


    def generate_comfyui_prompts(self, image_filename: Optional[str] = None) -> Dict[str, Any]:
        """Scan inspiration image(s) and generate detailed ComfyUI Image and Video prompts.

        Never returns a canned prompt in place of real output: if the vision model fails or the
        answer can't be parsed, the result says so (status 'error' / 'partial') and is not cached.
        """
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

        target_files, warnings = self._select_targets(files, image_filename, default_count=3)

        cache = self._load_vault_cache()
        knowledge_context = get_comfyui_context("inspiration", max_chars=VISION_KNOWLEDGE_CHARS)
        knowledge_version = hashlib.sha256(knowledge_context.encode("utf-8")).hexdigest()
        cache_key = "comfyui:" + knowledge_version + ":" + self._cache_key_for(target_files)
        cached = cache.get(cache_key)
        if cached:
            print(f"[Inspiration Scanner] Cache hit for ComfyUI prompt scan ({len(target_files)} image(s) unchanged since last analysis) - skipping vision call.")
            return {
                "status": "ok",
                "images_scanned": cached["images_scanned"],
                "total_images_in_vault": len(files),
                "full_markdown": cached["full_markdown"],
                "image_prompt": cached["image_prompt"],
                "negative_prompt": cached["negative_prompt"],
                "video_prompt": cached["video_prompt"],
                "image_description": cached.get("image_description", ""),
                "cache_hit": True,
                "warnings": warnings,
            }

        prompt = """You are Iris, an expert AI prompt engineer and senior visual technologist specializing in ComfyUI, FLUX.1, SDXL, and generative AI video models (LTX-Video 2.3 and MiniMax FastH3 image-to-video) for high-end boudoir, glamour, and creator aesthetics.

Analyze the provided inspiration image(s) with clinical precision. Describe ONLY what is actually visible - never invent a subject, wardrobe, setting or lighting that is not in the picture. Then reverse-engineer the lighting, composition, optics, pose, wardrobe, and atmosphere into exact, ready-to-paste ComfyUI prompts.
Use EXACTLY these section headings (the dashboard parses them):

### SECTION 0: WHAT YOU SEE
Two or three plain, factual sentences describing the photo (subject, pose, wardrobe, setting, framing, lighting).

### SECTION 1: COMFYUI POSITIVE IMAGE PROMPT (FLUX.1 / SDXL)
One comprehensive, highly photorealistic prompt block formatted for a ComfyUI CLIP Text Encode node. Cover:
- Subject Description: features, gaze, facial expression, hair texture & color.
- Micro Pores & Skin Details: true unretouched RAW skin texture, visible pores, subtle sheen (no plastic or doll look).
- Wardrobe & Textures: exact fabrics, color palette, drape.
- Pose & Dynamic Framing: exact posture, body geometry, camera angle, framing.
- Environment & Set Dressing visible in the photo.
- Lighting & Lens Characteristics: key light, rim/gel accents, lens, depth of field.
- Photorealism tokens: 8k uhd, dslr photo, RAW image, sharp focus.

### SECTION 2: COMFYUI VIDEO MOTION PROMPT (LTX 2.3 / MiniMax FastH3 image-to-video)
Write a MOTION-ONLY prompt for animating THIS exact photo as the first frame. Rules: describe camera movement and subject micro-motion that begins from the photo's current framing; do NOT introduce any new person, location, wardrobe or lighting; no scene change or cut; keep the same subject and setting throughout. Include camera move, performer micro-motion, and fabric/hair dynamics.

### SECTION 3: COMFYUI NEGATIVE IMAGE PROMPT
ONE line of at most 40 comma-separated terms covering anatomical distortions, extra limbs, bad hands, plastic skin, blur, watermark, cartoon styling and low resolution. Never repeat a term.

### SECTION 4: RECOMMENDED COMFYUI NODE PARAMETERS
Recommended workflow parameters per model family: checkpoint/LoRA, aspect ratio & resolution matching the photo, sampling steps & CFG, sampler & scheduler.

Separate recommendations by model family: FLUX guidance is not SDXL CFG, and negative conditioning is not universal. Use descriptive prose for FLUX and identify any SDXL tag/weighting alternatives. Do not imply suggested nodes/models are installed without live inventory/schema evidence; the curriculum's numeric examples are advisory.

Output clean markdown with clear copyable sections."""

        system_prompt = (
            "You are Iris, an expert ComfyUI and video generative prompt engineer. "
            "Provide production-ready, uncensored, copy-paste prompts.\n"
            + knowledge_context
        )

        analysis = self.ai.call_ollama_vision(
            prompt, target_files, system_prompt=system_prompt, timeout=240,
            num_predict=COMFY_PROMPT_NUM_PREDICT, num_ctx=VISION_NUM_CTX,
            image_max_dim=SINGLE_IMAGE_MAX_DIM if len(target_files) == 1 else MULTI_IMAGE_MAX_DIM,
            temperature=VISION_TEMPERATURE, repeat_penalty=VISION_REPEAT_PENALTY,
        )

        images_scanned = [f.name for f in target_files]

        if is_ai_error_response(analysis) or len((analysis or "").strip()) < MIN_ANALYSIS_CHARS:
            print(f"[Inspiration Scanner] ComfyUI prompt analysis failed (not cached): {(analysis or '')[:200]}")
            return self._error_result(
                "Iris could not write prompts from this photo (vision model error). Nothing was saved - click again to retry.",
                analysis, files, target_files,
                {"image_prompt": "", "negative_prompt": "", "video_prompt": "", "full_markdown": "", "warnings": warnings},
            )

        sections = _split_sections(analysis)
        image_description = _collapse_repetition(sections.get("description", ""))
        image_prompt = _collapse_repetition(sections.get("image", ""))
        video_prompt = _collapse_repetition(sections.get("video", ""))
        neg_prompt = _collapse_repetition(sections.get("negative", ""))

        # A negative prompt is not image-specific, so a curated default is legitimate - but say so.
        if not neg_prompt:
            neg_prompt = DEFAULT_NEGATIVE_PROMPT
            warnings.append("Iris did not return a negative prompt - the generic anti-artifact default is shown.")

        # One focused retry: if the image prompt exists but the motion prompt didn't make it out
        # (token budget spent elsewhere / model drifted), ask for just that section against the same photo.
        if image_prompt and not video_prompt:
            video_prompt = self._retry_video_prompt(target_files, image_description)
            if video_prompt:
                warnings.append("The video motion prompt was regenerated in a second focused pass.")

        if not image_prompt or not video_prompt:
            missing = [name for name, val in (("image prompt", image_prompt), ("video motion prompt", video_prompt)) if not val]
            warnings.append(
                "Iris's answer was missing: " + ", ".join(missing) + ". The full raw analysis is shown below - click again to retry."
            )
            print(f"[Inspiration Scanner] Partial ComfyUI analysis (not cached) - missing {missing}")
            return {
                "status": "partial",
                "images_scanned": images_scanned,
                "total_images_in_vault": len(files),
                "full_markdown": analysis,
                "image_prompt": image_prompt,
                "negative_prompt": neg_prompt,
                "video_prompt": video_prompt,
                "image_description": image_description,
                "cache_hit": False,
                "warnings": warnings,
            }

        cache[cache_key] = {
            "images_scanned": images_scanned,
            "full_markdown": analysis,
            "image_prompt": image_prompt,
            "negative_prompt": neg_prompt,
            "video_prompt": video_prompt,
            "image_description": image_description,
            "cached_at": time.time()
        }
        self._save_vault_cache(cache)

        return {
            "status": "ok",
            "images_scanned": images_scanned,
            "total_images_in_vault": len(files),
            "full_markdown": analysis,
            "image_prompt": image_prompt,
            "negative_prompt": neg_prompt,
            "video_prompt": video_prompt,
            "image_description": image_description,
            "cache_hit": False,
            "warnings": warnings,
        }

    def _retry_video_prompt(self, target_files: List[Path], description: str) -> str:
        """Second, tiny vision call that asks ONLY for the motion prompt for these photos."""
        hint = f"\nWhat the photo shows: {description}" if description else ""
        prompt = (
            "Write ONE motion-only prompt (60-110 words, plain prose, no headings, no lists) for animating THIS exact "
            "photo as the first frame of an image-to-video model (LTX 2.3 / MiniMax FastH3). Describe a camera move and "
            "subject micro-motion that start from the photo's current framing. Do NOT introduce any new person, location, "
            "wardrobe or lighting, and do not cut to another scene." + hint
        )
        text = self.ai.call_ollama_vision(
            prompt, target_files[:1], system_prompt="You are Iris, an expert image-to-video prompt engineer.",
            timeout=120, num_predict=320, num_ctx=VISION_NUM_CTX, image_max_dim=SINGLE_IMAGE_MAX_DIM,
            temperature=VISION_TEMPERATURE, repeat_penalty=VISION_REPEAT_PENALTY,
        )
        if is_ai_error_response(text):
            return ""
        text = _collapse_repetition(re.sub(r"^#{1,6}[^\n]*\n", "", (text or "").strip()).strip("*` \n"))
        return text if len(text.split()) >= 12 else ""


inspiration_scanner = InspirationScanner()

if __name__ == "__main__":
    print("Inspiration Scanner initialized. Vault path:", inspiration_scanner.inspiration_dir)
