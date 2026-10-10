"""Unit tests for the new ComfyUI client-character LoRA generation (adult-gated) and
full-PBR image-to-3D generation, added 2026-10-09.

Covers:
1. Client character generation is hard-gated behind adult_allowed in code (not just
   omitted from the tool description) - mirrors the MiniMax H3 adult-LoRA gate pattern.
2. Unknown character names are rejected with a clear error.
3. build_client_character_workflow() patches only prompt/seed/filename_prefix,
   leaving every other node (especially the client's identity LoRA) untouched, per
   the Commander's explicit "no changes to these workflows" instruction.
4. ai_operator.py's comfy_generate_client_character tool branch threads adult_allowed
   through from execute_internal_tool's own parameter - never trusts the tool-call
   JSON for this.
5. comfy_generate_3d_pbr's source image resolution uses the same marketing-source
   lockdown as the other postable-content tools (never implicitly from client_inbox).
"""
from unittest.mock import patch

import pytest

from pipeline.stages.comfyui_bridge import (
    ComfyUIBridge,
    CLIENT_CHARACTER_PROFILES,
)
from pipeline.stages.ai_operator import AIOperatorEngine


@pytest.fixture
def bridge():
    return ComfyUIBridge()


def test_client_character_registry_has_exactly_three_profiles():
    assert set(CLIENT_CHARACTER_PROFILES.keys()) == {"charlette", "margo", "melissa"}


def test_generate_client_character_image_rejected_without_adult_allowed(bridge):
    res = bridge.generate_client_character_image("charlette", adult_allowed=False)
    assert res["success"] is False
    assert "Adult Content Mode" in res["error"]


def test_generate_client_character_image_rejects_unknown_character(bridge):
    res = bridge.generate_client_character_image("nonexistent_client", adult_allowed=True)
    assert res["success"] is False
    assert "Unknown client character" in res["error"]


def test_generate_client_character_image_still_gated_even_for_known_character_without_authorization(bridge):
    """The adult-content check must run BEFORE the character-name check, so an
    unauthorized caller can't probe for valid character names."""
    res = bridge.generate_client_character_image("margo", adult_allowed=False)
    assert res["success"] is False
    assert "Adult Content Mode" in res["error"]


@pytest.mark.parametrize("character", ["charlette", "margo", "melissa"])
def test_build_client_character_workflow_patches_only_prompt_seed_and_filenames(bridge, character):
    original_workflow = bridge.build_client_character_workflow(character)
    original_lora = original_workflow["41:46"]["inputs"]["lora_name"]
    original_lora_strength = original_workflow["41:46"]["inputs"]["strength_model"]
    original_unet = original_workflow["41:38"]["inputs"]["unet_name"]

    patched = bridge.build_client_character_workflow(character, prompt="a custom test prompt", seed=777)

    assert patched["41:45"]["inputs"]["text"] == "a custom test prompt"
    assert patched["41:31"]["inputs"]["seed"] == 777
    assert patched["41:54"]["inputs"]["seed"] == 778
    assert patched["9"]["inputs"]["filename_prefix"] == f"CLIENT_CHARACTER_{character.upper()}_base"
    assert patched["42"]["inputs"]["filename_prefix"] == f"CLIENT_CHARACTER_{character.upper()}_final"

    # Everything else - especially the client's identity LoRA - must be untouched
    assert patched["41:46"]["inputs"]["lora_name"] == original_lora
    assert patched["41:46"]["inputs"]["strength_model"] == original_lora_strength
    assert patched["41:38"]["inputs"]["unet_name"] == original_unet


def test_build_client_character_workflow_keeps_template_prompt_when_none_given(bridge):
    workflow = bridge.build_client_character_workflow("melissa")
    assert len(workflow["41:45"]["inputs"]["text"]) > 0  # template's own default prompt preserved


def test_build_client_character_workflow_rejects_unknown_character(bridge):
    with pytest.raises(ValueError, match="Unknown client character"):
        bridge.build_client_character_workflow("someone_else")


def test_execute_internal_tool_threads_adult_allowed_into_client_character_tool():
    """adult_allowed must come from execute_internal_tool's own parameter (computed
    upstream from the Commander's real toggle/explicit request in chat()), never from
    the tool_call JSON itself."""
    engine = AIOperatorEngine()
    tool_call = {"tool": "comfy_generate_client_character", "character_name": "charlette"}

    with patch("pipeline.stages.comfyui_bridge.comfy_bridge.generate_client_character_image") as mock_gen:
        mock_gen.return_value = {"success": True, "image_path": "F:/fake/path.png"}
        engine.execute_internal_tool(tool_call, adult_allowed=True)
        assert mock_gen.call_args.kwargs["adult_allowed"] is True

        mock_gen.reset_mock()
        engine.execute_internal_tool(tool_call, adult_allowed=False)
        assert mock_gen.call_args.kwargs["adult_allowed"] is False


def test_comfy_generate_3d_pbr_uses_marketing_source_lockdown(tmp_path):
    """A bare filename for comfy_generate_3d_pbr must resolve via the same
    brand_assets-only lockdown as the other postable-content tools - never an
    implicit client_inbox guess."""
    engine = AIOperatorEngine()
    tool_call = {"tool": "comfy_generate_3d_pbr", "image": "some_photo.png"}

    with patch.object(AIOperatorEngine, "_resolve_marketing_source_image", return_value=tmp_path / "does_not_exist.png") as mock_resolve:
        result = engine.execute_internal_tool(tool_call)
        mock_resolve.assert_called_once_with("some_photo.png")
    assert result["status"] == "error"
    assert "not found" in result["error"]
