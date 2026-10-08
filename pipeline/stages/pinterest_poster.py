"""
WORKHORSE PIPELINE STAGE: PINTEREST PIN DISPATCHER
Handles direct Pinterest API v5 publishing for the CreatorMediaLab / @TheCreatorAsset
mainstream brand ONLY.

CRITICAL COMPLIANCE BOUNDARY:
Pinterest's Community Guidelines explicitly prohibit "sexually explicit or suggestive
depictions," "visible intimate body parts," and - directly relevant to this studio's
adult_creator_brand ("The Daily Creator Pulse") - the "promotion of commercial sexual
services like escort services, sexual chats or webcams."
(https://policy.pinterest.com/en/community-guidelines, "Adult sexual content & nudity")

Every single publish path in this module runs through is_pinterest_safe() first, which
hard-blocks anything that isn't explicitly tagged content_type="general", and additionally
keyword/path-scans as defense-in-depth. There is no bypass - Herald must never be able to
post adult_creator_brand ("creatorpulselab") content here under any circumstance.
"""

import base64
import hashlib
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import requests

from shared.atomic_writer import atomic_write_json, safe_read_json

# Mirrors the ADULT_CONTENT_KEYWORDS list used elsewhere (vision_agent.py,
# copy_synthesizer.py, prompt_synthesizer.py) plus terms specific to Pinterest's
# published Adult Content & Nudity policy (escort/webcam/cam-site promotion, etc.)
# so a mislabeled content_type still gets caught by the text itself.
PINTEREST_BLOCKED_KEYWORDS = [
    "adult", "boudoir", "nsfw", "onlyfans", "fansly", "glamour", "lingerie",
    "nude", "nudity", "intimate", "sensual", "fetish", "cam", "camgirl",
    "cam girl", "webcam", "chaturbate", "myfreecams", "mfc", "lovense",
    "escort", "bdsm", "erotic", "explicit", "ppv", "18+", "xxx", "sex",
    "sexual", "sexually", "strip", "topless", "vault", "tip menu",
    "fiverr_service_bot_adult"
]

# Defense-in-depth: if an image's source folder path contains any of these niche
# markers, block the pin even if the caller forgot to pass content_type="adult".
PINTEREST_BLOCKED_PATH_MARKERS = [
    "adult_creator_brand", "creator_pulse_lab", "creator_pulse", "boudoir",
    "cam", "adult", "cpl", "onlyfans", "fansly"
]

PIN_HISTORY_FILE = Path("F:/WORKHORSE/workspace/pinterest_pin_history.json")


class PinterestPoster:
    def __init__(self, config_path: str = "F:/WORKHORSE/config.json", secrets_path: str = "F:/WORKHORSE/secrets.json"):
        self.config_path = Path(config_path)
        self.secrets_path = Path(secrets_path)

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return {}
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _load_credentials(self) -> Dict[str, Any]:
        """Credentials live outside config.json (gitignored secrets.json) so they never land in version control."""
        return safe_read_json(self.secrets_path, default={}).get("pinterest_credentials", {})

    def _save_credentials(self, pinterest_creds: Dict[str, Any]) -> None:
        data = safe_read_json(self.secrets_path, default={})
        data["pinterest_credentials"] = pinterest_creds
        atomic_write_json(self.secrets_path, data)

    def _ensure_fresh_token(self) -> Optional[str]:
        """Returns a valid access token, transparently refreshing it via the stored
        refresh_token if it's expired or about to expire (Pinterest access tokens are
        short-lived, ~1 hour; refresh tokens last up to 365 days on a rolling basis)."""
        creds = self._load_credentials()
        access_token = (creds.get("access_token") or "").strip()
        refresh_token = (creds.get("refresh_token") or "").strip()
        expires_at = creds.get("token_expires_at", 0)
        app_id = (creds.get("app_id") or "").strip()
        app_secret = (creds.get("app_secret") or "").strip()

        if access_token and time.time() < (expires_at - 300):  # 5-minute safety buffer
            return access_token

        if not (refresh_token and app_id and app_secret):
            return access_token or None

        try:
            resp = requests.post(
                "https://api.pinterest.com/v5/oauth/token",
                auth=(app_id, app_secret),
                data={"grant_type": "refresh_token", "refresh_token": refresh_token},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=15
            )
            if resp.status_code == 200:
                tok = resp.json()
                creds["access_token"] = tok.get("access_token", "")
                creds["refresh_token"] = tok.get("refresh_token", refresh_token)
                creds["token_expires_at"] = time.time() + tok.get("expires_in", 3600)
                self._save_credentials(creds)
                return creds["access_token"]
            print(f"[PinterestPoster] Token refresh failed: HTTP {resp.status_code} - {resp.text}")
            return access_token or None
        except Exception as e:
            print(f"[PinterestPoster] Token refresh error: {e}")
            return access_token or None

    def verify_credentials(self) -> Dict[str, Any]:
        """Check if Pinterest credentials are configured and the token is valid."""
        token = self._ensure_fresh_token()
        if not token:
            return {
                "configured": False,
                "error": "Pinterest credentials not configured. Add app_id, app_secret, access_token, and refresh_token under 'pinterest_credentials' in secrets.json."
            }
        try:
            resp = requests.get(
                "https://api.pinterest.com/v5/user_account",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "configured": True,
                    "username": data.get("username"),
                    "account_type": data.get("account_type"),
                    "profile_image": data.get("profile_image")
                }
            return {"configured": False, "error": f"Pinterest API HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            return {"configured": False, "error": str(e)}

    def list_boards(self) -> Dict[str, Any]:
        """Lists the authenticated account's own boards (needed to pick a default_board_id)."""
        token = self._ensure_fresh_token()
        if not token:
            return {"success": False, "error": "Pinterest credentials not configured."}
        try:
            resp = requests.get(
                "https://api.pinterest.com/v5/boards",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                return {"success": True, "boards": [{"id": b.get("id"), "name": b.get("name")} for b in items]}
            return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def is_pinterest_safe(
        self,
        content_type: str = "general",
        text_blobs: Optional[List[str]] = None,
        source_path: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        TOS SAFETY GATE - mandatory, non-bypassable check run before every single pin.
        Returns (True, "") if the content is safe to publish on Pinterest, or
        (False, "<reason>") if it must be blocked. This is intentionally conservative:
        anything that even LOOKS adult-related gets blocked rather than risking the
        Pinterest account being suspended for a Community Guidelines violation.
        """
        if (content_type or "").strip().lower() != "general":
            return False, (
                f"Blocked: content_type is '{content_type}', not 'general'. Pinterest only ever "
                f"receives mainstream/general-brand content from Herald, never adult/boudoir content."
            )

        combined_text = " ".join([t for t in (text_blobs or []) if t]).lower()
        for kw in PINTEREST_BLOCKED_KEYWORDS:
            if kw in combined_text:
                return False, f"Blocked: text contains disallowed term '{kw}' per Pinterest's Adult Content & Nudity policy."

        if source_path:
            path_lower = str(source_path).lower()
            for marker in PINTEREST_BLOCKED_PATH_MARKERS:
                if marker in path_lower:
                    return False, f"Blocked: source path '{source_path}' is associated with the adult content brand/niche ('{marker}')."

        return True, ""

    def _is_duplicate_pin(self, text: str) -> bool:
        """Checks if an identical title/description was pinned in the last 7 days using SHA-256."""
        data = safe_read_json(PIN_HISTORY_FILE, default={"hashes": {}})
        txt_hash = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
        now = time.time()
        seven_days = 7 * 86400

        hashes = {h: ts for h, ts in data.get("hashes", {}).items() if now - ts < seven_days}
        if txt_hash in hashes:
            return True

        hashes[txt_hash] = now
        data["hashes"] = hashes
        atomic_write_json(PIN_HISTORY_FILE, data)
        return False

    def create_pin(
        self,
        board_id: str,
        title: str,
        description: str = "",
        link: str = "",
        image_path: Optional[str] = None,
        image_url: Optional[str] = None,
        content_type: str = "general"
    ) -> Dict[str, Any]:
        """Publishes a single pin. The TOS safety gate runs FIRST and unconditionally -
        there is no parameter or code path that skips it."""
        safe, reason = self.is_pinterest_safe(
            content_type=content_type,
            text_blobs=[title, description, link],
            source_path=image_path
        )
        if not safe:
            print(f"[PinterestPoster] BLOCKED pin (TOS safety gate): {reason}")
            return {"success": False, "status": "blocked_tos", "error": reason}

        if not board_id:
            return {"success": False, "error": "No board_id provided."}
        if not (image_path or image_url):
            return {"success": False, "error": "A pin requires either image_path or image_url."}

        if self._is_duplicate_pin(f"{title}|{description}"):
            return {"success": False, "status": "duplicate", "error": "Identical pin title/description posted within the last 7 days."}

        token = self._ensure_fresh_token()
        if not token:
            return {
                "success": False,
                "error": "Pinterest credentials not configured or token refresh failed. Add credentials under 'pinterest_credentials' in secrets.json."
            }

        if image_path:
            p = Path(image_path)
            if not p.exists():
                return {"success": False, "error": f"Image file not found: {image_path}"}
            try:
                from pipeline.stages.scrubber import metadata_scrubber
                metadata_scrubber.scrub_image(p)
            except Exception:
                pass
            try:
                mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
                b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
                media_source = {"source_type": "image_base64", "content_type": mime, "data": b64}
            except Exception as e:
                return {"success": False, "error": f"Failed to read/encode image: {e}"}
        else:
            media_source = {"source_type": "image_url", "url": image_url}

        payload = {
            "board_id": board_id,
            "title": title[:100],
            "description": description[:500],
            "media_source": media_source
        }
        if link:
            payload["link"] = link

        try:
            resp = requests.post(
                "https://api.pinterest.com/v5/pins",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=payload,
                timeout=30
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                pin_id = data.get("id")
                return {
                    "success": True,
                    "pin_id": pin_id,
                    "pin_url": f"https://www.pinterest.com/pin/{pin_id}/" if pin_id else None,
                    "board_id": board_id
                }
            return {"success": False, "error": f"Pinterest API error: HTTP {resp.status_code} - {resp.text}"}
        except Exception as e:
            return {"success": False, "error": f"Pinterest API request failed: {e}"}


pinterest_poster = PinterestPoster()
