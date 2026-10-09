"""Unit tests for pipeline/stages/davinci_bridge.py - the DaVinci Resolve scripting
integration for professional color grading of stills and video.

These tests deliberately do NOT require a running DaVinci Resolve instance (CI/dev
machines won't have it open) - they cover the parts that must work correctly
regardless: the style->CDL grade mapping, and the critical safety behavior that this
module must NEVER attempt to touch the native scripting DLL unless Resolve's process
is confirmed running first (doing so without Resolve running causes a hard access
violation crash in the native library, not a catchable Python exception - confirmed
empirically while building this bridge).
"""
import subprocess

import pytest

from pipeline.stages.davinci_bridge import (
    STYLE_CDL_GRADES,
    DaVinciBridgeUnavailable,
    get_resolve,
    check_connection,
    grade_still_image,
    grade_video_clip,
    _is_resolve_process_running,
)


def test_style_cdl_grades_cover_all_photo_retoucher_styles():
    """Every style name photo_retoucher.py's STYLE_PROFILES and color-grade presets
    use must have a corresponding CDL grade here, so style names mean the same thing
    whichever engine (native OpenCV or DaVinci) actually renders them."""
    expected_styles = {
        "natural", "glamour", "concert_stage", "family_event",
        "golden_hour", "cyber_neon", "monochrome_noir", "vintage_35mm", "clean_editorial"
    }
    assert expected_styles.issubset(set(STYLE_CDL_GRADES.keys()))


def test_every_cdl_grade_has_required_fields():
    for style, cdl in STYLE_CDL_GRADES.items():
        assert set(cdl.keys()) == {"Slope", "Offset", "Power", "Saturation"}, style
        for field in ("Slope", "Offset", "Power"):
            parts = cdl[field].split()
            assert len(parts) == 3, f"{style}.{field} must be 3 space-separated RGB values"
            for p in parts:
                float(p)  # must parse as a number
        float(cdl["Saturation"])


def test_get_resolve_raises_clear_error_without_crashing_when_not_running(monkeypatch):
    """The core safety assertion: when Resolve isn't running, get_resolve() must raise
    a catchable DaVinciBridgeUnavailable with an actionable message - NOT attempt to
    touch the native scripting DLL (which would risk a hard process crash)."""
    monkeypatch.setattr("pipeline.stages.davinci_bridge._is_resolve_process_running", lambda: False)
    with pytest.raises(DaVinciBridgeUnavailable) as exc_info:
        get_resolve()
    assert "not currently running" in str(exc_info.value)


def test_check_connection_never_raises_when_resolve_not_running(monkeypatch):
    monkeypatch.setattr("pipeline.stages.davinci_bridge._is_resolve_process_running", lambda: False)
    result = check_connection()
    assert result["connected"] is False
    assert "error" in result


def test_grade_still_image_missing_file_fails_gracefully(tmp_path):
    result = grade_still_image(tmp_path / "does_not_exist.jpg", style="natural")
    assert result["success"] is False
    assert "not found" in result["error"]


def test_grade_video_clip_missing_file_fails_gracefully(tmp_path):
    result = grade_video_clip(tmp_path / "does_not_exist.mp4", style="natural")
    assert result["success"] is False
    assert "not found" in result["error"]


def test_grade_still_image_fails_gracefully_when_resolve_not_running(tmp_path, monkeypatch):
    """Even with a real source file, if Resolve isn't running this must return a clean
    error dict, never raise/crash."""
    monkeypatch.setattr("pipeline.stages.davinci_bridge._is_resolve_process_running", lambda: False)
    fake_image = tmp_path / "source.jpg"
    fake_image.write_bytes(b"not a real jpeg but exists")
    result = grade_still_image(fake_image, style="natural")
    assert result["success"] is False
    assert "not currently running" in result["error"]


def test_is_resolve_process_running_reflects_actual_tasklist_state():
    """Smoke test that the real tasklist-based check runs without error and returns a
    bool (doesn't assert True/False since whether Resolve happens to be open on this
    machine right now is environment-dependent)."""
    result = _is_resolve_process_running()
    assert isinstance(result, bool)
