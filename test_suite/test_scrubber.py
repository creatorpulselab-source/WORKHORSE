"""Unit tests for pipeline/stages/scrubber.py (EXIF/metadata scrubbing).

Uses real small in-memory-generated images on disk (tmp_path fixture) so no
network/GPU dependency is needed - PIL is already a hard dependency of the
photo pipeline.
"""
from PIL import Image
from PIL.ExifTags import Base as ExifBase

from pipeline.stages.scrubber import MetadataScrubber


def _make_image_with_exif(path, fmt="JPEG"):
    img = Image.new("RGB", (8, 8), color=(120, 40, 200))
    exif = img.getexif()
    exif[ExifBase.Make.value] = "TestCamera"
    img.save(path, format=fmt, exif=exif)


def test_scrub_image_removes_exif_in_place(tmp_path):
    img_path = tmp_path / "photo.jpg"
    _make_image_with_exif(img_path)

    with Image.open(img_path) as before:
        assert len(before.getexif()) > 0

    scrubber = MetadataScrubber()
    result = scrubber.scrub_image(img_path)

    assert result["success"] is True
    with Image.open(img_path) as after:
        assert len(after.getexif()) == 0
    assert scrubber.scrubbed_count == 1


def test_scrub_image_to_separate_output_path(tmp_path):
    img_path = tmp_path / "photo.png"
    out_path = tmp_path / "clean.png"
    _make_image_with_exif(img_path, fmt="PNG")

    scrubber = MetadataScrubber()
    result = scrubber.scrub_image(img_path, output_path=out_path)

    assert result["success"] is True
    assert out_path.exists()
    with Image.open(out_path) as after:
        assert len(after.getexif()) == 0


def test_scrub_image_missing_file_returns_error():
    scrubber = MetadataScrubber()
    result = scrubber.scrub_image("F:/WORKHORSE/does_not_exist.jpg")
    assert result["success"] is False
    assert "error" in result
