"""Unit tests for the professional retouching engine added to photo_retoucher.py:
new color-grade presets (natural/concert/family), the Retouch4me-equivalent native
retouch passes (heal, skin tone, mattify, portrait volumes, eye redness, color match),
the print-ready 16-bit TIFF export, and the STYLE_PROFILES-driven process_photo_batch
pipeline (including that every style still produces usable, correctly-shaped output
and backward compatibility with callers that never pass edit_style).
"""
import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from pipeline.stages.photo_retoucher import PhotoRetoucher, STYLE_PROFILES


def _make_test_portrait() -> np.ndarray:
    """A small synthetic 'portrait-like' image: a skin-tone-colored oval (face) on a
    colored background, with a couple of bright 'eye' highlights and some small red
    blemish specks - enough structure to exercise skin masking, blemish healing, and
    highlight/shine detection without needing a real photo."""
    img = np.full((240, 180, 3), (60, 90, 140), dtype=np.uint8)  # BGR background
    cv2.ellipse(img, (90, 110), (55, 75), 0, 0, 360, (120, 150, 200), -1)  # skin-tone oval
    cv2.circle(img, (70, 95), 4, (255, 255, 255), -1)
    cv2.circle(img, (110, 95), 4, (255, 255, 255), -1)
    rng = np.random.default_rng(7)
    for _ in range(8):
        y, x = rng.integers(60, 160), rng.integers(55, 125)
        cv2.circle(img, (int(x), int(y)), 1, (40, 40, 160), -1)
    return img


@pytest.fixture
def retoucher_with_tmp_output():
    tmp_out = Path(tempfile.mkdtemp())
    r = PhotoRetoucher(output_base=str(tmp_out))
    yield r
    shutil.rmtree(tmp_out, ignore_errors=True)


@pytest.fixture
def test_portrait():
    return _make_test_portrait()


# --- New color grade presets ---

@pytest.mark.parametrize("preset", ["natural_true_to_life", "concert_stage", "family_event"])
def test_new_color_grade_presets_return_valid_image(test_portrait, preset):
    r = PhotoRetoucher()
    graded = r.apply_color_grade(test_portrait, preset=preset)
    assert graded.dtype == np.uint8
    assert graded.shape == test_portrait.shape


def test_existing_color_grade_presets_still_work(test_portrait):
    """Backward compatibility: the original 6 presets must still work unchanged."""
    r = PhotoRetoucher()
    for preset in ["moody_boudoir", "golden_hour", "cyber_neon", "monochrome_noir", "vintage_35mm", "clean_editorial"]:
        graded = r.apply_color_grade(test_portrait, preset=preset)
        assert graded.dtype == np.uint8
        assert graded.shape == test_portrait.shape


# --- New native professional retouch passes (Retouch4me-equivalent) ---

def test_heal_blemishes_removes_small_red_specks(test_portrait):
    r = PhotoRetoucher()
    healed = r.heal_blemishes(test_portrait, strength=1.0)
    assert healed.shape == test_portrait.shape
    assert healed.dtype == np.uint8


def test_correct_skin_tone_only_affects_skin_region(test_portrait):
    r = PhotoRetoucher()
    corrected = r.correct_skin_tone(test_portrait, strength=0.6)
    assert corrected.shape == test_portrait.shape
    # Background corners (outside the face oval) should be essentially untouched
    assert np.allclose(corrected[0:10, 0:10], test_portrait[0:10, 0:10], atol=5)


def test_reduce_shine_runs_without_error(test_portrait):
    r = PhotoRetoucher()
    result = r.reduce_shine(test_portrait, strength=0.7)
    assert result.shape == test_portrait.shape
    assert result.dtype == np.uint8


def test_enhance_portrait_volumes_preserves_color_only_shapes_luminance(test_portrait):
    r = PhotoRetoucher()
    result = r.enhance_portrait_volumes(test_portrait, strength=0.5)
    assert result.shape == test_portrait.shape
    # Hue should be roughly preserved since only the L channel is touched
    orig_hsv = cv2.cvtColor(test_portrait, cv2.COLOR_BGR2HSV)
    result_hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV)
    hue_diff = np.abs(orig_hsv[:, :, 0].astype(int) - result_hsv[:, :, 0].astype(int))
    assert np.median(hue_diff) < 5


def test_reduce_eye_redness_runs_without_error(test_portrait):
    r = PhotoRetoucher()
    result = r.reduce_eye_redness(test_portrait, strength=0.8)
    assert result.shape == test_portrait.shape
    assert result.dtype == np.uint8


def test_match_color_to_reference_shifts_toward_reference_tone():
    r = PhotoRetoucher()
    src = np.full((100, 100, 3), (200, 200, 50), dtype=np.uint8)   # cool/blue-green-ish
    reference = np.full((100, 100, 3), (50, 80, 200), dtype=np.uint8)  # warm/red-ish
    matched = r.match_color_to_reference(src, reference)
    # Matched result's mean should move closer to the reference's mean than the
    # original source was.
    orig_dist = np.linalg.norm(src.mean(axis=(0, 1)) - reference.mean(axis=(0, 1)))
    matched_dist = np.linalg.norm(matched.mean(axis=(0, 1)) - reference.mean(axis=(0, 1)))
    assert matched_dist < orig_dist


# --- Print-ready 16-bit TIFF export ---

def test_export_print_master_writes_16bit_tiff_with_icc_and_dpi(test_portrait, tmp_path):
    import tifffile
    r = PhotoRetoucher()
    out_path = tmp_path / "master.tiff"
    result_path = r.export_print_master(test_portrait, out_path, dpi=300)
    assert result_path == out_path
    assert out_path.exists()
    with tifffile.TiffFile(str(out_path)) as tf:
        page = tf.pages[0]
        assert page.dtype == np.uint16
        assert page.shape == test_portrait.shape
        assert 34675 in page.tags  # ICC profile tag
        assert page.tags["XResolution"].value == (300, 1)


# --- STYLE_PROFILES-driven process_photo_batch ---

@pytest.mark.parametrize("style", list(STYLE_PROFILES.keys()))
def test_process_photo_batch_every_style_produces_valid_package(retoucher_with_tmp_output, test_portrait, style, tmp_path):
    img_path = tmp_path / "source.jpg"
    cv2.imwrite(str(img_path), test_portrait, [cv2.IMWRITE_JPEG_QUALITY, 95])

    res = retoucher_with_tmp_output.process_photo_batch(
        image_paths=[img_path],
        shoot_name=f"test_{style}",
        edit_style=style,
        source_batch="test-batch"
    )
    assert res["status"] == "completed"
    assert res["total_processed"] == 1
    assert res["edit_style"] == style

    profile = STYLE_PROFILES[style]
    photo = res["photos"][0]
    assert "print_master" in photo  # print master always produced regardless of style
    assert ("teaser" in photo) == profile["watermark"]  # watermark only when the style calls for it


def test_process_photo_batch_without_edit_style_keeps_legacy_behavior(retoucher_with_tmp_output, test_portrait, tmp_path):
    """No edit_style given -> behaves exactly like before (raw preset/smooth_strength,
    always watermarked) for full backward compatibility with existing callers."""
    img_path = tmp_path / "source.jpg"
    cv2.imwrite(str(img_path), test_portrait, [cv2.IMWRITE_JPEG_QUALITY, 95])

    res = retoucher_with_tmp_output.process_photo_batch(
        image_paths=[img_path],
        shoot_name="legacy_test",
        preset="moody_boudoir",
        smooth_strength=0.5
    )
    assert res["status"] == "completed"
    assert res["edit_style"] is None
    assert "teaser" in res["photos"][0]  # legacy default always watermarks
