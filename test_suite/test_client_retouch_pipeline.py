"""Regression tests for the "client sent a package through Synapse for color
correction but the colors looked the same" incident (2026-10-10).

Root cause chain that was found and fixed:
1. A client's photos were uploaded as a single .zip archive. Nothing in the upload
   path extracted it, so aura_retouch/apex_package only ever saw the opaque .zip.
2. PhotoRetoucher.process_photo_batch silently skips any path cv2.imread() can't
   read (a .zip, in this case) and still returned status="completed" with zero
   photos processed - no error anywhere.
3. apex_package only ever zipped whatever was sitting in the raw upload batch -
   it had no way to find or include aura_retouch's actual retouched output, so it
   "successfully" repackaged the untouched original and reported the job done.

These tests lock in the three fixes:
- dashboard/server.py: `_extract_zip_uploads_into_batch` pulls real images out of an
  uploaded .zip into the same batch folder.
- pipeline/stages/photo_retoucher.py: `process_photo_batch` fails loudly
  (status="failed") instead of silently "completing" with zero processed photos.
- pipeline/stages/ai_operator.py: `apex_package` ships Aura's actual retouched
  package when one exists for the batch, and otherwise explicitly warns that the
  files are being packaged AS-IS/un-edited rather than claiming the job is done.
"""
import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
from PIL import Image


def _make_test_jpeg(path: Path, size=(40, 30), color=(120, 60, 200)):
    Image.new("RGB", size, color).save(path, "JPEG")


# --------------------------------------------------------------------------
# dashboard/server.py: _extract_zip_uploads_into_batch
# --------------------------------------------------------------------------

def test_extract_zip_uploads_pulls_images_out_of_a_client_zip(tmp_path):
    from dashboard.server import _extract_zip_uploads_into_batch

    batch_dir = tmp_path / "batch_test"
    batch_dir.mkdir()
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    img_a = src_dir / "JT2A5689.jpg"
    img_b = src_dir / "JT2A5690.jpg"
    _make_test_jpeg(img_a)
    _make_test_jpeg(img_b, color=(10, 200, 30))

    zip_path = batch_dir / "ClientShoot.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(img_a, arcname="JT2A5689.jpg")
        zf.write(img_b, arcname="nested/JT2A5690.jpg")  # nested path must flatten safely
        zf.writestr("notes.txt", "not an image")  # non-image entries are ignored

    extracted = _extract_zip_uploads_into_batch(batch_dir, zip_path)

    assert set(extracted) == {"JT2A5689.jpg", "JT2A5690.jpg"}
    assert (batch_dir / "JT2A5689.jpg").exists()
    assert (batch_dir / "JT2A5690.jpg").exists()
    # The original zip is left in place untouched, not deleted.
    assert zip_path.exists()


def test_extract_zip_uploads_rejects_path_traversal_members(tmp_path):
    from dashboard.server import _extract_zip_uploads_into_batch

    batch_dir = tmp_path / "batch_test"
    batch_dir.mkdir()
    outside_marker = tmp_path / "escaped.jpg"

    zip_path = batch_dir / "malicious.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../escaped.jpg", b"not-a-real-image-but-shouldnt-matter")

    extracted = _extract_zip_uploads_into_batch(batch_dir, zip_path)

    assert extracted == []
    assert not outside_marker.exists()


def test_extract_zip_uploads_handles_duplicate_filenames(tmp_path):
    from dashboard.server import _extract_zip_uploads_into_batch

    batch_dir = tmp_path / "batch_test"
    batch_dir.mkdir()
    img = tmp_path / "a.jpg"
    _make_test_jpeg(img)

    zip_path = batch_dir / "dup.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(img, arcname="shot.jpg")
        zf.write(img, arcname="folder1/shot.jpg")
        zf.write(img, arcname="folder2/shot.jpg")

    extracted = _extract_zip_uploads_into_batch(batch_dir, zip_path)

    assert len(extracted) == 3
    assert len(set(extracted)) == 3  # no file was silently overwritten


def test_extract_zip_uploads_bad_zip_is_non_fatal(tmp_path):
    from dashboard.server import _extract_zip_uploads_into_batch

    batch_dir = tmp_path / "batch_test"
    batch_dir.mkdir()
    fake_zip = batch_dir / "not_really_a_zip.zip"
    fake_zip.write_bytes(b"this is not a zip file")

    extracted = _extract_zip_uploads_into_batch(batch_dir, fake_zip)

    assert extracted == []  # does not raise


# --------------------------------------------------------------------------
# pipeline/stages/photo_retoucher.py: fail loudly on zero processed photos
# --------------------------------------------------------------------------

def test_process_photo_batch_fails_when_every_input_is_unreadable(tmp_path):
    from pipeline.stages.photo_retoucher import PhotoRetoucher

    not_an_image = tmp_path / "ClientShoot.zip"
    with zipfile.ZipFile(not_an_image, "w") as zf:
        zf.writestr("placeholder.txt", "zip contents aren't exposed as an image path")

    retoucher = PhotoRetoucher()
    retoucher.output_base = tmp_path / "output"

    result = retoucher.process_photo_batch(
        image_paths=[not_an_image],
        shoot_name="incident_regression_shoot",
        edit_style="concert_stage",
    )

    assert result["status"] == "failed"
    assert result["total_processed"] == 0
    assert "zip" in result["error"].lower() or "image" in result["error"].lower()
    # No empty package should be left behind masquerading as a finished delivery.
    assert not (tmp_path / "output" / "incident_regression_shoot_PHOTO_PACKAGE.zip").exists()


def test_process_photo_batch_still_completes_with_at_least_one_real_image(tmp_path):
    from pipeline.stages.photo_retoucher import PhotoRetoucher

    good_image = tmp_path / "real.jpg"
    _make_test_jpeg(good_image)
    bad_file = tmp_path / "bad.zip"
    bad_file.write_bytes(b"not an image")

    retoucher = PhotoRetoucher()
    retoucher.output_base = tmp_path / "output"

    result = retoucher.process_photo_batch(
        image_paths=[good_image, bad_file],
        shoot_name="mixed_batch_shoot",
        edit_style="natural",
    )

    assert result["status"] == "completed"
    assert result["total_processed"] == 1


# --------------------------------------------------------------------------
# pipeline/stages/ai_operator.py: aura_retouch surfaces retoucher failure honestly
# --------------------------------------------------------------------------

def test_aura_retouch_tool_reports_error_when_retoucher_processes_zero_photos(tmp_path, monkeypatch):
    from pipeline.stages.ai_operator import AIOperatorEngine

    batch_dir = tmp_path / "batch_bad"
    batch_dir.mkdir()
    zip_upload = batch_dir / "AshleyEsteves_live.zip"
    zip_upload.write_bytes(b"pretend zip bytes")

    engine = AIOperatorEngine()
    # aura_retouch with no "files" named defaults to everything in the batch - here
    # that's only the raw, unextracted zip, reproducing the exact incident shape.
    tool_call = {"tool": "aura_retouch", "edit_style": "concert_stage"}

    result = engine.execute_internal_tool(tool_call, batch_dir=batch_dir)

    assert result["status"] == "error"
    assert "media" not in result  # must never attach a bogus "finished" media card


def test_aura_retouch_missing_named_files_lists_whats_actually_in_the_batch(tmp_path):
    from pipeline.stages.ai_operator import AIOperatorEngine

    batch_dir = tmp_path / "batch_mismatch"
    batch_dir.mkdir()
    (batch_dir / "AshleyEsteves_live.zip").write_bytes(b"zip bytes")

    engine = AIOperatorEngine()
    tool_call = {
        "tool": "aura_retouch",
        "files": ["ashley_esteves_live_show_1.jpg", "ashley_esteves_live_show_2.jpg"],
        "edit_style": "concert_stage",
    }

    result = engine.execute_internal_tool(tool_call, batch_dir=batch_dir)

    assert result["status"] == "error"
    assert "ashley_esteves_live_show_1.jpg" in result["error"]
    assert "AshleyEsteves_live.zip" in result["error"]


# --------------------------------------------------------------------------
# pipeline/stages/ai_operator.py: apex_package no longer claims an un-edited
# passthrough is a finished, color-corrected deliverable
# --------------------------------------------------------------------------

@pytest.fixture
def apex_package_dirs(tmp_path, monkeypatch):
    client_inbox = tmp_path / "client_inbox"
    client_outputs = tmp_path / "client_deliveries"
    photos_output = tmp_path / "photos_output"
    client_inbox.mkdir()
    client_outputs.mkdir()
    photos_output.mkdir()
    monkeypatch.setattr("pipeline.stages.ai_operator.CLIENT_INBOX_DIR", client_inbox)
    monkeypatch.setattr("pipeline.stages.ai_operator.CLIENT_OUTPUTS_DIR", client_outputs)
    monkeypatch.setattr("pipeline.stages.ai_operator.WORKSPACE_DIR", tmp_path)
    return {"inbox": client_inbox, "outputs": client_outputs, "photos_output": photos_output}


def test_apex_package_warns_instead_of_claiming_success_with_no_retouch(apex_package_dirs):
    from pipeline.stages.ai_operator import AIOperatorEngine

    batch_dir = apex_package_dirs["inbox"] / "batch_no_retouch"
    batch_dir.mkdir()
    (batch_dir / "AshleyEsteves_live.zip").write_bytes(b"raw unedited client upload")

    engine = AIOperatorEngine()
    result = engine.execute_internal_tool(
        {"tool": "apex_package", "client_name": "Ashley Esteves"}, batch_dir=batch_dir
    )

    assert result["status"] == "warning"
    assert result["edited"] is False
    assert "AS-IS" in result["message"]
    assert "aura_retouch" in result["message"]


def test_apex_package_ships_the_real_retouched_output_when_it_exists(apex_package_dirs):
    from pipeline.stages.ai_operator import AIOperatorEngine

    batch_dir = apex_package_dirs["inbox"] / "batch_with_retouch"
    batch_dir.mkdir()
    (batch_dir / "AshleyEsteves_live.zip").write_bytes(b"raw unedited client upload")

    # Simulate a successful prior aura_retouch run for this exact batch.
    pkg_dir = apex_package_dirs["photos_output"] / "AshleyEsteves_LiveShow_RETOUCHED_PACKAGE"
    pkg_dir.mkdir(parents=True)
    manifest = {
        "shoot_name": "AshleyEsteves_LiveShow",
        "edit_style": "concert_stage",
        "source_batch": batch_dir.name,
        "source_filenames": ["JT2A5689.jpg", "JT2A5690.jpg"],
    }
    (pkg_dir / "manifest.json").write_text(json.dumps(manifest))
    retouched_zip = apex_package_dirs["photos_output"] / "AshleyEsteves_LiveShow_PHOTO_PACKAGE.zip"
    with zipfile.ZipFile(retouched_zip, "w") as zf:
        zf.writestr("01_master_fullres/JT2A5689_retouched.jpg", b"actually-edited-bytes")

    engine = AIOperatorEngine()
    result = engine.execute_internal_tool(
        {"tool": "apex_package", "client_name": "Ashley Esteves"}, batch_dir=batch_dir
    )

    assert result["status"] == "ok"
    assert result["edited"] is True
    assert "concert_stage" in result["message"]
    assert set(result["files"]) == {"JT2A5689.jpg", "JT2A5690.jpg"}

    # The delivered package must contain the EDITED bytes, not the raw client upload.
    delivered_zip = Path(result["download_path"])
    with zipfile.ZipFile(delivered_zip) as zf:
        names = zf.namelist()
        assert "01_master_fullres/JT2A5689_retouched.jpg" in names
        assert zf.read("01_master_fullres/JT2A5689_retouched.jpg") == b"actually-edited-bytes"
        assert "AshleyEsteves_live.zip" not in names  # raw upload isn't duplicated in
