"""
Synapse media routing + grounding helpers (pure functions, no Ollama/ComfyUI calls).

Why this module exists - root causes found in the 2026-10-18 bug check:

1. "Use the micro cinema image to video workflow" ran the generic LTX image-to-video tool with an
   invented prompt ("subject walks down a rain-slicked city street") because nothing mapped the
   Commander's wording ("micro cinema", "handheld", ...) to `comfy_viral_video_director`.
2. For animate commands the operator LLM never saw the photo (the vision guard intentionally keeps
   the image out of the 14B model's context), so it invented the motion prompt from words alone.
   LTX image-to-video treats the prompt as authoritative after frame 0, so a prompt describing a
   different scene produces a video that cuts to that scene.
3. The 4:5 portrait source was forced into 9:16 (704x1280), cropping the framing the Commander shot.
4. Synapse sent ~14K tokens to a model window that Ollama truncates to ~4K, silently dropping
   most of the system prompt (including the tool documentation).
"""

from __future__ import annotations

import math
import re
from typing import Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------------------------
# Viral video director mode detection
# ---------------------------------------------------------------------------------------------

VIRAL_MODE_ALIASES: Dict[str, Tuple[str, ...]] = {
    "micro_cinema": ("micro cinema", "micro-cinema", "microcinema", "micro_cinema"),
    "handheld_camera": ("handheld camera", "handheld_camera", "hand-held camera", "handheld cam", "handheld"),
    "fast_cut": ("fast cut", "fast-cut", "fast cuts", "fast_cut", "fast-cuts"),
    "one_take_shot": ("one take shot", "one-take shot", "one take", "one-take", "one_take_shot", "single take"),
    "time_lapse": ("time lapse", "time-lapse", "timelapse", "time_lapse"),
}

VIRAL_MODE_LABELS: Dict[str, str] = {
    "handheld_camera": "Handheld Camera",
    "micro_cinema": "Micro Cinema",
    "fast_cut": "Fast Cut",
    "one_take_shot": "One-Take Shot",
    "time_lapse": "Time-Lapse",
}

# "handheld" alone is ambiguous ("she holds a handheld mirror"), so it only counts as the
# Handheld Camera mode when the message is clearly about a video workflow.
_VIDEO_INTENT_WORDS = ("viral", "workflow", "mode", "moment", "template", "reel")
_GENERIC_VIRAL_CONTEXT = ("video", "reel", "moment", "workflow", "template", "clip", "short", "edit", "animate", "mode")


def _word_re(phrase: str) -> "re.Pattern[str]":
    return re.compile(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])", re.IGNORECASE)


def detect_viral_mode(message: str) -> Optional[str]:
    """Return the viral-director mode the Commander named, or None.

    Matches natural wording ("micro cinema", "time lapse", "handheld camera") as well as the
    snake_case ids. If several are named, the one mentioned first wins."""
    text = (message or "").lower()
    if not text:
        return None
    best: Optional[Tuple[int, str]] = None
    for mode, aliases in VIRAL_MODE_ALIASES.items():
        for alias in aliases:
            if alias == "handheld" and not any(w in text for w in _VIDEO_INTENT_WORDS):
                continue
            m = _word_re(alias).search(text)
            if m and (best is None or m.start() < best[0]):
                best = (m.start(), mode)
    return best[1] if best else None


def mentions_generic_viral(message: str) -> bool:
    """True for 'viral moment/reel/workflow' wording that doesn't pick one of the 5 modes."""
    text = (message or "").lower()
    return bool(_word_re("viral").search(text)) and any(w in text for w in _GENERIC_VIRAL_CONTEXT)


def parse_super_scale(message: str, default: int = 3) -> int:
    m = re.search(r"(?<![a-z0-9])([234])\s*x(?![a-z0-9])", (message or "").lower())
    return int(m.group(1)) if m else default


# ---------------------------------------------------------------------------------------------
# Motion / media intent (word-boundary safe)
# ---------------------------------------------------------------------------------------------

_MOTION_PHRASES = (
    "motion", "animate", "animation", "animating", "make it move", "make this move", "make this image move",
    "make the image move", "make the picture move", "give this image motion", "turn this image into video",
    "turn this into video", "turn this into a video", "make this into a video", "make this image into a video",
    "make a video", "make into video", "make into a video", "into a video", "into video", "image to video",
    "photo to video", "image-to-video", "photo-to-video", "i2v", "bring this photo to life",
    "bring this image to life", "video of this", "video test", "cinematic animation", "comfy_image_to_video",
    "zoom towards", "zoom toward", "camera zoom", "slow zoom", "camera movement", "move", "lick", "tongue",
)
_MOTION_RES = tuple(_word_re(p) for p in _MOTION_PHRASES)


def message_requests_motion(message: str) -> bool:
    """Word-boundary version of the old substring check.

    The old check did `"move" in msg` / `"lick" in msg`, so "remove the background" or
    "click the button" silently queued a video render."""
    text = (message or "").lower()
    return any(r.search(text) for r in _MOTION_RES)


_MEDIA_ACTION_PHRASES = (
    "svg", "stl", "glb", "3d model", "3d print", "stencil", "cricut", "vinyl cut", "upscale", "super scale",
    "retouch", "color grade", "convert to 3d", "make 3d",
)
_MEDIA_ACTION_RES = tuple(_word_re(p) for p in _MEDIA_ACTION_PHRASES)


def is_media_action_message(message: str) -> bool:
    """True when the message asks Synapse to DO something to media (animate, viral reel, SVG, STL...)."""
    text = (message or "").lower()
    if detect_viral_mode(text) or mentions_generic_viral(text) or message_requests_motion(text):
        return True
    return any(r.search(text) for r in _MEDIA_ACTION_RES)


# ---------------------------------------------------------------------------------------------
# Aspect-correct image-to-video resolution
# ---------------------------------------------------------------------------------------------

I2V_PIXEL_BUDGET = 720 * 1280      # the previous fixed size; keeps VRAM/render time the same
I2V_SIZE_MULTIPLE = 64             # LTX 2.3 template renders at half-res then 2x upscales


def pick_i2v_resolution(
    src_w: int,
    src_h: int,
    pixel_budget: int = I2V_PIXEL_BUDGET,
    multiple: int = I2V_SIZE_MULTIPLE,
    min_side: int = 512,
    max_side: int = 1536,
) -> Tuple[int, int]:
    """Pick (width, height) closest to the SOURCE aspect ratio within the same pixel budget.

    Previously every source was forced to 720x1280 (9:16): a 4:5 portrait lost its sides to a crop
    before a single frame rendered. Dimensions stay multiples of 64 (the template's requirement)."""
    if src_w <= 0 or src_h <= 0:
        return 704, 1280
    target = math.log(src_w / src_h)
    best: Optional[Tuple[float, float, int, int]] = None
    lo, hi = int(pixel_budget * 0.72), int(pixel_budget * 1.2)
    for w in range(min_side, max_side + 1, multiple):
        for h in range(min_side, max_side + 1, multiple):
            area = w * h
            if area < lo or area > hi:
                continue
            key = (abs(math.log(w / h) - target), abs(area - pixel_budget), w, h)
            if best is None or key < best:
                best = key
    return (best[2], best[3]) if best else (704, 1280)


# ---------------------------------------------------------------------------------------------
# Grounded image-to-video motion prompts
# ---------------------------------------------------------------------------------------------

# Words that describe a NEW place/scene. If the model's prompt contains one that is neither in the
# Commander's own message nor in what the vision model actually sees in the photo, the prompt is
# describing a different video than the photo - discard it.
SCENE_DRIFT_TERMS: Tuple[str, ...] = (
    "street", "streets", "city", "downtown", "skyline", "alley", "sidewalk", "pavement", "rain", "rainy",
    "rain-slicked", "neon", "night", "forest", "woods", "beach", "ocean", "sea", "mountain", "mountains",
    "desert", "highway", "road", "traffic", "crowd", "crowds", "pedestrians", "car", "cars", "train",
    "airport", "rooftop", "snow", "jungle", "river", "waterfall", "battlefield", "spaceship", "galaxy",
)
_DRIFT_RES = tuple((t, _word_re(t)) for t in SCENE_DRIFT_TERMS)


def find_scene_drift(prompt: str, allowed_text: str) -> List[str]:
    """Scene words in `prompt` that appear in neither the Commander's message nor the photo caption."""
    p = (prompt or "").lower()
    allowed = (allowed_text or "").lower()
    hits: List[str] = []
    for term, rx in _DRIFT_RES:
        if rx.search(p) and not rx.search(allowed):
            hits.append(term)
    return hits


_PREAMBLE_PATTERNS = (
    r"^(?:please\s+)?(?:can\s+you\s+)?(?:make|turn|convert|render)\s+(?:this\s+)?(?:image|photo|picture|pic)?\s*(?:in)?to\s+(?:a\s+)?video\s*(?:and\s+)?(?:please\s+)?",
    r"^(?:please\s+)?(?:animate|give\s+motion\s+to)\s+(?:this\s+)?(?:image|photo|picture)?\s*(?:and|where|with)?\s*",
    r"^(?:i\s+asked\s+it\s+to\s+)",
    r"^(?:generate|create|render)\s+(?:an?\s+)?(?:video|image|photo)\s+(?:of|where|with)\s*",
    r"^(?:have\s+her\s+|make\s+her\s+|have\s+him\s+|make\s+him\s+|make\s+the\s+person\s+|have\s+the\s+person\s+)",
)
_CAMERA_RE = re.compile(
    r"(?:,\s*|\s+and\s+)?(?:and\s+)?(?:have\s+the\s+camera|with\s+the\s+camera|the\s+camera|camera)\s+"
    r"(?P<adv>slowly\s+|gently\s+|smoothly\s+|quickly\s+)?"
    r"(?P<verb>zooms?|push(?:es)?[\s-]?in|pans?|tracks?|orbits?|dollies|dolly|pull(?:s)?[\s-]?back|tilts?)"
    r"(?P<rest>[^,.;]*)",
    re.IGNORECASE,
)
_CAMERA_VERBS = {
    "zoom": "zooms", "zooms": "zooms", "push in": "pushes in", "push-in": "pushes in", "pushes in": "pushes in",
    "pushin": "pushes in", "pan": "pans", "pans": "pans", "track": "tracks", "tracks": "tracks", "orbit": "orbits",
    "orbits": "orbits", "dolly": "dollies", "dollies": "dollies", "pull back": "pulls back", "pull-back": "pulls back",
    "pulls back": "pulls back", "tilt": "tilts", "tilts": "tilts",
}
ANCHOR_CLAUSE = (
    "Keep the exact same subject, outfit, setting and lighting as the first frame; one continuous single shot "
    "with no scene change, no cut and no new people or locations"
)


def extract_user_action(message: str) -> str:
    """The Commander's requested subject action with command boilerplate and camera wording removed."""
    action = (message or "").strip()
    for pat in _PREAMBLE_PATTERNS:
        action = re.sub(pat, "", action, flags=re.IGNORECASE).strip()
    action = _CAMERA_RE.sub("", action).strip()
    action = re.sub(r"\b(?:on|using|with)\s+this\s+(?:image|photo|picture)\b.*$", "", action, flags=re.IGNORECASE).strip()
    action = re.sub(r"^(?:and\s+|,\s*)+", "", action, flags=re.IGNORECASE).strip(" ,.;")
    return action


def extract_camera_move(message: str) -> str:
    """Natural-language camera sentence fragment from the Commander's wording, e.g.
    'slowly zoom towards her mouth' -> 'slowly zooms toward her mouth in a gradual, controlled move'."""
    m = _CAMERA_RE.search(message or "")
    if not m:
        return ""
    adverb = (m.group("adv") or "").strip().lower() or "smoothly"
    verb = re.sub(r"\s+", " ", m.group("verb").lower()).replace("pushin", "push in")
    verb = _CAMERA_VERBS.get(verb, verb)
    rest = re.sub(r"\btowards\b", "toward", (m.group("rest") or "").strip(), flags=re.IGNORECASE)
    fragment = f"{adverb} {verb}" + (f" {rest}" if rest else "")
    tail = " in a gradual, controlled move" + (", ending on a close-up of that area" if verb == "zooms" and rest else "")
    return fragment + tail


def _third_person(action: str, subject: str) -> str:
    action = action.strip()
    if not action:
        return ""
    words = action.split(None, 1)
    first, rest = words[0], (words[1] if len(words) > 1 else "")
    lower = first.lower()
    if lower.endswith("ing"):
        return f"{subject} is {first} {rest}".strip()
    if lower in ("is", "are", "was", "were", "has", "have") or lower.endswith("s"):
        return f"{subject} {action}"
    verb = first + ("es" if lower.endswith(("ch", "sh", "x", "z", "ss")) else "s")
    return f"{subject} {verb} {rest}".strip()


def _subject_pronoun(message: str) -> str:
    t = (message or "").lower()
    if _word_re("her").search(t) or _word_re("she").search(t):
        return "She"
    if _word_re("him").search(t) or _word_re("he").search(t) or _word_re("his").search(t):
        return "He"
    return "The subject"


def compose_motion_prompt(user_message: str) -> str:
    """A motion-only prompt built from the Commander's OWN words (no invented scene/lighting)."""
    camera = extract_camera_move(user_message)
    action = extract_user_action(user_message)
    subject = _subject_pronoun(user_message)
    parts: List[str] = []
    parts.append(f"The camera {camera}." if camera else "The camera holds a steady frame with a very slow, gentle push-in.")
    if action:
        parts.append(_third_person(action, subject).rstrip(".") + ", with natural breathing, subtle blinks and small organic movements.")
    else:
        parts.append(f"{subject} moves naturally with subtle breathing, soft blinks and small organic movements.")
    return " ".join(parts)


def build_grounded_i2v_prompt(
    user_message: str,
    llm_prompt: str,
    caption: str = "",
    min_llm_words: int = 12,
) -> Tuple[str, List[str]]:
    """Return (final_prompt, notes) for image-to-video.

    - Drops an LLM prompt that describes a different scene than the photo/the Commander's request.
    - Falls back to a motion prompt composed from the Commander's own words.
    - Always ends with the continuity anchor so frames after frame 0 stay faithful to the photo.
    """
    notes: List[str] = []
    base = (llm_prompt or "").strip()
    allowed = f"{user_message or ''} {caption or ''}"

    drift = find_scene_drift(base, allowed)
    if drift:
        notes.append(
            "Discarded the model's motion prompt: it described scene elements that are not in your photo or request ("
            + ", ".join(drift[:6]) + ") and would have replaced the photo with a different video."
        )
        base = ""
    if base and len(base.split()) < min_llm_words:
        notes.append("Model prompt was too short to trust; rebuilt it from your wording.")
        base = ""
    if not base:
        base = compose_motion_prompt(user_message or "")
        if "rebuilt" not in " ".join(notes) and not drift:
            notes.append("No usable model prompt; built one from your wording.")

    # An opener like "A close-up shot of..." tells the model the video STARTS tight, which the photo may not be.
    base = re.sub(r"^(?:an?\s+)?(?:extreme\s+)?close[- ]?up\s+(?:shot|view)\s+of\s+", "Starting from the photo's framing, ", base, flags=re.IGNORECASE)

    if ANCHOR_CLAUSE.lower()[:40] not in base.lower():
        base = base.rstrip(" .") + ". " + ANCHOR_CLAUSE + "."
    return base, notes


# ---------------------------------------------------------------------------------------------
# Prompt budgeting (Ollama truncates an oversized prompt to num_ctx/2+2 tokens)
# ---------------------------------------------------------------------------------------------

CHARS_PER_TOKEN = 3.5            # measured: 52K chars -> 13,944 tokens (3.7); 3.5 stays conservative
OUTPUT_RESERVE_TOKENS = 1800     # num_predict 1500 + headroom
SAFETY_MARGIN_TOKENS = 600


def estimate_tokens(text: str) -> int:
    return int(math.ceil(len(text or "") / CHARS_PER_TOKEN))


def knowledge_char_budget(
    window_tokens: int,
    fixed_chars: int,
    min_chars: int = 2500,
    max_chars: int = 16000,
) -> int:
    """How many characters of ComfyUI knowledge fit after everything else is accounted for.

    The dynamic arithmetic is the safety net (system prompt + history + user turn are subtracted from
    the window first); max_chars only mirrors comfyui_knowledge.MAX_CONTEXT_CHARS.
    Returns 0 when even the minimum slice cannot fit (caller should shrink history first)."""
    usable_tokens = window_tokens - OUTPUT_RESERVE_TOKENS - SAFETY_MARGIN_TOKENS
    remaining_chars = int(usable_tokens * CHARS_PER_TOKEN) - fixed_chars
    if remaining_chars < min_chars:
        return 0
    return min(remaining_chars, max_chars)
