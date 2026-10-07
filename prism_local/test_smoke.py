"""
Smoke tests for Prism (main.py). Run with: .venv\\Scripts\\python.exe -m pytest test_smoke.py -v

These hit the real local history.db / users.json but self-clean every row/setting
they touch, and never call a real AI provider (all provider calls are mocked).
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(main.app)

# Smallest possible valid PNG (1x1 transparent pixel)
TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
IMAGE_DATA_URL = "data:image/png;base64," + TINY_PNG_B64


def _new_session(username="admin", hours=1):
    return main._create_session(username, hours)


def _drop_session(token):
    conn = sqlite3.connect(main.DB_PATH, timeout=10)
    conn.execute("DELETE FROM sessions WHERE token=?", (token,))
    conn.commit()
    conn.close()


def _drop_history(entry_id):
    conn = sqlite3.connect(main.DB_PATH, timeout=10)
    conn.execute("DELETE FROM history WHERE id=?", (entry_id,))
    conn.commit()
    conn.close()


def _add_test_user(username, password):
    data = main._load_users()
    salt = "0123456789abcdef0123456789abcdef"
    data["users"][username] = {"salt": salt, "hash": main._hash_pw(password, salt), "enabled": True}
    main._save_users(data)


def _remove_test_user(username):
    data = main._load_users()
    data["users"].pop(username, None)
    main._save_users(data)


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------

def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200


def test_login_page_served():
    r = client.get("/login")
    assert r.status_code == 200
    assert b"<html" in r.content.lower()


def test_root_serves_app_shell():
    r = client.get("/")
    assert r.status_code == 200
    assert b"Prism" in r.content


def test_manifest_valid():
    r = client.get("/manifest.json")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Prism"
    assert data["icons"]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def test_unauthenticated_whoami_rejected():
    r = client.get("/api/whoami")
    assert r.status_code == 401


def test_invalid_login_rejected():
    r = client.post("/api/login", json={"username": "admin", "password": "definitely-wrong-pw-xyz"})
    assert r.status_code == 401


def test_authenticated_whoami():
    token = _new_session()
    try:
        r = client.get("/api/whoami", cookies={"que_session": token})
        assert r.status_code == 200
        assert r.json()["username"] == "admin"
    finally:
        _drop_session(token)


# ---------------------------------------------------------------------------
# Caption variants regression tests (the feature we just wired for video)
# ---------------------------------------------------------------------------

def test_generate_variants_gemini_structured_path(monkeypatch):
    """provider == gemini: variants use _gemini_structured -> '---'-joined captions."""
    token = _new_session()
    entry_id = None
    monkeypatch.setattr(
        main, "_gemini_structured",
        lambda cfg, prompt, image_bytes, schema: {"captions": ["Take one.", "Take two.", "Take three."]},
    )
    try:
        cfg = main.load_config()
        if (cfg.get("provider") or "ollama") != "gemini":
            import pytest
            pytest.skip("config.json provider is not gemini locally")
        r = client.post(
            "/api/generate",
            json={"image_b64": IMAGE_DATA_URL, "mode": "post", "platform": "instagram", "variants": True},
            cookies={"que_session": token},
        )
        assert r.status_code == 200
        body = r.json()
        entry_id = body["id"]
        text = body["results"]["post"]
        parts = [p.strip() for p in text.split("---") if p.strip()]
        assert len(parts) == 3
    finally:
        if entry_id:
            _drop_history(entry_id)
        _drop_session(token)


def test_generate_variants_text_fallback_path(monkeypatch):
    """Non-gemini provider: variants use VARIANTS_SUFFIX + plain-text '---' split."""
    token = _new_session()
    entry_id = None
    fake_cfg = dict(main.load_config())
    fake_cfg["provider"] = "ollama"
    monkeypatch.setattr(main, "load_config", lambda: fake_cfg)
    monkeypatch.setattr(
        main, "_call_provider",
        lambda cfg, prompt, image_bytes, opts: "Take one.\n---\nTake two.\n---\nTake three.",
    )
    try:
        r = client.post(
            "/api/generate",
            json={"image_b64": IMAGE_DATA_URL, "mode": "post", "platform": "instagram", "variants": True},
            cookies={"que_session": token},
        )
        assert r.status_code == 200
        body = r.json()
        entry_id = body["id"]
        text = body["results"]["post"]
        parts = [p.strip() for p in text.split("---") if p.strip()]
        assert len(parts) == 3
    finally:
        if entry_id:
            _drop_history(entry_id)
        _drop_session(token)


def test_variants_skips_signature_and_hashtags(monkeypatch):
    """Regression test: signature/hub-hashtag suffix must NOT be appended when variants=True."""
    token = _new_session()
    entry_ids = []
    monkeypatch.setattr(
        main, "_gemini_structured",
        lambda cfg, prompt, image_bytes, schema: {"captions": ["Cap A.", "Cap B.", "Cap C."]},
    )
    monkeypatch.setattr(
        main, "_call_provider",
        lambda cfg, prompt, image_bytes, opts: "Plain single caption.",
    )
    original = client.get("/api/user-settings", cookies={"que_session": token}).json()
    try:
        upd = client.post(
            "/api/user-settings",
            json={"signature": "-- Test Signature Marker"},
            cookies={"que_session": token},
        )
        assert upd.status_code == 200

        base_payload = {"image_b64": IMAGE_DATA_URL, "mode": "post", "platform": "instagram"}

        r_off = client.post("/api/generate", json={**base_payload, "variants": False}, cookies={"que_session": token})
        assert r_off.status_code == 200
        body_off = r_off.json()
        entry_ids.append(body_off["id"])
        assert "Test Signature Marker" in body_off["results"]["post"]

        r_on = client.post("/api/generate", json={**base_payload, "variants": True}, cookies={"que_session": token})
        assert r_on.status_code == 200
        body_on = r_on.json()
        entry_ids.append(body_on["id"])
        assert "Test Signature Marker" not in body_on["results"]["post"]
    finally:
        client.post(
            "/api/user-settings",
            json={"signature": original.get("signature", "")},
            cookies={"que_session": token},
        )
        for eid in entry_ids:
            _drop_history(eid)
        _drop_session(token)


# ---------------------------------------------------------------------------
# Account deletion
# ---------------------------------------------------------------------------

def test_delete_account_wrong_password_rejected():
    _add_test_user("_smoketest_delete_user", "correct-horse-battery-staple")
    token = _new_session("_smoketest_delete_user")
    try:
        r = client.post("/api/delete-account", json={"password": "wrong-password"}, cookies={"que_session": token})
        assert r.status_code == 401
        # account must still exist/log in fine after a failed attempt
        assert "_smoketest_delete_user" in main._load_users()["users"]
    finally:
        _drop_session(token)
        _remove_test_user("_smoketest_delete_user")


def test_delete_account_success_removes_user_and_data():
    _add_test_user("_smoketest_delete_user2", "correct-horse-battery-staple")
    token = _new_session("_smoketest_delete_user2")
    conn = sqlite3.connect(main.DB_PATH, timeout=10)
    conn.execute("INSERT INTO usage (username, date, count) VALUES (?,?,?)", ("_smoketest_delete_user2", "2026-01-01", 3))
    conn.execute(
        "INSERT INTO scheduled_posts (id, owner, history_id, platform, mode, content, thumb, scheduled_for, status, created_at, updated_at) "
        "VALUES ('smoketest-post-1','_smoketest_delete_user2',NULL,'instagram','post','x',NULL,'2026-01-01','pending','2026-01-01','2026-01-01')"
    )
    conn.commit()
    conn.close()
    try:
        r = client.post("/api/delete-account", json={"password": "correct-horse-battery-staple"}, cookies={"que_session": token})
        assert r.status_code == 200
        assert "_smoketest_delete_user2" not in main._load_users()["users"]

        conn = sqlite3.connect(main.DB_PATH, timeout=10)
        assert conn.execute("SELECT COUNT(*) FROM sessions WHERE username=?", ("_smoketest_delete_user2",)).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM usage WHERE username=?", ("_smoketest_delete_user2",)).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM scheduled_posts WHERE owner=?", ("_smoketest_delete_user2",)).fetchone()[0] == 0
        conn.close()

        # cookie should be cleared / no longer usable
        r2 = client.get("/api/whoami", cookies={"que_session": token})
        assert r2.status_code == 401
    finally:
        _remove_test_user("_smoketest_delete_user2")


def test_delete_account_blocked_if_last_user():
    """Refuse to delete the only remaining enabled account (would lock out the whole app)."""
    _add_test_user("_smoketest_delete_lastuser", "correct-horse-battery-staple")
    data = main._load_users()
    disabled = []
    for uname, urec in data["users"].items():
        if uname != "_smoketest_delete_lastuser" and urec.get("enabled", True):
            urec["enabled"] = False
            disabled.append(uname)
    main._save_users(data)
    token = _new_session("_smoketest_delete_lastuser")
    try:
        r = client.post("/api/delete-account", json={"password": "correct-horse-battery-staple"}, cookies={"que_session": token})
        assert r.status_code == 400
    finally:
        _drop_session(token)
        _remove_test_user("_smoketest_delete_lastuser")
        data = main._load_users()
        for uname in disabled:
            if uname in data["users"]:
                data["users"][uname]["enabled"] = True
        main._save_users(data)

