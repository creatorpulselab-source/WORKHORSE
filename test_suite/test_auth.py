"""Unit tests for shared/auth.py (password hashing + signed session tokens).

These are pure stdlib functions with no network/GPU/filesystem dependency,
making them the highest-value, lowest-friction target for a first test pass.
"""
import time

from shared.auth import (
    hash_password,
    verify_password,
    make_session_token,
    verify_session_token,
    get_session_id,
)


def test_hash_password_generates_salt_and_hash():
    result = hash_password("correct-horse-battery-staple")
    assert "salt" in result and "hash" in result
    assert len(bytes.fromhex(result["salt"])) == 16
    assert len(bytes.fromhex(result["hash"])) == 32


def test_hash_password_is_deterministic_given_same_salt():
    salt = bytes.fromhex("00" * 16)
    r1 = hash_password("password123", salt=salt)
    r2 = hash_password("password123", salt=salt)
    assert r1 == r2


def test_hash_password_differs_with_random_salt():
    r1 = hash_password("password123")
    r2 = hash_password("password123")
    assert r1["salt"] != r2["salt"]
    assert r1["hash"] != r2["hash"]


def test_verify_password_accepts_correct_password():
    result = hash_password("hunter2")
    assert verify_password("hunter2", result["salt"], result["hash"]) is True


def test_verify_password_rejects_wrong_password():
    result = hash_password("hunter2")
    assert verify_password("wrong-password", result["salt"], result["hash"]) is False


def test_verify_password_rejects_malformed_salt():
    result = hash_password("hunter2")
    assert verify_password("hunter2", "not-hex", result["hash"]) is False


def test_session_token_round_trips():
    secret = "test-session-secret"
    token = make_session_token(secret, max_age_seconds=3600)
    assert verify_session_token(token, secret) is True


def test_session_token_rejects_wrong_secret():
    token = make_session_token("secret-a", max_age_seconds=3600)
    assert verify_session_token(token, "secret-b") is False


def test_session_token_rejects_expired_token():
    token = make_session_token("test-session-secret", max_age_seconds=-1)
    assert verify_session_token(token, "test-session-secret") is False


def test_session_token_rejects_malformed_token():
    assert verify_session_token("not-a-valid-token", "any-secret") is False
    assert verify_session_token("", "any-secret") is False


def test_session_token_rejects_tampered_expiry():
    secret = "test-session-secret"
    token = make_session_token(secret, max_age_seconds=3600)
    sid, expiry, sig = token.split(".", 2)
    tampered = f"{sid}.{int(expiry) + 999999}.{sig}"
    assert verify_session_token(tampered, secret) is False


def test_get_session_id_returns_unique_id_per_token():
    """Each login must get its own session id so per-session chat memory never bleeds
    across different browsers/devices."""
    secret = "test-session-secret"
    token_a = make_session_token(secret, max_age_seconds=3600)
    token_b = make_session_token(secret, max_age_seconds=3600)
    sid_a = get_session_id(token_a, secret)
    sid_b = get_session_id(token_b, secret)
    assert sid_a is not None and sid_b is not None
    assert sid_a != sid_b


def test_get_session_id_rejects_invalid_token():
    assert get_session_id("not-a-valid-token", "any-secret") is None
    assert get_session_id("", "any-secret") is None


def test_get_session_id_rejects_legacy_two_part_token_format():
    """Tokens issued before the per-session-id format (expiry.sig, no sid) must be
    treated as invalid rather than silently misparsed, forcing a fresh login."""
    import hmac
    import hashlib
    expiry = str(int(time.time()) + 3600)
    sig = hmac.new(b"test-session-secret", expiry.encode(), hashlib.sha256).hexdigest()
    legacy_token = f"{expiry}.{sig}"
    assert get_session_id(legacy_token, "test-session-secret") is None
