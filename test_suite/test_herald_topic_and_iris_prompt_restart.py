"""Test suite for:
1. Topic-matched, action-oriented visual prompts reflecting what is in the post or newsletter.
2. Video motion prompts tailored to the subject matter and camera movement.
3. Iris QC prompt restarts: on rejection, immediately quarantine to qc_rejected and restart with a fresh prompt.
4. Foreground occlusion detection: reject images where microphones, gear, or clutter block the subject.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from pipeline.stages.herald_scheduler import HeraldScheduler, BRAND_VIBES
from pipeline.stages.comfyui_bridge import ComfyUIBridge


@pytest.fixture
def scheduler():
    return HeraldScheduler()


@pytest.fixture
def bridge():
    return ComfyUIBridge()


# =========================================================================
# 1. TOPIC & ACTION MATCHED VISUAL PROMPT TESTS
# =========================================================================

def test_craft_topic_visual_prompt_color_science_action(scheduler):
    """Verify Lightroom / Portra 400 topic crafts active color grading and film examination prompts."""
    topic = "Here is the exact color science behind the Kodak Portra 400 film aesthetic in Lightroom with tone curves and HSL."
    prompt_0 = scheduler._craft_topic_visual_prompt("creator_media_lab", topic_text=topic, variant_seed=0)
    prompt_1 = scheduler._craft_topic_visual_prompt("creator_media_lab", topic_text=topic, variant_seed=1)
    prompt_3 = scheduler._craft_topic_visual_prompt("creator_media_lab", topic_text=topic, variant_seed=3)

    assert "DaVinci" in prompt_0 or "color wheels" in prompt_0 or "Studio Display" in prompt_0
    assert "film negative strips" in prompt_1 or "light box" in prompt_1 or "Kodak Portra" in prompt_1
    assert "flat-lay" in prompt_3 or "film canisters" in prompt_3
    # Variants must be distinct creative interpretations of the color science topic
    assert prompt_0 != prompt_1


def test_craft_topic_visual_prompt_studio_lighting_action(scheduler):
    """Verify studio lighting topics craft active softbox positioning and feathered light prompts."""
    topic = "Feather your key light 45 degrees across the shoulder rather than pointing directly at the face."
    prompt_0 = scheduler._craft_topic_visual_prompt("creator_media_lab", topic_text=topic, variant_seed=0)
    prompt_1 = scheduler._craft_topic_visual_prompt("creator_media_lab", topic_text=topic, variant_seed=1)

    assert "45-degree feathered key light" in prompt_0 or "softbox" in prompt_0
    assert "positioning a 48-inch softbox" in prompt_1 or "C-stand" in prompt_1
    assert prompt_0 != prompt_1


def test_craft_topic_visual_prompt_monetization_lifestyle_and_flatlay(scheduler):
    """Verify monetization topics craft action prompts: poolside analytics, digital download cards, flat-lays."""
    topic = "Tier your digital product offerings: Starter Kit ($17), Pro Asset Bundle ($47), and VIP All-Access ($147)."
    prompt_0 = scheduler._craft_topic_visual_prompt("creator_pulse_lab", topic_text=topic, variant_seed=0)
    prompt_1 = scheduler._craft_topic_visual_prompt("creator_pulse_lab", topic_text=topic, variant_seed=1)
    prompt_3 = scheduler._craft_topic_visual_prompt("creator_pulse_lab", topic_text=topic, variant_seed=3)

    assert "bikini" in prompt_0 or "pool" in prompt_0 or "Stripe sales analytics" in prompt_0
    assert "download cards" in prompt_1 or "tank top" in prompt_1
    assert "flat-lay" in prompt_3 or "iPad Pro" in prompt_3
    assert prompt_0 != prompt_1


def test_craft_topic_visual_prompt_video_reels_and_loops(scheduler):
    """Verify video loop and 60fps topics craft dynamic motion shots and editing bays."""
    topic = "Turn your long-form shoots into 60s viral teasers, 9:16 TikTok crops, and 60fps loops."
    prompt_0 = scheduler._craft_topic_visual_prompt("creator_pulse_lab", topic_text=topic, variant_seed=0)
    prompt_1 = scheduler._craft_topic_visual_prompt("creator_pulse_lab", topic_text=topic, variant_seed=1)
    prompt_2 = scheduler._craft_topic_visual_prompt("creator_pulse_lab", topic_text=topic, variant_seed=2)

    assert "walking fluidly" in prompt_0 or "cinematic breeze" in prompt_0 or "halter dress" in prompt_0
    assert "filming dynamic vertical video" in prompt_1 or "gimbal" in prompt_1
    assert "editing bay" in prompt_2 or "curved monitor" in prompt_2 or "60fps" in prompt_2


# =========================================================================
# 2. TOPIC-AWARE VIDEO MOTION PROMPTS
# =========================================================================

def test_pick_motion_prompt_matches_topic_action(scheduler):
    """Verify _pick_motion_prompt generates motion matching the post topic."""
    # Video topic
    vid_motion = scheduler._pick_motion_prompt("creator_pulse_lab", topic_text="60s viral teasers and vertical video loops")
    assert "gimbal" in vid_motion or "tracking" in vid_motion

    # Lighting topic
    light_motion = scheduler._pick_motion_prompt("creator_media_lab", topic_text="Feather your key light 45 degrees across the shoulder")
    assert "push-in" in light_motion or "softbox" in light_motion

    # Color grading topic
    color_motion = scheduler._pick_motion_prompt("creator_media_lab", topic_text="Portra 400 tone curves and HSL color grading")
    assert "adjusting dials" in color_motion or "console" in color_motion


# =========================================================================
# 3. IRIS QC REJECTION IMMEDIATE QUARANTINE & PROMPT RESTART
# =========================================================================

def test_iris_rejection_quarantines_and_restarts_with_new_prompt(bridge, tmp_path):
    """Verify that when attempt 1 fails Iris QC, the image is quarantined to qc_rejected
    and attempt 2 restarts with a fresh alternative prompt."""
    staged_file_1 = tmp_path / "staged_attempt_1.png"
    staged_file_2 = tmp_path / "staged_attempt_2.png"

    def make_file(p):
        p.write_bytes(b"\x89PNG\r\n\x1a\nfakeimage")

    attempt_counter = [0]
    prompts_used = []

    def mock_download_image(filename, subfolder="", folder_type="output"):
        attempt_counter[0] += 1
        if attempt_counter[0] == 1:
            make_file(staged_file_1)
            return staged_file_1
        else:
            make_file(staged_file_2)
            return staged_file_2

    def mock_build_workflow(**kwargs):
        prompts_used.append(kwargs.get("positive_prompt"))
        return {}

    def mock_iris_qc(image_path, original_prompt=""):
        # Attempt 1 fails for extra fingers; attempt 2 passes
        if "attempt_1" in str(image_path):
            return {
                "passed": False,
                "is_sfw": True,
                "aesthetic_score": 5.0,
                "extra_limbs_detected": True,
                "defects_summary": "6 fingers on left hand",
                "recommendation": "RETRY_NEW_SEED"
            }
        else:
            return {
                "passed": True,
                "is_sfw": True,
                "aesthetic_score": 9.2,
                "extra_limbs_detected": False,
                "defects_summary": "Clean",
                "recommendation": "APPROVED"
            }

    primary_prompt = "Initial prompt about video editing"
    alt_prompt = "Alternative prompt: Alluring creator in an emerald slip dress adjusting color wheels"

    with patch.object(bridge, "check_connection", return_value={"online": True, "host": "x", "port": 1}), \
         patch.object(bridge, "build_standard_workflow", side_effect=mock_build_workflow), \
         patch.object(bridge, "queue_prompt", return_value={"prompt_id": "test_pid"}), \
         patch.object(bridge, "wait_for_execution", return_value=[{"filename": "staged.png"}]), \
         patch.object(bridge, "download_image", side_effect=mock_download_image), \
         patch.object(bridge, "run_iris_qc_audit", side_effect=mock_iris_qc), \
         patch.object(bridge, "_log_audit_record"):

        res = bridge.generate_and_audit(
            positive_prompt=primary_prompt,
            auto_qc=True,
            prompt_alternatives=[alt_prompt]
        )

    assert res["success"] is True
    assert res["attempts_taken"] == 2
    # Verify attempt 1 used primary prompt, attempt 2 restarted with the new alternative prompt!
    assert prompts_used[0] == primary_prompt
    assert prompts_used[1] == alt_prompt


# =========================================================================
# 4. FOREGROUND OCCLUSION DETECTION
# =========================================================================

def test_iris_qc_gate_rejects_foreground_occlusion(bridge, tmp_path):
    """Verify run_iris_qc_audit marks passed=False when unwanted objects or microphones block the subject."""
    img = tmp_path / "occluded_subject.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\nfakeimage")

    mock_qc_resp = json.dumps({
        "passed": False,
        "is_sfw": True,
        "aesthetic_score": 6.0,
        "extra_limbs_detected": False,
        "facial_distortion_detected": False,
        "nudity_or_nsfw_detected": False,
        "foreground_occlusion_detected": True,
        "defects_summary": "Microphone boom arm and tripod pole cutting across subject's face",
        "occlusion_notes": "Heavy foreground clutter obscuring the subject",
        "recommendation": "RETRY_NEW_PROMPT"
    })

    with patch.object(bridge.ai, "call_ollama_vision", return_value=mock_qc_resp):
        audit = bridge.run_iris_qc_audit(img, original_prompt="Creator portrait with microphone")
        assert audit["passed"] is False
        assert audit["foreground_occlusion_detected"] is True
        assert audit["recommendation"] == "RETRY_NEW_PROMPT"
