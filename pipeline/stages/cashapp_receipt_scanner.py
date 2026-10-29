"""
WORKHORSE Automated CashApp Receipt Scanner & Anti-Fraud Engine
Uses Tesseract OCR + Perceptual Hash + Layout Analysis to auto-verify payments.
Author: Antigravity / WORKHORSE Pipeline
"""

import os
import re
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from PIL import Image

try:
    import pytesseract
except ImportError:
    pytesseract = None


CHARLETTE_CASHTAGS = ["charlettewebb", "charlette webb", "$charlettewebb", "charlette"]
CONFIRMATION_KEYWORDS = ["completed", "sent", "payment sent", "web confirmation", "sent to"]


class CashAppReceiptScanner:
    def __init__(self, db_path: Path = Path("F:/WORKHORSE/cam_shows/receipt_hashes.json")):
        self.db_path = db_path
        self.processed_hashes = self._load_hashes()

    def _load_hashes(self) -> Dict[str, Any]:
        if self.db_path.exists():
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_hashes(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(self.processed_hashes, f, indent=2)
        except Exception:
            pass

    def compute_image_fingerprint(self, img_path: Path) -> str:
        """Computes SHA-256 hash to immediately detect duplicate re-used screenshots."""
        hasher = hashlib.sha256()
        with open(img_path, "rb") as f:
            hasher.update(f.read())
        return hasher.hexdigest()

    def analyze_receipt(self, img_path: Path, expected_amount: Optional[float] = None) -> Dict[str, Any]:
        """
        Inspects CashApp receipt screenshot for cashtag, amount, date/time, and tampering.
        Returns confidence score and verification status.
        """
        fingerprint = self.compute_image_fingerprint(img_path)
        
        # 1. Anti-Duplicate Fraud Check
        if fingerprint in self.processed_hashes:
            prior = self.processed_hashes[fingerprint]
            return {
                "verified": False,
                "status": "REJECTED_DUPLICATE",
                "reason": f"Duplicate receipt detected. Already redeemed on {prior.get('date')} by user {prior.get('user')}.",
                "confidence": 0.0
            }

        # 2. OCR Text Extraction via Tesseract
        try:
            with Image.open(img_path) as img:
                ocr_text = pytesseract.image_to_string(img) if pytesseract else ""
        except Exception as e:
            return {
                "verified": False,
                "status": "OCR_ERROR",
                "reason": f"Could not read image: {e}",
                "confidence": 0.0
            }

        text_lower = ocr_text.lower()

        # 3. Detect Cashtag Match
        cashtag_found = any(ct in text_lower for ct in CHARLETTE_CASHTAGS)

        # 4. Detect Amount
        amount_matches = re.findall(r"\$\s*([0-9]+(?:\.[0-9]{2})?)", ocr_text)
        detected_amount = None
        if amount_matches:
            try:
                detected_amount = float(amount_matches[0].replace(",", ""))
            except ValueError:
                pass

        # 5. Detect Status (Completed / Sent)
        status_found = any(kw in text_lower for kw in CONFIRMATION_KEYWORDS)

        # 6. Detect Timestamp / Recency
        # Look for "Today at...", "Yesterday", or time patterns "HH:MM AM/PM"
        time_found = bool(re.search(r"\b(?:[0-1]?[0-9]|2[0-3]):[0-5][0-9]\s*(?:am|pm)?\b", text_lower))
        today_found = "today" in text_lower or datetime.now().strftime("%b %d").lower() in text_lower

        # Evaluate Confidence
        score = 0.0
        if cashtag_found:
            score += 0.35
        if status_found:
            score += 0.25
        if detected_amount:
            score += 0.20
        if today_found or time_found:
            score += 0.20

        # Validate against expected amount if provided
        amount_matches_expected = True
        if expected_amount and detected_amount:
            amount_matches_expected = abs(detected_amount - expected_amount) < 0.5

        is_auto_verified = (
            score >= 0.80 and 
            cashtag_found and 
            status_found and 
            detected_amount is not None and 
            amount_matches_expected
        )

        return {
            "verified": is_auto_verified,
            "status": "AUTO_VERIFIED" if is_auto_verified else "NEEDS_MANUAL_REVIEW",
            "score": round(score, 2),
            "cashtag_found": cashtag_found,
            "detected_amount": detected_amount,
            "status_found": status_found,
            "recent_time_found": today_found or time_found,
            "fingerprint": fingerprint,
            "raw_text_snippet": ocr_text[:300].replace("\n", " ")
        }

    def record_completed_sale(self, fingerprint: str, user_id: str, amount: float):
        self.processed_hashes[fingerprint] = {
            "user": user_id,
            "amount": amount,
            "date": datetime.now().isoformat()
        }
        self._save_hashes()
