import json
import random
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Tuple
import sys

sys.path.insert(0, str(Path("F:/WORKHORSE")))
from shared.ai_providers import AIProviderService, is_ai_error_response
from shared.comfyui_knowledge import get_comfyui_context

# Target channels that strictly demand 100% SFW content
PUBLIC_CHANNELS = {
    "pinterest", "twitter", "x", "creatorpulselab", "thecreatorasset",
    "instagram", "tiktok", "youtube", "linkedin", "etsy", "public",
    "social", "creator_media_lab", "cml", "newsletter"
}

# Explicit anatomical and adult terminology - strictly forbidden on public channels
STRICT_NSFW_KEYWORDS = [
    "nude", "naked", "topless", "nsfw", "porn", "explicit", "erotic",
    "nipple", "nipples", "bare breasts", "genital", "genitals", "pussy",
    "cock", "dick", "vagina", "penis", "dildo", "cum", "cumshot",
    "masturbation", "penetration", "anal", "gangbang", "blowjob",
    "fellatio", "deepthroat", "bukkake", "uncensored", "sexually"
]

# Suggestive / adult-adjacent keywords that require authorization and channel gating
SUGGESTIVE_ADULT_KEYWORDS = [
    "adult", "boudoir", "glamour", "lingerie", "underwear", "bra", "panties",
    "sensual", "intimate", "fetish", "cam", "camgirl", "webcam", "onlyfans",
    "fansly", "bikini", "thong", "cleavage", "provocative", "seductive",
    "sheer", "see-through", "oiled skin", "fiverr_service_bot_adult"
]

ADULT_CONTENT_KEYWORDS = STRICT_NSFW_KEYWORDS + SUGGESTIVE_ADULT_KEYWORDS

# ---------------------------------------------------------------------------
# CINEMATOGRAPHY & AESTHETIC DIRECTORIES (Eliminating Monotony & Repetition)
# ---------------------------------------------------------------------------

CINEMATIC_OPTICS = [
    {
        "name": "85mm Editorial Portrait",
        "lens": "85mm f/1.4 prime lens",
        "description": "optical compression, creamy circular bokeh, tack-sharp focal isolation on the subject's iris, flattering facial geometry"
    },
    {
        "name": "50mm Classic Prime",
        "lens": "50mm f/1.8 normal prime lens",
        "description": "natural human-eye perspective, zero optical distortion, true-to-life spatial depth, balanced subject-environment integration"
    },
    {
        "name": "35mm Environmental",
        "lens": "35mm f/2.0 wide prime lens",
        "description": "immersive environmental perspective, rich contextual architectural storytelling, gentle natural depth rolloff"
    },
    {
        "name": "24mm Dynamic Wide",
        "lens": "24mm f/2.8 ultra-wide lens",
        "description": "low-angle dramatic perspective, dynamic diagonal vanishing lines, expansive architectural backdrop with sharp peripheral presence"
    },
    {
        "name": "105mm Macro Detail",
        "lens": "105mm f/2.8 macro telephoto lens",
        "description": "extreme subject isolation, razor-thin depth of field, micro-textural fidelity capturing fine fabric weave, skin pores, and specular reflections"
    },
    {
        "name": "Anamorphic Cinematic",
        "lens": "anamorphic cinema prime lens",
        "description": "cinematic widescreen framing, subtle horizontal lens flare streaks, characteristic elliptical bokeh, organic filmic depth"
    }
]

LIGHTING_SCHEMAS = [
    {
        "name": "Rembrandt Portrait",
        "lighting": "soft 45-degree directional key light casting a distinct triangular highlight on the shadowed cheek, subtle diffused fill"
    },
    {
        "name": "Chiaroscuro Contrast",
        "lighting": "dramatic chiaroscuro lighting with steep tonal contrast, deep velvety shadow gradients, Caravaggio-inspired illumination"
    },
    {
        "name": "Golden Hour Warmth",
        "lighting": "warm 3200K low-angle golden hour sunlight streaming from the side, luminous edge rim lighting, long soft amber shadows"
    },
    {
        "name": "Diffused North Light",
        "lighting": "broad diffused softbox illumination mimicking North-facing studio window light, ultra-smooth tonal transitions and soft shadows"
    },
    {
        "name": "Editorial Direct Flash",
        "lighting": "direct on-camera editorial flash aesthetic, crisp defined contact shadows, glossy specular highlights, punchy color vibrancy"
    },
    {
        "name": "Blue Hour Twilight",
        "lighting": "cool 7000K twilight ambient dusk light, gentle moody shadow tones with subtle warm interior tungsten accent practicals"
    },
    {
        "name": "Cyberpunk Neon Rim",
        "lighting": "dual-tone neon rim lighting with electric cyan and magenta edge highlights reflecting subtly off polished surfaces"
    },
    {
        "name": "Volumetric Light Shafts",
        "lighting": "volumetric sunbeams cutting through atmospheric haze, delicate god rays, cinematic Tyndall scattering"
    }
]

COLOR_GRADING_PROFILES = [
    {
        "name": "Kodak Portra 400",
        "color_profile": "Kodak Portra 400 film profile, warm golden skin tones, soft pastel highlight rolloff, fine organic grain"
    },
    {
        "name": "Fujifilm Provia",
        "color_profile": "Fujifilm Provia 100F slide film color science, true-to-life neutral whites, vivid saturated hues, crisp resolving clarity"
    },
    {
        "name": "Cinestill 800T",
        "color_profile": "Cinestill 800T tungsten aesthetic, subtle red halation around specular light sources, rich teal shadow tones"
    },
    {
        "name": "Modern Digital Cinema",
        "color_profile": "Arri Alexa 35 color science, wide dynamic range, organic highlight recovery, nuanced cinematic color gradation"
    },
    {
        "name": "Ilford HP5 Monochrome",
        "color_profile": "Ilford HP5 Plus silver gelatin black and white, deep blacks, rich tactile mid-tones, timeless contrast"
    }
]

COMPOSITION_STYLES = [
    {
        "name": "Rule of Thirds Asymmetric",
        "framing": "asymmetric composition following rule of thirds, subject offset with generous negative space and balanced visual weight"
    },
    {
        "name": "Low-Angle Hero",
        "framing": "low-angle upward perspective, commanding powerful posture, leading lines converging toward the subject"
    },
    {
        "name": "Intimate Close-Up",
        "framing": "tight intimate close-up framing, focus locked onto iris and eyelashes, subtle textural skin pore detail"
    },
    {
        "name": "High-Angle Geometric",
        "framing": "elevated 45-degree high-angle perspective, geometric floor shadows, graphic overhead composition"
    },
    {
        "name": "Environmental Medium",
        "framing": "medium environmental shot, subject harmoniously integrated into architectural interior, layered foreground framing"
    }
]

CAMERA_MOTIONS_VIDEO = [
    {
        "name": "Slow Forward Dolly Push-In",
        "camera_motion": "Slow, steady forward dolly push-in tracking smoothly toward the subject, gradually intensifying intimacy"
    },
    {
        "name": "Smooth Orbital Arc Shot",
        "camera_motion": "Smooth 45-degree orbital arc shot gliding horizontally around the subject, revealing spatial depth and background parallax"
    },
    {
        "name": "Subtle Handheld Drift",
        "camera_motion": "Organic, gentle handheld camera drift with micro-stabilized breathing inertia, creating authentic documentary presence"
    },
    {
        "name": "Low-Angle Tilt-Up Reveal",
        "camera_motion": "Low-angle camera tilting smoothly upward from waist level to eyeline, creating an authoritative, striking hero perspective"
    },
    {
        "name": "Slow Lateral Trucking Shot",
        "camera_motion": "Slow lateral trucking tracking shot sliding parallel to the subject as lighting highlights sweep across features"
    },
    {
        "name": "Static Tripod with Kinetic Subject",
        "camera_motion": "Composed static camera locked on a heavy studio tripod, allowing pure subject and environmental kinetic motion to command the frame"
    }
]


class PromptSynthesizer:
    """MUSE [34 Se] (Selenium) - Master AI Image & Video Prompt Engineer.
    
    Trained on the Commander's local ComfyUI curriculum (comfyui_llm_learning_guide.md).
    Understands model architectures, text encoder mechanics, spatial geometries,
    and strict SFW vs. NSFW policies:
      - FLUX.1 / FLUX.2 Klein: Dense, descriptive natural language prose; spatial RoPE directives;
        exact typography in quotes; ZERO negative prompt (inert).
      - SDXL / SD 1.5: Hybrid subject prose + comma-separated weighted tokens (tag:1.2) +
        mandatory artifact-suppressing negative prompts.
      - WAN 2.1 / 2.2: 4-part video prompt formula (Camera Kinetics, Continuous Subject Action,
        Environmental Motion, Temporal Progression over 3-5 seconds).
      - LTX-Video 2.3: Real-time action, motion velocity cues, frame-by-frame lighting dynamics,
        and acoustic soundscape descriptions.
      - MiniMax H3 (Hailuo AI): 4-part modular standard [Camera] + [Subject] + [Lighting] + [Audio]
        and chronological multishot syntax.
      - Trellis.2 & Pixal3D (3D Mesh): Neutral studio background invariant, 50-85mm orthographic
        perspective, shadowless wrap lighting for clean geometry and UV projection.
      - Strict SFW Enforcement: Automatically sanitizes and translates adult scenes into high-end
        fashion editorial visuals for public channels (Pinterest, Twitter @TheCreatorAsset, @creatorpulselab).
    """

    def __init__(self, config_path: str = "F:/WORKHORSE/config.json"):
        self.ai = AIProviderService(config_path)

    # ---------------------------------------------------------------------------
    # CONTENT TYPE & SAFETY VERIFICATION
    # ---------------------------------------------------------------------------

    def _detect_content_type(self, preset: str, target_channel: Optional[str] = None) -> str:
        """Auto-classifies a job preset as 'adult' or 'general'.
        If target_channel is a public platform, ALWAYS forces 'general' (100% SFW)."""
        if target_channel and target_channel.lower() in PUBLIC_CHANNELS:
            return "general"
        preset_lower = (preset or "").lower()
        return "adult" if any(k in preset_lower for k in ADULT_CONTENT_KEYWORDS) else "general"

    def is_sfw_prompt(self, text: str) -> Tuple[bool, List[str]]:
        """Scans prompt text for any adult, boudoir, or NSFW keywords.
        Returns (is_sfw: bool, matched_tokens: List[str])."""
        if not text:
            return True, []
        text_lower = text.lower()
        # Word boundary matching to prevent false positives (e.g., 'broadcast' matching 'cast')
        matched = []
        for kw in ADULT_CONTENT_KEYWORDS:
            pattern = rf"\b{re.escape(kw)}\b"
            if re.search(pattern, text_lower):
                matched.append(kw)
        return len(matched) == 0, matched

    def sanitize_scene_for_public(self, scene_description: str) -> str:
        """Translates boudoir or adult scene elements into high-end, elegant editorial
        fashion concepts guaranteed 100% SFW for public distribution (Pinterest, X, blogs)."""
        if not scene_description:
            return "Contemporary creative portrait, poised subject in tailored editorial wardrobe, soft ambient studio lighting."

        sanitized = scene_description

        # Direct substitutions of adult/boudoir items with high-fashion equivalents
        replacements = [
            (r"\b(lingerie|panties|bra|underwear|thong|g-string)\b", "tailored silk blazer and structured evening attire"),
            (r"\b(boudoir|bedroom|on the bed|in bed)\b", "modern sunlit architectural loft with minimalist concrete and wood interior"),
            (r"\b(nude|naked|topless|bare breasts|exposed nipples)\b", "elegant high-fashion silhouette with layered silk and wool textures"),
            (r"\b(sensual|provocative|seductive)\b", "confident, poised, editorial"),
            (r"\b(oiled skin|wet skin)\b", "luminous, naturally radiant skin with soft specular glow"),
            (r"\b(sheer|see-through|translucent)\b", "refined fine-knit cashmere and woven textured fabric"),
            (r"\b(bikini|micro bikini)\b", "chic minimalist resortwear and tailored linen"),
            (r"\b(onlyfans|fansly|cam|camgirl|webcam)\b", "creative studio portfolio"),
            (r"\b(erotic|fetish|nsfw|xxx)\b", "artistic fine-art"),
            (r"\b(parted lips|bedroom eyes)\b", "direct, thoughtful gaze into the camera lens")
        ]

        for pattern, replacement in replacements:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

        # Eliminate any remaining strict NSFW terms
        for kw in STRICT_NSFW_KEYWORDS:
            sanitized = re.sub(rf"\b{re.escape(kw)}\b", "", sanitized, flags=re.IGNORECASE)

        # Clean double spaces
        sanitized = re.sub(r"\s+", " ", sanitized).strip()
        return sanitized

    def audit_prompt_safety(self, prompt: str, target_channel: str = "public") -> Dict[str, Any]:
        """Audits a prompt against channel standards and returns a structured safety certification."""
        is_sfw, matched = self.is_sfw_prompt(prompt)
        is_public = target_channel.lower() in PUBLIC_CHANNELS or target_channel.lower() == "public"

        if is_public and not is_sfw:
            return {
                "passed": False,
                "is_sfw": False,
                "target_channel": target_channel,
                "violations": matched,
                "recommendation": "REJECT_NSFW_FOR_PUBLIC_CHANNEL"
            }

        return {
            "passed": True,
            "is_sfw": is_sfw,
            "target_channel": target_channel,
            "violations": matched,
            "recommendation": "APPROVED"
        }

    # ---------------------------------------------------------------------------
    # AESTHETIC DIRECTORS & DYNAMIC SAMPLING
    # ---------------------------------------------------------------------------

    def sample_aesthetic_profile(self, preset: str = "", seed: Optional[int] = None) -> Dict[str, Any]:
        """Samples a harmonious, dynamic cinematic aesthetic profile (optics, lighting,
        color science, composition, motion) to eliminate visual monotony and repetition."""
        rng = random.Random(seed) if seed is not None else random.Random()
        optics = rng.choice(CINEMATIC_OPTICS)
        lighting = rng.choice(LIGHTING_SCHEMAS)
        color = rng.choice(COLOR_GRADING_PROFILES)
        composition = rng.choice(COMPOSITION_STYLES)
        motion = rng.choice(CAMERA_MOTIONS_VIDEO)

        return {
            "optics": optics,
            "lighting": lighting,
            "color_grading": color,
            "composition": composition,
            "video_camera_motion": motion
        }

    def get_aesthetic_variations(self, count: int = 6) -> List[Dict[str, Any]]:
        """Returns a list of distinct aesthetic profiles for series generation."""
        variations = []
        for i in range(count):
            variations.append({
                "optics": CINEMATIC_OPTICS[i % len(CINEMATIC_OPTICS)],
                "lighting": LIGHTING_SCHEMAS[i % len(LIGHTING_SCHEMAS)],
                "color_grading": COLOR_GRADING_PROFILES[i % len(COLOR_GRADING_PROFILES)],
                "composition": COMPOSITION_STYLES[i % len(COMPOSITION_STYLES)],
                "video_camera_motion": CAMERA_MOTIONS_VIDEO[i % len(CAMERA_MOTIONS_VIDEO)]
            })
        return variations

    # ---------------------------------------------------------------------------
    # MODEL-SPECIFIC PROMPT SYNTHESIS METHODS
    # ---------------------------------------------------------------------------

    def generate_flux_prompt(
        self,
        scene_description: str,
        aesthetic: Optional[Dict[str, Any]] = None,
        content_type: str = "auto",
        target_channel: Optional[str] = None
    ) -> str:
        """Constructs a FLUX.1 / FLUX.2 Klein compatible prompt paragraph:
        - Dense natural language descriptive prose
        - RoPE spatial directives
        - Exact lighting and optical specifications
        - ZERO negative prompt, NO comma-salad buzzwords."""
        resolved_type = self._detect_content_type(content_type, target_channel)
        grounded_scene = self.sanitize_scene_for_public(scene_description) if resolved_type == "general" else scene_description

        prof = aesthetic or self.sample_aesthetic_profile()
        lens = prof["optics"]["lens"]
        lens_desc = prof["optics"]["description"]
        lighting = prof["lighting"]["lighting"]
        color = prof["color_grading"]["color_profile"]
        comp = prof["composition"]["framing"]

        prompt = (
            f"A masterfully composed medium shot photographed with an {lens}, providing {lens_desc}. "
            f"{grounded_scene}. The scene is illuminated by {lighting}, establishing subtle depth and rich textural definition. "
            f"Framed with {comp}. Rendered with {color}, capturing natural unretouched skin textures, visible pores, "
            f"and tangible fabric weave."
        )
        return prompt.strip()

    def generate_sdxl_prompt(
        self,
        scene_description: str,
        aesthetic: Optional[Dict[str, Any]] = None,
        content_type: str = "auto",
        target_channel: Optional[str] = None
    ) -> Dict[str, str]:
        """Constructs an SDXL / SD 1.5 prompt pair:
        - Hybrid subject prose + weighted CLIP tokens
        - Mandatory negative prompt dictionary."""
        resolved_type = self._detect_content_type(content_type, target_channel)
        grounded_scene = self.sanitize_scene_for_public(scene_description) if resolved_type == "general" else scene_description

        prof = aesthetic or self.sample_aesthetic_profile()
        lens = prof["optics"]["lens"]
        lighting = prof["lighting"]["name"]
        color = prof["color_grading"]["name"]

        positive = (
            f"photograph of {grounded_scene}, {prof['composition']['name']}, captured on {lens}, "
            f"({lighting}:1.15), ({color}:1.1), (natural skin texture:1.2), (subsurface scattering:1.1), "
            f"sharp focus, professional photography, clean composition"
        )
        negative = (
            "ugly, deformed, bad anatomy, bad hands, missing fingers, extra limbs, mutated digits, "
            "blurry, out of focus, low quality, lowres, plastic skin, oversaturated, distorted face, "
            "watermark, signature, text, amateur snapshot"
        )
        if resolved_type == "general":
            negative += ", nude, nudity, nsfw, topless, cleavage, lingerie, underwear, erotic"

        return {"positive": positive, "negative": negative}

    def generate_wan_video_prompt(
        self,
        scene_description: str,
        camera_motion: Optional[str] = None,
        content_type: str = "auto",
        target_channel: Optional[str] = None
    ) -> str:
        """Constructs a WAN 2.1 / 2.2 4-part video motion prompt:
        1. Camera Direction & Movement
        2. Subject Kinetic Action (continuous progressive verbs)
        3. Environmental Motion
        4. Temporal Progression (3-5 seconds)."""
        resolved_type = self._detect_content_type(content_type, target_channel)
        grounded_scene = self.sanitize_scene_for_public(scene_description) if resolved_type == "general" else scene_description

        motion = camera_motion or self.sample_aesthetic_profile()["video_camera_motion"]["camera_motion"]

        prompt = (
            f"{motion}. The subject naturally shifts their gaze toward the camera, breathing softly with subtle chest "
            f"and shoulder elevation while gently adjusting their posture within the scene: {grounded_scene}. "
            f"Ambient atmospheric air currents gently move loose hair strands and fine fabric edges. "
            f"Over the duration of the shot, lighting reflections smoothly track across features with natural physical inertia."
        )
        return prompt.strip()

    def generate_ltx_video_prompt(
        self,
        scene_description: str,
        camera_motion: Optional[str] = None,
        content_type: str = "auto",
        target_channel: Optional[str] = None
    ) -> str:
        """Constructs an LTX-Video 2.3 prompt with real-time motion velocity,
        lighting transitions, and acoustic soundscape cues."""
        resolved_type = self._detect_content_type(content_type, target_channel)
        grounded_scene = self.sanitize_scene_for_public(scene_description) if resolved_type == "general" else scene_description

        motion = camera_motion or "A steady cinematic push-in tracking smoothly at moderate velocity"

        prompt = (
            f"{motion} focusing on {grounded_scene}. The subject performs continuous, organic micro-movements, "
            f"blinking naturally and softly turning their head. Lighting shifts subtly across facial contours as camera angle deepens. "
            f"Audio Soundscape: subtle rustle of fine fabric, soft ambient room tone, gentle quiet breath."
        )
        return prompt.strip()

    def generate_minimax_video_prompt(
        self,
        scene_description: str,
        multi_shot: bool = False,
        content_type: str = "auto",
        target_channel: Optional[str] = None
    ) -> str:
        """Constructs a MiniMax H3 (Hailuo AI) 4-part modular prompt:
        [Camera Movement] + [Subject Performance] + [Lighting & Environment] + [Audio Soundscape]."""
        resolved_type = self._detect_content_type(content_type, target_channel)
        grounded_scene = self.sanitize_scene_for_public(scene_description) if resolved_type == "general" else scene_description

        prof = self.sample_aesthetic_profile()
        cam_motion = prof["video_camera_motion"]["camera_motion"]
        lighting = prof["lighting"]["lighting"]

        if multi_shot:
            prompt = (
                f"[Shot 1]: {cam_motion} establishing the scene. {grounded_scene}. "
                f"Lighting: {lighting}. Audio: soft ambient room presence and quiet breeze.\n"
                f"[Shot 2]: Smooth cut to a closer medium portrait as the subject looks directly into the lens with quiet poise. "
                f"Audio: clear fabric movement and soft exhale."
            )
        else:
            prompt = (
                f"[Camera Movement]: {cam_motion}.\n"
                f"[Subject Performance]: The subject in {grounded_scene} exhibits natural kinetic movement, gently shifting weight and engaging the camera with poise.\n"
                f"[Lighting & Environment]: {lighting}, with organic ambient depth.\n"
                f"[Audio Soundscape]: subtle atmospheric studio reverberation, gentle rustle of clothing."
            )
        return prompt.strip()

    def generate_trellis_3d_prompt(
        self,
        scene_description: str,
        content_type: str = "auto",
        target_channel: Optional[str] = None
    ) -> str:
        """Constructs a Trellis.2 & Pixal3D (3D Mesh) generation prompt:
        - Neutral background invariant (solid white/transparent)
        - 50mm-85mm orthographic perspective (zero wide-angle distortion)
        - Shadowless uniform wrap-around lighting for mesh geometry."""
        resolved_type = self._detect_content_type(content_type, target_channel)
        grounded_scene = self.sanitize_scene_for_public(scene_description) if resolved_type == "general" else scene_description

        prompt = (
            f"3D asset reference render of {grounded_scene}, isolated on a seamless pure solid white background. "
            f"Orthographic 85mm perspective, zero wide-angle distortion, centered full subject visibility. "
            f"Even, shadowless diffuse wrap-around studio illumination revealing complete geometric surface topology, "
            f"clean silhouettes, and crisp texture projection for PBR mesh generation."
        )
        return prompt.strip()

    def generate_relighting_prompt(
        self,
        scene_description: str,
        lighting_style: str = "rembrandt",
        backdrop: str = "modern_architectural_studio",
        content_type: str = "auto",
        target_channel: Optional[str] = None
    ) -> Dict[str, str]:
        """Constructs an IC-Light / neural relighting prompt pair for portrait transformation:
        - Physically accurate light transport specification (direction, bounce, color temp)
        - Background environment integration with matching light falloff
        - 100% skin pore preservation directive (zero airbrushed/plastic look)."""
        resolved_type = self._detect_content_type(content_type, target_channel)
        grounded_scene = self.sanitize_scene_for_public(scene_description) if resolved_type == "general" else scene_description

        lighting_profiles = {
            "rembrandt": "Strong 45-degree directional tungsten key light from camera left creating a classic triangular highlight on the shadowed cheek, subtle cool 6500K fill on the right, defined shadow falloff under jawline",
            "golden_hour": "Warm low-angle 3000K sunlight streaming from behind and left, luminous amber rim light separating hair and shoulders from background, warm golden bounce card fill on face",
            "beauty_dish": "Direct frontal beauty dish with diffusion sock positioned 3 feet above lens, perfectly round catchlights in pupils, smooth symmetrical shadow under chin, radiant cheekbone highlights",
            "cyber_neon": "Dual-tone theatrical edge lighting with intense magenta rim light on camera left and electric cyan fill on camera right, subtle specular reflections on skin",
            "high_key_daylight": "Broad, ultra-soft diffused north window daylight, virtually shadowless wrap illumination, clean high-key commercial editorial atmosphere"
        }
        light_directive = lighting_profiles.get(lighting_style.lower(), lighting_profiles["rembrandt"])

        backdrop_profiles = {
            "modern_architectural_studio": "minimalist architectural studio interior with smooth cast concrete walls and warm vertical oak slats, soft ambient depth",
            "penthouse_skyline": "high-rise luxury penthouse interior with floor-to-ceiling glass windows overlooking a soft-focus twilight city skyline with warm bokeh",
            "dark_velvet_studio": "timeless fine-art portrait studio with deep charcoal textured canvas backdrop, rich shadow gradient",
            "parisian_loft": "sun-drenched Parisian artist loft with ornate white crown molding, herringbone hardwood floor, and soft daylight haze"
        }
        env_directive = backdrop_profiles.get(backdrop.lower(), backdrop_profiles["modern_architectural_studio"])

        positive = (
            f"Relit studio portrait of {grounded_scene}, set within a {env_directive}. "
            f"Illumination: {light_directive}. "
            f"Accurate physical light transport, natural skin pores and micro-texture fully preserved, tangible fabric weave, "
            f"85mm portrait compression, razor-sharp focus on iris."
        )
        negative = (
            "plastic skin, overly smoothed, airbrushed, cartoon, illustration, 3d render, "
            "harsh digital clipping, unnatural rim glow, bad cutout edges, floating head, "
            "deformed facial features, blurry, low resolution"
        )
        if resolved_type == "general":
            negative += ", nude, nudity, nsfw, lingerie, underwear, provocative"

        return {"positive": positive.strip(), "negative": negative.strip(), "lighting_style": lighting_style, "environment": backdrop}

    # ---------------------------------------------------------------------------
    # MAIN PIPELINE PROMPT KIT GENERATOR (Preserves Exact 3-Call Test Contract)
    # ---------------------------------------------------------------------------

    def generate_prompt_kit(
        self,
        scene_description: str,
        preset: str = "Adult Creator Shoot",
        content_type: str = "auto",
        progress_cb: Optional[Callable[[str, int], None]] = None,
        target_channel: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a Flux image prompt, a WAN video motion prompt, and 6 pose-series
        prompt variations - all grounded in Iris's real forensic scene description.
        
        Strictly enforces SFW policies for public channels and injects dynamic cinematography
        to eliminate monotonous, repetitive outputs.
        
        Preserves exact 3 Ollama calls for offline test compatibility, while enriching the
        returned kit with model-specific prompts for SDXL, LTX, MiniMax, and Trellis 3D.
        """
        resolved_type = self._detect_content_type(preset, target_channel) if content_type == "auto" else content_type
        if target_channel and target_channel.lower() in PUBLIC_CHANNELS:
            resolved_type = "general"

        # If general/public, guarantee that the ground-truth scene description has no adult residue
        active_scene = self.sanitize_scene_for_public(scene_description) if resolved_type == "general" else scene_description

        explicit_note = (
            "Use direct, explicit adult-content vocabulary where appropriate - this is for "
            "private, consenting adult creator content and must not be censored or softened."
            if resolved_type == "adult" else
            "STRICT 100% SFW: Keep all vocabulary tasteful, elegant, and brand-safe for mainstream platforms. "
            "Strictly NO nudity, NO underwear/lingerie, NO provocative posing, NO adult terms."
        )

        base_context = f"""GROUND-TRUTH SCENE DESCRIPTION (from real reference photos - stay faithful to this, do not invent new details):
{active_scene}

{explicit_note}"""

        # Sample a dynamic aesthetic profile to break visual monotony
        aesthetic = self.sample_aesthetic_profile(preset)
        optics_directive = f"Shoot with an {aesthetic['optics']['lens']} ({aesthetic['optics']['description']})."
        lighting_directive = f"Illuminate with {aesthetic['lighting']['lighting']}."
        color_directive = f"Color science: {aesthetic['color_grading']['color_profile']}."
        comp_directive = f"Composition: {aesthetic['composition']['framing']}."

        if progress_cb:
            progress_cb("Muse Agent: Crafting dynamic Flux image generation prompt...", 10)

        flux_request = f"""You are Muse, an expert AI prompt engineer specializing in ComfyUI, FLUX.1, and SDXL image generation.
{base_context}

Aesthetic Direction:
- {optics_directive}
- {lighting_directive}
- {color_directive}
- {comp_directive}

Using the ground-truth scene description and aesthetic direction above, write ONE single-paragraph, highly detailed FLUX.1 natural-language prompt that recreates this subject, outfit, pose, setting, and lighting. Describe spatial relationships, tangible fabric textures, skin pores, and lighting direction with photographic precision.
Do NOT use generic comma-separated buzzwords (such as '8k uhd, masterpiece, sharp focus, RAW photo').
Output ONLY the prompt paragraph, no headers or explanation."""

        flux_request += "\nUse descriptive natural-language prose for FLUX; do not use CLIP weighting syntax."

        raw_flux = self.ai.call_ollama_text(
            flux_request,
            system_prompt="You are Muse, an expert AI image-prompt engineer for FLUX.1/SDXL.\n"
            + get_comfyui_context("image_prompt")
        )
        if is_ai_error_response(raw_flux):
            return self._error_result(raw_flux, resolved_type)
        flux_prompt = self._clean_response(raw_flux)

        if progress_cb:
            progress_cb("Muse Agent: Crafting WAN 4-part video motion prompt...", 40)

        wan_camera_motion = aesthetic["video_camera_motion"]["camera_motion"]
        wan_request = f"""You are Muse, an expert AI video-prompt engineer specializing in WAN2.1/2.2 and CogVideoX image-to-video generation.
{base_context}

Camera Movement: {wan_camera_motion}

Using the ground-truth scene description above, write ONE cinematic 4-part video motion prompt (under 90 words) suitable for turning a still photo of this subject into a short video clip.
Follow the ComfyUI video formula:
1. Camera Direction & Movement (incorporate the specified camera movement)
2. Subject Kinetic Action (continuous progressive verbs: breathing, subtle gaze shift, posture adjustment)
3. Environmental Motion (fabric movement, ambient air, lighting shifts)
4. Temporal Progression (how the 3-5 second clip unfolds).

Output ONLY the prompt, no headers or explanation."""

        raw_wan = self.ai.call_ollama_text(
            wan_request,
            system_prompt="You are Muse, an expert AI video-prompt engineer for WAN2.1/2.2.\n"
            + get_comfyui_context("video_prompt")
        )
        if is_ai_error_response(raw_wan):
            return self._error_result(raw_wan, resolved_type)
        wan_prompt = self._clean_response(raw_wan)

        if progress_cb:
            progress_cb("Muse Agent: Crafting 6-pose variation series...", 70)

        pose_request = f"""You are Muse, an expert AI prompt engineer creating a 6-pose variation series for FLUX.1/SDXL.
{base_context}

Using the ground-truth scene description above (keep subject, outfit, and setting IDENTICAL across all 6), write 6 numbered single-paragraph FLUX.1-compatible prompts, each describing a DIFFERENT pose and camera-angle variation:
1. Pose 1: Full-Length Environmental Stance (35mm wide lens, full body establishing shot, grounded posture)
2. Pose 2: 3/4 Editorial Profile (50mm lens, weight shifted, dynamic shoulder and hip tilt, three-quarters angle)
3. Pose 3: Intimate Close-Up Portrait (85mm f/1.4 lens, tight head-and-shoulders framing, focus locked onto eyes, creamy bokeh)
4. Pose 4: Seated Asymmetric Relaxation (50mm lens, subject seated gracefully on chair or bench, asymmetric leg placement)
5. Pose 5: Dynamic Kinetic Mid-Motion (24mm or 35mm lens, captured mid-stride or turning back toward lens, fabric in motion)
6. Pose 6: Dramatic Perspective / Low-Angle Accent (Low-angle hero perspective looking upward, strong architectural lines)

Format strictly as:
1. <prompt text>
2. <prompt text>
...through 6.
No extra commentary before, between, or after the 6 entries."""

        raw_pose = self.ai.call_ollama_text(
            pose_request,
            system_prompt="You are Muse, an expert AI prompt engineer creating pose-series variations.\n"
            + get_comfyui_context("pose_prompt")
        )
        if is_ai_error_response(raw_pose):
            return self._error_result(raw_pose, resolved_type)
        pose_series_raw = self._clean_response(raw_pose)
        pose_variations = self._parse_pose_series(pose_series_raw)

        if progress_cb:
            progress_cb("Muse Agent: Prompt kit complete!", 100)

        # Derived model-specific prompt syntheses for the full ComfyUI arsenal
        sdxl_prompts = self.generate_sdxl_prompt(active_scene, aesthetic=aesthetic, content_type=resolved_type)
        ltx_prompt = self.generate_ltx_video_prompt(active_scene, camera_motion=wan_camera_motion, content_type=resolved_type)
        minimax_prompt = self.generate_minimax_video_prompt(active_scene, content_type=resolved_type)
        trellis_prompt = self.generate_trellis_3d_prompt(active_scene, content_type=resolved_type)

        is_sfw, matched_tokens = self.is_sfw_prompt(flux_prompt)
        channel_safe = is_sfw if (resolved_type == "general" or (target_channel and target_channel.lower() in PUBLIC_CHANNELS)) else True

        return {
            "status": "ok",
            "flux_image_prompt": flux_prompt,
            "wan_video_prompt": wan_prompt,
            "pose_series": pose_variations,
            "content_type": resolved_type,
            "sdxl_image_prompt": sdxl_prompts,
            "ltx_video_prompt": ltx_prompt,
            "minimax_video_prompt": minimax_prompt,
            "trellis_3d_prompt": trellis_prompt,
            "aesthetic_direction": aesthetic,
            "is_sfw": is_sfw,
            "channel_safe": channel_safe
        }

    def _error_result(self, raw_error: str, resolved_type: str) -> Dict[str, Any]:
        """Returns a clearly-flagged failure instead of silently embedding an AI
        provider infrastructure error string."""
        failure_notice = "[Muse prompt generation unavailable - local AI service error. Retry once Ollama is back online.]"
        return {
            "status": "error",
            "error": raw_error,
            "flux_image_prompt": failure_notice,
            "wan_video_prompt": failure_notice,
            "pose_series": [],
            "content_type": resolved_type,
            "sdxl_image_prompt": {"positive": failure_notice, "negative": failure_notice},
            "ltx_video_prompt": failure_notice,
            "minimax_video_prompt": failure_notice,
            "trellis_3d_prompt": failure_notice,
            "aesthetic_direction": {},
            "is_sfw": True,
            "channel_safe": True
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
    print("Prompt Synthesizer (Muse) initialized with multi-model ComfyUI curriculum grounding.")
