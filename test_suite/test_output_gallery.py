"""Unit tests for the unified 'Completed Work' output gallery, added 2026-10-10.

Addresses the Commander's "I need a folder where all completed work goes that I
can get to from in WORKHORSE... everything asked for in chat should come to the
chat where it can be viewed and or downloaded" request.

Covers:
1. shared/output_categories.py - the single source of truth used by both
   dashboard/server.py (gallery + download endpoints) and ai_operator.py (per-tool
   media tagging) - category auto-detection, download URL construction, and that a
   file outside every registered directory is never silently miscategorized.
2. dashboard/server.py's _resolve_output_file() - path traversal protection, unknown
   category rejection, missing file rejection - the only way a caller can reach a
   file through this authenticated system.
3. ai_operator.py's _attach_media() helper - used by every content-producing tool
   branch (comfy_generate, comfy_image_to_video, comfy_generate_3d_pbr,
   comfy_generate_client_character, create_banner, aura_retouch, apex_package,
   comfy_background_change, comfy_subject_swap) - confirms it never raises on a
   nonexistent/garbage path and produces a well-formed media entry for a real file.
4. The /api/outputs/gallery endpoint's category filtering and recency sorting.
"""
import asyncio
from pathlib import Path

import pytest
from fastapi import HTTPException

from shared.output_categories import (
    OUTPUT_CATEGORIES,
    build_download_url,
    categorize_path,
    build_media_entry,
)


@pytest.fixture
def patched_categories(tmp_path, monkeypatch):
    """Points every registered output category at an isolated tmp directory so
    these tests never touch (or depend on) real F:/WORKHORSE output folders."""
    new_dirs = {}
    for key in OUTPUT_CATEGORIES:
        cat_dir = tmp_path / key
        cat_dir.mkdir(parents=True, exist_ok=True)
        new_dirs[key] = cat_dir
        monkeypatch.setitem(OUTPUT_CATEGORIES, key, {**OUTPUT_CATEGORIES[key], "dir": cat_dir})
    return new_dirs


# --------------------------------------------------------------------------
# shared/output_categories.py
# --------------------------------------------------------------------------

def test_categorize_path_detects_known_category(patched_categories):
    f = patched_categories["marketing_images"] / "render.png"
    f.write_bytes(b"fake-png-bytes")
    assert categorize_path(f) == "marketing_images"


def test_categorize_path_returns_none_for_unregistered_location(tmp_path, patched_categories):
    stray = tmp_path / "somewhere_else" / "file.png"
    stray.parent.mkdir(parents=True, exist_ok=True)
    stray.write_bytes(b"x")
    assert categorize_path(stray) is None


def test_build_download_url_rejects_file_not_in_claimed_category(patched_categories):
    """A file that physically lives under 'client_deliveries' must never be issued
    a download URL under 'marketing_images' even if explicitly asked for - this is
    what prevents a client file from ever being mislabeled as postable content."""
    wrong_file = patched_categories["client_deliveries"] / "client_file.zip"
    wrong_file.write_bytes(b"x")
    assert build_download_url("marketing_images", wrong_file) is None


def test_build_download_url_builds_correct_authenticated_url(patched_categories):
    f = patched_categories["banners"] / "my banner.png"
    f.write_bytes(b"x")
    url = build_download_url("banners", f)
    assert url == "/api/outputs/file?category=banners&path=my%20banner.png"


def test_build_download_url_unknown_category_returns_none(patched_categories):
    f = patched_categories["banners"] / "f.png"
    f.write_bytes(b"x")
    assert build_download_url("not_a_real_category", f) is None


def test_build_media_entry_full_shape(patched_categories):
    f = patched_categories["marketing_videos"] / "clip.mp4"
    f.write_bytes(b"x")
    entry = build_media_entry(f, title="A Test Clip")
    assert entry == {
        "type": "video",
        "url": "/api/outputs/file?category=marketing_videos&path=clip.mp4",
        "filename": "clip.mp4",
        "title": "A Test Clip",
        "category_label": OUTPUT_CATEGORIES["marketing_videos"]["label"],
    }


def test_build_media_entry_returns_none_for_uncategorized_path(tmp_path, patched_categories):
    stray = tmp_path / "random.png"
    stray.write_bytes(b"x")
    assert build_media_entry(stray) is None


def test_client_character_renders_recursive_subfolder_still_categorized(patched_categories):
    """Client character renders live in per-character subfolders - categorize_path
    must still resolve those nested files correctly."""
    nested = patched_categories["client_character_renders"] / "charlette" / "render.png"
    nested.parent.mkdir(parents=True, exist_ok=True)
    nested.write_bytes(b"x")
    assert categorize_path(nested) == "client_character_renders"


# --------------------------------------------------------------------------
# dashboard/server.py - _resolve_output_file() and /api/outputs/gallery
# --------------------------------------------------------------------------

def test_resolve_output_file_returns_real_file(patched_categories):
    from dashboard.server import _resolve_output_file
    f = patched_categories["marketing_images"] / "a.png"
    f.write_bytes(b"x")
    resolved = _resolve_output_file("marketing_images", "a.png")
    assert resolved == f.resolve()


def test_resolve_output_file_rejects_path_traversal(patched_categories):
    from dashboard.server import _resolve_output_file
    with pytest.raises(HTTPException) as exc_info:
        _resolve_output_file("marketing_images", "../client_deliveries/secret.zip")
    assert exc_info.value.status_code == 403


def test_resolve_output_file_rejects_unknown_category(patched_categories):
    from dashboard.server import _resolve_output_file
    with pytest.raises(HTTPException) as exc_info:
        _resolve_output_file("not_a_real_category", "a.png")
    assert exc_info.value.status_code == 404


def test_resolve_output_file_rejects_missing_file(patched_categories):
    from dashboard.server import _resolve_output_file
    with pytest.raises(HTTPException) as exc_info:
        _resolve_output_file("marketing_images", "does_not_exist.png")
    assert exc_info.value.status_code == 404


def test_outputs_gallery_filters_by_category_and_sorts_by_recency(patched_categories):
    from dashboard.server import get_outputs_gallery
    import time

    img_dir = patched_categories["marketing_images"]
    (img_dir / "older.png").write_bytes(b"x")
    old_mtime = time.time() - 100
    import os
    os.utime(img_dir / "older.png", (old_mtime, old_mtime))
    (img_dir / "newer.png").write_bytes(b"x")

    other_dir = patched_categories["banners"]
    (other_dir / "banner.png").write_bytes(b"x")

    result = asyncio.run(get_outputs_gallery(category="marketing_images"))
    assert result["total_found"] == 2
    filenames = [item["filename"] for item in result["items"]]
    assert filenames == ["newer.png", "older.png"]  # newest first
    assert all(item["category"] == "marketing_images" for item in result["items"])


def test_outputs_gallery_scans_all_categories_when_none_given(patched_categories):
    from dashboard.server import get_outputs_gallery
    (patched_categories["marketing_images"] / "a.png").write_bytes(b"x")
    (patched_categories["banners"] / "b.png").write_bytes(b"x")

    result = asyncio.run(get_outputs_gallery())
    categories_found = {item["category"] for item in result["items"]}
    assert {"marketing_images", "banners"}.issubset(categories_found)


# --------------------------------------------------------------------------
# ai_operator.py's _attach_media() - used by every content-producing tool branch
# --------------------------------------------------------------------------

def test_attach_media_adds_entry_for_real_categorized_file(patched_categories):
    from pipeline.stages.ai_operator import AIOperatorEngine
    f = patched_categories["marketing_images"] / "result.png"
    f.write_bytes(b"x")
    result = AIOperatorEngine._attach_media({"status": "ok"}, f, title="My Render")
    assert result["media"][0]["filename"] == "result.png"
    assert result["media"][0]["title"] == "My Render"


def test_attach_media_noops_for_nonexistent_path(patched_categories):
    from pipeline.stages.ai_operator import AIOperatorEngine
    result = AIOperatorEngine._attach_media({"status": "ok"}, "F:/does/not/exist.png")
    assert "media" not in result


def test_attach_media_noops_for_none_path():
    from pipeline.stages.ai_operator import AIOperatorEngine
    result = AIOperatorEngine._attach_media({"status": "ok"}, None)
    assert "media" not in result


def test_attach_media_noops_for_uncategorized_real_file(tmp_path, patched_categories):
    """A real file that happens to sit outside every registered output directory
    must never be silently tagged as media - prevents an unrelated filesystem path
    from ever being exposed through the authenticated download endpoint."""
    from pipeline.stages.ai_operator import AIOperatorEngine
    stray = tmp_path / "unrelated.png"
    stray.write_bytes(b"x")
    result = AIOperatorEngine._attach_media({"status": "ok"}, stray)
    assert "media" not in result


def test_attach_media_appends_multiple_entries(patched_categories):
    from pipeline.stages.ai_operator import AIOperatorEngine
    f1 = patched_categories["marketing_images"] / "a.png"
    f1.write_bytes(b"x")
    f2 = patched_categories["marketing_videos"] / "b.mp4"
    f2.write_bytes(b"x")
    result = {"status": "ok"}
    AIOperatorEngine._attach_media(result, f1, title="first")
    AIOperatorEngine._attach_media(result, f2, title="second")
    assert len(result["media"]) == 2
    assert result["media"][0]["title"] == "first"
    assert result["media"][1]["title"] == "second"
