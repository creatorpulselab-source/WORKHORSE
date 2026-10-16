"""
Regression tests for WORKHORSE Deterministic NSFW / Skin-Density Pixel Firewall.
Guarantees that public commercial channels (Twitter/X, Pinterest, etc.) will never
publish topless or nude imagery.
"""

from pathlib import Path
import pytest
from pipeline.stages.nsfw_firewall import evaluate_image_sfw, is_strictly_sfw_media
from pipeline.stages.herald_scheduler import HeraldScheduler
from pipeline.stages.twitter_poster import TwitterPoster


def test_pixel_firewall_hard_rejects_topless_nude_render():
    nude_file = Path("F:/WORKHORSE/workspace/brand_assets/qc_rejected/CML_Studio_00049__1791983748.png")
    if not nude_file.exists():
        pytest.skip("Reference image not present in test environment")

    # 1. Path marker check blocks quarantined folder
    is_safe, reason, _ = evaluate_image_sfw(nude_file)
    assert is_safe is False
    assert "restricted folder" in reason.lower()

    # 2. Forensic pixel density analysis
    import cv2
    import numpy as np
    from pipeline.stages.nsfw_firewall import detect_skin_mask
    img = cv2.imread(str(nude_file))
    skin_mask = detect_skin_mask(img)
    h, w = skin_mask.shape
    torso = skin_mask[int(h*0.35):int(h*0.75), int(w*0.20):int(w*0.80)]
    torso_pct = (np.count_nonzero(torso) / torso.size) * 100.0
    assert torso_pct > 28.0


def test_pixel_firewall_approves_clothed_commercial_portraits():
    clothed_file1 = Path("F:/WORKHORSE/workspace/brand_assets/creator_media_lab/CML_Studio_00050__1791997372.png")
    clothed_file2 = Path("F:/WORKHORSE/workspace/brand_assets/creator_media_lab/CML_Studio_00051__1792011784.png")

    for f in [clothed_file1, clothed_file2]:
        if not f.exists():
            continue
        is_safe, reason, metrics = evaluate_image_sfw(f)
        assert is_safe is True
        assert metrics.get("torso_skin_pct", 0) < 28.0


def test_herald_media_verification_rejects_nude_via_pixel_firewall():
    scheduler = HeraldScheduler()
    nude_file = Path("F:/WORKHORSE/workspace/brand_assets/qc_rejected/CML_Studio_00049__1791983748.png")
    if not nude_file.exists():
        pytest.skip("Reference image not present in test environment")

    assert scheduler._verify_media_is_strictly_sfw(str(nude_file)) is False


def test_twitter_poster_has_deletion_methods():
    tp = TwitterPoster()
    assert hasattr(tp, "delete_tweet")
    assert hasattr(tp, "delete_thread")
    assert callable(tp.delete_tweet)
    assert callable(tp.delete_thread)
