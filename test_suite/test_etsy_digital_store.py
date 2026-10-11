"""Regression tests for pipeline/stages/etsy_digital_store.py - the Etsy digital
product bundler used by both the manual /api/etsy/bundle dashboard route and the
Stripe/Gumroad webhook auto-fulfillment path (order_radar.py's _fulfill_web_order via
webhook_product_map).

Bug found and fixed here (2026-10-10): bundle_etsy_product() had no validation of its
product_type argument - an unrecognized value matched none of the conditional content
blocks, silently producing a near-empty "bundle" (just the listing metadata text file,
zero actual product content) while still returning status "ok". Because this function
is reachable from webhook_product_map (an admin-configurable mapping), a misconfigured
entry could have resulted in a paying Stripe/Gumroad customer receiving an empty
deliverable with no error surfaced anywhere. Fixed to fail safe toward "all" instead.
"""
import zipfile
from pathlib import Path

import pytest


@pytest.fixture
def store(tmp_path):
    from pipeline.stages.etsy_digital_store import EtsyDigitalStore
    return EtsyDigitalStore(output_base=str(tmp_path))


def test_all_bundle_contains_every_product_category(store):
    result = store.bundle_etsy_product(product_type="all")

    assert result["status"] == "ok"
    assert result["bundle_name"] == "ETSY_DIGITAL_CREATOR_ALL_PACK"
    zip_path = Path(result["zip_path"])
    assert zip_path.name == "ETSY_DIGITAL_CREATOR_ALL_PACK.zip"
    assert zip_path.exists()

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()

    # 5 Lightroom presets + install guide
    assert sum(1 for n in names if n.startswith("01_Lightroom_Presets/") and n.endswith(".xmp")) == 5
    assert "01_Lightroom_Presets/INSTALLATION_GUIDE.txt" in names
    # 3 legal contracts
    assert sum(1 for n in names if n.startswith("02_Model_Contracts_and_Releases/")) == 3
    # posing guide
    assert "03_Boudoir_Posing_Cards/50_Boudoir_Posing_Guide_Cards.html" in names
    # 2 social promo templates
    assert sum(1 for n in names if n.startswith("04_Social_Promo_Templates/")) == 2
    # listing metadata always included
    assert "ETSY_LISTING_METADATA_AND_TAGS.txt" in names


@pytest.mark.parametrize("product_type,expected_prefix,other_prefixes", [
    ("presets", "01_Lightroom_Presets/", ["02_Model_Contracts_and_Releases/", "03_Boudoir_Posing_Cards/", "04_Social_Promo_Templates/"]),
    ("contracts", "02_Model_Contracts_and_Releases/", ["01_Lightroom_Presets/", "03_Boudoir_Posing_Cards/", "04_Social_Promo_Templates/"]),
    ("posing", "03_Boudoir_Posing_Cards/", ["01_Lightroom_Presets/", "02_Model_Contracts_and_Releases/", "04_Social_Promo_Templates/"]),
    ("templates", "04_Social_Promo_Templates/", ["01_Lightroom_Presets/", "02_Model_Contracts_and_Releases/", "03_Boudoir_Posing_Cards/"]),
])
def test_single_category_bundle_contains_only_that_category(store, product_type, expected_prefix, other_prefixes):
    result = store.bundle_etsy_product(product_type=product_type)
    assert result["bundle_name"] == f"ETSY_DIGITAL_CREATOR_{product_type.upper()}_PACK"

    with zipfile.ZipFile(result["zip_path"]) as zf:
        names = zf.namelist()

    assert any(n.startswith(expected_prefix) for n in names)
    for other in other_prefixes:
        assert not any(n.startswith(other) for n in names)
    assert "ETSY_LISTING_METADATA_AND_TAGS.txt" in names  # always included regardless of category


def test_unrecognized_product_type_falls_back_to_all_instead_of_shipping_empty_bundle(store):
    result = store.bundle_etsy_product(product_type="typo_in_webhook_product_map")

    assert result["status"] == "ok"
    assert result["product_type"] == "all"  # silently corrected
    assert result["requested_product_type"] == "typo_in_webhook_product_map"  # original is still visible
    assert result["total_files"] > 0

    with zipfile.ZipFile(result["zip_path"]) as zf:
        names = zf.namelist()
    # Must contain real product content, not just the listing text file.
    assert any(n.endswith(".xmp") for n in names)
    assert any(n.startswith("02_Model_Contracts_and_Releases/") for n in names)


def test_lightroom_presets_are_five_distinct_named_xmp_files_with_real_content(store):
    presets = store.generate_lightroom_presets()
    assert len(presets) == 5
    for fname, content in presets.items():
        assert fname.endswith(".xmp")
        assert "crs:UUID" in content
        assert "<x:xmpmeta" in content


def test_legal_contracts_cover_adult_release_2257_and_location(store):
    contracts = store.generate_legal_contracts()
    assert "01_Adult_Model_Release_Agreement.html" in contracts
    assert "02_18_USC_2257_Compliance_Checklist.html" in contracts
    assert "03_Shoot_Location_Release_Agreement.html" in contracts


def test_zip_entries_are_relative_not_absolute_paths(store):
    """Confirms a customer's extracted ZIP never reveals the local server's absolute
    filesystem path (e.g. F:/WORKHORSE/workspace/etsy_bundles/...)."""
    result = store.bundle_etsy_product(product_type="all")
    with zipfile.ZipFile(result["zip_path"]) as zf:
        for name in zf.namelist():
            assert not name.startswith("/")
            assert ":" not in name  # no Windows drive letter (e.g. "F:/...") leaked in
