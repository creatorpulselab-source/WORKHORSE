import ast
import inspect
import json
import textwrap
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from pipeline.stages.ai_operator import (
    AIOperatorEngine,
    extract_tool_calls,
    SYSTEM_PROMPT,
    DEFAULT_TEXT_MODEL,
    DEFAULT_VISION_MODEL,
)

@pytest.fixture
def operator_engine(tmp_path, monkeypatch):
    monkeypatch.setattr("pipeline.stages.ai_operator.WORKSPACE_DIR", tmp_path)
    monkeypatch.setattr("pipeline.stages.ai_operator.CLIENT_INBOX_DIR", tmp_path / "client_inbox")
    monkeypatch.setattr("pipeline.stages.ai_operator.CLIENT_OUTPUTS_DIR", tmp_path / "client_deliveries")
    monkeypatch.setattr("pipeline.stages.ai_operator.OPERATOR_CHAT_SESSIONS_DIR", tmp_path / "sessions")
    monkeypatch.setattr("pipeline.stages.ai_operator.ERROR_LOG_FILE", tmp_path / "error_log.json")
    monkeypatch.setattr("pipeline.stages.ai_operator.INCIDENT_LOG_FILE", tmp_path / "incident_log.json")
    (tmp_path / "client_inbox").mkdir(parents=True, exist_ok=True)
    (tmp_path / "client_deliveries").mkdir(parents=True, exist_ok=True)
    (tmp_path / "sessions").mkdir(parents=True, exist_ok=True)
    engine = AIOperatorEngine()
    return engine


# 1. Tool Call Parsing - Nested Structures
def test_extract_tool_calls_nested_loras_inline():
    """Verify inline tool calls with nested objects and arrays are not truncated."""
    raw = (
        'Certainly Commander! Here is the generation command:\n'
        '{"tool": "comfy_generate", "prompt": "cyberpunk portrait", "loras": [{"name": "flux_real", "strength": 0.8}, {"name": "skin_texture", "strength": 0.5}], "steps": 30}\n'
        'Let me know when you need modifications.'
    )
    tools, clean, errors = extract_tool_calls(raw)
    assert len(tools) == 1
    assert len(errors) == 0
    assert tools[0]["tool"] == "comfy_generate"
    assert len(tools[0]["loras"]) == 2
    assert tools[0]["loras"][0]["name"] == "flux_real"
    assert tools[0]["loras"][1]["strength"] == 0.5
    assert '{"tool":' not in clean
    assert "Certainly Commander!" in clean


def test_extract_tool_calls_nested_items_fenced():
    """Verify fenced ```json ... ``` tool calls with nested arrays and objects parse cleanly."""
    raw = (
        'Here is the tip menu layout:\n'
        '```json\n'
        '{\n'
        '  "tool": "generate_tip_menu",\n'
        '  "title": "VIP Club",\n'
        '  "theme": "neon_cyber",\n'
        '  "items": [\n'
        '    {"tokens": "50", "action": "Flash Snap"},\n'
        '    {"tokens": "200", "action": "Custom Audio Note"}\n'
        '  ]\n'
        '}\n'
        '```\n'
        'Ready for client review.'
    )
    tools, clean, errors = extract_tool_calls(raw)
    assert len(tools) == 1
    assert len(errors) == 0
    assert tools[0]["tool"] == "generate_tip_menu"
    assert len(tools[0]["items"]) == 2
    assert tools[0]["items"][0]["tokens"] == "50"
    assert "```json" not in clean


def test_extract_tool_calls_malformed_surfaces_parse_error():
    """Verify malformed/unclosed tool calls surface a parse error instead of silently dropping."""
    raw = 'Initiating render: {"tool": "comfy_generate", "prompt": "unclosed string without closing brace'
    tools, clean, errors = extract_tool_calls(raw)
    assert len(tools) == 0
    assert len(errors) == 1
    assert "unclosed" in errors[0]["error"].lower()


def test_chat_logs_tool_call_parse_error(operator_engine, monkeypatch):
    """Verify chat() logs a tool_call_parse_error event when encountering malformed JSON."""
    monkeypatch.setattr("pipeline.stages.ai_operator.vram_manager.prepare_for_model", lambda m: True)
    mock_post = MagicMock()
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "message": {"content": 'Calling tool: {"tool": "broken_tool", "prompt": "unclosed...'}
    }
    monkeypatch.setattr("requests.post", mock_post)

    logged_errors = []
    def mock_log_error(component, msg, context=None):
        logged_errors.append((component, msg, context))
    monkeypatch.setattr(operator_engine, "log_error", mock_log_error)

    res = operator_engine.chat("Test broken tool parse")
    assert res["status"] == "ok"
    assert any(e[0] == "tool_call_parse_error" for e in logged_errors)


# 2. Vision Model Selection Honoring Config
def test_detect_vision_requirement_honors_configured_iris_model(operator_engine, monkeypatch, tmp_path):
    """Verify detect_vision_requirement prioritizes agents.iris.vision_model from config.json."""
    fake_config = tmp_path / "config.json"
    fake_config.write_text(json.dumps({
        "agents": {
            "iris": {
                "vision_model": "custom_studio_vl:14b"
            }
        }
    }), encoding="utf-8")
    monkeypatch.setattr("pipeline.stages.ai_operator.CONFIG_FILE", fake_config)

    monkeypatch.setattr(operator_engine, "get_available_models", lambda: ["other-vl:8b", "custom_studio_vl:14b"])

    is_vision, reason, images, resolved_model = operator_engine.detect_vision_requirement(
        message="Please inspect this photo and analyze the lighting",
        attached_files=None,
        batch_dir=None
    )
    assert is_vision is True
    assert resolved_model == "custom_studio_vl:14b"


# 3. Comprehensive System Diagnostics
def test_run_system_diagnostics_comprehensive_components(operator_engine, monkeypatch, tmp_path):
    """Verify run_system_diagnostics audits ComfyUI, Dual GPU/VRAM, Arbiter, Herald, Social, FFmpeg, and Storage."""
    mock_get = MagicMock()
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"models": [{"name": DEFAULT_TEXT_MODEL}]}
    monkeypatch.setattr("requests.get", mock_get)

    fake_comfy = MagicMock()
    fake_comfy.check_connection.return_value = {"online": True, "host": "192.168.1.74:8188", "response_time_ms": 12.5}
    monkeypatch.setattr("pipeline.stages.comfyui_bridge.comfy_bridge", fake_comfy)

    fake_herald = MagicMock()
    fake_herald.DAILY_SLOTS = ["slot_1", "slot_2", "slot_3", "slot_4", "slot_5"]
    fake_herald.get_daily_schedule_state.return_value = {"date": "2026-10-12"}
    monkeypatch.setattr("pipeline.stages.herald_scheduler.herald_scheduler", fake_herald)

    fake_arbiter = MagicMock()
    fake_arbiter.status.return_value = {"locked": False, "current_task": None}
    monkeypatch.setattr("shared.gpu1_arbiter.gpu1_arbiter", fake_arbiter)

    monkeypatch.setattr("shutil.which", lambda prog: "C:\\ffmpeg\\bin\\ffmpeg.exe" if prog == "ffmpeg" else None)

    report = operator_engine.run_system_diagnostics()

    assert "components" in report
    components = report["components"]
    assert "ollama" in components
    assert "comfyui" in components
    assert components["comfyui"]["status"] == "ok"
    assert "dual_gpu" in components
    assert "gpu1_arbiter" in components
    assert components["gpu1_arbiter"]["status"] == "ok"
    assert "herald_scheduler" in components
    assert components["herald_scheduler"]["slots_count"] == 5
    assert "social_credentials" in components
    assert "ffmpeg" in components
    assert components["ffmpeg"]["status"] == "ok"
    assert "storage_f" in components


# 4. ComfyUI Architecture & Workflow Knowledge Grounding in SYSTEM_PROMPT
def test_system_prompt_comfyui_knowledge_grounding():
    """Verify SYSTEM_PROMPT thoroughly grounds Synapse in ComfyUI architecture and production workflows."""
    prompt = SYSTEM_PROMPT
    assert "RTX 5070 Ti" in prompt
    assert "192.168.1.74:8188" in prompt
    assert "FLUX.1" in prompt
    assert "LTX-Video 2.3" in prompt
    assert "MiniMax H3" in prompt
    assert "Trellis 2" in prompt
    assert "Subject Swap" in prompt
    assert "SAM3" in prompt
    assert "Iris" in prompt and "Quality Control" in prompt
    assert "VAEDecodeTiled" in prompt
    assert "STRICT CHARACTER LORA POLICY" in prompt
    assert "ML_FLUX" in prompt and "CW_FLUX" in prompt and "Margo_FLUX" in prompt


# 5. Autonomous Healing & Overwatch Duties in SYSTEM_PROMPT
def test_system_prompt_healing_and_overwatch_grounding():
    """Verify SYSTEM_PROMPT thoroughly grounds Synapse in autonomous healing and overwatch sentinel duties."""
    prompt = SYSTEM_PROMPT
    assert "AUTONOMOUS HEALING & OVERWATCH SENTINEL DUTIES" in prompt
    assert "Dual-GPU Guardrails & Isolation" in prompt
    assert "VRAM Circuit Breaker Overwatch" in prompt
    assert "Storage & Workspace Auto-Pruning" in prompt
    assert "Self-Healing Auto-Remediation Loop" in prompt
    assert "Full-Spectrum System Diagnostics" in prompt


# 6. Architectural Safety Boundaries (Actions Requiring UI Confirmation)
def test_system_prompt_architectural_safety_boundaries():
    """Verify SYSTEM_PROMPT explicitly marks high-impact commercial actions as requiring UI confirmation."""
    prompt = SYSTEM_PROMPT
    assert "ARCHITECTURAL SAFETY BOUNDARIES" in prompt
    assert "Starting the full multi-stage video pipeline" in prompt
    assert "Releasing live client fulfillment packages on Fiverr or Etsy" in prompt
    assert "Auto-publishing autonomous content engine drops" in prompt


def test_synapse_chat_operator_does_not_contain_unsafe_fulfillment_tools(operator_engine):
    """Assert that high-risk commercial release and bulk publishing are rejected with error."""
    unsafe_chat_tools = [
        "publish_tweet_now",
        "fulfill_fiverr_order",
        "fulfill_etsy_order",
        "send_mass_newsletter",
        "start_video_pipeline",
        "auto_publish_content_engine",
    ]
    for unsafe_tool in unsafe_chat_tools:
        result = operator_engine.execute_internal_tool({"tool": unsafe_tool})
        assert result.get("status") == "error"
        assert result.get("error") == f"Unknown tool: {unsafe_tool}"


# 7. Tool Catalog Coverage (~40 Registered Tools via AST Inspection)
def test_tool_catalog_size_and_reachability():
    """Verify that all 40 core studio tools are registered in execute_internal_tool."""
    source = textwrap.dedent(inspect.getsource(AIOperatorEngine.execute_internal_tool))
    tree = ast.parse(source)

    handled_tools = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            if isinstance(node.left, ast.Name) and node.left.id == "tool_name":
                for comp in node.comparators:
                    if isinstance(comp, ast.Constant) and isinstance(comp.value, str):
                        handled_tools.add(comp.value)

    core_tools = [
        "check_daily_schedule", "herald_dispatch_now", "radar_scan_now",
        "system_diagnostics", "fix_vram_overflow", "comfy_status",
        "iris_qc_audit", "gpu_guardrails_status", "comfy_generate_glb",
        "comfy_background_change", "comfy_generate_3d_pbr", "comfy_subject_swap",
        "comfy_remote_purge", "comfy_prewarm", "comfy_search_models",
        "prune_staging_buffer", "scrub_file_metadata", "trend_radar_sweep",
        "get_daily_trends", "incident_log", "generate_tip_menu",
        "aura_retouch", "create_banner", "generate_shoot_concepts",
        "scan_inspiration_vault", "apex_package", "newsletter_add",
        "newsletter_remove", "newsletter_stats", "ingest_link",
        "block_swap_model", "hardware_allocation", "repair_subscribers",
        "notify_commander", "webhook_fulfillment_status", "content_engine_run_now",
        "content_engine_status"
    ]
    for t in core_tools:
        assert t in handled_tools, f"Core tool '{t}' is missing from execute_internal_tool!"
    assert len(handled_tools) >= 38


# 8. Second-Pass Tool Feedback Loop
def test_chat_second_pass_tool_feedback(operator_engine, monkeypatch):
    """Verify that when a tool executes and initial reply is empty, chat feeds results back to LLM for second pass."""
    monkeypatch.setattr("pipeline.stages.ai_operator.vram_manager.prepare_for_model", lambda m: True)
    chat_calls = []

    def mock_post(url, json=None, timeout=None):
        chat_calls.append((url, json))
        resp = MagicMock()
        resp.status_code = 200
        if len(chat_calls) == 1:
            resp.json.return_value = {
                "message": {"content": '{"tool": "system_diagnostics"}'}
            }
        else:
            resp.json.return_value = {
                "message": {"content": "All systems are green, Commander. ComfyUI and Dual GPUs are operating nominally."}
            }
        return resp

    monkeypatch.setattr("requests.post", mock_post)
    monkeypatch.setattr(operator_engine, "run_tool_and_log", lambda tool_call, adult_allowed=False, batch_dir=None: {
        "status": "ok", "tool": "system_diagnostics", "overall_status": "healthy"
    })

    res = operator_engine.chat("Status report please")
    assert res["status"] == "ok"
    assert len(res["executed_actions"]) == 1
    assert "All systems are green, Commander" in res["reply"]
    assert len(chat_calls) == 2
    assert "The internal studio tools have finished execution" in chat_calls[1][1]["messages"][-1]["content"]
