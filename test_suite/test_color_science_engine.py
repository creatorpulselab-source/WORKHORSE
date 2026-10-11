"""Unit tests for the professional color science and retouch engine:
- color_science.py (adaptive skin modeling, linear-light highlights/shadows, cast correction, masked retouch)
- photo_retoucher.py pro_natural integration (ICC-tagged JPEGs, 16-bit TIFFs, batch execution)
"""
import shutil
import tempfile
from pathlib import Path
from PIL import Image

import cv2
import numpy as np
import pytest

from pipeline.stages.color_science import (
    estimate_skin,
    process_image,
    to_uint8_dithered,
    SKIN_HUE_BAND
)
from pipeline.stages.photo_retoucher import PhotoRetoucher, STYLE_PROFILES


def _make_test_portrait() -> np.ndarray:
    """Create a synthetic test portrait with skin oval, eyes, and cool background."""
    img = np.full((240, 180, 3), (150, 70, 40), dtype=np.uint8)  # Cool blue background
    cv2.ellipse(img, (90, 110), (55, 75), 0, 0, 360, (120, 150, 200), -1)  # skin oval
    cv2.circle(img, (70, 95), 4, (255, 255, 255), -1)  # white eyes
    cv2.circle(img, (110, 95), 4, (255, 255, 255), -1)
    cv2.circle(img, (70, 95), 1, (0, 0, 0), -1)  # dark pupils
    cv2.circle(img, (110, 95), 1, (0, 0, 0), -1)
    rng = np.random.default_rng(7)
    for _ in range(8):
        y, x = rng.integers(60, 160), rng.integers(55, 125)
        cv2.circle(img, (int(x), int(y)), 1, (40, 40, 160), -1)  # small red blemish specks
    return img


@pytest.fixture
def test_portrait():
    return _make_test_portrait()


def test_skin_model_detects_skin_oval(test_portrait):
    f_bgr = test_portrait.astype(np.float32) / 255.0
    lab = cv2.cvtColor(f_bgr, cv2.COLOR_BGR2LAB)
    mask, stats = estimate_skin(lab)
    assert mask is not None
    assert stats is not None
    assert stats["coverage_pct"] > 5.0
    # Center of face oval should be confident skin
    assert mask[110, 90] > 0.5
    # Corner (cool blue background) should be non-skin
    assert mask[5, 5] < 0.1


def test_process_image_runs_end_to_end(test_portrait):
    out_f32, report = process_image(test_portrait, smooth_strength=0.3)
    assert out_f32.dtype == np.float32
    assert out_f32.shape == test_portrait.shape
    assert out_f32.min() >= 0.0
    assert out_f32.max() <= 1.0
    assert "p99_7_after" in report
    assert "exposure_ev" in report


def test_dithered_uint8_conversion(test_portrait):
    out_f32, _ = process_image(test_portrait)
    u8 = to_uint8_dithered(out_f32)
    assert u8.dtype == np.uint8
    assert u8.shape == test_portrait.shape
    assert np.all(u8 >= 0) and np.all(u8 <= 255)


def test_photo_retoucher_pro_natural_preset(test_portrait):
    r = PhotoRetoucher()
    graded = r.apply_color_grade(test_portrait, preset="pro_natural")
    assert graded.dtype == np.uint8
    assert graded.shape == test_portrait.shape


def test_pro_natural_batch_pipeline(tmp_path, test_portrait):
    out_base = tmp_path / "output"
    in_dir = tmp_path / "input"
    in_dir.mkdir(parents=True)
    img_path = in_dir / "test_shot.jpg"
    cv2.imwrite(str(img_path), test_portrait)

    retoucher = PhotoRetoucher(output_base=str(out_base))
    result = retoucher.process_photo_batch(
        image_paths=[img_path],
        shoot_name="test_pro_batch",
        preset="pro_natural",
        edit_style="pro_natural",
        smooth_strength=0.3,
        print_master=True
    )

    assert result["status"] == "completed"
    assert result["total_processed"] == 1

    pkg_dir = out_base / "test_pro_batch_RETOUCHED_PACKAGE"
    master_file = pkg_dir / "01_master_fullres" / "test_shot_retouched.jpg"
    print_file = pkg_dir / "05_print_master_16bit" / "test_shot_print_master.tiff"

    assert master_file.exists()
    assert print_file.exists()

    # Verify master JPEG has embedded ICC profile
    with Image.open(master_file) as im:
        icc = im.info.get("icc_profile")
        assert icc is not None, "Master JPEG must have an embedded ICC profile"

    # Verify 16-bit TIFF print master
    tiff_img = cv2.imread(str(print_file), cv2.IMREAD_UNCHANGED)
    assert tiff_img.dtype == np.uint16, "Print master must be 16-bit TIFF"
