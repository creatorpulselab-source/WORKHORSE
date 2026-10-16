"""Unit test suite for Muse (PromptSynthesizer) specialized prompt engineering:
1. Architectural model grounding: FLUX, SDXL, WAN 2.1/2.2, LTX-Video, MiniMax H3, Trellis.2 / Pixal3D.
2. Dynamic aesthetic engine: Varied optics, lenses, lighting schemas, color profiles, compositions.
3. SFW vs. NSFW knowledge & channel gating: Automatic public sanitization, prompt safety audit, strict channel enforcement.
4. Pose variation series: 6 distinct compositional and anatomical variations.
"""
from unittest.mock import Mock, patch
import pytest

from pipeline.stages.prompt_synthesizer import (
    PromptSynthesizer,
    CINEMATIC_OPTICS,
    LIGHTING_SCHEMAS,
    COLOR_GRADING_PROFILES,
    COMPOSITION_STYLES,
    CAMERA_MOTIONS_VIDEO,
    PUBLIC_CHANNELS,
    STRICT_NSFW_KEYWORDS,
    SUGGESTIVE_ADULT_KEYWORDS,
)


@pytest.fixture
def muse():
    return PromptSynthesizer()


# =========================================================================
# 1. SFW VS. NSFW INTELLIGENCE & CHANNEL SAFETY
# =========================================================================

def test_muse_detects_clean_sfw_prompt(muse):
    """Clean editorial prompt must be recognized as 100% SFW."""
    prompt = "A high-fashion model in a tailored wool blazer standing in a sunlit architectural gallery."
    is_sfw, matched = muse.is_sfw_prompt(prompt)
    assert is_sfw is True
    assert matched == []


def test_muse_detects_strict_nsfw_prompt(muse):
    """Explicit nudity or adult tokens must be flagged immediately."""
    bad_prompts = [
        "A nude model posing topless with bare breasts on a bed",
        "Subject in erotic pose with visible nipples",
        "Explicit adult shoot with penetration and cumshot"
    ]
    for prompt in bad_prompts:
        is_sfw, matched = muse.is_sfw_prompt(prompt)
        assert is_sfw is False
        assert len(matched) > 0


def test_muse_detects_suggestive_boudoir_prompt(muse):
    """Boudoir and lingerie tokens must be flagged for safety auditing."""
    prompt = "Sensual boudoir portrait in black lace lingerie and sheer robe on a silk bed."
    is_sfw, matched = muse.is_sfw_prompt(prompt)
    assert is_sfw is False
    assert any(k in matched for k in ["boudoir", "lingerie", "sheer", "sensual"])


def test_muse_sanitizes_boudoir_scene_for_public_channels(muse):
    """Sanitizing an adult/boudoir scene turns it into an elegant, high-fashion SFW editorial description."""
    boudoir_scene = "Subject in sheer black lace lingerie reclining on a silk bed in a moody boudoir, provocative seductive pose with parted lips."
    sanitized = muse.sanitize_scene_for_public(boudoir_scene)

    is_sfw, matched = muse.is_sfw_prompt(sanitized)
    assert is_sfw is True, f"Sanitized text still contained adult tokens: {matched} in '{sanitized}'"
    assert "lingerie" not in sanitized.lower()
    assert "boudoir" not in sanitized.lower()
    assert "provocative" not in sanitized.lower()
    assert "seductive" not in sanitized.lower()
    assert "sheer" not in sanitized.lower()
    # High-fashion editorial elements substituted
    assert any(term in sanitized.lower() for term in ["tailored", "blazer", "loft", "architectural", "poised", "editorial", "gaze"])


def test_muse_safety_audit_rejects_nsfw_for_public_channels(muse):
    """Audit fails closed when an NSFW prompt is targeted at public channels like Pinterest or Twitter."""
    nsfw_prompt = "Boudoir shoot with model in seductive lingerie."
    for channel in ["pinterest", "twitter", "creatorpulselab", "thecreatorasset"]:
        audit = muse.audit_prompt_safety(nsfw_prompt, target_channel=channel)
        assert audit["passed"] is False
        assert audit["is_sfw"] is False
        assert audit["recommendation"] == "REJECT_NSFW_FOR_PUBLIC_CHANNEL"


def test_muse_safety_audit_approves_sfw_for_public_channels(muse):
    """Audit approves clean, professional prompts for public channels."""
    sfw_prompt = "Confident creative entrepreneur in tailored linen shirt, natural 50mm portrait in modern studio."
    audit = muse.audit_prompt_safety(sfw_prompt, target_channel="pinterest")
    assert audit["passed"] is True
    assert audit["is_sfw"] is True
    assert audit["recommendation"] == "APPROVED"


# =========================================================================
# 2. MODEL-SPECIFIC PROMPT SYNTHESIS
# =========================================================================

def test_muse_generates_flux_prompt_with_natural_prose_and_zero_negative(muse):
    """FLUX prompt must use descriptive prose, specific optics and lighting, and no negative prompt or buzzwords."""
    scene = "A product designer presenting a sleek ceramic vase."
    flux_prompt = muse.generate_flux_prompt(scene)
    assert isinstance(flux_prompt, str)
    assert len(flux_prompt) > 80
    assert "A masterfully composed medium shot photographed with" in flux_prompt
    assert "8k uhd, masterpiece" not in flux_prompt.lower()


def test_muse_generates_sdxl_prompt_with_weighted_tokens_and_negative(muse):
    """SDXL prompt must return both positive prompt with weights and mandatory artifact-suppressing negative."""
    scene = "A fashion model in an oversized trench coat."
    sdxl_result = muse.generate_sdxl_prompt(scene, content_type="general")
    assert isinstance(sdxl_result, dict)
    assert "positive" in sdxl_result
    assert "negative" in sdxl_result

    pos = sdxl_result["positive"]
    neg = sdxl_result["negative"]
    assert "(natural skin texture:1.2)" in pos
    assert "bad anatomy" in neg
    assert "blurry" in neg
    assert "nude" in neg  # SFW enforces nudity suppression in negative


def test_muse_generates_wan_video_prompt_with_4_part_kinetics(muse):
    """WAN video prompt must include camera motion, subject kinetics, environmental motion, and temporal progression."""
    scene = "Creative professional in modern workspace."
    wan_prompt = muse.generate_wan_video_prompt(scene)
    assert isinstance(wan_prompt, str)
    assert any(cam["camera_motion"] in wan_prompt for cam in CAMERA_MOTIONS_VIDEO)
    assert "gently adjusting their posture" in wan_prompt
    assert "Over the duration of the shot" in wan_prompt


def test_muse_generates_ltx_video_prompt_with_soundscape(muse):
    """LTX prompt must include motion velocity and acoustic soundscape cues."""
    scene = "Musician tuning an acoustic guitar in a loft."
    ltx_prompt = muse.generate_ltx_video_prompt(scene)
    assert "Audio Soundscape:" in ltx_prompt
    assert "tracking smoothly" in ltx_prompt


def test_muse_generates_minimax_modular_prompt(muse):
    """MiniMax prompt must follow the 4-part modular bracketed format or multishot."""
    scene = "Architect examining blueprints in sunlight."
    minimax_prompt = muse.generate_minimax_video_prompt(scene, multi_shot=False)
    assert "[Camera Movement]:" in minimax_prompt
    assert "[Subject Performance]:" in minimax_prompt
    assert "[Lighting & Environment]:" in minimax_prompt
    assert "[Audio Soundscape]:" in minimax_prompt


def test_muse_generates_trellis_3d_mesh_prompt(muse):
    """Trellis prompt must enforce solid white background invariant and orthographic perspective."""
    scene = "Designer sneakers on a turntable."
    trellis_prompt = muse.generate_trellis_3d_prompt(scene)
    assert "solid white background" in trellis_prompt.lower()
    assert "orthographic" in trellis_prompt.lower()
    assert "pbr mesh generation" in trellis_prompt.lower()


# =========================================================================
# 3. DYNAMIC AESTHETIC ENGINE & MONOTONY ELIMINATION
# =========================================================================

def test_muse_aesthetic_sampling_provides_diverse_parameters(muse):
    """Sampling aesthetic profiles across seeds yields varied lenses, lighting, and film color profiles."""
    prof1 = muse.sample_aesthetic_profile(seed=101)
    prof2 = muse.sample_aesthetic_profile(seed=999)

    assert "optics" in prof1
    assert "lighting" in prof1
    assert "color_grading" in prof1
    assert "composition" in prof1
    assert "video_camera_motion" in prof1

    # High probability of distinct combinations across different seeds
    assert (
        prof1["optics"]["name"] != prof2["optics"]["name"] or
        prof1["lighting"]["name"] != prof2["lighting"]["name"] or
        prof1["color_grading"]["name"] != prof2["color_grading"]["name"]
    )


def test_muse_get_aesthetic_variations_count(muse):
    """Returns 6 distinct aesthetic variations for series generation."""
    variations = muse.get_aesthetic_variations(6)
    assert len(variations) == 6
    lens_names = [v["optics"]["name"] for v in variations]
    assert len(set(lens_names)) >= 4


# =========================================================================
# 4. FULL PROMPT KIT INTEGRATION & BACKWARD COMPATIBILITY
# =========================================================================

def test_generate_prompt_kit_enforces_sfw_for_public_targets(muse):
    """When target_channel is a public channel, prompt kit strictly sanitizes boudoir input."""
    raw_boudoir = "Subject in revealing lace lingerie in boudoir bedroom."
    mock_responses = [
        "A high-fashion model wearing a tailored silk blazer in an architectural studio.",
        "Slow orbital tracking shot as the subject turns gracefully.",
        "\n".join(f"{i}. Variation {i}." for i in range(1, 7))
    ]
    with patch.object(muse.ai, "call_ollama_text", side_effect=mock_responses):
        kit = muse.generate_prompt_kit(
            scene_description=raw_boudoir,
            preset="Adult Creator Shoot",
            target_channel="pinterest"
        )

    assert kit["status"] == "ok"
    assert kit["content_type"] == "general"  # Forced general for pinterest
    assert kit["channel_safe"] is True
    assert "sdxl_image_prompt" in kit
    assert "ltx_video_prompt" in kit
    assert "minimax_video_prompt" in kit
    assert "trellis_3d_prompt" in kit
    assert len(kit["pose_series"]) == 6
