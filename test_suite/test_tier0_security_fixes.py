"""Regression tests for Tier 0 fixes identified in the QA priority execution plan
(2026-10-10): confirmed active bugs/security gaps in Order Radar webhook fulfillment
and Fiverr delivery, fixed directly (not just documented) because each had an obvious
correct direction:

1. Stripe webhook signature verification now rejects old/replayed timestamps, and
   fulfillment now checks payment_status before shipping product (an unpaid
   checkout.session.completed must not fulfill).
2. Secrets (app_password, stripe_webhook_secret) are never echoed back in plaintext
   by any config-reading method/route - only boolean presence flags.
3. The customer-facing download URL is now configurable instead of a hardcoded,
   likely-unreachable private Tailscale IP, and warns loudly when left unset.
4. Fiverr fulfillment asset selection now picks the true newest-by-modification-time
   file (not an arbitrary directory-listing/alphabetical "last" entry), supports an
   explicit client-bound asset_filename, and surfaces a visible warning whenever more
   than one candidate file existed and the Commander didn't pick one explicitly -
   closing a cross-client delivery risk.
5. The webhook fulfillment race condition (two near-simultaneous deliveries for the
   same order both passing the "not already fulfilled" check) is now closed with a
   lock + immediate reservation.
"""
import hashlib
import hmac
import json
import os
import threading
import time
import zipfile
from pathlib import Path

import pytest


# --------------------------------------------------------------------------
# shared helpers
# --------------------------------------------------------------------------

def _make_radar(tmp_path):
    from pipeline.stages.order_radar import OrderRadar
    return OrderRadar(base_dir=str(tmp_path))


def _stripe_signature_header(secret: str, payload: bytes, timestamp: int) -> str:
    signed_payload = f"{timestamp}.{payload.decode('utf-8')}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={sig}"


# --------------------------------------------------------------------------
# Stripe: replay-window rejection
# --------------------------------------------------------------------------

def test_stripe_signature_accepts_a_fresh_timestamp(tmp_path):
    radar = _make_radar(tmp_path)
    radar.update_config(stripe_webhook_secret="whsec_test123")
    payload = b'{"type":"checkout.session.completed"}'
    header = _stripe_signature_header("whsec_test123", payload, int(time.time()))
    assert radar.verify_stripe_signature(payload, header) is True


def test_stripe_signature_rejects_an_old_replayed_timestamp(tmp_path):
    radar = _make_radar(tmp_path)
    radar.update_config(stripe_webhook_secret="whsec_test123")
    payload = b'{"type":"checkout.session.completed"}'
    old_timestamp = int(time.time()) - 10_000  # far outside the 300s tolerance
    header = _stripe_signature_header("whsec_test123", payload, old_timestamp)
    # The HMAC itself is perfectly valid for this payload+timestamp - only the
    # timestamp-tolerance check should reject it.
    assert radar.verify_stripe_signature(payload, header) is False


# --------------------------------------------------------------------------
# Stripe: unpaid-session fulfillment gap
# --------------------------------------------------------------------------

@pytest.fixture
def stubbed_bundle_and_email(monkeypatch, tmp_path):
    """Prevents real ZIP building and real SMTP sends during these tests."""
    from pipeline.stages import order_radar as order_radar_module
    bundle_calls = []

    class FakeEtsyStore:
        def bundle_etsy_product(self, product_type):
            bundle_calls.append(product_type)
            fake_zip = tmp_path / f"{product_type}_bundle.zip"
            with zipfile.ZipFile(fake_zip, "w") as zf:
                zf.writestr("readme.txt", "fake bundle")
            return {"status": "ok", "zip_path": str(fake_zip), "bundle_name": f"{product_type}_bundle"}

    monkeypatch.setattr(
        "pipeline.stages.etsy_digital_store.EtsyDigitalStore", FakeEtsyStore
    )
    email_calls = []

    def fake_send_email(self, recipient, product_title, download_url):
        email_calls.append((recipient, product_title, download_url))
        return {"success": True, "recipient": recipient}

    monkeypatch.setattr(order_radar_module.OrderRadar, "send_fulfillment_email", fake_send_email)
    return {"bundle_calls": bundle_calls, "email_calls": email_calls}


def _signed_stripe_payload(radar, session_obj: dict):
    event = {"type": "checkout.session.completed", "data": {"object": session_obj}}
    payload = json.dumps(event).encode("utf-8")
    header = _stripe_signature_header(radar.config["stripe_webhook_secret"], payload, int(time.time()))
    return payload, header


def test_stripe_webhook_does_not_fulfill_an_unpaid_session(tmp_path, stubbed_bundle_and_email):
    radar = _make_radar(tmp_path)
    radar.update_config(stripe_webhook_secret="whsec_test123")
    session_obj = {
        "id": "cs_test_unpaid",
        "customer_email": "buyer@example.com",
        "payment_status": "unpaid",
        "amount_total": 1500,
    }
    payload, header = _signed_stripe_payload(radar, session_obj)

    result = radar.handle_stripe_webhook(payload, header)

    assert result["success"] is True
    assert result["ignored"] is True
    assert "payment_status" in result["reason"]
    assert stubbed_bundle_and_email["bundle_calls"] == []  # must never build/ship product
    assert not any(o.get("id") == "cs_test_unpaid" for o in radar.orders)


def test_stripe_webhook_fulfills_a_paid_session(tmp_path, stubbed_bundle_and_email):
    radar = _make_radar(tmp_path)
    radar.update_config(stripe_webhook_secret="whsec_test123")
    session_obj = {
        "id": "cs_test_paid",
        "customer_email": "buyer@example.com",
        "payment_status": "paid",
        "amount_total": 1500,
    }
    payload, header = _signed_stripe_payload(radar, session_obj)

    result = radar.handle_stripe_webhook(payload, header)

    assert result["success"] is True
    assert stubbed_bundle_and_email["bundle_calls"] == ["all"]
    assert any(o.get("id") == "cs_test_paid" and o.get("status") == "fulfilled_auto" for o in radar.orders)


def test_stripe_webhook_fulfills_when_payment_status_is_absent_for_backward_compat(tmp_path, stubbed_bundle_and_email):
    radar = _make_radar(tmp_path)
    radar.update_config(stripe_webhook_secret="whsec_test123")
    session_obj = {"id": "cs_test_legacy", "customer_email": "buyer@example.com", "amount_total": 1500}
    payload, header = _signed_stripe_payload(radar, session_obj)

    result = radar.handle_stripe_webhook(payload, header)

    assert result["success"] is True
    assert stubbed_bundle_and_email["bundle_calls"] == ["all"]


# --------------------------------------------------------------------------
# Webhook fulfillment race condition
# --------------------------------------------------------------------------

def test_concurrent_duplicate_fulfillment_only_builds_one_bundle(tmp_path, monkeypatch):
    from pipeline.stages import order_radar as order_radar_module

    radar = _make_radar(tmp_path)
    build_started = threading.Event()
    release_build = threading.Event()
    bundle_calls = []

    class SlowFakeEtsyStore:
        def bundle_etsy_product(self, product_type):
            bundle_calls.append(product_type)
            build_started.set()
            release_build.wait(timeout=5)  # hold the "slow work" open so both threads overlap
            fake_zip = tmp_path / "slow_bundle.zip"
            with zipfile.ZipFile(fake_zip, "w") as zf:
                zf.writestr("x.txt", "x")
            return {"status": "ok", "zip_path": str(fake_zip), "bundle_name": "slow_bundle"}

    monkeypatch.setattr("pipeline.stages.etsy_digital_store.EtsyDigitalStore", SlowFakeEtsyStore)
    monkeypatch.setattr(
        order_radar_module.OrderRadar, "send_fulfillment_email",
        lambda self, recipient, product_title, download_url: {"success": True}
    )

    results = []

    def call_fulfill():
        results.append(radar._fulfill_web_order(
            source="stripe", external_id="cs_race_test",
            buyer_email="buyer@example.com", product_type="all", amount="$15.00"
        ))

    t1 = threading.Thread(target=call_fulfill)
    t1.start()
    build_started.wait(timeout=5)  # ensure t1 is inside the "slow" bundle build...
    t2 = threading.Thread(target=call_fulfill)
    t2.start()  # ...before t2 starts, simulating a near-simultaneous duplicate webhook
    time.sleep(0.2)
    release_build.set()
    t1.join(timeout=5)
    t2.join(timeout=5)

    assert len(bundle_calls) == 1  # the second call must never reach the bundle builder
    fulfilled = [o for o in radar.orders if o.get("id") == "cs_race_test" and o.get("status") == "fulfilled_auto"]
    assert len(fulfilled) == 1  # exactly one final order record, never two


# --------------------------------------------------------------------------
# Secrets are never echoed back in plaintext
# --------------------------------------------------------------------------

def test_get_redacted_config_never_contains_raw_secret_values(tmp_path):
    radar = _make_radar(tmp_path)
    radar.update_config(app_password="super-secret-app-pw", stripe_webhook_secret="whsec_live_abc123")

    redacted = radar.get_redacted_config()

    serialized = json.dumps(redacted)
    assert "super-secret-app-pw" not in serialized
    assert "whsec_live_abc123" not in serialized
    assert redacted["has_app_password"] is True
    assert redacted["has_stripe_webhook_secret"] is True


def test_update_config_return_value_is_also_redacted(tmp_path):
    """This is literally what /api/radar/webhook/config and /api/radar/config return
    to the caller - it must never carry a raw secret regardless of which fields were
    just updated."""
    radar = _make_radar(tmp_path)
    returned = radar.update_config(app_password="another-secret", stripe_webhook_secret="whsec_abc")
    serialized = json.dumps(returned)
    assert "another-secret" not in serialized
    assert "whsec_abc" not in serialized


# --------------------------------------------------------------------------
# Configurable (not hardcoded-private-IP) customer download URL
# --------------------------------------------------------------------------

def test_download_base_url_falls_back_to_an_obvious_placeholder_when_unset(tmp_path, capsys):
    radar = _make_radar(tmp_path)
    url = radar._public_download_base_url()
    assert "100.66.45.48" not in url  # the old hardcoded private Tailscale IP must be gone
    assert "CONFIGURE" in url  # obviously a placeholder, not a URL that looks real
    captured = capsys.readouterr()
    assert "not configured" in captured.out.lower()


def test_download_base_url_uses_configured_value_and_strips_trailing_slash(tmp_path):
    radar = _make_radar(tmp_path)
    radar.update_config(public_download_base_url="https://shop.example.com/")
    assert radar._public_download_base_url() == "https://shop.example.com"


# --------------------------------------------------------------------------
# Fiverr fulfillment: newest-by-mtime (not alphabetical/directory-order), explicit
# binding, and a visible warning on ambiguity
# --------------------------------------------------------------------------

@pytest.fixture
def fiverr_http_client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from dashboard import server
    from shared.auth import make_session_token

    monkeypatch.setattr(server, "_get_session_secret", lambda: "test-fiverr-secret")
    monkeypatch.setattr(server, "BASE_DIR", tmp_path)
    captured_calls = []

    def fake_fulfill_order(**kwargs):
        captured_calls.append(kwargs)
        return {"status": "ok", "delivery_zip_name": "FO_TEST_DELIVERY_PACKAGE.zip", "delivery_zip_size_kb": 1.0, "delivery_note": "note"}

    monkeypatch.setattr(server.fiverr_bot, "fulfill_order", fake_fulfill_order)

    client = TestClient(server.app)
    client.cookies.set(server.SESSION_COOKIE, make_session_token("test-fiverr-secret"))
    client.captured_calls = captured_calls
    yield client
    client.close()


def test_fiverr_fulfill_picks_true_newest_by_mtime_not_filename_order(tmp_path, fiverr_http_client):
    photos_dir = tmp_path / "workspace" / "photos_output"
    photos_dir.mkdir(parents=True)
    # Deliberately reversed: "aaa" sorts first alphabetically but is the NEWEST file;
    # "zzz" sorts last alphabetically (what the old `glob()[-1]` bug would have picked)
    # but is actually the OLDEST file. Only a correct mtime-based selection picks "aaa".
    older_but_sorts_last = photos_dir / "zzz_older_client_PACKAGE.zip"
    newer_but_sorts_first = photos_dir / "aaa_newer_client_PACKAGE.zip"
    older_but_sorts_last.write_bytes(b"old")
    newer_but_sorts_first.write_bytes(b"new")
    old_time = time.time() - 10_000
    os.utime(older_but_sorts_last, (old_time, old_time))

    response = fiverr_http_client.post("/api/fiverr/fulfill", json={
        "gig_id": "gig_retouch", "client_name": "Correct Client", "order_number": "FO_1"
    })

    assert response.status_code == 200
    assert fiverr_http_client.captured_calls[-1]["assets"] == [str(newer_but_sorts_first)]
    assert "warning" in response.json()  # ambiguity (2 candidates) must be visible, not silent


def test_fiverr_fulfill_with_explicit_asset_filename_skips_the_guess_entirely(tmp_path, fiverr_http_client):
    photos_dir = tmp_path / "workspace" / "photos_output"
    photos_dir.mkdir(parents=True)
    wrong_client_newest = photos_dir / "wrong_client_PACKAGE.zip"
    right_client_older = photos_dir / "right_client_PACKAGE.zip"
    wrong_client_newest.write_bytes(b"wrong")
    right_client_older.write_bytes(b"right")
    old_time = time.time() - 10_000
    os.utime(right_client_older, (old_time, old_time))

    response = fiverr_http_client.post("/api/fiverr/fulfill", json={
        "gig_id": "gig_retouch", "client_name": "Right Client", "order_number": "FO_2",
        "asset_filename": "right_client_PACKAGE.zip"
    })

    assert response.status_code == 200
    data = response.json()
    assert "warning" not in data or not data.get("warning")
    assert fiverr_http_client.captured_calls[-1]["assets"] == [str(right_client_older)]


def test_fiverr_fulfill_rejects_a_missing_explicit_asset_filename(tmp_path, fiverr_http_client):
    photos_dir = tmp_path / "workspace" / "photos_output"
    photos_dir.mkdir(parents=True)
    (photos_dir / "some_client_PACKAGE.zip").write_bytes(b"x")

    response = fiverr_http_client.post("/api/fiverr/fulfill", json={
        "gig_id": "gig_retouch", "client_name": "Nobody", "order_number": "FO_3",
        "asset_filename": "does_not_exist.zip"
    })

    assert response.json()["status"] == "error"
    assert fiverr_http_client.captured_calls == []  # must never fall through to delivering ANY file


def test_fiverr_fulfill_asset_filename_cannot_escape_its_gig_directory(tmp_path, fiverr_http_client):
    photos_dir = tmp_path / "workspace" / "photos_output"
    photos_dir.mkdir(parents=True)
    secret_outside_file = tmp_path / "config" / "order_radar_config.json"
    secret_outside_file.parent.mkdir(parents=True)
    secret_outside_file.write_text('{"app_password": "leak-me-not"}')

    response = fiverr_http_client.post("/api/fiverr/fulfill", json={
        "gig_id": "gig_retouch", "client_name": "Attacker", "order_number": "FO_4",
        "asset_filename": "../config/order_radar_config.json"
    })

    assert response.json()["status"] == "error"
    assert fiverr_http_client.captured_calls == []
