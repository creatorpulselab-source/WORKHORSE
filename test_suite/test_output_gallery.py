"""Unit tests for the unified 'Completed Work' output gallery, added 2026-10-10,
and its 4-business-line separation (Fiverr / Etsy / Social Media / Synapse) added
2026-10-10 (same day, follow-up request).

Addresses the Commander's "I need a folder where all completed work goes that I
can get to from in WORKHORSE... everything asked for in chat should come to the
chat where it can be viewed and or downloaded" request, and the follow-up "yes it
needs to be separated. Fiverr, Etsy, Social media, Synapse."

Covers:
1. shared/output_categories.py - the single source of truth used by both
   dashboard/server.py (gallery + download endpoints) and ai_operator.py (per-tool
   media tagging) - category auto-detection, download URL construction, and that a
   file outside every registered directory is never silently miscategorized.
2. Every category's 'group' field (fiverr/etsy/social/synapse) and that the 4 new
   business-line-specific categories (fiverr_deliveries, etsy_bundles, the 4
   social_* categories) are registered with the real folders their producing code
   actually writes to.
3. categorize_path()'s depth-first, exact-vs-recursive disambiguation - needed now
   that social media's per-brand video folders intentionally nest inside the
   general-purpose Synapse video folder (comfy_video_renders/creator_pulse_lab/
   lives inside comfy_video_renders/) - and exclude_prefixes, which keeps Herald's
   CPL_/CML_-prefixed mirrored image copies from double-counting under Synapse.
4. dashboard/server.py's _resolve_output_file() - path traversal protection, unknown
   category rejection, missing file rejection - the only way a caller can reach a
   file through this authenticated system.
5. ai_operator.py's _attach_media() helper - used by every content-producing tool
   branch (comfy_generate, comfy_image_to_video, comfy_generate_3d_pbr,
   comfy_generate_client_character, create_banner, aura_retouch, apex_package,
   comfy_background_change, comfy_subject_swap) - confirms it never raises on a
   nonexistent/garbage path and produces a well-formed media entry for a real file.
6. The /api/outputs/gallery endpoint's category/group filtering and recency sorting.
7. comfyui_bridge.generate_image_to_video()'s new dest_subdir param - confirms
   Herald's scheduled social videos land in a dedicated per-brand subfolder,
   genuinely separate from ad-hoc Synapse chat videos (which keep dest_subdir=None).
"""
import asyncio
from pathlib import Path

import pytest
from fastapi import HTTPException

from shared.output_categories import (
    OUTPUT_CATEGORIES,
    GROUP_LABELS,
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
        "download_url": "/api/outputs/file?category=marketing_videos&path=clip.mp4",
        "preview_url": "/api/outputs/preview?category=marketing_videos&path=clip.mp4",
        "preview_type": "video",
        "filename": "clip.mp4",
        "title": "A Test Clip",
        "category_label": OUTPUT_CATEGORIES["marketing_videos"]["label"],
        "group": "synapse",
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
# 4-business-line grouping (Fiverr / Etsy / Social Media / Synapse)
# --------------------------------------------------------------------------

def test_every_category_has_a_valid_group():
    for cat_key, cat in OUTPUT_CATEGORIES.items():
        assert cat.get("group") in GROUP_LABELS, f"{cat_key} is missing a valid group"


def test_fiverr_and_etsy_categories_point_at_their_real_pipeline_folders():
    """Must match the actual folders fiverr_service_bot.py/dropzone_fulfiller.py and
    etsy_digital_store.py write finished deliverables to - a mismatch here would
    silently make the Fiverr/Etsy gallery tabs empty forever."""
    assert OUTPUT_CATEGORIES["fiverr_deliveries"]["dir"].name == "fiverr_deliveries"
    assert OUTPUT_CATEGORIES["fiverr_deliveries"]["group"] == "fiverr"
    assert OUTPUT_CATEGORIES["etsy_bundles"]["dir"].name == "etsy_bundles"
    assert OUTPUT_CATEGORIES["etsy_bundles"]["group"] == "etsy"


def test_social_media_categories_are_distinct_from_synapse_categories():
    social_cats = [k for k, c in OUTPUT_CATEGORIES.items() if c["group"] == "social"]
    assert set(social_cats) == {
        "social_images_mainstream", "social_images_pulse",
        "social_videos_mainstream", "social_videos_pulse",
    }
    # Social video folders must be real, distinct subfolders - not the same directory
    # Synapse's general marketing_videos category scans.
    assert OUTPUT_CATEGORIES["social_videos_pulse"]["dir"] != OUTPUT_CATEGORIES["marketing_videos"]["dir"]
    assert OUTPUT_CATEGORIES["social_videos_pulse"]["dir"].parent == OUTPUT_CATEGORIES["marketing_videos"]["dir"]


def test_categorize_path_disambiguates_nested_social_video_from_synapse_video(tmp_path, monkeypatch):
    """Real-world layout: comfy_video_renders/creator_pulse_lab/ nests inside
    comfy_video_renders/ itself. A file directly in the parent folder must resolve to
    the general Synapse category; a file in the brand subfolder must resolve to the
    specific Social Media category - never the other way around, and never both."""
    video_root = tmp_path / "comfy_video_renders"
    pulse_dir = video_root / "creator_pulse_lab"
    pulse_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setitem(OUTPUT_CATEGORIES, "marketing_videos", {**OUTPUT_CATEGORIES["marketing_videos"], "dir": video_root})
    monkeypatch.setitem(OUTPUT_CATEGORIES, "social_videos_pulse", {**OUTPUT_CATEGORIES["social_videos_pulse"], "dir": pulse_dir})

    synapse_video = video_root / "ad_hoc_clip.mp4"
    synapse_video.write_bytes(b"x")
    social_video = pulse_dir / "scheduled_post.mp4"
    social_video.write_bytes(b"x")

    assert categorize_path(synapse_video) == "marketing_videos"
    assert categorize_path(social_video) == "social_videos_pulse"


def test_marketing_images_excludes_brand_prefixed_mirror_copies(patched_categories):
    """CPL_/CML_-prefixed files in comfy_renders are mirrored copies of a brand-
    targeted social render (see comfyui_bridge's brand_target mirroring) - they must
    never be auto-tagged as Synapse content, since the canonical copy already lives
    under the Social Media group's own brand folder."""
    img_dir = patched_categories["marketing_images"]
    (img_dir / "WORKHORSE_Render_00099.png").write_bytes(b"x")
    (img_dir / "CPL_Boudoir_00099.png").write_bytes(b"x")
    (img_dir / "CML_Studio_00099.png").write_bytes(b"x")

    assert categorize_path(img_dir / "WORKHORSE_Render_00099.png") == "marketing_images"
    assert categorize_path(img_dir / "CPL_Boudoir_00099.png") is None
    assert categorize_path(img_dir / "CML_Studio_00099.png") is None


def test_outputs_gallery_filters_by_group(patched_categories):
    from dashboard.server import get_outputs_gallery
    (patched_categories["fiverr_deliveries"] / "ORDER1_DELIVERY_PACKAGE.zip").write_bytes(b"x")
    (patched_categories["etsy_bundles"] / "bundle.zip").write_bytes(b"x")
    (patched_categories["marketing_images"] / "a.png").write_bytes(b"x")

    result = asyncio.run(get_outputs_gallery(group="fiverr"))
    assert result["total_found"] == 1
    assert result["items"][0]["category"] == "fiverr_deliveries"
    assert result["items"][0]["group"] == "fiverr"
    assert result["items"][0]["group_label"] == GROUP_LABELS["fiverr"]


def test_outputs_gallery_excludes_brand_mirrored_copies_from_synapse_group(patched_categories):
    from dashboard.server import get_outputs_gallery
    img_dir = patched_categories["marketing_images"]
    (img_dir / "WORKHORSE_Render_00001.png").write_bytes(b"x")
    (img_dir / "CPL_Boudoir_00001.png").write_bytes(b"x")

    result = asyncio.run(get_outputs_gallery(category="marketing_images"))
    filenames = [item["filename"] for item in result["items"]]
    assert filenames == ["WORKHORSE_Render_00001.png"]


# --------------------------------------------------------------------------
# comfyui_bridge.generate_image_to_video()'s dest_subdir social-media separation
# --------------------------------------------------------------------------

def test_generate_image_to_video_defaults_to_synapse_folder_without_dest_subdir(tmp_path, monkeypatch):
    from pipeline.stages.comfyui_bridge import ComfyUIBridge
    import pipeline.stages.comfyui_bridge as bridge_module

    fake_video_root = tmp_path / "comfy_video_renders"
    monkeypatch.setattr(bridge_module, "VIDEO_RENDERS_DIR", fake_video_root)

    bridge = ComfyUIBridge()
    staged = tmp_path / "staged.mp4"
    staged.write_bytes(b"x")
    src_img = tmp_path / "source.png"
    src_img.write_bytes(b"x")

    monkeypatch.setattr(bridge, "check_connection", lambda: {"online": True})
    monkeypatch.setattr(bridge, "upload_image_to_comfy", lambda p: "uploaded.png")
    monkeypatch.setattr(bridge, "build_image_to_video_workflow", lambda **kwargs: {})
    monkeypatch.setattr(bridge, "queue_prompt", lambda wf: {"prompt_id": "abc123"})
    monkeypatch.setattr(bridge, "wait_for_video_execution", lambda prompt_id, timeout_seconds=900: [{"filename": "staged.mp4"}])
    monkeypatch.setattr(bridge, "download_video", lambda **kwargs: staged)

    result = bridge.generate_image_to_video(source_image_path=src_img, prompt="test motion")
    assert result["success"] is True
    assert Path(result["file_path"]).parent == fake_video_root
    assert result["url_path"] == f"/static/brand_assets/comfy_video_renders/{Path(result['file_path']).name}"


def test_generate_image_to_video_uses_brand_subfolder_with_dest_subdir(tmp_path, monkeypatch):
    """Herald's scheduled social posts pass dest_subdir=brand_key so the video lands
    in a dedicated per-brand folder, genuinely separate from ad-hoc Synapse videos."""
    from pipeline.stages.comfyui_bridge import ComfyUIBridge
    import pipeline.stages.comfyui_bridge as bridge_module

    fake_video_root = tmp_path / "comfy_video_renders"
    monkeypatch.setattr(bridge_module, "VIDEO_RENDERS_DIR", fake_video_root)

    bridge = ComfyUIBridge()
    staged = tmp_path / "staged.mp4"
    staged.write_bytes(b"x")
    src_img = tmp_path / "source.png"
    src_img.write_bytes(b"x")

    monkeypatch.setattr(bridge, "check_connection", lambda: {"online": True})
    monkeypatch.setattr(bridge, "upload_image_to_comfy", lambda p: "uploaded.png")
    monkeypatch.setattr(bridge, "build_image_to_video_workflow", lambda **kwargs: {})
    monkeypatch.setattr(bridge, "queue_prompt", lambda wf: {"prompt_id": "abc123"})
    monkeypatch.setattr(bridge, "wait_for_video_execution", lambda prompt_id, timeout_seconds=900: [{"filename": "staged.mp4"}])
    monkeypatch.setattr(bridge, "download_video", lambda **kwargs: staged)

    result = bridge.generate_image_to_video(source_image_path=src_img, prompt="test motion", dest_subdir="creator_pulse_lab")
    assert result["success"] is True
    assert Path(result["file_path"]).parent == fake_video_root / "creator_pulse_lab"
    assert result["url_path"] == f"/static/brand_assets/comfy_video_renders/creator_pulse_lab/{Path(result['file_path']).name}"


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


@pytest.fixture
def output_http_client(monkeypatch):
    from fastapi.testclient import TestClient
    from dashboard import server
    monkeypatch.setattr(server, "_get_session_secret", lambda: "test-output-preview-secret")
    # No context manager: do not start real GPU/scheduler lifespan tasks.
    with_cookie = TestClient(server.app)
    from shared.auth import make_session_token
    with_cookie.cookies.set(server.SESSION_COOKIE, make_session_token("test-output-preview-secret"))
    yield with_cookie
    with_cookie.close()


def test_view_is_inline_download_is_attachment_and_video_supports_ranges(patched_categories, output_http_client):
    file = patched_categories["marketing_videos"] / "clip.mp4"
    file.write_bytes(b"0123456789")
    query = {"category": "marketing_videos", "path": file.name}
    view = output_http_client.get("/api/outputs/preview", params=query)
    assert view.status_code == 200
    assert view.headers["content-disposition"].startswith("inline;")
    assert view.headers["content-type"] == "video/mp4"
    assert view.content == file.read_bytes()
    download = output_http_client.get("/api/outputs/file", params=query)
    assert download.headers["content-disposition"].startswith("attachment;")
    partial = output_http_client.get("/api/outputs/preview", params=query, headers={"Range": "bytes=2-5"})
    assert partial.status_code == 206
    assert partial.content == b"2345"


def test_zip_contents_viewable_without_extracting_and_html_is_sandboxed(patched_categories, output_http_client):
    from zipfile import ZipFile
    package = patched_categories["fiverr_deliveries"] / "order.zip"
    with ZipFile(package, "w") as archive:
        archive.writestr("folder/my image.png", b"png")
        archive.writestr("preview.html", "<h1>Work</h1><script>alert(1)</script>")
        archive.writestr("notes.txt", "Created work notes")
        archive.writestr("unknown.bin", b"binary")
        archive.writestr("../unsafe.png", b"unsafe")
    query = {"category": "fiverr_deliveries", "path": package.name}
    listing = output_http_client.get("/api/outputs/archive", params=query)
    assert listing.status_code == 200
    items = {item["filename"]: item for item in listing.json()["items"]}
    assert "../unsafe.png" not in items
    assert items["unknown.bin"]["preview_url"] is None
    image = output_http_client.get(items["folder/my image.png"]["preview_url"])
    assert image.content == b"png"
    assert image.headers["content-type"] == "image/png"
    assert image.headers["content-disposition"].startswith("inline;")
    html = output_http_client.get(items["preview.html"]["preview_url"])
    assert "sandbox;" in html.headers["content-security-policy"]
    assert html.headers["x-content-type-options"] == "nosniff"
    assert output_http_client.get(items["notes.txt"]["preview_url"]).text == "Created work notes"
    download = output_http_client.get(items["folder/my image.png"]["download_url"])
    assert download.content == b"png"
    assert download.headers["content-disposition"].startswith("attachment;")
    assert list(package.parent.iterdir()) == [package]
    assert output_http_client.get("/api/outputs/preview", params={**query, "member": "../unsafe.png"}).status_code == 400
    assert output_http_client.get("/api/outputs/preview", params={**query, "member": "missing.png"}).status_code == 404


def test_preview_endpoints_require_login(patched_categories, output_http_client):
    output_http_client.cookies.clear()
    for route in ("preview", "archive", "file"):
        response = output_http_client.get(f"/api/outputs/{route}", params={"category": "banners", "path": "a.png"})
        assert response.status_code == 401


def test_archive_limits_and_corruption_are_explicit(patched_categories, output_http_client, monkeypatch):
    from zipfile import ZipFile
    from dashboard import server
    package = patched_categories["etsy_bundles"] / "bundle.zip"
    query = {"category": "etsy_bundles", "path": package.name}
    with ZipFile(package, "w") as archive:
        archive.writestr("big.txt", "12345")
    monkeypatch.setattr(server, "MAX_PREVIEW_BYTES", 4)
    item = output_http_client.get("/api/outputs/archive", params=query).json()["items"][0]
    assert item["preview_url"] is None
    assert output_http_client.get("/api/outputs/preview", params={**query, "member": "big.txt"}).status_code == 413
    monkeypatch.setattr(server, "MAX_ARCHIVE_ENTRIES", 0)
    assert output_http_client.get("/api/outputs/archive", params=query).status_code == 413
    package.write_bytes(b"not a zip")
    assert output_http_client.get("/api/outputs/archive", params=query).status_code == 422


def test_gallery_provides_separate_view_and_download_urls(patched_categories):
    from dashboard.server import get_outputs_gallery
    (patched_categories["marketing_3d_models"] / "character.glb").write_bytes(b"glb")
    item = asyncio.run(get_outputs_gallery(category="marketing_3d_models"))["items"][0]
    assert item["preview_type"] == "model_3d"
    assert item["preview_url"].startswith("/api/outputs/preview?")
    assert item["download_url"].startswith("/api/outputs/file?")


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
