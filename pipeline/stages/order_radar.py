from shared.atomic_writer import atomic_write_json, safe_read_json
import os
import json
import imaplib
import email
from email.header import decode_header
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import random

class OrderRadar:
    """
    Automated Order Radar for WORKHORSE.
    Monitors digitalcreatorassets@gmail.com via secure IMAP for incoming Fiverr & Etsy order alerts.
    """
    def __init__(self, base_dir: str = "F:/WORKHORSE"):
        self.base_dir = Path(base_dir)
        self.config_file = self.base_dir / "config" / "order_radar_config.json"
        self.orders_file = self.base_dir / "workspace" / "orders_history.json"
        
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.orders_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.load_config()
        self.load_orders()

    def load_config(self) -> Dict[str, Any]:
        default_config = {
            "email": "digitalcreatorassets@gmail.com",
            "app_password": "",
            "imap_server": "imap.gmail.com",
            "imap_port": 993,
            "check_interval_seconds": 120,
            "auto_check": False,
            "sound_alerts": True,
            "last_checked": None
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

    def update_config(self, app_password: Optional[str] = None, auto_check: Optional[bool] = None) -> Dict[str, Any]:
        if app_password is not None:
            self.config["app_password"] = app_password.replace(" ", "").strip()
        if auto_check is not None:
            self.config["auto_check"] = bool(auto_check)
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


# Global singleton instance export
order_radar = OrderRadar()
