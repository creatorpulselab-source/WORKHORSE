"""Password hashing and signed session tokens for the WORKHORSE dashboard (stdlib only, no new deps)."""
import hashlib
import hmac
import time
from typing import Dict, Optional


def hash_password(password: str, salt: Optional[bytes] = None) -> Dict[str, str]:
    salt = salt or __import__("os").urandom(16)
    dk = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=32)
    return {"salt": salt.hex(), "hash": dk.hex()}


def verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    try:
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=32)
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


def make_session_token(secret: str, max_age_seconds: int = 7 * 24 * 3600) -> str:
    expiry = int(time.time()) + max_age_seconds
    sig = hmac.new(secret.encode("utf-8"), str(expiry).encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{expiry}.{sig}"


def verify_session_token(token: str, secret: str) -> bool:
    try:
        expiry_str, sig = token.split(".", 1)
        expiry = int(expiry_str)
    except Exception:
        return False
    if time.time() > expiry:
        return False
    expected = hmac.new(secret.encode("utf-8"), expiry_str.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)
