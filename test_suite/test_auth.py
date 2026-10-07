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
    expiry, sig = token.split(".", 1)
    tampered = f"{int(expiry) + 999999}.{sig}"
    assert verify_session_token(tampered, secret) is False
