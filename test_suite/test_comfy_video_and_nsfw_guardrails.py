"""Regression test suite for:
1. ComfyUI Image-to-Video tool aliases & uploaded image resolution in Synapse chat.
2. Media card attachment and chat history persistence for rendered video outputs.
3. Strict NSFW & anti-nudity guardrails: Herald & Content Engine cannot produce or post nude images/videos;
   only the Commander can authorize NSFW generation.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from pipeline.stages.ai_operator import AIOperatorEngine, CLIENT_INBOX_DIR
from pipeline.stages.herald_scheduler import BRAND_VIBES, HeraldScheduler
from pipeline.stages.content_engine import NEGATIVE_PROMPT as CE_NEGATIVE_PROMPT


@pytest.fixture
def operator_engine():
    return AIOperatorEngine()


# =========================================================================
# 1. TOOL ALIASES & SOURCE IMAGE RESOLUTION
# =========================================================================

def test_tool_alias_comfy_generate_video_maps_to_comfy_image_to_video(operator_engine):
    """Verify tool alias 'comfy_generate_video' and 'image_to_video' map to comfy_image_to_video."""
    tool_call = {
        "tool": "comfy_generate_video",
        "image": "test.jpg",
        "prompt": "slow pan down",
    }
    with patch.object(operator_engine, "_resolve_marketing_source_image", return_value=Path("non_existent.jpg")):
        result = operator_engine.execute_internal_tool(tool_call)
        assert result["status"] == "error"
        assert "Source image not found" in result["error"]
        assert result.get("tool") == "comfy_image_to_video"


def test_resolve_marketing_source_image_resolves_placeholder_to_attached_file(tmp_path, operator_engine):
    """When Synapse passes '...' or empty as the image, it must resolve to the user's attached file."""
    uploaded_file = tmp_path / "user_uploaded_portrait.jpg"
    uploaded_file.write_bytes(b"image-bytes")

    resolved = operator_engine._resolve_marketing_source_image(
        "...",
        attached_files=[str(uploaded_file)]
    )
    assert resolved == uploaded_file
    assert resolved.exists()


def test_resolve_marketing_source_image_resolves_bare_name_in_batch_dir(tmp_path, operator_engine):
    """When a bare filename matching a file in the user's batch_dir is passed, it resolves to batch_dir."""
    batch_dir = tmp_path / "batch_12345"
    batch_dir.mkdir()
    target_img = batch_dir / "JT2A6418_teaser_preview.jpg"
    target_img.write_bytes(b"preview-bytes")

    resolved = operator_engine._resolve_marketing_source_image(
        "JT2A6418_teaser_preview.jpg",
        batch_dir=batch_dir
    )
    assert resolved == target_img
    assert resolved.exists()


def test_comfy_image_to_video_attaches_media_card(tmp_path, operator_engine):
    """Verify successful video generation populates result['video'] and result['media'] with valid preview and download URLs."""
    source_img = tmp_path / "source.jpg"
    source_img.write_bytes(b"source-img")

    video_dest = Path("F:/WORKHORSE/workspace/brand_assets/comfy_video_renders/test_video_123.mp4")
    video_dest.parent.mkdir(parents=True, exist_ok=True)
    video_dest.write_bytes(b"video-bytes")

    try:
        with patch("pipeline.stages.comfyui_bridge.comfy_bridge.generate_image_to_video") as mock_gen:
            mock_gen.return_value = {
                "success": True,
                "file_path": str(video_dest),
                "filename": video_dest.name,
                "url_path": f"/static/brand_assets/comfy_video_renders/{video_dest.name}"
            }
            res = operator_engine.execute_internal_tool({
                "tool": "comfy_image_to_video",
                "image": str(source_img),
                "prompt": "slow pan"
            })

            assert res["status"] == "ok"
            assert res.get("video") == str(video_dest)
            assert "media" in res
            assert len(res["media"]) > 0
            media_item = res["media"][0]
            assert media_item["type"] == "video"
            assert "/api/outputs/file" in media_item["download_url"]
            assert "/api/outputs/preview" in media_item["preview_url"]
    finally:
        video_dest.unlink(missing_ok=True)


# =========================================================================
# 2. CHAT HISTORY SERIALIZATION WITH ACTIONS
# =========================================================================

def test_chat_saves_executed_actions_in_history(operator_engine, monkeypatch, tmp_path):
    """Verify chat() persists executed_actions with media entries in session history for frontend reload."""
    session_id = "test_session_video_history"
    monkeypatch.setattr("pipeline.stages.ai_operator.vram_manager.prepare_for_model", lambda m: True)

    resp_mock = MagicMock()
    resp_mock.status_code = 200
    resp_mock.json.return_value = {
        "message": {"content": '{"tool": "system_diagnostics"}'}
    }
    monkeypatch.setattr("requests.post", lambda url, json=None, timeout=None: resp_mock)

    operator_engine.clear_history(session_id)
    chat_res = operator_engine.chat("Diagnose system", session_id=session_id)

    history = operator_engine.get_history(session_id)
    assert len(history) == 2
    assistant_entry = history[1]
    assert assistant_entry["role"] == "assistant"
    assert "actions" in assistant_entry
    assert len(assistant_entry["actions"]) > 0
    assert assistant_entry["actions"][0].get("tool") == "system_diagnostics"


# =========================================================================
# 3. STRICT NSFW & ANTI-NUDITY GUARDRAILS
# =========================================================================

def test_herald_brand_vibes_negative_prompts_forbid_nudity():
    """Verify Herald's negative prompts for both creator_pulse_lab and creator_media_lab strictly forbid nudity."""
    for brand_key in ["creator_pulse_lab", "creator_media_lab"]:
        vibe = BRAND_VIBES[brand_key]
        neg = vibe["negative_prompt"].lower()
        assert "nude" in neg, f"Missing 'nude' in {brand_key} negative prompt"
        assert "nudity" in neg, f"Missing 'nudity' in {brand_key} negative prompt"
        assert "naked" in neg, f"Missing 'naked' in {brand_key} negative prompt"
        assert "topless" in neg, f"Missing 'topless' in {brand_key} negative prompt"
        assert "nsfw" in neg, f"Missing 'nsfw' in {brand_key} negative prompt"
        assert "explicit" in neg, f"Missing 'explicit' in {brand_key} negative prompt"


def test_herald_video_upgrade_strictly_disables_adult_loras(tmp_path):
    """Verify Herald's video upgrade forces lora_config=[] (zero adult LoRAs) for automated social video."""
    test_cfg = {
        "marketing_channels": {
            "adult_creator_brand": {
                "video_posting": {
                    "enabled": True,
                    "slot_id": "slot_1_morning",
                    "engine": "minimax_h3",
                    "duration_seconds": 8
                }
            }
        }
    }
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps(test_cfg), encoding="utf-8")
    scheduler = HeraldScheduler(config_path=str(cfg_file))

    with patch("pipeline.stages.comfyui_bridge.comfy_bridge.generate_image_to_video_minimax") as mock_gen:
        mock_gen.return_value = {"success": True, "file_path": "fake.mp4", "filename": "fake.mp4"}
        res = scheduler._maybe_upgrade_to_video("creatorpulselab", "slot_1_morning", "source.jpg")
        assert res == "fake.mp4"
        assert mock_gen.call_args.kwargs.get("lora_config") == []


def test_content_engine_negative_prompt_forbids_nudity():
    """Verify Content Engine's base negative prompt includes anti-nudity tokens."""
    neg = CE_NEGATIVE_PROMPT.lower()
    assert "nude" in neg
    assert "nudity" in neg
    assert "naked" in neg
    assert "nsfw" in neg
    assert "topless" in neg


def test_ai_operator_comfy_generate_enforces_anti_nude_when_adult_not_allowed(operator_engine):
    """Verify comfy_generate automatically appends anti-nude negative prompts when adult_allowed=False."""
    with patch("pipeline.stages.comfyui_bridge.comfy_bridge.generate_and_audit") as mock_audit:
        mock_audit.return_value = {"success": True, "filename": "test.png", "qc_audit": {"passed": True}}
        operator_engine.execute_internal_tool({
            "tool": "comfy_generate",
            "prompt": "high-fashion portrait",
            "negative_prompt": "blurry"
        }, adult_allowed=False)

        assert mock_audit.called
        call_neg = mock_audit.call_args.kwargs["negative_prompt"].lower()
        assert "nude" in call_neg
        assert "nudity" in call_neg
        assert "naked" in call_neg
        assert "topless" in call_neg


def test_ai_operator_comfy_image_to_video_enforces_anti_nude_when_adult_not_allowed(tmp_path, operator_engine):
    """Verify comfy_image_to_video automatically appends anti-nude negative prompts when adult_allowed=False."""
    src = tmp_path / "img.jpg"
    src.write_bytes(b"data")

    with patch("pipeline.stages.comfyui_bridge.comfy_bridge.generate_image_to_video") as mock_gen:
        mock_gen.return_value = {"success": True, "file_path": "test.mp4", "filename": "test.mp4"}
        operator_engine.execute_internal_tool({
            "tool": "comfy_image_to_video",
            "image": str(src),
            "prompt": "slow pan",
            "negative_prompt": "blurry"
        }, adult_allowed=False)

        assert mock_gen.called
        call_neg = mock_gen.call_args.kwargs["negative_prompt"].lower()
        assert "nude" in call_neg
        assert "nudity" in call_neg
        assert "topless" in call_neg


# =========================================================================
# 4. UNQUOTED TOOL PARSING & VISION BYPASS ON TOOL ACTION INTENT
# =========================================================================

def test_extract_tool_calls_unquoted_and_markdown_bold():
    """Verify extract_tool_calls parses unquoted keys and markdown-bold-wrapped tool calls."""
    from pipeline.stages.ai_operator import extract_tool_calls
    sample = """Commander — I've received your image.
**{tool: "comfy_generate_video", "image": "...", "prompt": "Slow cinematic pan", "width": 720, "height": 1280, "num_frames": 300, "fps": 30, "engine": "ltx2.3", "duration_seconds": 10, "adult_tuning": false}**
Processing started."""

    tools, clean, errors = extract_tool_calls(sample)
    assert len(tools) == 1
    assert tools[0]["tool"] == "comfy_generate_video"
    assert tools[0]["image"] == "..."
    assert tools[0]["engine"] == "ltx2.3"
    assert len(errors) == 0
    assert "**" not in clean
    assert "comfy_generate_video" not in clean


def test_detect_vision_requirement_bypasses_vl_on_tool_actions(operator_engine, tmp_path):
    """Verify detect_vision_requirement keeps 14B text model when user asks to animate/transform an image,

    reserving expensive Qwen-VL model swaps strictly for explicit visual inspection or critique."""
    img = tmp_path / "test_user_img.jpg"
    img.write_bytes(b"data")

    # Animation / tool action intents -> Should stay on text model (is_vision=False)
    for prompt in [
        "Add motion to this image.",
        "Use image to video with comfyui and give this image motion.",
        "Make this move using comfyui image to video work flow",
        "Animate this photo",
        "Retouch this photo"
    ]:
        is_v, reason, imgs, model = operator_engine.detect_vision_requirement(
            message=prompt,
            attached_files=[str(img)]
        )
        assert is_v is False, f"Expected is_vision=False for '{prompt}', got {is_v}"

    # Visual inspection / critique intents -> Must engage Vision mode (is_vision=True)
    for prompt in [
        "Look at this image and tell me how the lighting looks",
        "Inspect this photo and critique the composition",
        "What do you see in this photo?"
    ]:
        is_v, reason, imgs, model = operator_engine.detect_vision_requirement(
            message=prompt,
            attached_files=[str(img)]
        )
        assert is_v is True, f"Expected is_vision=True for '{prompt}', got {is_v}"


# =========================================================================
# 5. STRICT SFW ENFORCEMENT & IRIS NUDITY REJECTION GATES
# =========================================================================

def test_herald_creator_pulse_prompts_are_strictly_sfw():
    """Verify BRAND_VIBES['creator_pulse_lab'] contains zero boudoir, lingerie, or sensual prompts."""
    vibe = BRAND_VIBES["creator_pulse_lab"]
    forbidden_words = ["boudoir", "lingerie", "sensual", "sultry", "robe slipping", "bed", "sheets", "sheer mesh", "seductive"]
    for p in vibe["prompts"]:
        p_lower = p.lower()
        for fw in forbidden_words:
            assert fw not in p_lower, f"Forbidden word '{fw}' found in prompt: {p}"


def test_iris_qc_gate_rejects_detected_nudity(tmp_path):
    """Verify run_iris_qc_audit marks passed=False and REJECT_NSFW_CONTENT when nudity is detected."""
    from pipeline.stages.comfyui_bridge import ComfyUIBridge
    bridge = ComfyUIBridge()
    img = tmp_path / "test_nude.png"
    img.write_bytes(b"data")

    # Mock Ollama vision returning nudity detected
    mock_qc_resp = json.dumps({
        "passed": False,
        "aesthetic_score": 8.0,
        "extra_limbs_detected": False,
        "facial_distortion_detected": False,
        "nudity_or_nsfw_detected": True,
        "defects_summary": "Explicit nudity detected.",
        "modesty_notes": "Subject has exposed breasts.",
        "recommendation": "REJECT_NSFW_CONTENT"
    })
    with patch.object(bridge.ai, "call_ollama_vision", return_value=mock_qc_resp):
        audit = bridge.run_iris_qc_audit(img)
        assert audit["passed"] is False
        assert audit.get("nudity_or_nsfw_detected") is True
        assert audit.get("recommendation") == "REJECT_NSFW_CONTENT"


def test_herald_pre_post_filter_drops_boudoir_and_adult_files():
    """Verify Herald's pre-post filter drops any file with 'boudoir' or adult tokens in filename."""
    from pipeline.stages.herald_scheduler import HeraldScheduler
    scheduler = HeraldScheduler()

    blocked = [
        "CPL_Boudoir_00041__1791910813.png",
        "nude_model.jpg",
        "topless_render.png",
        "lingerie_shoot.webp",
        "provocative_photo.jpg"
    ]
    blocked_tokens = [
        "boudoir", "nude", "naked", "nsfw", "topless", "lingerie",
        "porn", "explicit", "erotic", "bikini", "swimwear", "sheer",
        "provocative", "seductive", "charlette", "margo", "melissa"
    ]
    for fn in blocked:
        fn_lower = Path(fn).name.lower()
        assert any(k in fn_lower for k in blocked_tokens), f"Expected {fn} to be matched by blocked_tokens"
