"""Regression tests for the Dropzone auto-fulfillment fixes (2026-10-10), activated
because the Commander wants hands-off photo delivery to be a real, running part of
the workflow. Confirmed bugs fixed here, each with a test proving the fix:

1. Flat-copy filename collisions across subfolders no longer silently overwrite
   (and lose) an earlier photo with the same name.
2. `photos_processed` no longer counts files that failed to decode as images; a
   batch where EVERY file fails to decode is reported as a clear failure instead of
   silently "completing" with an empty delivery.
3. Leftover `_extracting_*` directories (from a crash mid-run) are never picked up
   again as a new incoming order.
4. A file-stability window means an item still being copied/written is skipped (and
   retried later), not opened mid-write.
5. One failing item in a scan no longer prevents the other items from being
   processed, and a failed item is left in place (not renamed PROCESSED_) instead of
   being silently marked done.
6. The final delivery ZIP is named `{order_name}_DELIVERY_PACKAGE.zip` - matching
   exactly what `/api/download/fiverr/{order_number}` expects (a prior
   `_FINAL_DELIVERY_PACKAGE` name silently did not match that route at all).
"""
import os
import time
import zipfile
from pathlib import Path

import pytest
from PIL import Image


def _make_test_jpeg(path: Path, color=(100, 150, 200)):
    Image.new("RGB", (40, 30), color).save(path, "JPEG")


def _age_path(path: Path, seconds_old: float):
    """Backdates a file/dir's mtime so the stability check treats it as settled,
    without needing a real sleep in the test."""
    old_time = time.time() - seconds_old
    os.utime(path, (old_time, old_time))
    if path.is_dir():
        for f in path.rglob("*"):
            os.utime(f, (old_time, old_time))


@pytest.fixture
def isolated_dropzone(tmp_path, monkeypatch):
    from pipeline.stages import dropzone_fulfiller as dz_module
    dropzone_dir = tmp_path / "dropzone"
    output_dir = tmp_path / "fiverr_deliveries"
    dropzone_dir.mkdir()
    output_dir.mkdir()
    monkeypatch.setattr(dz_module, "DROPZONE_DIR", dropzone_dir)
    monkeypatch.setattr(dz_module, "OUTPUT_DIR", output_dir)
    fulfiller = dz_module.DropzoneFulfiller()
    return {"dropzone": dropzone_dir, "output": output_dir, "fulfiller": fulfiller}


def test_successful_order_produces_correctly_named_zip_and_marks_input_processed(isolated_dropzone):
    order_dir = isolated_dropzone["dropzone"] / "ClientFoo"
    order_dir.mkdir()
    _make_test_jpeg(order_dir / "shot1.jpg")
    _make_test_jpeg(order_dir / "shot2.jpg", color=(10, 200, 10))
    _age_path(order_dir, seconds_old=60)

    results = isolated_dropzone["fulfiller"].process_dropzone()

    assert len(results) == 1
    r = results[0]
    assert r["status"] == "completed"
    assert r["photos_processed"] == 2
    assert r["photos_skipped_unreadable"] == []
    zip_path = Path(r["zip_path"])
    assert zip_path.name == "ClientFoo_DELIVERY_PACKAGE.zip"  # matches /api/download/fiverr/{order_number}
    assert zip_path.exists()
    assert not order_dir.exists()
    assert (isolated_dropzone["dropzone"] / "PROCESSED_ClientFoo").exists()


def test_filename_collision_across_subfolders_does_not_lose_a_photo(isolated_dropzone):
    order_dir = isolated_dropzone["dropzone"] / "ClientCollision"
    sub_a = order_dir / "cam_a"
    sub_b = order_dir / "cam_b"
    sub_a.mkdir(parents=True)
    sub_b.mkdir(parents=True)
    _make_test_jpeg(sub_a / "IMG_0001.jpg", color=(255, 0, 0))
    _make_test_jpeg(sub_b / "IMG_0001.jpg", color=(0, 255, 0))  # same filename, different subfolder
    _age_path(order_dir, seconds_old=60)

    results = isolated_dropzone["fulfiller"].process_dropzone()

    assert results[0]["status"] == "completed"
    assert results[0]["photos_processed"] == 2  # both photos survived, neither overwritten


def test_unreadable_file_is_not_counted_as_processed_when_some_images_are_valid(isolated_dropzone):
    order_dir = isolated_dropzone["dropzone"] / "ClientMixed"
    order_dir.mkdir()
    _make_test_jpeg(order_dir / "good.jpg")
    (order_dir / "corrupt.jpg").write_bytes(b"not a real jpeg")
    _age_path(order_dir, seconds_old=60)

    results = isolated_dropzone["fulfiller"].process_dropzone()

    r = results[0]
    assert r["status"] == "completed"
    assert r["photos_processed"] == 1
    assert "corrupt.jpg" in r["photos_skipped_unreadable"]


def test_batch_where_every_file_is_unreadable_fails_instead_of_delivering_empty_zip(isolated_dropzone):
    order_dir = isolated_dropzone["dropzone"] / "ClientAllBad"
    order_dir.mkdir()
    (order_dir / "corrupt1.jpg").write_bytes(b"garbage")
    (order_dir / "corrupt2.jpg").write_bytes(b"also garbage")
    _age_path(order_dir, seconds_old=60)

    results = isolated_dropzone["fulfiller"].process_dropzone()

    r = results[0]
    assert r["status"] == "failed"
    assert not list(isolated_dropzone["output"].glob("*.zip"))
    # Left in place for inspection/retry, not silently marked done.
    assert order_dir.exists()
    assert not (isolated_dropzone["dropzone"] / "PROCESSED_ClientAllBad").exists()


def test_leftover_extracting_directory_is_never_reprocessed_as_a_new_order(isolated_dropzone):
    leftover = isolated_dropzone["dropzone"] / "_extracting_SomeOldCrashedOrder"
    leftover.mkdir()
    _make_test_jpeg(leftover / "already_extracted.jpg")
    _age_path(leftover, seconds_old=60)

    results = isolated_dropzone["fulfiller"].process_dropzone()

    assert results == []  # must be completely ignored, not treated as a fresh drop
    assert leftover.exists()  # left alone either way


def test_recently_modified_item_is_skipped_until_stable(isolated_dropzone):
    order_dir = isolated_dropzone["dropzone"] / "ClientFreshlyDropped"
    order_dir.mkdir()
    _make_test_jpeg(order_dir / "shot.jpg")
    # No _age_path() call - mtime is "now", simulating a drop still possibly mid-copy.

    results = isolated_dropzone["fulfiller"].process_dropzone()
    assert results == []  # skipped this cycle, not processed prematurely
    assert order_dir.exists()  # untouched, will be retried on a later scan

    _age_path(order_dir, seconds_old=60)
    results_after_settling = isolated_dropzone["fulfiller"].process_dropzone()
    assert results_after_settling[0]["status"] == "completed"


def test_one_failing_item_does_not_block_or_crash_processing_of_the_others(isolated_dropzone):
    good_order = isolated_dropzone["dropzone"] / "ClientGood"
    good_order.mkdir()
    _make_test_jpeg(good_order / "shot.jpg")
    _age_path(good_order, seconds_old=60)

    bad_zip = isolated_dropzone["dropzone"] / "ClientBadZip.zip"
    bad_zip.write_bytes(b"this is not a valid zip file")
    _age_path(bad_zip, seconds_old=60)

    results = isolated_dropzone["fulfiller"].process_dropzone()

    by_name = {r["order_name"]: r for r in results}
    assert by_name["ClientGood"]["status"] == "completed"
    assert by_name["ClientBadZip"]["status"] == "failed"
    # The failed zip stays in place (not renamed PROCESSED_) so it can be retried/inspected.
    assert bad_zip.exists()
    assert not (isolated_dropzone["dropzone"] / "PROCESSED_ClientBadZip.zip").exists()
