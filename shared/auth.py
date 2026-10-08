"""Password hashing and signed session tokens for the WORKHORSE dashboard (stdlib only, no new deps)."""
import hashlib
import hmac
import os
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
    """Issues a signed session token that embeds a unique, random session id (sid) so each
    login gets its own session (e.g. for per-session SYNAPSE chat memory), not just a shared
    expiry-based signature."""
    sid = os.urandom(16).hex()
    expiry = int(time.time()) + max_age_seconds
    payload = f"{sid}.{expiry}"
    sig = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def get_session_id(token: str, secret: str) -> Optional[str]:
    """Verifies a session token's signature and expiry, returning its unique session id if
    valid or None otherwise. Tokens issued before the per-session id format (2-part
    expiry.sig tokens) are treated as invalid, requiring a fresh login."""
    try:
        sid, expiry_str, sig = token.split(".", 2)
        expiry = int(expiry_str)
    except Exception:
        return None
    if time.time() > expiry:
        return None
    payload = f"{sid}.{expiry_str}"
    expected = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    return sid


def verify_session_token(token: str, secret: str) -> bool:
    return get_session_id(token, secret) is not None
