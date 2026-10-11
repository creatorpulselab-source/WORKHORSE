"""Regression tests for pipeline/stages/fiverr_service_bot.py's fulfill_order() flow,
completing Tier 2 coverage for the Fiverr business line (asset-SELECTION safety was
already fixed/tested in test_tier0_security_fixes.py - these tests cover the
packaging/delivery step that runs after an asset has been chosen).

Correction to the QA evaluation's "guessable filename" concern: /api/download/fiverr/
{order_number} is NOT in PUBLIC_PATHS/PUBLIC_PREFIXES in dashboard/server.py, so it
already requires a valid WORKHORSE login session - an attacker would need a valid
session first, unlike the deliberately-public, token-protected
/api/download/order/{token} webhook flow. Still worth locking in with a test so this
protection can't silently regress.
"""
import zipfile
from pathlib import Path

import pytest


@pytest.fixture
def fiverr_bot(tmp_path):
    from pipeline.stages.fiverr_service_bot import FiverrServiceBot
    return FiverrServiceBot(output_base=str(tmp_path))


def test_fulfill_order_creates_correctly_named_zip_matching_download_route(fiverr_bot, tmp_path):
    result = fiverr_bot.fulfill_order(gig_id="gig_retouch", order_number="FO_5001", client_name="Jane Doe")

    assert result["status"] == "completed"
    zip_path = Path(result["delivery_zip"])
    assert zip_path.name == "FO_5001_DELIVERY_PACKAGE.zip"  # exact route convention
    assert zip_path.exists()


def test_fulfill_order_includes_delivery_note_even_with_no_assets(fiverr_bot):
    result = fiverr_bot.fulfill_order(gig_id="gig_retouch", order_number="FO_5002", assets=None)

    assert result["status"] == "completed"
    with zipfile.ZipFile(result["delivery_zip"]) as zf:
        names = zf.namelist()
    assert "DELIVERY_NOTE_AND_INSTRUCTIONS.txt" in names
    assert result["files_count"] == 1


def test_fulfill_order_silently_skips_a_missing_asset_path_without_failing(fiverr_bot, tmp_path):
    real_asset = tmp_path / "real_delivery.zip"
    real_asset.write_bytes(b"real content")
    missing_asset = str(tmp_path / "this_file_was_never_created.zip")

    result = fiverr_bot.fulfill_order(
        gig_id="gig_retouch", order_number="FO_5003",
        assets=[str(real_asset), missing_asset]
    )

    assert result["status"] == "completed"
    with zipfile.ZipFile(result["delivery_zip"]) as zf:
        names = zf.namelist()
    assert "real_delivery.zip" in names
    assert "this_file_was_never_created.zip" not in names
    assert result["files_count"] == 2  # delivery note + the one real asset


def test_fulfill_order_includes_real_assets_with_actual_bytes(fiverr_bot, tmp_path):
    asset_a = tmp_path / "master.jpg"
    asset_a.write_bytes(b"photo-bytes-aaa")
    asset_b = tmp_path / "grade.jpg"
    asset_b.write_bytes(b"photo-bytes-bbb")

    result = fiverr_bot.fulfill_order(
        gig_id="gig_retouch", order_number="FO_5004",
        assets=[str(asset_a), str(asset_b)]
    )

    with zipfile.ZipFile(result["delivery_zip"]) as zf:
        assert zf.read("master.jpg") == b"photo-bytes-aaa"
        assert zf.read("grade.jpg") == b"photo-bytes-bbb"


def test_delivery_note_mentions_client_name_and_falls_back_for_unknown_gig(fiverr_bot):
    note = fiverr_bot.generate_delivery_note("gig_retouch", client_name="Jane Doe")
    assert "Jane Doe" in note

    # An unrecognized gig_id must fall back to a known gig rather than raising.
    fallback_note = fiverr_bot.generate_delivery_note("not_a_real_gig_id", client_name="Jane Doe")
    assert "Jane Doe" in fallback_note


def test_get_all_gigs_returns_every_configured_gig(fiverr_bot):
    gigs = fiverr_bot.get_all_gigs()
    gig_ids = {g["id"] for g in gigs}
    assert {"gig_retouch", "gig_teaser", "gig_copy", "gig_banner"}.issubset(gig_ids)


def test_download_fiverr_route_requires_authentication():
    """Confirms the guessable-filename concern is mitigated: this route is not in
    PUBLIC_PATHS/PUBLIC_PREFIXES, so an unauthenticated request is rejected before a
    filename is ever even considered."""
    from fastapi.testclient import TestClient
    from dashboard import server
    client = TestClient(server.app)
    response = client.get("/api/download/fiverr/FO_5001", follow_redirects=False)
    assert response.status_code == 401
