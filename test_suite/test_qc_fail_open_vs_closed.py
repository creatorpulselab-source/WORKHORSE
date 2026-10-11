"""Regression tests for the IRIS QC fail-open/fail-closed policy decided with the
Commander (2026-10-10): QC stays fail-open ONLY when the check itself couldn't run
(vision model offline/timeout/malformed response); a genuine rejection after
exhausting retries now fails closed instead of silently returning success=True.

Root cause this fixes: comfyui_bridge.py's generate_and_audit() previously returned
success=True (with only a "warning" field) for an image Iris explicitly rejected on
every retry attempt, and saved it into the exact same folder
(workspace/brand_assets/comfy_renders) the Completed Work gallery scans as approved
content - indistinguishable from a real pass. content_engine.py's autonomous
image->video->copy pipeline only checks "success", so it would have proceeded with a
QC-rejected image. Herald's social-posting path already checked both "success" and
qc_audit.passed correctly, so this gap was asymmetric, not universal.
"""
from pathlib import Path
from unittest.mock import patch

import pytest

from pipeline.stages.comfyui_bridge import ComfyUIBridge


@pytest.fixture
def bridge(tmp_path, monkeypatch):
    import pipeline.stages.comfyui_bridge as bridge_module
    workspace = tmp_path / "workspace"
    monkeypatch.setattr(bridge_module, "WORKSPACE_DIR", workspace)
    monkeypatch.setattr(bridge_module, "STAGING_DIR", workspace / "comfy_staging")
    monkeypatch.setattr(bridge_module, "RENDERS_DIR", workspace / "brand_assets" / "comfy_renders")
    return ComfyUIBridge()


def _make_staged_image(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fake-png-bytes")


def _make_real_image_with_exif(path: Path):
    from PIL import Image
    from PIL.ExifTags import Base as ExifBase
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (8, 8), color=(120, 40, 200))
    exif = img.getexif()
    exif[ExifBase.Make.value] = "ComfyUI-Workflow-Metadata"
    img.save(path, format="PNG", exif=exif)


# --------------------------------------------------------------------------
# run_iris_qc_audit: fail-open on infra failure, but now auditable/distinguishable
# --------------------------------------------------------------------------

def test_qc_infra_failure_stays_fail_open_but_is_marked_distinctly(bridge, tmp_path):
    image_path = tmp_path / "render.png"
    _make_staged_image(image_path)

    with patch.object(bridge.ai, "call_ollama_vision", side_effect=TimeoutError("Ollama timed out")):
        audit = bridge.run_iris_qc_audit(image_path, original_prompt="test prompt")

    assert audit["passed"] is True  # fail-open preserved, per the Commander's decision
    assert audit["qc_infra_unavailable"] is True  # but now distinguishable from a real pass
    assert audit["recommendation"] == "APPROVED_QC_UNAVAILABLE"


def test_qc_genuine_pass_has_no_infra_unavailable_marker(bridge, tmp_path):
    image_path = tmp_path / "render.png"
    _make_staged_image(image_path)
    valid_response = (
        '{"passed": true, "aesthetic_score": 9.0, "extra_limbs_detected": false, '
        '"facial_distortion_detected": false, "defects_summary": "clean", '
        '"anatomy_notes": "fine", "recommendation": "APPROVED"}'
    )

    with patch.object(bridge.ai, "call_ollama_vision", return_value=valid_response):
        audit = bridge.run_iris_qc_audit(image_path, original_prompt="test prompt")

    assert audit["passed"] is True
    assert "qc_infra_unavailable" not in audit  # must not be conflated with a verified pass


# --------------------------------------------------------------------------
# _execute_generate_and_audit: genuine rejection after exhausted retries fails closed
# --------------------------------------------------------------------------

def test_exhausted_retries_with_genuine_rejection_fails_closed_and_quarantines(bridge, tmp_path):
    staged_file = tmp_path / "staged_output.png"

    def fake_download_image(filename, subfolder="", folder_type="output"):
        _make_staged_image(staged_file)
        return staged_file

    rejected_audit = {
        "passed": False, "aesthetic_score": 3.0, "extra_limbs_detected": True,
        "facial_distortion_detected": False, "defects_summary": "extra fingers detected",
        "recommendation": "RETRY_NEW_SEED",
    }

    with patch.object(bridge, "check_connection", return_value={"online": True, "host": "x", "port": 1}), \
         patch.object(bridge, "build_standard_workflow", return_value={}), \
         patch.object(bridge, "queue_prompt", return_value={"prompt_id": "abc123"}), \
         patch.object(bridge, "wait_for_execution", return_value=[{"filename": "staged_output.png", "subfolder": "", "type": "output"}]), \
         patch.object(bridge, "download_image", side_effect=fake_download_image), \
         patch.object(bridge, "run_iris_qc_audit", return_value=rejected_audit), \
         patch.object(bridge, "_log_audit_record"):
        result = bridge.generate_and_audit(positive_prompt="test prompt", auto_qc=True)

    assert result["success"] is False  # previously True - this is the fix
    assert "warning" not in result  # old "ship it anyway" field must be gone
    assert result["qc_audit"]["passed"] is False

    quarantined = Path(result["quarantined_file_path"])
    assert quarantined.exists()
    # Must land in the staging quarantine folder, NOT the gallery-scanned renders dir.
    assert "comfy_staging" in str(quarantined)
    assert "qc_rejected" in str(quarantined)
    import pipeline.stages.comfyui_bridge as bridge_module
    assert not (bridge_module.RENDERS_DIR / staged_file.name).exists()


def test_genuine_pass_still_succeeds_and_lands_in_renders_dir(bridge, tmp_path):
    """Sanity check that the fix didn't break the normal successful path."""
    staged_file = tmp_path / "staged_pass.png"

    def fake_download_image(filename, subfolder="", folder_type="output"):
        _make_staged_image(staged_file)
        return staged_file

    passed_audit = {
        "passed": True, "aesthetic_score": 9.0, "extra_limbs_detected": False,
        "facial_distortion_detected": False, "defects_summary": "clean",
        "recommendation": "APPROVED",
    }

    with patch.object(bridge, "check_connection", return_value={"online": True, "host": "x", "port": 1}), \
         patch.object(bridge, "build_standard_workflow", return_value={}), \
         patch.object(bridge, "queue_prompt", return_value={"prompt_id": "abc123"}), \
         patch.object(bridge, "wait_for_execution", return_value=[{"filename": "staged_pass.png", "subfolder": "", "type": "output"}]), \
         patch.object(bridge, "download_image", side_effect=fake_download_image), \
         patch.object(bridge, "run_iris_qc_audit", return_value=passed_audit), \
         patch.object(bridge, "_log_audit_record"):
        result = bridge.generate_and_audit(positive_prompt="test prompt", auto_qc=True)

    assert result["success"] is True
    assert Path(result["file_path"]).exists()
    import pipeline.stages.comfyui_bridge as bridge_module
    assert str(bridge_module.RENDERS_DIR) in result["file_path"] or "brand_assets" in result["file_path"]


# --------------------------------------------------------------------------
# QC-bypassed path must still scrub metadata (previously only the QC-PASSED
# branch did) - many ComfyUI setups embed the full workflow JSON, including the
# exact prompt text, into PNG metadata by default, which is a real content-privacy
# concern for explicit/client-identifying prompts if that image is ever shared.
# comfy_background_change/comfy_subject_swap already scrubbed unconditionally.
# --------------------------------------------------------------------------

def test_qc_bypassed_path_still_scrubs_metadata(bridge, tmp_path):
    staged_file = tmp_path / "staged_bypassed.png"

    def fake_download_image(filename, subfolder="", folder_type="output"):
        _make_real_image_with_exif(staged_file)
        return staged_file

    with patch.object(bridge, "check_connection", return_value={"online": True, "host": "x", "port": 1}), \
         patch.object(bridge, "build_standard_workflow", return_value={}), \
         patch.object(bridge, "queue_prompt", return_value={"prompt_id": "abc123"}), \
         patch.object(bridge, "wait_for_execution", return_value=[{"filename": "staged_bypassed.png", "subfolder": "", "type": "output"}]), \
         patch.object(bridge, "download_image", side_effect=fake_download_image):
        result = bridge.generate_and_audit(positive_prompt="test prompt", auto_qc=False)

    assert result["success"] is True
    assert result["qc_bypassed"] is True

    from PIL import Image
    with Image.open(result["file_path"]) as img:
        assert len(img.getexif()) == 0  # metadata must be stripped even though QC was skipped

