"""Offline regression coverage for guide retrieval and real agent prompt wiring."""

import hashlib
import json
from unittest.mock import Mock

import pytest

from shared import comfyui_knowledge as knowledge


@pytest.fixture
def local_guide(tmp_path, monkeypatch):
    guide = tmp_path / "guide.md"
    guide.write_bytes(knowledge.GUIDE_PATH.read_bytes())
    monkeypatch.setattr(knowledge, "GUIDE_PATH", guide)
    return guide


@pytest.mark.parametrize("task", knowledge.TASK_MODULES)
def test_task_context_is_bounded_and_preserves_operating_contract(task, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    context = knowledge.get_comfyui_context(task)
    assert len(context) <= knowledge.MAX_CONTEXT_CHARS
    assert "SHA256:" in context
    assert "NOT fine-tuning" in context
    assert "/object_info" in context
    assert "authorization gates and response contract" in context
    assert "Pixel QC cannot prove graph correctness" in context
    assert context.endswith("--- END COMFYUI KNOWLEDGE ---")


@pytest.mark.parametrize(("query", "section"), [
    ("Trellis PBR", "### 12.4"),
    ("LTX video", "### 12.2"),
    ("MiniMax H3", "### 12.3"),
    ("stack LoRAs", "### 13.4"),
    ("GGUF quantization", "### 14.6"),
    ("upscale tiled", "### 14.1"),
    ("ControlNet scheduling", "### 14.2"),
    ("regional multi-subject", "### 14.3"),
    ("IP-Adapter FaceID", "### 14.4"),
    ("FreeU PAG", "### 14.5"),
    ("dynamic wildcards", "### 14.7"),
    ("LivePortrait audio", "### 14.8"),
    ("precision inpainting", "## Module 8:"),
    ("IC-Light relighting", "## Module 10:"),
    ("image-to-image", "## Module 7:"),
])
def test_operator_retrieves_the_requested_specialty(query, section):
    context = knowledge.get_comfyui_context("operator", query)
    assert section in context
    assert "## Module 1:" in context
    assert "## Module 17:" in context


@pytest.mark.parametrize(("query", "letter"), [
    ("SDXL workflow", "A"),
    ("FLUX workflow", "B"),
    ("SVD workflow", "C"),
    ("inpainting graph", "D"),
    ("IC-Light relighting graph", "E"),
    ("ref-to-video workflow", "F"),
    ("Trellis PBR workflow", "G"),
    ("LoRA workflow", "H"),
    ("hi-res upscale graph", "I"),
    ("ControlNet workflow", "J"),
    ("regional graph", "K"),
    ("FaceID workflow", "L"),
    ("FLUX GGUF workflow", "M"),
])
def test_retrieved_blueprint_is_whole_not_truncated(query, letter):
    context = knowledge.get_comfyui_context("operator", query)
    module = knowledge._modules(knowledge.GUIDE_PATH.read_text(encoding="utf-8-sig"))[15]
    blueprint = module.split(f"### Blueprint {letter}:", 1)[1].split("### Blueprint ", 1)[0].strip()
    assert f"### Blueprint {letter}:" in context
    assert blueprint in context
    assert len(context) <= knowledge.MAX_CONTEXT_CHARS


def test_guide_edits_are_visible_on_the_next_call(local_guide):
    before = knowledge.get_comfyui_context("image_prompt")
    text = local_guide.read_text(encoding="utf-8")
    local_guide.write_text(text.replace("## Module 6:", "## Module 6: UPDATED"), encoding="utf-8")
    after = knowledge.get_comfyui_context("image_prompt")
    assert "## Module 6: UPDATED" in after
    assert before != after
    assert hashlib.sha256(local_guide.read_text(encoding="utf-8").encode("utf-8")).hexdigest() in after


@pytest.mark.parametrize("invalid", ["missing", "empty", "incomplete", "empty-module", "bad-encoding"])
def test_unavailable_guide_is_logged_and_not_presented_as_loaded(local_guide, invalid, caplog):
    if invalid == "missing":
        # Point at a nonexistent path rather than deleting even a test fixture.
        knowledge.GUIDE_PATH = local_guide.parent / "missing.md"
    elif invalid == "empty":
        local_guide.write_text("", encoding="utf-8")
    elif invalid == "incomplete":
        local_guide.write_text("## Module 1: Only one module\nBody", encoding="utf-8")
    elif invalid == "empty-module":
        local_guide.write_text(
            "\n\n".join(f"## Module {n}: Test\n" + ("" if n == 6 else "Body") for n in range(1, 19)),
            encoding="utf-8"
        )
    else:
        local_guide.write_bytes(b"\xff\xfe")
    context = knowledge.get_comfyui_context("operator")
    assert "COMFYUI TRAINING GUIDE UNAVAILABLE" in context
    assert "do not claim guide-backed expertise" in context
    assert "SHA256:" not in context
    assert "ComfyUI training guide unavailable" in caplog.text


def test_oversized_sections_are_omitted_whole(local_guide):
    text = local_guide.read_text(encoding="utf-8")
    local_guide.write_text(text.replace("## Module 1:", "## Module 1: " + "x" * 20000), encoding="utf-8")
    context = knowledge.get_comfyui_context("operator")
    assert len(context) <= knowledge.MAX_CONTEXT_CHARS
    assert "## Module 1:" not in context
    assert "additional sections omitted" in context
    assert "For requested execution graphs, use API prompt JSON" in context


def test_unknown_task_is_an_explicit_programming_error():
    with pytest.raises(ValueError, match="Unknown ComfyUI knowledge task"):
        knowledge.get_comfyui_context("unknown")


def test_muse_all_three_calls_receive_task_specific_guidance(tmp_path, monkeypatch):
    from pipeline.stages.prompt_synthesizer import PromptSynthesizer

    muse = PromptSynthesizer(str(tmp_path / "config.json"))
    call = Mock(side_effect=[
        "A natural-language studio portrait.",
        "Slow dolly with natural hair movement.",
        "\n".join(f"{n}. Pose {n}." for n in range(1, 7))
    ])
    monkeypatch.setattr(muse.ai, "call_ollama_text", call)
    result = muse.generate_prompt_kit("A subject in a blue jacket.", preset="Studio Portrait")
    assert result["status"] == "ok"
    assert len(result["pose_series"]) == 6
    systems = [args.kwargs["system_prompt"] for args in call.call_args_list]
    assert all("You are Muse" in system and "SHA256:" in system for system in systems)
    assert "### 13.4" in systems[0]
    assert "## Module 11:" in systems[1]
    assert "### 14.3" in systems[2]
    assert result["flux_image_prompt"] == "A natural-language studio portrait."


def test_iris_prompt_cache_is_invalidated_when_the_guide_changes(local_guide, tmp_path, monkeypatch):
    from pipeline.stages import inspiration_scanner as scanner_module

    vault = tmp_path / "vault"
    scanner = scanner_module.InspirationScanner(str(vault), str(tmp_path / "config.json"))
    monkeypatch.setattr(scanner_module, "VAULT_CACHE_FILE", tmp_path / "cache.json")
    (vault / "reference.jpg").write_bytes(b"mock image")
    response = (
        "### SECTION 1: POSITIVE\n```\nA studio portrait.\n```\n"
        "### SECTION 2: NEGATIVE\n```\nBlur.\n```\n"
        "### SECTION 3: VIDEO\n```\nSlow dolly.\n```\n"
        "### SECTION 4: PARAMETERS\nModel-specific settings."
    )
    call = Mock(return_value=response)
    monkeypatch.setattr(scanner.ai, "call_ollama_vision", call)
    first = scanner.generate_comfyui_prompts()
    second = scanner.generate_comfyui_prompts()
    assert first["image_prompt"] == "A studio portrait."
    assert second["cache_hit"] is True
    assert call.call_count == 1
    system = call.call_args.kwargs["system_prompt"]
    assert "You are Iris" in system and "## Module 6:" in system

    local_guide.write_text(local_guide.read_text(encoding="utf-8") + "\nRevision update.", encoding="utf-8")
    third = scanner.generate_comfyui_prompts()
    assert third["cache_hit"] is False
    assert call.call_count == 2
    assert call.call_args.kwargs["system_prompt"] != system
    assert third["image_prompt"] == first["image_prompt"]


def test_iris_qc_receives_reference_without_changing_rejection_policy(tmp_path, monkeypatch):
    from pipeline.stages.comfyui_bridge import ComfyUIBridge

    bridge = ComfyUIBridge(tmp_path / "config.json")
    call = Mock(return_value=json.dumps({
        "passed": True, "aesthetic_score": 9, "extra_limbs_detected": True,
        "facial_distortion_detected": False
    }))
    monkeypatch.setattr(bridge.ai, "call_ollama_vision", call)
    result = bridge.run_iris_qc_audit(tmp_path / "image.png")
    system = call.call_args.kwargs["system_prompt"]
    assert "## Module 2:" in system and "## Module 18:" in system
    assert "never an execution graph" in system
    assert "## Module 17:" not in system
    assert result["passed"] is False
    assert result["recommendation"] == "RETRY_NEW_SEED"


def test_synapse_actual_chat_payload_contains_guide_and_preserves_identity(tmp_path, monkeypatch):
    from pipeline.stages import ai_operator as operator_module
    from pipeline.stages.comfyui_bridge import comfy_bridge
    from pipeline.stages.trend_researcher import trend_researcher

    monkeypatch.setattr(operator_module, "OPERATOR_CHAT_SESSIONS_DIR", tmp_path)
    monkeypatch.setattr(operator_module, "get_latest_client_batch_dir", lambda session: None)
    monkeypatch.setattr(operator_module.vram_manager, "prepare_for_model", lambda model: None)
    monkeypatch.setattr(comfy_bridge, "get_prompt_context_summary", lambda: "LIVE COMFY INVENTORY")
    monkeypatch.setattr(trend_researcher, "get_daily_summary_prompt_context", lambda: "")
    engine = operator_module.AIOperatorEngine()
    monkeypatch.setattr(engine, "detect_vision_requirement", lambda **kwargs: (False, "", [], None))
    monkeypatch.setattr(engine, "get_live_task_status_context", lambda: "LIVE AGENT STATUS")
    monkeypatch.setattr(engine, "get_recent_incidents", lambda **kwargs: [])
    response = Mock(status_code=200)
    response.json.return_value = {"message": {"content": "Use the tested workflow, Commander."}}
    post = Mock(return_value=response)
    monkeypatch.setattr(operator_module.requests, "post", post)

    result = engine.chat("Explain a Trellis PBR workflow", session_id="guide-test")
    assert result["status"] == "ok"
    system = post.call_args.kwargs["json"]["messages"][0]["content"]
    assert system.startswith(operator_module.SYSTEM_PROMPT)
    assert "LIVE AGENT STATUS" in system and "LIVE COMFY INVENTORY" in system
    assert "### 12.4" in system and "### Blueprint G:" in system
    assert "Keep your WORKHORSE agent identity" in system
    assert result["executed_actions"] == []
    assert (tmp_path / "guide-test.json").exists()
