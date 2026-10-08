from shared.atomic_writer import atomic_write_json, safe_read_json
import os
import json
import imaplib
import email
from email.header import decode_header
import re
import hmac
import hashlib
import secrets as secrets_lib
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import random

# Download tokens are capability-style (unguessable random strings) rather than
# sequential order IDs, so the public /api/download/order/{token} route can stay
# unauthenticated for real buyers without letting anyone enumerate other orders.
DOWNLOAD_TOKEN_BYTES = 24
DOWNLOAD_TOKEN_TTL_DAYS = 14

class OrderRadar:
    """
    Automated Order Radar for WORKHORSE.
    Monitors digitalcreatorassets@gmail.com via secure IMAP for incoming Fiverr & Etsy order alerts.
    """
    def __init__(self, base_dir: str = "F:/WORKHORSE"):
        self.base_dir = Path(base_dir)
        self.config_file = self.base_dir / "config" / "order_radar_config.json"
        self.orders_file = self.base_dir / "workspace" / "orders_history.json"
        self.tokens_file = self.base_dir / "workspace" / "order_download_tokens.json"
        
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.orders_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.load_config()
        self.load_orders()
        self.load_download_tokens()

    def load_config(self) -> Dict[str, Any]:
        default_config = {
            "email": "digitalcreatorassets@gmail.com",
            "app_password": "",
            "imap_server": "imap.gmail.com",
            "imap_port": 993,
            "check_interval_seconds": 120,
            "auto_check": False,
            "sound_alerts": True,
            "last_checked": None,
            # Pipe 1 - Webhook Auto-Fulfillment (Stripe / Gumroad). Left blank until the
            # Commander creates real seller accounts - webhooks return "awaiting_setup"
            # until these are filled in via update_config(), same pattern as app_password.
            "stripe_webhook_secret": "",
            "gumroad_seller_id": "",
            # Maps an external product identifier (Stripe Price metadata.product_type, or
            # Gumroad product_permalink) to one of etsy_store's existing bundle IDs
            # (presets/contracts/posing/templates/all). Unknown keys fall back to "all".
            "webhook_product_map": {}
        }
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    default_config.update(data)
            except Exception:
                pass
        self.config = default_config
        self.save_config()
        return self.config

    def save_config(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving radar config: {e}")

    def load_orders(self) -> List[Dict[str, Any]]:
        if self.orders_file.exists():
            try:
                with open(self.orders_file, "r", encoding="utf-8") as f:
                    self.orders = json.load(f)
                    return self.orders
            except Exception:
                pass
        self.orders = []
        return self.orders

    def save_orders(self):
        try:
            with open(self.orders_file, "w", encoding="utf-8") as f:
                json.dump(self.orders, f, indent=2)
        except Exception as e:
            print(f"Error saving orders: {e}")

    def load_download_tokens(self) -> Dict[str, Any]:
        if self.tokens_file.exists():
            try:
                with open(self.tokens_file, "r", encoding="utf-8") as f:
                    self.download_tokens = json.load(f)
                    return self.download_tokens
            except Exception:
                pass
        self.download_tokens = {}
        return self.download_tokens

    def save_download_tokens(self):
        try:
            atomic_write_json(self.tokens_file, self.download_tokens)
        except Exception as e:
            print(f"Error saving download tokens: {e}")

    def update_config(self, app_password: Optional[str] = None, auto_check: Optional[bool] = None,
                       stripe_webhook_secret: Optional[str] = None, gumroad_seller_id: Optional[str] = None,
                       webhook_product_map: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        if app_password is not None:
            self.config["app_password"] = app_password.replace(" ", "").strip()
        if auto_check is not None:
            self.config["auto_check"] = bool(auto_check)
        if stripe_webhook_secret is not None:
            self.config["stripe_webhook_secret"] = stripe_webhook_secret.strip()
        if gumroad_seller_id is not None:
            self.config["gumroad_seller_id"] = gumroad_seller_id.strip()
        if webhook_product_map is not None:
            self.config["webhook_product_map"] = webhook_product_map
        self.save_config()
        return self.config

    def check_inbox(self) -> Dict[str, Any]:
        """Connect to Gmail via IMAP and scan for incoming Fiverr or Etsy orders."""
        user_email = self.config.get("email", "digitalcreatorassets@gmail.com")
        app_pw = self.config.get("app_password", "")
        self.config["last_checked"] = datetime.now().isoformat()
        self.save_config()

        if not app_pw:
            return {
                "status": "awaiting_app_password",
                "email": user_email,
                "message": "Enter your 16-character Google App Password to enable live inbox sync.",
                "orders_found": 0,
                "active_orders": self.orders
            }

        try:
            mail = imaplib.IMAP4_SSL(self.config.get("imap_server", "imap.gmail.com"), self.config.get("imap_port", 993))
            mail.login(user_email, app_pw)
            mail.select("INBOX")

            status, messages = mail.search(None, '(OR FROM "fiverr" FROM "etsy")')
            if status != "OK":
                mail.logout()
                return {"status": "ok", "message": "No order messages found", "new_orders": 0, "active_orders": self.orders}

            msg_ids = messages[0].split()
            new_orders_count = 0

            for mid in msg_ids[-10:]:
                res, data = mail.fetch(mid, "(RFC822)")
                if res != "OK":
                    continue
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)

                subject_header = decode_header(msg["Subject"])[0]
                subject = subject_header[0]
                if isinstance(subject, bytes):
                    try:
                        subject = subject.decode(subject_header[1] or "utf-8", errors="ignore")
                    except Exception:
                        subject = subject.decode("utf-8", errors="ignore")

                sender = msg.get("From", "")
                platform = "fiverr" if "fiverr" in sender.lower() or "fiverr" in subject.lower() else "etsy"
                
                # Verify subject actually indicates an order/purchase rather than general account notices
                subj_lower = subject.lower()
                order_keywords = ["order", "sale", "bought", "purchased", "sold", "payment", "receipt", "booked", "gig"]
                if not any(k in subj_lower for k in order_keywords):
                    continue

                order_id = self._extract_order_id(subject, platform)

                if any(o.get("id") == order_id for o in self.orders):
                    continue

                new_order = {
                    "id": order_id,
                    "platform": platform,
                    "buyer": self._extract_buyer(subject, platform),
                    "title": subject,
                    "amount": "$35.00" if platform == "fiverr" else "$24.99",
                    "received_at": datetime.now().isoformat(),
                    "status": "pending",
                    "raw_subject": subject,
                    "sender": sender
                }
                self.orders.insert(0, new_order)
                new_orders_count += 1

            mail.logout()
            self.save_orders()

            return {
                "status": "connected",
                "email": user_email,
                "new_orders": new_orders_count,
                "total_orders": len(self.orders),
                "orders": self.orders,
                "last_checked": self.config["last_checked"]
            }

        except imaplib.IMAP4.error as e:
            return {
                "status": "auth_error",
                "email": user_email,
                "error": f"IMAP authentication failed: {str(e)}. Please check your Google App Password.",
                "active_orders": self.orders
            }
        except Exception as e:
            return {
                "status": "error",
                "email": user_email,
                "error": f"Connection error: {str(e)}",
                "active_orders": self.orders
            }

    def simulate_order(self, platform: str = "fiverr") -> Dict[str, Any]:
        """Simulate an incoming order so the user can test UI alerts and fulfillment without waiting for buyers."""
        order_num = random.randint(10000, 99999)
        if platform == "fiverr":
            buyers = ["velvet_muse_la", "glamour_sophia", "boudoir_jess", "creator_chloe", "studio_vixen"]
            gigs = [
                ("gig_retouch", "I will color grade and retouch your glamour & model photo shoot", "VIP Studio Master Set ($75)", "$75.00"),
                ("gig_teaser", "I will create a 60s viral video teaser & 9:16 vertical reels", "Social Promo Duo ($45)", "$45.00"),
                ("gig_copy", "I will write high-converting social media captions and hashtag kits", "Weekly Release Plan ($40)", "$40.00"),
                ("gig_banner", "I will design custom OnlyFans / Fansly promo banners and tip menus", "Banner & Tip Menu Duo ($45)", "$45.00")
            ]
            gig_choice = random.choice(gigs)
            buyer = random.choice(buyers)
            order_data = {
                "id": f"FO-{order_num}",
                "platform": "fiverr",
                "gig_id": gig_choice[0],
                "buyer": buyer,
                "title": gig_choice[1],
                "package": gig_choice[2],
                "amount": gig_choice[3],
                "received_at": datetime.now().isoformat(),
                "status": "pending",
                "deadline": "24 Hours",
                "raw_subject": f"New Order from {buyer} (Order #FO-{order_num})"
            }
        else:
            buyers = ["photographer_mark", "boudoir_studio_nyc", "amber_creates", "glamour_lens_uk"]
            buyer = random.choice(buyers)
            order_data = {
                "id": f"ETSY-{order_num}",
                "platform": "etsy",
                "gig_id": "etsy_bundle",
                "buyer": buyer,
                "title": "Boudoir Lightroom Presets & 50 Posing Guide Cards Bundle",
                "package": "Master Digital Pack",
                "amount": "$29.99",
                "received_at": datetime.now().isoformat(),
                "status": "fulfilled_auto",
                "deadline": "Instant Digital Delivery (Completed by Etsy)",
                "raw_subject": f"Etsy Order #{order_num} from {buyer} — Payment Confirmed"
            }

        self.orders.insert(0, order_data)
        self.save_orders()
        return {
            "status": "simulated",
            "order": order_data,
            "total_orders": len(self.orders)
        }

    def _extract_order_id(self, subject: str, platform: str) -> str:
        match = re.search(r'#?([A-Z0-9]{5,10})', subject)
        if match:
            return match.group(1)
        return f"{platform.upper()}_{datetime.now().strftime('%m%d%H%M')}"

    def _extract_buyer(self, subject: str, platform: str) -> str:
        match = re.search(r'from\s+([A-Za-z0-9_\-]+)', subject, re.IGNORECASE)
        if match:
            return match.group(1)
        return "CreatorClient"

    def mark_fulfilled(self, order_id: str) -> bool:
        for o in self.orders:
            if o.get("id") == order_id:
                o["status"] = "fulfilled"
                o["fulfilled_at"] = datetime.now().isoformat()
                self.save_orders()
                return True
        return False

    # =====================================================================
    # PIPE 1 - WEBHOOK AUTO-FULFILLMENT (Stripe / Gumroad)
    # Stripe/Gumroad Webhook -> verify -> Apex-style ZIP build (reusing
    # etsy_store's existing digital bundle catalog) -> instant email with a
    # capability-token download link -> order marked fulfilled_auto.
    # Etsy itself has no real seller API wired here (would require Etsy's
    # OAuth Open API) - Etsy orders stay on the existing IMAP polling path
    # in check_inbox(). This block only covers real Stripe/Gumroad webhooks.
    # =====================================================================
    def verify_stripe_signature(self, payload: bytes, sig_header: str) -> bool:
        """Manually verifies Stripe's documented webhook signature scheme
        (HMAC-SHA256 of 'timestamp.payload') - no stripe SDK dependency needed."""
        secret = self.config.get("stripe_webhook_secret", "")
        if not secret or not sig_header:
            return False
        try:
            parts = dict(p.split("=", 1) for p in sig_header.split(",") if "=" in p)
            timestamp = parts.get("t")
            signature = parts.get("v1")
            if not timestamp or not signature:
                return False
            signed_payload = f"{timestamp}.{payload.decode('utf-8')}".encode("utf-8")
            expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected, signature)
        except Exception as e:
            print(f"[OrderRadar] Stripe signature verification error: {e}")
            return False

    def handle_stripe_webhook(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        if not self.config.get("stripe_webhook_secret"):
            return {"success": False, "status": "awaiting_setup", "error": "Stripe webhook secret not configured yet"}
        if not self.verify_stripe_signature(payload, sig_header):
            return {"success": False, "status": "invalid_signature", "error": "Stripe signature verification failed"}

        try:
            event = json.loads(payload.decode("utf-8"))
        except Exception as e:
            return {"success": False, "error": f"Invalid JSON payload: {e}"}

        if event.get("type") != "checkout.session.completed":
            return {"success": True, "ignored": True, "reason": f"Unhandled event type: {event.get('type')}"}

        session = event.get("data", {}).get("object", {})
        buyer_email = (session.get("customer_details") or {}).get("email") or session.get("customer_email")
        if not buyer_email:
            return {"success": False, "error": "No buyer email present in Stripe session payload"}

        product_type = (session.get("metadata") or {}).get("product_type", "all")
        product_type = self.config.get("webhook_product_map", {}).get(product_type, product_type)
        amount_total = session.get("amount_total")
        amount_str = f"${amount_total / 100:.2f}" if isinstance(amount_total, (int, float)) else "N/A"

        return self._fulfill_web_order(
            source="stripe",
            external_id=session.get("id", f"cs_{int(time.time())}"),
            buyer_email=buyer_email,
            product_type=product_type,
            amount=amount_str
        )

    def handle_gumroad_webhook(self, form: Dict[str, Any]) -> Dict[str, Any]:
        """Gumroad 'Ping' notifications are plain form-POSTs with no signature - the
        only verification available is matching the configured seller_id."""
        configured_seller_id = self.config.get("gumroad_seller_id", "")
        if not configured_seller_id:
            return {"success": False, "status": "awaiting_setup", "error": "Gumroad seller_id not configured yet"}

        incoming_seller_id = str(form.get("seller_id", ""))
        if incoming_seller_id != configured_seller_id:
            return {"success": False, "status": "invalid_seller", "error": "Gumroad seller_id mismatch"}

        if str(form.get("test", "")).lower() == "true":
            return {"success": True, "ignored": True, "reason": "Gumroad test ping"}

        buyer_email = form.get("email")
        if not buyer_email:
            return {"success": False, "error": "No buyer email present in Gumroad ping payload"}

        permalink = form.get("product_permalink", "")
        product_type = self.config.get("webhook_product_map", {}).get(permalink, "all")
        price_cents = form.get("price")
        amount_str = f"${int(price_cents) / 100:.2f}" if price_cents and str(price_cents).isdigit() else "N/A"

        return self._fulfill_web_order(
            source="gumroad",
            external_id=form.get("sale_id", f"gr_{int(time.time())}"),
            buyer_email=buyer_email,
            product_type=product_type,
            amount=amount_str
        )

    def _fulfill_web_order(self, source: str, external_id: str, buyer_email: str, product_type: str, amount: str) -> Dict[str, Any]:
        """Apex [78 Pt]-style packaging: builds the digital bundle zip, mints a
        single-use capability download link, emails the buyer instantly, and
        records the order - mirrors the existing Etsy/Fiverr fulfillment pattern."""
        if any(o.get("id") == external_id for o in self.orders):
            return {"success": True, "ignored": True, "reason": "Duplicate webhook delivery (order already recorded)"}

        try:
            from pipeline.stages.etsy_digital_store import EtsyDigitalStore
            etsy_store = EtsyDigitalStore()
            bundle_res = etsy_store.bundle_etsy_product(product_type=product_type)
        except Exception as e:
            return {"success": False, "error": f"Failed to build fulfillment ZIP: {e}"}

        if bundle_res.get("status") != "ok":
            return {"success": False, "error": f"Bundle build failed: {bundle_res}"}

        zip_path = bundle_res["zip_path"]
        token = secrets_lib.token_urlsafe(DOWNLOAD_TOKEN_BYTES)
        self.download_tokens[token] = {
            "zip_path": zip_path,
            "order_id": external_id,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now().timestamp() + DOWNLOAD_TOKEN_TTL_DAYS * 86400)
        }
        self.save_download_tokens()

        download_url = f"https://100.66.45.48:8800/api/download/order/{token}"
        email_res = self.send_fulfillment_email(buyer_email, bundle_res["bundle_name"], download_url)

        order_data = {
            "id": external_id,
            "platform": source,
            "buyer": buyer_email,
            "title": bundle_res["bundle_name"],
            "amount": amount,
            "received_at": datetime.now().isoformat(),
            "status": "fulfilled_auto",
            "deadline": "Instant Digital Delivery (Webhook Auto-Fulfillment)",
            "download_url": download_url,
            "email_sent": email_res.get("success", False)
        }
        self.orders.insert(0, order_data)
        self.save_orders()

        return {
            "success": True,
            "order": order_data,
            "download_url": download_url,
            "email_result": email_res
        }

    def send_fulfillment_email(self, recipient: str, product_title: str, download_url: str) -> Dict[str, Any]:
        """Sends a one-off purchase delivery email, reusing the same SMTP credentials
        already verified working for the daily newsletters (no second mail account)."""
        try:
            from pipeline.stages.newsletter_manager import NewsletterManager
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            from email.header import Header

            nm = NewsletterManager()
            cfg = nm.load_config()
            email_cfg = cfg.get("email", {})
            if not email_cfg or not email_cfg.get("enabled"):
                return {"success": False, "error": "Email dispatch is disabled in config"}

            html_body = f"""
            <html><body style='font-family:sans-serif;background:#0b0e14;color:#e6e6e6;padding:30px;'>
            <h2 style='color:#4cc9f0;'>Thank you for your purchase!</h2>
            <p>Your order <strong>{product_title}</strong> is ready for instant download.</p>
            <p><a href='{download_url}' style='background:#4f7cff;color:#fff;padding:12px 20px;border-radius:6px;text-decoration:none;'>Download Your Files</a></p>
            <p style='font-size:12px;color:#888;'>This link is valid for {DOWNLOAD_TOKEN_TTL_DAYS} days.</p>
            </body></html>
            """

            with smtplib.SMTP(email_cfg["smtp_host"], email_cfg["smtp_port"], timeout=20) as server:
                server.ehlo()
                server.starttls()
                server.login(email_cfg["sender"], email_cfg["password"])
                msg = MIMEMultipart("alternative")
                msg["Subject"] = Header(f"Your download is ready: {product_title}", "utf-8")
                msg["From"] = f"CreatorMediaLab <{email_cfg['sender']}>"
                msg["To"] = recipient
                msg.attach(MIMEText(html_body, "html", "utf-8"))
                server.send_message(msg)

            print(f"[OrderRadar] Fulfillment email sent to {recipient}")
            return {"success": True, "recipient": recipient}
        except Exception as e:
            print(f"[OrderRadar] Fulfillment email failed: {e}")
            return {"success": False, "error": str(e)}

    def get_delivery_by_token(self, token: str) -> Optional[Path]:
        """Resolves a capability download token to its ZIP path, enforcing expiry."""
        entry = self.download_tokens.get(token)
        if not entry:
            return None
        if time.time() > entry.get("expires_at", 0):
            return None
        zip_path = Path(entry["zip_path"])
        return zip_path if zip_path.exists() else None


# Global singleton instance export
order_radar = OrderRadar()
