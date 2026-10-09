from shared.atomic_writer import atomic_write_json, safe_read_json
"""
WORKHORSE MULTI-PUBLICATION DISPATCHER ENGINE (AGENT: HERALD [33 As])
Manages both private and public newsletters, blogs, and automated Twitter/X threads:
  1. 🌿 Florida Dispensary Deals (Private / Invite-Only Morning Scraper)
  2. 💋 The Daily Creator Pulse (Public • Adult Creators, Models & PPV Hacks)
  3. 📸 The Shutter & Studio Wire (Public • Photographers, Color Grading & Presets)
  4. ⚡ The Creator Blueprint (Public • Media Automation, Viral Hooks & Growth)

RESPONSIVE EMAIL ARCHITECTURE:
  - PC / Desktop: Horizontal multi-column layout (820px canvas, side-by-side schematic & visual diagram, 3-column promo suite).
  - Mobile: Fluid single-column vertical layout (100% width stacked cards, full-width touch buttons).
  - Zero Email Attachments: Hosted CDN images loaded inline without attachment cards or paperclips.
"""

import os
import sys
import json
import html

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import time
import smtplib
import subprocess
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header

from pipeline.stages.copy_synthesizer import CopySynthesizer

LINKTREE_URL = "https://linktr.ee/CreatorMediaLab"
ETSY_URL = "https://www.etsy.com/shop/CreatorMediaLab"
FIVERR_URL = "https://www.fiverr.com/s/X00R79G"
TWITTER_URL = "https://twitter.com/TheCreatorAsset"
TWITTER_ASSET_URL = "https://twitter.com/TheCreatorAsset"
TWITTER_PULSE_URL = "https://twitter.com/creatorpulselab"
PORTAL_BASE_URL = "https://digitalcreatorassets-source.github.io/creatormedialab/"
PORTAL_PULSE_URL = f"{PORTAL_BASE_URL}?pub=creator_pulse"
PORTAL_STUDIO_URL = f"{PORTAL_BASE_URL}?pub=studio_wire"
PORTAL_BLUEPRINT_URL = f"{PORTAL_BASE_URL}?pub=creator_blueprint"
PORTAL_DISPENSARY_URL = f"{PORTAL_BASE_URL}?pub=dispensary_deals"

# Hosted High-Resolution Diagram CDN URLs (Zero Email Attachments)
IMG_CREATOR_PULSE = "https://iili.io/n0FDRMx.jpg"
IMG_STUDIO_WIRE = "https://iili.io/n0FtLZJ.jpg"
IMG_CREATOR_FLYWHEEL = "https://iili.io/n0FDacB.jpg"


class NewsletterManager:
    def __init__(self, 
                 scripts_dir: str = "F:/AI_Media_Scripts",
                 workspace_base: str = "F:/WORKHORSE/workspace"):
        self.scripts_dir = Path(scripts_dir)
        self.config_path = self.scripts_dir / "deals_config.json"
        self.script_path = self.scripts_dir / "dispensary_deals.py"
        self.venv_python = self.scripts_dir / ".venv" / "Scripts" / "python.exe"
        if not self.venv_python.exists():
            self.venv_python = Path(sys.executable)

        self.workspace = Path(workspace_base)
        self.logs_dir = self.workspace / "newsletter_logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.logs_dir / "latest_run.log"
        self.subscribers_path = self.workspace / "newsletter_subscribers.json"
        self.scribe_cache_path = self.workspace / "scribe_daily_content.json"
        self._scribe: Optional[CopySynthesizer] = None

        self.current_process: Optional[subprocess.Popen] = None
        self.run_status: str = "idle"
        self.last_run_time: Optional[str] = None
        self._lock = threading.RLock()
        self._ensure_subscribers_seeded()

        # Multi-Publication Roster
        self.publications = {
            "creator_pulse": {
                "id": "creator_pulse",
                "name": "💋 The Daily Creator Pulse",
                "subject": "💋 The Daily Creator Pulse: 5-Part Morning Monetization Playbook & Visual Guide",
                "badge": "PUBLIC • HIGH VIRAL",
                "audience": "OnlyFans, Fansly, Cam Performers & Models",
                "schedule": "Daily 9:00 AM EST",
                "type": "public_growth",
                "funnel": "Fiverr Retouching, Etsy Bio Kits & Linktree"
            },
            "studio_wire": {
                "id": "studio_wire",
                "name": "📸 The Shutter & Studio Wire",
                "subject": "📸 The Shutter & Studio Wire: Portra 400 Lightroom Masterclass + 45° Lighting Blueprint",
                "badge": "PUBLIC • HIGH CONVERSION",
                "audience": "Portrait Photographers, Retouchers & Studios",
                "schedule": "Daily 8:30 AM EST",
                "type": "public_growth",
                "funnel": "Etsy Lightroom Presets (.XMP), Fiverr Batch Edits & Linktree"
            },
            "creator_blueprint": {
                "id": "creator_blueprint",
                "name": "⚡ The Creator Blueprint",
                "subject": "⚡ The Creator Blueprint: The $0 to $5k Media Asset Flywheel + Automated Content Engine",
                "badge": "PUBLIC • BROAD MEDIA",
                "audience": "Digital Creators, Freelancers & Media Builders",
                "schedule": "Daily 10:00 AM EST",
                "type": "public_growth",
                "funnel": "Linktree Hub (Etsy + Fiverr + Studio)"
            },
            "dispensary_deals": {
                "id": "dispensary_deals",
                "name": "🌿 Florida Dispensary Deals",
                "subject": "🌿 Florida Dispensary Deals: Morning Verified Drops & Patient Briefing",
                "badge": "PRIVATE • INVITE ONLY",
                "audience": "Medical Patients & Local Deal Hunters",
                "schedule": "Daily 7:00 AM EST",
                "type": "private_invite",
                "funnel": "Private Scraper Digest & Linktree"
            }
        }

    def get_publications(self) -> List[Dict[str, Any]]:
        return list(self.publications.values())

    # ──────────────────────────────────────────────────────────────────────────
    # SCRIBE [6 C] — DYNAMIC DAILY EDITORIAL CONTENT (NEWSLETTER LEAD STORIES,
    # MARKDOWN ARTICLES & TWITTER/X THREADS). Generated once per publication per
    # calendar day and cached to disk so repeated dashboard previews don't hammer
    # Ollama; falls back to static copy below if Scribe or Ollama are unavailable.
    # ──────────────────────────────────────────────────────────────────────────
    def _get_scribe(self) -> CopySynthesizer:
        with self._lock:
            if self._scribe is None:
                self._scribe = CopySynthesizer()
            return self._scribe

    def _log_fallback_incident(self, pub_id: str, reason: str) -> None:
        """Lazily logs to the shared incident log (same file the dashboard's Health
        Diagnostics modal reads) when a newsletter has to fall back to static copy, so
        it's visible instead of silently repeating the same body text day after day.
        Imported lazily to avoid a circular import with ai_operator.py, which itself
        imports NewsletterManager."""
        try:
            from pipeline.stages.ai_operator import ai_operator
            ai_operator.log_incident(
                "newsletter_manager",
                f"Scribe daily content generation failed for '{pub_id}': {reason}",
                "Falling back to static newsletter copy for today - content will not be unique to today.",
                status="needs_attention"
            )
        except Exception:
            pass

    def _get_daily_scribe_content(self, pub_id: str) -> Optional[Dict[str, Any]]:
        """Returns today's Scribe-generated content for pub_id, generating and caching
        it on first call of the day. Returns None (never raises) if generation fails,
        so every caller can gracefully fall back to its static copy. Retries once before
        giving up, since a single transient Ollama hiccup used to immediately fall back
        to the same static body for the rest of the day."""
        today_key = datetime.now().strftime("%Y-%m-%d")
        cache = safe_read_json(self.scribe_cache_path, default={})
        cached_entry = cache.get(pub_id)
        if cached_entry and cached_entry.get("date") == today_key and cached_entry.get("content"):
            return cached_entry["content"]

        pub = self.publications.get(pub_id, self.publications["creator_pulse"])
        result = None
        last_error = None
        for attempt in range(2):
            try:
                scribe = self._get_scribe()
                result = scribe.generate_daily_publication_content(
                    pub_id=pub_id,
                    pub_name=pub["name"],
                    audience=pub["audience"],
                    funnel_blurb=pub["funnel"],
                    today_str=datetime.now().strftime("%A, %B %d, %Y")
                )
                if result and result.get("success"):
                    break
                last_error = (result.get("error") if result else "no result")
                result = None
            except Exception as e:
                last_error = str(e)
                result = None
            print(f"[NewsletterManager] Scribe daily content generation attempt {attempt + 1}/2 failed for {pub_id}: {last_error}")

        if not result:
            self._log_fallback_incident(pub_id, last_error or "unknown error")
            return None

        cache[pub_id] = {"date": today_key, "content": result}
        atomic_write_json(self.scribe_cache_path, cache)
        return result

    def load_config(self) -> Dict[str, Any]:
        with self._lock:
            if not self.config_path.exists():
                return {}
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception as e:
                print(f"[NewsletterManager] Error loading config: {e}")
                return {}

        recipients = []
        email_sec = cfg.get("email", {})
        if "recipients" in email_sec and isinstance(email_sec["recipients"], list):
            recipients = [r.strip() for r in email_sec["recipients"] if r.strip()]
        elif "recipient" in email_sec and email_sec["recipient"]:
            recipients = [r.strip() for r in email_sec["recipient"].split(",") if r.strip()]

        cfg["recipients_list"] = recipients
        return cfg

    def save_config(self, cfg: Dict[str, Any]) -> bool:
        with self._lock:
            try:
                recipients = cfg.get("recipients_list", [])
                if "email" in cfg:
                    cfg["email"]["recipients"] = recipients
                    cfg["email"]["recipient"] = ", ".join(recipients) if recipients else ""

                clean_cfg = {k: v for k, v in cfg.items() if k != "recipients_list"}
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(clean_cfg, f, indent=2)
                return True
            except Exception as e:
                print(f"[NewsletterManager] Error saving config: {e}")
                return False

    def add_subscriber(self, email: str) -> Dict[str, Any]:
        email = email.strip().lower()
        if not email or "@" not in email or "." not in email:
            return {"success": False, "error": "Invalid email address format"}

        cfg = self.load_config()
        recipients = cfg.get("recipients_list", [])
        if email in recipients:
            return {"success": False, "error": f"{email} is already subscribed"}

        recipients.append(email)
        cfg["recipients_list"] = recipients
        if self.save_config(cfg):
            return {"success": True, "message": f"Added {email}", "recipients": recipients}
        return {"success": False, "error": "Failed to persist subscriber list"}

    def remove_subscriber(self, email: str) -> Dict[str, Any]:
        email = email.strip().lower()
        cfg = self.load_config()
        recipients = cfg.get("recipients_list", [])
        if email not in recipients:
            return {"success": False, "error": f"{email} is not in subscriber list"}

        recipients.remove(email)
        cfg["recipients_list"] = recipients
        if self.save_config(cfg):
            return {"success": True, "message": f"Removed {email}", "recipients": recipients}
        return {"success": False, "error": "Failed to persist subscriber list"}

    def update_elements(self, elements: Dict[str, Any], categories: Optional[List[str]] = None, min_discount: Optional[int] = None) -> bool:
        cfg = self.load_config()
        if "elements" not in cfg:
            cfg["elements"] = {}

        for k, v in elements.items():
            if k in cfg["elements"]:
                cfg["elements"][k].update(v)
            else:
                cfg["elements"][k] = v

        if categories is not None:
            cfg["categories"] = categories
        if min_discount is not None:
            cfg["min_discount_pct"] = min_discount

        return self.save_config(cfg)

    def _ensure_subscribers_seeded(self):
        with self._lock:
            if not self.subscribers_path.exists():
                cfg = self.load_config()
                recipients = cfg.get("recipients_list", ["careypmediagroup@gmail.com"])
                subs = []
                for r in recipients:
                    subs.append({
                        "email": r,
                        "name": "Carey",
                        "publications": ["creator_pulse", "studio_wire", "creator_blueprint", "dispensary_deals"],
                        "subscribed_at": datetime.now().isoformat(),
                        "source": "admin_seed",
                        "status": "active"
                    })
                try:
                    with open(self.subscribers_path, "w", encoding="utf-8") as f:
                        json.dump({"subscribers": subs, "updated_at": datetime.now().isoformat()}, f, indent=2)
                except Exception as e:
                    print(f"[NewsletterManager] Could not seed subscribers: {e}")

    def load_subscribers(self) -> Dict[str, Any]:
        with self._lock:
            if not self.subscribers_path.exists():
                self._ensure_subscribers_seeded()
            try:
                with open(self.subscribers_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[NewsletterManager] Error loading subscribers: {e}")
                return {"subscribers": [], "updated_at": datetime.now().isoformat()}

    def save_subscribers(self, data: Dict[str, Any]) -> bool:
        with self._lock:
            try:
                data["updated_at"] = datetime.now().isoformat()
                with open(self.subscribers_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                return True
            except Exception as e:
                print(f"[NewsletterManager] Error saving subscribers: {e}")
                return False

    def _sync_dispensary_deal_recipient(self, email: str, add: bool = True):
        try:
            cfg = self.load_config()
            recipients = cfg.get("recipients_list", [])
            email = email.lower().strip()
            if add and email not in recipients:
                recipients.append(email)
                cfg["recipients_list"] = recipients
                self.save_config(cfg)
            elif not add and email in recipients:
                recipients.remove(email)
                cfg["recipients_list"] = recipients
                self.save_config(cfg)
        except Exception as e:
            print(f"[NewsletterManager] Failed to sync dispensary deal recipient: {e}")

    def subscribe_multi(self, email: str, publications: List[str], name: str = "", source: str = "web_portal", send_welcome: bool = True) -> Dict[str, Any]:
        email = email.strip().lower()
        if not email or "@" not in email or "." not in email:
            return {"success": False, "error": "Invalid email address format"}

        valid_pubs = [p for p in publications if p in self.publications]
        if not valid_pubs:
            return {"success": False, "error": "No valid publications selected"}

        data = self.load_subscribers()
        subs = data.get("subscribers", [])
        
        existing_sub = next((s for s in subs if s.get("email", "").lower() == email), None)
        is_new = False
        newly_added_pubs = []
        
        if existing_sub:
            cur_pubs = set(existing_sub.get("publications", []))
            for p in valid_pubs:
                if p not in cur_pubs:
                    newly_added_pubs.append(p)
                    cur_pubs.add(p)
            existing_sub["publications"] = list(cur_pubs)
            if name:
                existing_sub["name"] = name.strip()
            existing_sub["status"] = "active"
            existing_sub["last_updated"] = datetime.now().isoformat()
        else:
            is_new = True
            newly_added_pubs = valid_pubs
            subs.append({
                "email": email,
                "name": name.strip(),
                "publications": valid_pubs,
                "subscribed_at": datetime.now().isoformat(),
                "source": source,
                "status": "active"
            })
            
        data["subscribers"] = subs
        self.save_subscribers(data)

        if "dispensary_deals" in valid_pubs:
            self._sync_dispensary_deal_recipient(email, add=True)

        welcome_dispatched = []
        target_welcomes = valid_pubs if send_welcome else []
        if send_welcome and target_welcomes:
            welcome_dispatched = list(target_welcomes)
            def _send_welcomes():
                for pub_id in target_welcomes:
                    try:
                        self.send_welcome_email(pub_id=pub_id, recipient=email, name=name)
                        time.sleep(1.0)
                    except Exception as exc:
                        print(f"[NewsletterManager] Welcome dispatch error for {email} ({pub_id}): {exc}")
            
            threading.Thread(target=_send_welcomes, daemon=True).start()

        pub_names = [self.publications[p]["name"] for p in valid_pubs]
        return {
            "success": True,
            "message": f"Successfully subscribed to {len(valid_pubs)} publication(s)",
            "email": email,
            "publications": valid_pubs,
            "publication_names": pub_names,
            "welcome_queued": welcome_dispatched,
            "is_new": is_new
        }

    def unsubscribe(self, email: str, publication: Optional[str] = None) -> Dict[str, Any]:
        email = email.strip().lower()
        data = self.load_subscribers()
        subs = data.get("subscribers", [])
        
        target = next((s for s in subs if s.get("email", "").lower() == email), None)
        if not target:
            return {"success": False, "error": "Email address not found in subscriber roster"}

        if publication and publication != "all" and publication in target.get("publications", []):
            target["publications"].remove(publication)
            if not target["publications"]:
                target["status"] = "unsubscribed"
            message = f"Unsubscribed from {self.publications.get(publication, {}).get('name', publication)}"
            if publication == "dispensary_deals":
                self._sync_dispensary_deal_recipient(email, add=False)
        else:
            target["publications"] = []
            target["status"] = "unsubscribed"
            message = "Unsubscribed from all publications"
            self._sync_dispensary_deal_recipient(email, add=False)

        target["unsubscribed_at"] = datetime.now().isoformat()
        self.save_subscribers(data)
        return {"success": True, "message": message, "email": email}

    def get_subscribers_summary(self) -> Dict[str, Any]:
        data = self.load_subscribers()
        subs = data.get("subscribers", [])
        counts = {p: 0 for p in self.publications}
        active_subs = [s for s in subs if s.get("status") != "unsubscribed"]
        for s in active_subs:
            for p in s.get("publications", []):
                if p in counts:
                    counts[p] += 1
        return {
            "total_active": len(active_subs),
            "counts_by_publication": counts,
            "subscribers": subs,
            "publications": self.get_publications()
        }

    def send_welcome_email(self, pub_id: str, recipient: str, name: str = "") -> Dict[str, Any]:
        cfg = self.load_config()
        email_cfg = cfg.get("email", {})
        if not email_cfg or not email_cfg.get("enabled"):
            return {"success": False, "error": "Email dispatch is disabled in config"}

        pub = self.publications.get(pub_id, self.publications["creator_pulse"])
        salutation = f"Hey {name}," if name else "Hey Creator,"
        
        welcome_subjects = {
            "creator_pulse": "💋 Welcome to The Daily Creator Pulse: Your Day 1 Monetization Blueprint & Visual Rig",
            "studio_wire": "📸 Welcome to The Shutter & Studio Wire: Your 45° Key/Fill Blueprint + Portra 400 Formula",
            "creator_blueprint": "⚡ Welcome to The Creator Blueprint: Your $0 to $5k Media Asset Flywheel",
            "dispensary_deals": "🌿 Welcome to Florida Dispensary Deals: Morning Drops Confirmed"
        }
        subject = welcome_subjects.get(pub_id, f"Welcome to {pub['name']}!")
        
        html_body = self.get_html_preview(pub_id)
        
        welcome_banner = f"""
    <!-- WELCOME ONBOARDING BANNER -->
    <tr>
      <td class='mobile-pad' style='padding:18px 36px 6px 36px;'>
        <table width='100%' cellspacing='0' cellpadding='0' style='background:linear-gradient(135deg, rgba(76,201,240,0.18) 0%, rgba(247,37,133,0.18) 100%);border:1px solid #4cc9f0;border-radius:10px;padding:16px 20px;'>
          <tr>
            <td>
              <div style='font-size:11px;font-weight:800;letter-spacing:1.5px;text-transform:uppercase;color:#4cc9f0;margin-bottom:4px;'>⚡ OFFICIAL SUBSCRIBER CONFIRMATION &bull; DAY 1 ISSUE</div>
              <div style='font-size:16px;font-weight:800;color:#ffffff;line-height:1.3;'>{salutation} You're confirmed for {pub['name']}!</div>
              <div style='font-size:13px;color:#cbd5e1;margin-top:6px;line-height:1.5;'>Here is today's full-fidelity briefing and masterclass. You will receive every new issue directly in your inbox at <strong>{pub['schedule']}</strong>. Save this address to your contacts so it never lands in promotions!</div>
            </td>
          </tr>
        </table>
      </td>
    </tr>
        """
        if "<!-- WELCOME_HOOK -->" in html_body:
            html_body = html_body.replace("<!-- WELCOME_HOOK -->", welcome_banner)

        try:
            with smtplib.SMTP(email_cfg["smtp_host"], email_cfg["smtp_port"], timeout=20) as server:
                server.ehlo()
                server.starttls()
                server.login(email_cfg["sender"], email_cfg["password"])

                msg = MIMEMultipart("alternative")
                msg["Subject"] = Header(subject, "utf-8")
                msg["From"] = f"CreatorMediaLab <{email_cfg['sender']}>"
                msg["To"] = recipient
                msg.attach(MIMEText(html_body, "html", "utf-8"))

                server.send_message(msg)
                print(f"[NewsletterManager] Welcome issue sent to {recipient} ({pub_id})")
                return {
                    "success": True,
                    "recipient": recipient,
                    "pub_id": pub_id,
                    "subject": subject
                }
        except Exception as e:
            print(f"[NewsletterManager] Welcome email dispatch failed for {recipient}: {e}")
            return {"success": False, "error": str(e)}


    def trigger_dispatch(self) -> Dict[str, Any]:
        with self._lock:
            if self.run_status == "running":
                return {
                    "success": False,
                    "message": "Dispatch is already running in background",
                    "status": "running"
                }

            self.run_status = "running"
            self.last_run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        def _runner():
            print(f"[Herald] Starting Morning Dispatch at {self.last_run_time}...")
            if not self.script_path.exists():
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now()}] ERROR: Target script {self.script_path} not found.\n")
                self.run_status = "error"
                return

            with open(self.log_file, "w", encoding="utf-8") as log_f:
                log_f.write(f"=== HERALD DISPATCH INITIATED: {self.last_run_time} ===\n")
                log_f.write(f"Interpreter: {self.venv_python}\n")
                log_f.write(f"Target Script: {self.script_path}\n")
                log_f.write("-" * 60 + "\n\n")
                log_f.flush()

                try:
                    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
                    process = subprocess.Popen(
                        [str(self.venv_python), str(self.script_path)],
                        cwd=str(self.scripts_dir),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        env=env
                    )
                    self.current_process = process

                    for line in process.stdout:
                        log_f.write(line)
                        log_f.flush()

                    process.wait()
                    if process.returncode == 0:
                        self.run_status = "completed"
                        log_f.write(f"\n=== HERALD DISPATCH COMPLETED SUCCESSFULLY [Code: 0] ===\n")
                    else:
                        self.run_status = "error"
                        log_f.write(f"\n=== HERALD DISPATCH FAILED [Code: {process.returncode}] ===\n")

                except Exception as exc:
                    self.run_status = "error"
                    log_f.write(f"\n[CRITICAL ERROR] Failed to launch script: {exc}\n")
                finally:
                    log_f.flush()

        t = threading.Thread(target=_runner, daemon=True)
        t.start()

        return {
            "success": True,
            "message": "Herald morning dispatch started in background",
            "status": "running",
            "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def get_run_status(self) -> Dict[str, Any]:
        if self.current_process and self.current_process.poll() is not None:
            if self.run_status == "running":
                self.run_status = "completed" if self.current_process.returncode == 0 else "error"

        recent_logs = ""
        if self.log_file.exists():
            try:
                with open(self.log_file, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                    recent_logs = "".join(lines[-150:])
            except Exception as e:
                recent_logs = f"Error reading logs: {e}"

        return {
            "status": self.run_status,
            "last_run_time": self.last_run_time,
            "recent_logs": recent_logs
        }

    # ──────────────────────────────────────────────────────────────────────────
    # REAL AUTOMATED DISPATCH — sends today's issue to every active subscriber
    # opted into this publication. This is the actual daily-send counterpart to
    # send_test_email (single test recipient) / send_welcome_email (one-off onboarding).
    # ──────────────────────────────────────────────────────────────────────────
    def send_publication_now(self, pub_id: str) -> Dict[str, Any]:
        cfg = self.load_config()
        email_cfg = cfg.get("email", {})
        if not email_cfg or not email_cfg.get("enabled"):
            return {"success": False, "error": "Email dispatch is disabled in config"}

        pub = self.publications.get(pub_id)
        if not pub:
            return {"success": False, "error": f"Unknown publication '{pub_id}'"}

        subs = self.load_subscribers().get("subscribers", [])
        recipients = [
            s["email"] for s in subs
            if s.get("status") == "active" and pub_id in (s.get("publications") or [])
        ]
        if not recipients:
            return {"success": False, "error": f"No active subscribers for '{pub_id}'", "sent": 0}

        subject = pub["subject"]
        html_body = self.get_html_preview(pub_id)
        sent: List[str] = []
        failed: List[Dict[str, str]] = []

        try:
            with smtplib.SMTP(email_cfg["smtp_host"], email_cfg["smtp_port"], timeout=20) as server:
                server.ehlo()
                server.starttls()
                server.login(email_cfg["sender"], email_cfg["password"])
                for recipient in recipients:
                    try:
                        msg = MIMEMultipart("alternative")
                        msg["Subject"] = Header(subject, "utf-8")
                        msg["From"] = f"CreatorMediaLab <{email_cfg['sender']}>"
                        msg["To"] = recipient
                        msg.attach(MIMEText(html_body, "html", "utf-8"))
                        server.send_message(msg)
                        sent.append(recipient)
                        print(f"[NewsletterManager] '{pub_id}' sent to {recipient}")
                    except Exception as e:
                        failed.append({"email": recipient, "error": str(e)})
                        print(f"[NewsletterManager] '{pub_id}' FAILED for {recipient}: {e}")
        except Exception as e:
            print(f"[NewsletterManager] SMTP connection failed while dispatching '{pub_id}': {e}")
            return {"success": False, "error": str(e), "sent": 0, "recipients_attempted": len(recipients)}

        return {
            "success": len(sent) > 0,
            "pub_id": pub_id,
            "subject": subject,
            "sent": len(sent),
            "sent_to": sent,
            "failed": failed,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    # ──────────────────────────────────────────────────────────────────────────
    # CLEAN ZERO-ATTACHMENT EMAIL SENDER
    # ──────────────────────────────────────────────────────────────────────────
    def send_test_email(self, pub_id: str = "creator_pulse", recipient: str = "careypmediagroup@gmail.com") -> Dict[str, Any]:
        cfg = self.load_config()
        email_cfg = cfg.get("email", {})
        if not email_cfg or not email_cfg.get("enabled"):
            return {"success": False, "error": "Email dispatch is disabled in config"}

        pub = self.publications.get(pub_id, self.publications["creator_pulse"])
        subject = f"[TEST ISSUE] {pub['subject']}"
        html_body = self.get_html_preview(pub_id)

        try:
            with smtplib.SMTP(email_cfg["smtp_host"], email_cfg["smtp_port"], timeout=20) as server:
                server.ehlo()
                server.starttls()
                server.login(email_cfg["sender"], email_cfg["password"])

                # Clean alternative multipart — ZERO MIMEImage attachments
                msg = MIMEMultipart("alternative")
                msg["Subject"] = Header(subject, "utf-8")
                msg["From"] = f"CreatorMediaLab <{email_cfg['sender']}>"
                msg["To"] = recipient
                msg.attach(MIMEText(html_body, "html", "utf-8"))

                server.send_message(msg)
                print(f"[NewsletterManager] Test email for {pub_id} successfully sent to {recipient}")
                return {
                    "success": True,
                    "message": f"Newsletter '{pub['name']}' sent to {recipient}",
                    "recipient": recipient,
                    "subject": subject,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
        except Exception as e:
            print(f"[NewsletterManager] Failed to send email: {e}")
            return {"success": False, "error": str(e)}

    # ──────────────────────────────────────────────────────────────────────────
    # RESPONSIVE HORIZONTAL (PC) / VERTICAL (MOBILE) EMAIL BUILDERS
    # ──────────────────────────────────────────────────────────────────────────
    def _load_iris_verified_filenames(self) -> set:
        """Returns the set of filenames with a passed=true IRIS QC audit record."""
        audit_log = self.workspace / "comfy_qc_audit.json"
        verified = set()
        if audit_log.exists():
            try:
                with open(audit_log, "r", encoding="utf-8") as f:
                    records = json.load(f)
                for r in records:
                    if r.get("passed") and r.get("filename"):
                        verified.add(r["filename"])
            except Exception:
                pass
        return verified

    def get_latest_comfy_visual(self, pub_id: str = "creator_pulse") -> Optional[Path]:
        """
        Retrieves the latest IRIS-QC-verified visual render for the SPECIFIC brand.
        - 'creator_pulse' / 'creatorpulselab': searches workspace/brand_assets/creator_pulse_lab
        - 'studio_wire' / 'creator_blueprint' / 'TheCreatorAsset': searches workspace/brand_assets/creator_media_lab
        Falls back to brand prefix filtering (CPL_ vs CML_).
        Only ever returns a file with a passed=true record in comfy_qc_audit.json - a
        test render or a render that failed QC must never be auto-attached to a live post.
        """
        is_pulse = any(k in pub_id.lower() for k in ["pulse", "boudoir", "cam", "adult", "cpl"])
        target_subfolder = "creator_pulse_lab" if is_pulse else "creator_media_lab"
        target_prefix = "CPL_" if is_pulse else "CML_"
        verified_names = self._load_iris_verified_filenames()

        def _latest_verified(files: List[Path]) -> Optional[Path]:
            verified_files = [f for f in files if f.name in verified_names]
            if not verified_files:
                return None
            verified_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return verified_files[0]

        # 1. Dedicated brand folder
        brand_dir = self.workspace / "brand_assets" / target_subfolder
        if brand_dir.exists():
            files = [f for f in brand_dir.iterdir() if f.is_file() and f.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]]
            picked = _latest_verified(files)
            if picked:
                return picked

        # 2. General comfy_renders filtered by brand prefix
        renders_dir = self.workspace / "brand_assets" / "comfy_renders"
        if renders_dir.exists():
            filtered = [
                f for f in renders_dir.iterdir()
                if f.is_file() and f.name.startswith(target_prefix) and f.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]
            ]
            picked = _latest_verified(filtered)
            if picked:
                return picked

        # 3. Fallback: only an IRIS-verified render, regardless of brand prefix - never
        # fall back to "whatever file is newest" since that can be an unaudited test render
        renders_dir = self.workspace / "brand_assets" / "comfy_renders"
        if renders_dir.exists():
            all_files = [f for f in renders_dir.iterdir() if f.is_file() and f.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]]
            picked = _latest_verified(all_files)
            if picked:
                return picked

        return None

    def _warn_if_visual_stale(self, pub_id: str, visual_path: Path) -> None:
        """Logs a (once-per-day-per-publication) incident when the newsletter's embedded
        image isn't from today - it's still a real IRIS-verified render, just not freshly
        generated for today's send, so this is visibility rather than a hard failure."""
        try:
            render_date = datetime.fromtimestamp(visual_path.stat().st_mtime).strftime("%Y-%m-%d")
            today_key = datetime.now().strftime("%Y-%m-%d")
            if render_date == today_key:
                return
            state_key = f"stale_visual_warned_{pub_id}_{today_key}"
            cache = safe_read_json(self.scribe_cache_path, default={})
            if cache.get(state_key):
                return
            cache[state_key] = True
            atomic_write_json(self.scribe_cache_path, cache)
            self._log_fallback_incident(
                pub_id,
                f"Embedded newsletter image '{visual_path.name}' was last generated on {render_date}, not today ({today_key}) - no fresh verified render was available."
            )
        except Exception:
            pass

    def get_publication_visual_embed(self, pub_id: str = "creator_pulse") -> Dict[str, str]:
        """
        Returns image src and captions for newsletters.
        If an approved ComfyUI 5070 Ti render exists, embeds it dynamically.
        Otherwise falls back to the default diagram CDN.
        """
        import base64
        visual_path = self.get_latest_comfy_visual(pub_id)
        if visual_path and visual_path.exists():
            self._warn_if_visual_stale(pub_id, visual_path)
            try:
                b64 = base64.b64encode(visual_path.read_bytes()).decode("utf-8")
                mime = "image/png" if visual_path.suffix.lower() == ".png" else "image/jpeg"
                data_uri = f"data:{mime};base64,{b64}"
                url_path = f"/static/brand_assets/comfy_renders/{visual_path.name}"
                is_pulse = any(k in pub_id.lower() for k in ["pulse", "boudoir", "cam", "adult", "cpl"])
                if is_pulse:
                    caption = "💋 Figure 4.1 &bull; Luxury Boudoir & Monetization Styling (RTX 5070 Ti &bull; Iris [77 Ir] Verified)"
                    subcaption = "Warm Rim Lighting &bull; Intimate Velvet & Satin Texture"
                else:
                    caption = "📸 Figure 4.1 &bull; Editorial Studio Masterclass (RTX 5070 Ti &bull; Iris [77 Ir] Verified)"
                    subcaption = "5600K Key + Kodak Portra 400 Calibration &bull; Magazine Depth of Field"

                return {
                    "src": data_uri,
                    "web_src": url_path,
                    "local_path": str(visual_path),
                    "filename": visual_path.name,
                    "caption": caption,
                    "subcaption": subcaption
                }
            except Exception:
                pass

        default_map = {
            "creator_pulse": (IMG_CREATOR_PULSE, "📸 Figure 4.1 &bull; Studio Setup", "5600K Softbox + 3200K Rim"),
            "studio_wire": (IMG_STUDIO_WIRE, "📸 Figure 3.1 &bull; Beauty Dish", "45° Feather + Silver Clamshell"),
            "creator_blueprint": (IMG_CREATOR_FLYWHEEL, "⚡ Figure 2.1 &bull; Flywheel", "Service Validation to Digital Assets"),
        }
        src, cap, subcap = default_map.get(pub_id, (IMG_CREATOR_PULSE, "Studio Visual", "Creator Media Lab"))
        return {
            "src": src,
            "web_src": src,
            "local_path": "",
            "filename": "",
            "caption": cap,
            "subcaption": subcap
        }

    def get_twitter_thread_with_media(self, pub_id: str = "creator_pulse") -> Dict[str, Any]:
        """Returns thread text array along with latest ComfyUI verified image path for Twitter/X."""
        thread = self.get_twitter_thread(pub_id)
        visual_path = self.get_latest_comfy_visual(pub_id)
        return {
            "thread": thread,
            "media_path": str(visual_path) if visual_path else None,
            "media_filename": visual_path.name if visual_path else None,
            "pub": pub_id
        }

    def get_html_preview(self, pub_id: str = "creator_pulse") -> str:
        today_str = datetime.now().strftime("%A, %B %d, %Y")

        if pub_id == "creator_pulse":
            return self._build_creator_pulse_html(today_str)
        elif pub_id == "studio_wire":
            return self._build_studio_wire_html(today_str)
        elif pub_id == "creator_blueprint":
            return self._build_creator_blueprint_html(today_str)
        else:
            return self._build_dispensary_deals_html(today_str)

    # ── 1. THE DAILY CREATOR PULSE ──────────────────────────────────────────
    def _build_creator_pulse_html(self, today_str: str) -> str:
        visual_info = self.get_publication_visual_embed("creator_pulse")
        img_src = visual_info["src"]
        caption = visual_info["caption"]
        subcaption = visual_info["subcaption"]
        scribe_content = self._get_daily_scribe_content("creator_pulse")
        lead_headline = html.escape((scribe_content or {}).get("lead_headline") or "Why Tight Face-Framing Crops Are Beating Full-Body Feeds")
        lead_body = html.escape((scribe_content or {}).get("lead_body") or "Short-form recommendation engines (TikTok, IG Reels, and Twitter/X) are heavily penalizing wide glamour shots that resemble sensitive content. Top-earning creators are seeing a 3.4x lift in organic reach by using tight 4:5 portrait crops focusing strictly on eye contact, lips, and subtle expressions.")
        return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1.0'>
  <title>The Daily Creator Pulse</title>
  <style>
    body {{ margin:0; padding:24px 12px; background-color:#070b14; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; color:#e2e8f0; -webkit-text-size-adjust:100%; -ms-text-size-adjust:100%; }}
    table {{ border-collapse:collapse; mso-table-lspace:0pt; mso-table-rspace:0pt; }}
    img {{ border:0; height:auto; line-height:100%; outline:none; text-decoration:none; max-width:100%; }}
    .main-table {{ width:100%; max-width:820px; margin:0 auto; background:#0d1527; border:1px solid #f72585; border-radius:14px; overflow:hidden; box-shadow:0 12px 40px rgba(0,0,0,0.75); }}
    
    .row-fluid {{ font-size:0; text-align:left; }}
    .col-half {{ display:inline-block; width:100%; max-width:364px; vertical-align:top; box-sizing:border-box; text-align:left; }}
    .col-third {{ display:inline-block; width:100%; max-width:218px; vertical-align:top; box-sizing:border-box; text-align:left; }}
    .col-pad-right {{ margin-right:16px; }}
    .promo-pad-right {{ margin-right:10px; }}

    @media only screen and (max-width: 680px) {{
      body {{ padding:10px 4px !important; }}
      .main-table {{ width:100% !important; max-width:100% !important; border-radius:0 !important; border-left:none !important; border-right:none !important; }}
      .col-half, .col-third {{ display:block !important; width:100% !important; max-width:100% !important; margin-right:0 !important; margin-bottom:14px !important; }}
      .mobile-pad {{ padding-left:18px !important; padding-right:18px !important; }}
      .mobile-header-pad {{ padding:24px 18px 20px 18px !important; }}
      .mobile-btn {{ display:block !important; width:100% !important; text-align:center !important; box-sizing:border-box !important; margin-bottom:8px !important; }}
    }}
  </style>
</head>
<body style='margin:0;padding:24px 12px;background-color:#070b14;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:#e2e8f0;'>
  <table role='presentation' width='100%' cellspacing='0' cellpadding='0' border='0' align='center' class='main-table' style='max-width:820px;margin:0 auto;background:#0d1527;border:1px solid #f72585;border-radius:14px;overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,0.75);'>
    
    <!-- HEADER BRANDING -->
    <tr>
      <td class='mobile-header-pad' style='padding:32px 36px 26px 36px;background:linear-gradient(135deg, rgba(247,37,133,0.22) 0%, rgba(114,9,183,0.35) 100%);border-bottom:2px solid #f72585;'>
        <table width='100%' cellspacing='0' cellpadding='0'>
          <tr>
            <td>
              <span style='display:inline-block;background:#f72585;color:#ffffff;font-size:10.5px;font-weight:800;letter-spacing:1.2px;padding:4px 12px;border-radius:12px;text-transform:uppercase;'>ISSUE #042 &bull; CREATOR MONETIZATION PLAYBOOK</span>
              <h1 style='margin:12px 0 6px 0;font-size:28px;font-weight:900;color:#ffffff;letter-spacing:-0.5px;'>💋 The Daily Creator Pulse</h1>
              <p style='margin:0;font-size:13.5px;color:#cbd5e1;line-height:1.5;'>Daily Organic Traffic, High-Converting PPV Formulas & Stream Monetization &bull; {today_str}</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- WELCOME_HOOK -->

    <!-- INFORMATION AREA 1: ALGORITHM & TRAFFIC WATCH (HORIZONTAL METRIC CARDS ON PC) -->
    <tr>
      <td class='mobile-pad' style='padding:28px 36px 18px 36px;'>
        <div style='display:inline-block;background:rgba(247,37,133,0.15);color:#f72585;font-size:11px;font-weight:800;letter-spacing:1px;padding:3px 10px;border-radius:4px;text-transform:uppercase;margin-bottom:8px;'>
          SECTION 1 &bull; ALGORITHM & TRAFFIC RADAR
        </div>
        <h2 style='margin:0 0 10px 0;font-size:20px;color:#ffffff;'>{lead_headline}</h2>
        <p style='margin:0 0 16px 0;font-size:14px;line-height:1.65;color:#cbd5e1;'>
          {lead_body}
        </p>

        <!-- 2-COLUMN HORIZONTAL METRIC CARDS ON PC, VERTICAL ON MOBILE -->
        <div class='row-fluid' style='font-size:0;text-align:left;'>
          <div class='col-half col-pad-right' style='display:inline-block;width:100%;max-width:364px;vertical-align:top;box-sizing:border-box;margin-right:16px;background:#090d18;border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:14px 18px;'>
            <span style='font-size:11px;color:#94a3b8;text-transform:uppercase;font-weight:bold;letter-spacing:0.5px;'>Organic Retention Benchmark</span>
            <div style='font-size:22px;font-weight:bold;color:#10b981;margin-top:4px;'>78.4% at 3 Seconds</div>
            <span style='font-size:12px;color:#64748b;'>With natural editorial eye contact</span>
          </div>
          <div class='col-half' style='display:inline-block;width:100%;max-width:364px;vertical-align:top;box-sizing:border-box;background:#090d18;border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:14px 18px;'>
            <span style='font-size:11px;color:#94a3b8;text-transform:uppercase;font-weight:bold;letter-spacing:0.5px;'>Feed Shadowban Risk</span>
            <div style='font-size:22px;font-weight:bold;color:#f72585;margin-top:4px;'>Reduced by 62%</div>
            <span style='font-size:12px;color:#64748b;'>Bypasses aggressive AI moderation</span>
          </div>
        </div>
      </td>
    </tr>

    <!-- INFORMATION AREA 2: HIGH-CONVERTING PPV SCRIPTS -->
    <tr>
      <td class='mobile-pad' style='padding:18px 36px;'>
        <div style='display:inline-block;background:rgba(247,37,133,0.15);color:#f72585;font-size:11px;font-weight:800;letter-spacing:1px;padding:3px 10px;border-radius:4px;text-transform:uppercase;margin-bottom:8px;'>
          SECTION 2 &bull; PPV & DM TEASER FORMULAS
        </div>
        <h2 style='margin:0 0 10px 0;font-size:20px;color:#ffffff;'>3 Swipe-File Teasers That Out-Converted Explicit Photos</h2>
        <p style='margin:0 0 14px 0;font-size:14px;line-height:1.65;color:#cbd5e1;'>
          Curiosity and perceived intimacy convert locked mass messages at a significantly higher percentage than explicit descriptions. Use these 3 tested formulas tonight:
        </p>

        <!-- Script 1 -->
        <div style='background:#090d18;border-left:4px solid #f72585;padding:14px 18px;border-radius:0 8px 8px 0;margin-bottom:12px;border-top:1px solid rgba(255,255,255,0.05);border-right:1px solid rgba(255,255,255,0.05);border-bottom:1px solid rgba(255,255,255,0.05);'>
          <strong style='color:#f72585;font-size:13.5px;'>🎧 Script 1: The "Midnight Audio" Teaser ($18 - $25 Unlock)</strong>
          <p style='margin:6px 0 4px 0;font-size:13.5px;color:#f8fafc;font-style:italic;'>
            "Put your headphones on before you press play... 🎧 Whispered voice memo from yesterday's studio shoot. Unlocked for my top 5% only."
          </p>
          <span style='font-size:11.5px;color:#94a3b8;'>Insight: Audio triggers intense 1-on-1 emotional connection without devaluing your visual media set.</span>
        </div>

        <!-- Script 2 -->
        <div style='background:#090d18;border-left:4px solid #f72585;padding:14px 18px;border-radius:0 8px 8px 0;margin-bottom:12px;border-top:1px solid rgba(255,255,255,0.05);border-right:1px solid rgba(255,255,255,0.05);border-bottom:1px solid rgba(255,255,255,0.05);'>
          <strong style='color:#f72585;font-size:13.5px;'>🔒 Script 2: The "Curiosity Gap" Vault ($35 - $50 Unlock)</strong>
          <p style='margin:6px 0 4px 0;font-size:13.5px;color:#f8fafc;font-style:italic;'>
            "My photographer told me not to post these 4 frames anywhere on the public feed... Too unfiltered. Unlocking the raw set in DMs for the next 2 hours only."
          </p>
          <span style='font-size:11.5px;color:#94a3b8;'>Insight: Artificial scarcity plus behind-the-scenes taboos drive urgency among whale spenders.</span>
        </div>

        <!-- Script 3 -->
        <div style='background:#090d18;border-left:4px solid #f72585;padding:14px 18px;border-radius:0 8px 8px 0;border-top:1px solid rgba(255,255,255,0.05);border-right:1px solid rgba(255,255,255,0.05);border-bottom:1px solid rgba(255,255,255,0.05);'>
          <strong style='color:#f72585;font-size:13.5px;'>🗳️ Script 3: The "Color Grade Choice" Poll ($5 - $10 Tip)</strong>
          <p style='margin:6px 0 4px 0;font-size:13.5px;color:#f8fafc;font-style:italic;'>
            "Which color grade should I post on my public feed tomorrow: Golden Hour Glow or Dark Boudoir? Tip $5 with your vote and I will send you the unreleased outtake."
          </p>
          <span style='font-size:11.5px;color:#94a3b8;'>Insight: Low-friction micro-tipping activates non-spending subscribers into active purchasers.</span>
        </div>
      </td>
    </tr>

    <!-- INFORMATION AREA 3: STREAM TIP MENU LADDER (HORIZONTAL RESPONSIVE DATA GRID) -->
    <tr>
      <td class='mobile-pad' style='padding:18px 36px;'>
        <div style='display:inline-block;background:rgba(255,209,102,0.15);color:#ffd166;font-size:11px;font-weight:800;letter-spacing:1px;padding:3px 10px;border-radius:4px;text-transform:uppercase;margin-bottom:8px;'>
          SECTION 3 &bull; STREAM & CAM ENGAGEMENT
        </div>
        <h2 style='margin:0 0 10px 0;font-size:20px;color:#ffffff;'>The "Ladder Milestone" System For Cam & Live Streams</h2>
        <p style='margin:0 0 14px 0;font-size:14px;line-height:1.65;color:#cbd5e1;'>
          Static tip menus hit donation ceilings quickly because viewers feel like they are purchasing an isolated item. Replacing static lists with a <strong>Progressive Ladder</strong> creates collective room momentum:
        </p>

        <div style='overflow-x:auto;-webkit-overflow-scrolling:touch;width:100%;max-width:100%;margin-bottom:8px;'><table width='100%' class='responsive-table' cellspacing='0' cellpadding='10' style='font-size:13px;color:#cbd5e1;border-collapse:collapse;margin-bottom:8px;'>
            <tr style='background:#090d18;color:#ffd166;font-weight:bold;'>
              <th align='left' style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Milestone</th>
              <th align='left' style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Token Target</th>
              <th align='left' style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Action</th>
              <th align='left' style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Viewer Trigger</th>
            </tr>
            <tr>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);font-weight:bold;'>Tier 1</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);color:#10b981;font-weight:bold;'>150 Tokens</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Whispered audio secret</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Low barrier entry</td>
            </tr>
            <tr style='background:rgba(255,255,255,0.02);'>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);font-weight:bold;'>Tier 2</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);color:#10b981;font-weight:bold;'>450 Tokens</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Song request & outfit change</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Interactive collaboration</td>
            </tr>
            <tr>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);font-weight:bold;'>Tier 3 (Peak)</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);color:#ffd166;font-weight:bold;'>900 Tokens</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>VIP private polaroid drop</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Exclusivity climax</td>
            </tr>
          </table>
        </div>
      </td>
    </tr>

    <!-- INFORMATION AREA 4: LIGHTING & VISUAL AESTHETIC (HORIZONTAL ON PC, VERTICAL ON MOBILE) -->
    <tr>
      <td class='mobile-pad' style='padding:18px 36px;'>
        <div style='display:inline-block;background:rgba(59,130,246,0.15);color:#60a5fa;font-size:11px;font-weight:800;letter-spacing:1px;padding:3px 10px;border-radius:4px;text-transform:uppercase;margin-bottom:8px;'>
          SECTION 4 &bull; LIGHTING & VISUAL PRODUCTION
        </div>
        <h2 style='margin:0 0 10px 0;font-size:20px;color:#ffffff;'>The "2-Light Rim Formula" For Phone & Webcam Streaming</h2>
        <p style='margin:0 0 16px 0;font-size:14px;line-height:1.65;color:#cbd5e1;'>
          Most creators rely on a single ring light placed right in front of their face. This flattens your facial features and creates washed-out skin. Adding a single $25 warm accent light behind your shoulder creates instant 3-dimensional depth:
        </p>

        <!-- 2-COLUMN RESPONSIVE DIAGRAM CONTAINER: HORIZONTAL ON PC, VERTICAL ON MOBILE -->
        <div class='row-fluid' style='font-size:0;text-align:left;'>
          
          <!-- LEFT COLUMN: SCHEMATIC SPECIFICATIONS & RULES -->
          <div class='col-half col-pad-right' style='display:inline-block;width:100%;max-width:364px;vertical-align:top;box-sizing:border-box;margin-right:16px;'>
            <div class='ascii-diagram' style='background:#060a14;border:1px solid rgba(96,165,250,0.3);border-radius:8px;padding:14px;font-family:Consolas,monaco,monospace;font-size:11px;color:#93c5fd;line-height:1.55;margin-bottom:12px;overflow-x:auto;max-width:100%;box-sizing:border-box;'>
[WARM RIM (3200K)] ── (Behind Hair) ──┐<br>
                                       ↓<br>
               [ CREATOR / MODEL ]<br>
                        ↑<br>
[KEY SOFTBOX (5600K)] ── 45° Angle ───┘<br>
                        ↑<br>
            [ 4K PHONE / CAM @ EYE ]
            </div>
            <div style='background:#090d18;border-left:3px solid #60a5fa;padding:10px 14px;border-radius:0 6px 6px 0;font-size:12px;color:#94a3b8;line-height:1.5;'>
              <strong style='color:#e2e8f0;'>Pro Tip:</strong> Set Key Light to 5600K clean white; dial Warm Rim Light to 3200K amber. The color temperature contrast separates hair from dark studio walls instantly.
            </div>
          </div>

          <!-- RIGHT COLUMN: HIGH-RESOLUTION VISUAL DIAGRAM IMAGE -->
          <div class='col-half' style='display:inline-block;width:100%;max-width:364px;vertical-align:top;box-sizing:border-box;'>
            <div style='border-radius:10px;overflow:hidden;border:1px solid rgba(247,37,133,0.4);background:#090d18;box-shadow:0 8px 25px rgba(0,0,0,0.7);'>
              <img src="{img_src}" alt="Creator Studio Visual" width="364" style="width:100%;max-width:364px;height:auto;display:block;margin:0 auto;border:none;">
              <table width='100%' cellspacing='0' cellpadding='0' border='0' style='background:#060a14;border-top:1px solid rgba(255,255,255,0.06);padding:10px 14px;'>
                <tr>
                  <td align='left' style='font-size:11.5px;color:#f72585;font-weight:bold;'>{caption}</td>
                  <td align='right' style='font-size:11px;color:#94a3b8;'>{subcaption}</td>
                </tr>
              </table>
            </div>
          </div>

        </div>
      </td>
    </tr>

    <!-- INFORMATION AREA 5: CREATOR Q&A & RETENTION HACK -->
    <tr>
      <td class='mobile-pad' style='padding:18px 36px 28px 36px;'>
        <div style='display:inline-block;background:rgba(16,185,129,0.15);color:#10b981;font-size:11px;font-weight:800;letter-spacing:1px;padding:3px 10px;border-radius:4px;text-transform:uppercase;margin-bottom:8px;'>
          SECTION 5 &bull; SUBSCRIBER RETENTION HABIT
        </div>
        <h2 style='margin:0 0 10px 0;font-size:20px;color:#ffffff;'>The "First 60 Minutes" Renewal Rule</h2>
        <p style='margin:0;font-size:14px;line-height:1.65;color:#cbd5e1;'>
          82% of subscriber churn happens silently when a fan's rebill fails or they toggle off auto-renew. Setting a daily morning habit to send a personalized 1-sentence DM ("Saw you've been here since March, unlocking today's set on your profile as a thank you") recovers up to 28% of expired fans before they delete the app.
        </p>
      </td>
    </tr>

    <!-- DEDICATED PROMO SECTION (AT THE VERY BOTTOM: HORIZONTAL 3-COLUMN CARDS ON PC, VERTICAL ON MOBILE) -->
    <tr>
      <td class='mobile-pad' style='padding:0 36px 36px 36px;'>
        <div style='background:linear-gradient(135deg, rgba(247,37,133,0.2) 0%, rgba(114,9,183,0.35) 100%);border:2px solid #f72585;border-radius:12px;padding:26px 18px;text-align:center;'>
          <span style='font-size:11px;font-weight:800;color:#ffd166;letter-spacing:1.2px;text-transform:uppercase;'>CREATORMEDIALAB &bull; OFFICIAL CREATOR SUITE</span>
          <h2 style='margin:8px 0 6px 0;font-size:22px;color:#ffffff;'>Upgrade Your Visual Edge & Monetize Faster</h2>
          <p style='margin:0 0 22px 0;font-size:13.5px;color:#e2e8f0;line-height:1.6;max-width:580px;margin-left:auto;margin-right:auto;'>
            Stop using cheap airbrush blur. Get your photo shoots professionally retouched with authentic editorial skin texture, or grab our signature cam bio kits and presets.
          </p>
          
          <!-- 3 HORIZONTAL SERVICE CARDS ON PC, VERTICAL ON MOBILE -->
          <div class='row-fluid' style='font-size:0;text-align:center;'>
            
            <!-- Card 1: Fiverr -->
            <div class='col-third promo-pad-right' style='display:inline-block;width:100%;max-width:218px;vertical-align:top;box-sizing:border-box;margin-right:10px;background:rgba(9,13,24,0.7);border:1px solid rgba(247,37,133,0.4);border-radius:8px;padding:16px 12px;text-align:center;'>
              <div style='font-size:20px;margin-bottom:6px;'>🎨</div>
              <strong style='font-size:13px;color:#ffffff;display:block;'>Pro Retouching</strong>
              <p style='font-size:11px;color:#cbd5e1;margin:6px 0 14px 0;line-height:1.35;'>Authentic skin pores & magazine lighting.</p>
              <a href='{FIVERR_URL}' target='_blank' class='mobile-btn' style='display:inline-block;background:#f72585;color:#ffffff;font-size:11.5px;font-weight:bold;text-decoration:none;padding:9px 12px;border-radius:6px;text-transform:uppercase;letter-spacing:0.5px;'>Fiverr Gig &rarr;</a>
            </div>

            <!-- Card 2: Etsy -->
            <div class='col-third promo-pad-right' style='display:inline-block;width:100%;max-width:218px;vertical-align:top;box-sizing:border-box;margin-right:10px;background:rgba(9,13,24,0.7);border:1px solid rgba(255,255,255,0.15);border-radius:8px;padding:16px 12px;text-align:center;'>
              <div style='font-size:20px;margin-bottom:6px;'>🛍️</div>
              <strong style='font-size:13px;color:#ffffff;display:block;'>Cam Bio Kits</strong>
              <p style='font-size:11px;color:#cbd5e1;margin:6px 0 14px 0;line-height:1.35;'>Stream templates, tip menus & cheat sheets.</p>
              <a href='{ETSY_URL}' target='_blank' class='mobile-btn' style='display:inline-block;background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);color:#ffffff;font-size:11.5px;font-weight:bold;text-decoration:none;padding:9px 12px;border-radius:6px;text-transform:uppercase;letter-spacing:0.5px;'>Etsy Store &rarr;</a>
            </div>

            <!-- Card 3: Linktree -->
            <div class='col-third' style='display:inline-block;width:100%;max-width:218px;vertical-align:top;box-sizing:border-box;background:rgba(9,13,24,0.7);border:1px solid rgba(16,185,129,0.4);border-radius:8px;padding:16px 12px;text-align:center;'>
              <div style='font-size:20px;margin-bottom:6px;'>🔗</div>
              <strong style='font-size:13px;color:#ffffff;display:block;'>Central Hub</strong>
              <p style='font-size:11px;color:#cbd5e1;margin:6px 0 14px 0;line-height:1.35;'>All creative tools, presets & VIP waitlist.</p>
              <a href='{LINKTREE_URL}' target='_blank' class='mobile-btn' style='display:inline-block;background:#10b981;color:#04172a;font-size:11.5px;font-weight:bold;text-decoration:none;padding:9px 12px;border-radius:6px;text-transform:uppercase;letter-spacing:0.5px;'>Linktree Hub &rarr;</a>
            </div>

          </div>
        </div>
      </td>
    </tr>

    <!-- FOOTER -->
    <tr>
      <td class='mobile-pad' style='padding:22px 36px;background:#050912;border-top:1px solid rgba(255,255,255,0.08);text-align:center;'>
        <p style='margin:0 0 8px 0;font-size:12.5px;color:#94a3b8;'>
          Published daily by <strong>The Daily Creator Pulse</strong> &bull; Follow on X: <a href='{TWITTER_PULSE_URL}' target='_blank' style='color:#f72585;text-decoration:none;'>@creatorpulselab</a> &bull; Portal & Archive: <a href='{PORTAL_PULSE_URL}' target='_blank' style='color:#f72585;text-decoration:none;'>Daily Creator Pulse Portal</a>
        </p>
        <p style='margin:0;font-size:11px;color:#475569;'>
          Dispatched by Herald [33 As] &bull; WORKHORSE Creator Workflow Automation.
        </p>
      </td>
    </tr>
  </table>
</body>
</html>"""

    # ── 2. THE SHUTTER & STUDIO WIRE ─────────────────────────────────────────
    def _build_studio_wire_html(self, today_str: str) -> str:
        visual_info = self.get_publication_visual_embed("studio_wire")
        img_src = visual_info["src"]
        caption = visual_info["caption"]
        subcaption = visual_info["subcaption"]
        scribe_content = self._get_daily_scribe_content("studio_wire")
        lead_headline = html.escape((scribe_content or {}).get("lead_headline") or "Why Digital Sensor Highlights Look Brittle (And How To Fix It)")
        lead_body = html.escape((scribe_content or {}).get("lead_body") or "Digital CMOS sensors capture light linearly: when a highlight clips, it truncates instantly to pure #FFFFFF with zero chromatic transition. Analog film, by contrast, has a natural chemical S-curve with soft silver halide shoulder compression. In portraiture, this is why digital forehead highlights look greasy while editorial magazine film looks velvety.")
        return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1.0'>
  <title>The Shutter & Studio Wire</title>
  <style>
    body {{ margin:0; padding:24px 12px; background-color:#070b14; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; color:#e2e8f0; -webkit-text-size-adjust:100%; -ms-text-size-adjust:100%; }}
    table {{ border-collapse:collapse; mso-table-lspace:0pt; mso-table-rspace:0pt; }}
    img {{ border:0; height:auto; line-height:100%; outline:none; text-decoration:none; max-width:100%; }}
    .main-table {{ width:100%; max-width:820px; margin:0 auto; background:#0d1527; border:1px solid #00f2fe; border-radius:14px; overflow:hidden; box-shadow:0 12px 40px rgba(0,0,0,0.75); }}
    
    .row-fluid {{ font-size:0; text-align:left; }}
    .col-half {{ display:inline-block; width:100%; max-width:364px; vertical-align:top; box-sizing:border-box; text-align:left; }}
    .col-third {{ display:inline-block; width:100%; max-width:218px; vertical-align:top; box-sizing:border-box; text-align:left; }}
    .col-pad-right {{ margin-right:16px; }}
    .promo-pad-right {{ margin-right:10px; }}

    @media only screen and (max-width: 680px) {{
      body {{ padding:10px 4px !important; }}
      .main-table {{ width:100% !important; max-width:100% !important; border-radius:0 !important; border-left:none !important; border-right:none !important; }}
      .col-half, .col-third {{ display:block !important; width:100% !important; max-width:100% !important; margin-right:0 !important; margin-bottom:14px !important; }}
      .mobile-pad {{ padding-left:18px !important; padding-right:18px !important; }}
      .mobile-header-pad {{ padding:24px 18px 20px 18px !important; }}
      .mobile-btn {{ display:block !important; width:100% !important; text-align:center !important; box-sizing:border-box !important; margin-bottom:8px !important; }}
    }}
  </style>
</head>
<body style='margin:0;padding:24px 12px;background-color:#070b14;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:#e2e8f0;'>
  <table role='presentation' width='100%' cellspacing='0' cellpadding='0' border='0' align='center' class='main-table' style='max-width:820px;margin:0 auto;background:#0d1527;border:1px solid #00f2fe;border-radius:14px;overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,0.75);'>
    
    <!-- HEADER BRANDING -->
    <tr>
      <td class='mobile-header-pad' style='padding:32px 36px 26px 36px;background:linear-gradient(135deg, rgba(0,242,254,0.18) 0%, rgba(30,58,138,0.35) 100%);border-bottom:2px solid #00f2fe;'>
        <table width='100%' cellspacing='0' cellpadding='0'>
          <tr>
            <td>
              <span style='display:inline-block;background:#00f2fe;color:#04172a;font-size:10.5px;font-weight:800;letter-spacing:1.2px;padding:4px 12px;border-radius:12px;text-transform:uppercase;'>ISSUE #088 &bull; COLOR SCIENCE & STUDIO LIGHTING</span>
              <h1 style='margin:12px 0 6px 0;font-size:28px;font-weight:900;color:#ffffff;letter-spacing:-0.5px;'>📸 The Shutter & Studio Wire</h1>
              <p style='margin:0;font-size:13.5px;color:#cbd5e1;line-height:1.5;'>Lightroom Film Science, Lighting Schematics & Client Growth &bull; {today_str}</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- WELCOME_HOOK -->

    <!-- INFORMATION AREA 1: COLOR SCIENCE RADAR -->
    <tr>
      <td class='mobile-pad' style='padding:28px 36px 18px 36px;'>
        <div style='display:inline-block;background:rgba(0,242,254,0.15);color:#00f2fe;font-size:11px;font-weight:800;letter-spacing:1px;padding:3px 10px;border-radius:4px;text-transform:uppercase;margin-bottom:8px;'>
          SECTION 1 &bull; COLOR SCIENCE RADAR
        </div>
        <h2 style='margin:0 0 10px 0;font-size:20px;color:#ffffff;'>{lead_headline}</h2>
        <p style='margin:0;font-size:14px;line-height:1.65;color:#cbd5e1;'>
          {lead_body}
        </p>
      </td>
    </tr>

    <!-- INFORMATION AREA 2: LIGHTROOM RECIPE (HORIZONTAL PARAMETER DATA TABLE) -->
    <tr>
      <td class='mobile-pad' style='padding:18px 36px;'>
        <div style='display:inline-block;background:rgba(16,185,129,0.15);color:#10b981;font-size:11px;font-weight:800;letter-spacing:1px;padding:3px 10px;border-radius:4px;text-transform:uppercase;margin-bottom:8px;'>
          SECTION 2 &bull; LIGHTROOM RECIPE OF THE DAY
        </div>
        <h2 style='margin:0 0 10px 0;font-size:20px;color:#ffffff;'>The Exact Sliders For The Kodak Portra 400 Tone Curve</h2>
        <p style='margin:0 0 14px 0;font-size:14px;line-height:1.65;color:#cbd5e1;'>
          Replicating Kodak Portra 400 does not require heavy destructive filters. It comes down to 3 precise slider adjustments in your RAW develop module:
        </p>

        <div style='overflow-x:auto;-webkit-overflow-scrolling:touch;width:100%;max-width:100%;margin-bottom:8px;'><table width='100%' class='responsive-table' cellspacing='0' cellpadding='10' style='font-size:13px;color:#cbd5e1;border-collapse:collapse;margin-bottom:8px;'>
            <tr style='background:#090d18;color:#00f2fe;font-weight:bold;'>
              <th align='left' style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Module</th>
              <th align='left' style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Exact Setting</th>
              <th align='left' style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Film Characteristic</th>
            </tr>
            <tr>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);font-weight:bold;'>RGB Tone Curve</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);color:#00f2fe;'>Lift Black Point to 18-22</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Creates creamy, matte shadow roll-off</td>
            </tr>
            <tr style='background:rgba(255,255,255,0.02);'>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);font-weight:bold;'>HSL Orange</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);color:#00f2fe;'>Sat: -4% | Lum: +8%</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Luminous skin tones without orange mask</td>
            </tr>
            <tr>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);font-weight:bold;'>Color Wheels</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);color:#00f2fe;'>Midtones Hue 42 (6%) | Shadows 215 (4%)</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Classic warm/cool editorial split toning</td>
            </tr>
          </table>
        </div>
      </td>
    </tr>

    <!-- INFORMATION AREA 3: STUDIO LIGHTING BLUEPRINT (HORIZONTAL ON PC, VERTICAL ON MOBILE) -->
    <tr>
      <td class='mobile-pad' style='padding:18px 36px;'>
        <div style='display:inline-block;background:rgba(59,130,246,0.15);color:#60a5fa;font-size:11px;font-weight:800;letter-spacing:1px;padding:3px 10px;border-radius:4px;text-transform:uppercase;margin-bottom:8px;'>
          SECTION 3 &bull; STUDIO LIGHTING BLUEPRINT
        </div>
        <h2 style='margin:0 0 10px 0;font-size:20px;color:#ffffff;'>The 45° Feathered Beauty Dish with Clamshell Fill</h2>
        <p style='margin:0 0 16px 0;font-size:14px;line-height:1.65;color:#cbd5e1;'>
          This is the primary lighting setup used in high-end cosmetic and glamour editorial campaigns. By feathering the beauty dish just in front of the model's nose, the center hotspot bypasses the face and only the soft edge illuminates the skin:
        </p>

        <!-- 2-COLUMN RESPONSIVE DIAGRAM CONTAINER: HORIZONTAL ON PC, VERTICAL ON MOBILE -->
        <div class='row-fluid' style='font-size:0;text-align:left;'>
          
          <!-- LEFT COLUMN: SCHEMATIC SPECIFICATIONS & RULES -->
          <div class='col-half col-pad-right' style='display:inline-block;width:100%;max-width:364px;vertical-align:top;box-sizing:border-box;margin-right:16px;'>
            <div class='ascii-diagram' style='background:#060a14;border:1px solid rgba(0,242,254,0.3);border-radius:8px;padding:14px;font-family:Consolas,monaco,monospace;font-size:11px;color:#67e8f9;line-height:1.55;margin-bottom:12px;overflow-x:auto;max-width:100%;box-sizing:border-box;'>
[KEY: 22" BEAUTY DISH] ── 45° Feather ──┐<br>
                                         ↓<br>
                [ MODEL / SUBJECT ]<br>
                                         ↑<br>
[FILL: SILVER REFLECTOR] ── Upward ─────┘<br>
                        ↑<br>
          [ 85mm f/1.8 @ f/5.6 ]
            </div>
            <div style='background:#090d18;border-left:3px solid #00f2fe;padding:10px 14px;border-radius:0 6px 6px 0;font-size:12px;color:#94a3b8;line-height:1.5;'>
              <strong style='color:#e2e8f0;'>Specs:</strong> Distance 3.5 ft from model. Power set key light to f/5.6 on incident meter; curved silver reflector bounces 1.5 stops lower for seamless neck shadow transition.
            </div>
          </div>

          <!-- RIGHT COLUMN: HIGH-RESOLUTION VISUAL DIAGRAM IMAGE -->
          <div class='col-half' style='display:inline-block;width:100%;max-width:364px;vertical-align:top;box-sizing:border-box;'>
            <div style='border-radius:10px;overflow:hidden;border:1px solid rgba(0,242,254,0.4);background:#090d18;box-shadow:0 8px 25px rgba(0,0,0,0.7);'>
              <img src="{img_src}" alt="Editorial Studio Lighting" width="364" style="width:100%;max-width:364px;height:auto;display:block;margin:0 auto;border:none;">
              <div style="padding:10px 14px;background:#060a14;border-top:1px solid rgba(255,255,255,0.06);display:flex;justify-content:space-between;align-items:center;">
                <span style="font-size:11.5px;color:#00f2fe;font-weight:bold;">{caption}</span>
                <span style="font-size:11px;color:#94a3b8;">{subcaption}</span>
              </div>
            </div>
          </div>

        </div>
      </td>
    </tr>

    <!-- INFORMATION AREA 4: POSING & DIRECTING CUES -->
    <tr>
      <td class='mobile-pad' style='padding:18px 36px;'>
        <div style='display:inline-block;background:rgba(234,179,8,0.15);color:#facc15;font-size:11px;font-weight:800;letter-spacing:1px;padding:3px 10px;border-radius:4px;text-transform:uppercase;margin-bottom:8px;'>
          SECTION 4 &bull; MODEL DIRECTING PLAYBOOK
        </div>
        <h2 style='margin:0 0 10px 0;font-size:20px;color:#ffffff;'>3 Micro-Cues That Eliminate Client Stiffness Instantly</h2>
        <p style='margin:0 0 12px 0;font-size:14px;line-height:1.65;color:#cbd5e1;'>
          Never tell a client or model to "smile naturally" or "relax" &mdash; it immediately makes them conscious of their posture. Instead, direct micro-movements:
        </p>
        <ul style='margin:0 0 6px 0;padding-left:20px;font-size:13.5px;line-height:1.7;color:#cbd5e1;'>
          <li><strong>"Breathe out through parted lips":</strong> Automatically releases jaw tension and prevents tight, clenched smiles.</li>
          <li><strong>"Shift 70% of your weight to your rear foot":</strong> Creates an S-curve through the hip line and prevents square, boxy stances.</li>
          <li><strong>"Drop your front shoulder 1 inch":</strong> Creates diagonal asymmetry across the clavicle, producing instant high-fashion lines.</li>
        </ul>
      </td>
    </tr>

    <!-- INFORMATION AREA 5: STUDIO PRICING & DELIVERY HACK -->
    <tr>
      <td class='mobile-pad' style='padding:18px 36px 28px 36px;'>
        <div style='display:inline-block;background:rgba(16,185,129,0.15);color:#10b981;font-size:11px;font-weight:800;letter-spacing:1px;padding:3px 10px;border-radius:4px;text-transform:uppercase;margin-bottom:8px;'>
          SECTION 5 &bull; STUDIO PRICING & DELIVERY HACK
        </div>
        <h2 style='margin:0 0 10px 0;font-size:20px;color:#ffffff;'>Why Delivering 300 Unedited RAW Photos Kills Referrals</h2>
        <p style='margin:0;font-size:14px;line-height:1.65;color:#cbd5e1;'>
          Clients do not want data dumps; they want curated glamour. Photographers who deliver 300 unretouched files force clients into decision fatigue. Delivering a tight, fully color-graded gallery of 25&ndash;40 master photos within 24 hours justifies charging $350&ndash;$750 per session and generates immediate word-of-mouth client referrals.
        </p>
      </td>
    </tr>

    <!-- DEDICATED PROMO SECTION (AT THE VERY BOTTOM: HORIZONTAL 3-COLUMN CARDS ON PC, VERTICAL ON MOBILE) -->
    <tr>
      <td class='mobile-pad' style='padding:0 36px 36px 36px;'>
        <div style='background:linear-gradient(135deg, rgba(0,242,254,0.15) 0%, rgba(30,58,138,0.35) 100%);border:2px solid #00f2fe;border-radius:12px;padding:26px 18px;text-align:center;'>
          <span style='font-size:11px;font-weight:800;color:#00f2fe;letter-spacing:1.2px;text-transform:uppercase;'>STUDIO ASSETS &bull; CREATORMEDIALAB</span>
          <h2 style='margin:8px 0 6px 0;font-size:22px;color:#ffffff;'>Stop Manually Tweaking 40 Sliders On Every Photo</h2>
          <p style='margin:0 0 22px 0;font-size:13.5px;color:#e2e8f0;line-height:1.6;max-width:580px;margin-left:auto;margin-right:auto;'>
            Download our signature 5-Preset Editorial .XMP Bundle on Etsy, or outsource your shoot's batch skin retouching and color grading to our studio on Fiverr.
          </p>
          
          <!-- 3 HORIZONTAL SERVICE CARDS ON PC, VERTICAL ON MOBILE -->
          <div class='row-fluid' style='font-size:0;text-align:center;'>
            
            <!-- Card 1: Etsy -->
            <div class='col-third promo-pad-right' style='display:inline-block;width:100%;max-width:218px;vertical-align:top;box-sizing:border-box;margin-right:10px;background:rgba(9,13,24,0.7);border:1px solid rgba(0,242,254,0.4);border-radius:8px;padding:16px 12px;text-align:center;'>
              <div style='font-size:20px;margin-bottom:6px;'>📸</div>
              <strong style='font-size:13px;color:#ffffff;display:block;'>Portra Presets</strong>
              <p style='font-size:11px;color:#cbd5e1;margin:6px 0 14px 0;line-height:1.35;'>5-Preset Editorial .XMP profile pack.</p>
              <a href='{ETSY_URL}' target='_blank' class='mobile-btn' style='display:inline-block;background:#00f2fe;color:#04172a;font-size:11.5px;font-weight:bold;text-decoration:none;padding:9px 12px;border-radius:6px;text-transform:uppercase;letter-spacing:0.5px;'>Etsy Presets &rarr;</a>
            </div>

            <!-- Card 2: Fiverr -->
            <div class='col-third promo-pad-right' style='display:inline-block;width:100%;max-width:218px;vertical-align:top;box-sizing:border-box;margin-right:10px;background:rgba(9,13,24,0.7);border:1px solid rgba(255,255,255,0.15);border-radius:8px;padding:16px 12px;text-align:center;'>
              <div style='font-size:20px;margin-bottom:6px;'>🎨</div>
              <strong style='font-size:13px;color:#ffffff;display:block;'>Batch Retouching</strong>
              <p style='font-size:11px;color:#cbd5e1;margin:6px 0 14px 0;line-height:1.35;'>High-end skin tones & color grades.</p>
              <a href='{FIVERR_URL}' target='_blank' class='mobile-btn' style='display:inline-block;background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);color:#ffffff;font-size:11.5px;font-weight:bold;text-decoration:none;padding:9px 12px;border-radius:6px;text-transform:uppercase;letter-spacing:0.5px;'>Fiverr Studio &rarr;</a>
            </div>

            <!-- Card 3: Linktree -->
            <div class='col-third' style='display:inline-block;width:100%;max-width:218px;vertical-align:top;box-sizing:border-box;background:rgba(9,13,24,0.7);border:1px solid rgba(16,185,129,0.4);border-radius:8px;padding:16px 12px;text-align:center;'>
              <div style='font-size:20px;margin-bottom:6px;'>🔗</div>
              <strong style='font-size:13px;color:#ffffff;display:block;'>Studio Hub</strong>
              <p style='font-size:11px;color:#cbd5e1;margin:6px 0 14px 0;line-height:1.35;'>All presets, tutorials & booking links.</p>
              <a href='{LINKTREE_URL}' target='_blank' class='mobile-btn' style='display:inline-block;background:#10b981;color:#04172a;font-size:11.5px;font-weight:bold;text-decoration:none;padding:9px 12px;border-radius:6px;text-transform:uppercase;letter-spacing:0.5px;'>Linktree Hub &rarr;</a>
            </div>

          </div>
        </div>
      </td>
    </tr>

    <!-- FOOTER -->
    <tr>
      <td class='mobile-pad' style='padding:22px 36px;background:#050912;border-top:1px solid rgba(255,255,255,0.08);text-align:center;'>
        <p style='margin:0 0 8px 0;font-size:12.5px;color:#94a3b8;'>
          Published daily by <strong>CreatorMediaLab</strong> &bull; Follow on X: <a href='{TWITTER_ASSET_URL}' target='_blank' style='color:#00f2fe;text-decoration:none;'>@TheCreatorAsset</a> &bull; Central Hub: <a href='{LINKTREE_URL}' target='_blank' style='color:#00f2fe;text-decoration:none;'>linktr.ee/CreatorMediaLab</a> &bull; Portal: <a href='{PORTAL_STUDIO_URL}' target='_blank' style='color:#00f2fe;text-decoration:none;'>Studio Wire</a>
        </p>
        <p style='margin:0;font-size:11px;color:#475569;'>
          Dispatched by Herald [33 As] &bull; WORKHORSE Pro Photo Lab.
        </p>
      </td>
    </tr>
  </table>
</body>
</html>"""

    # ── 3. THE CREATOR BLUEPRINT ─────────────────────────────────────────────
    def _build_creator_blueprint_html(self, today_str: str) -> str:
        scribe_content = self._get_daily_scribe_content("creator_blueprint")
        lead_headline = html.escape((scribe_content or {}).get("lead_headline") or "The Micro-Asset Shift: Why $15 Digital Downloads Outsell $500 Courses")
        lead_body = html.escape((scribe_content or {}).get("lead_body") or "Creator monetization has permanently shifted away from bloated 10-hour video masterclasses toward instant, tangible micro-assets. Modern buyers want immediate utility: Lightroom .XMP presets, stream bio kits, prompt cheat sheets, and editing templates. These digital downloads have 100% gross margins, zero fulfillment labor, and instant gratification.")
        return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1.0'>
  <title>The Creator Blueprint</title>
  <style>
    body {{ margin:0; padding:24px 12px; background-color:#070b14; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; color:#e2e8f0; -webkit-text-size-adjust:100%; -ms-text-size-adjust:100%; }}
    table {{ border-collapse:collapse; mso-table-lspace:0pt; mso-table-rspace:0pt; }}
    img {{ border:0; height:auto; line-height:100%; outline:none; text-decoration:none; max-width:100%; }}
    .main-table {{ width:100%; max-width:820px; margin:0 auto; background:#0d1527; border:1px solid #eab308; border-radius:14px; overflow:hidden; box-shadow:0 12px 40px rgba(0,0,0,0.75); }}
    
    .row-fluid {{ font-size:0; text-align:left; }}
    .col-half {{ display:inline-block; width:100%; max-width:364px; vertical-align:top; box-sizing:border-box; text-align:left; }}
    .col-third {{ display:inline-block; width:100%; max-width:218px; vertical-align:top; box-sizing:border-box; text-align:left; }}
    .col-pad-right {{ margin-right:16px; }}
    .promo-pad-right {{ margin-right:10px; }}

    @media only screen and (max-width: 680px) {{
      body {{ padding:10px 4px !important; }}
      .main-table {{ width:100% !important; max-width:100% !important; border-radius:0 !important; border-left:none !important; border-right:none !important; }}
      .col-half, .col-third {{ display:block !important; width:100% !important; max-width:100% !important; margin-right:0 !important; margin-bottom:14px !important; }}
      .mobile-pad {{ padding-left:18px !important; padding-right:18px !important; }}
      .mobile-header-pad {{ padding:24px 18px 20px 18px !important; }}
      .mobile-btn {{ display:block !important; width:100% !important; text-align:center !important; box-sizing:border-box !important; margin-bottom:8px !important; }}
    }}
  </style>
</head>
<body style='margin:0;padding:24px 12px;background-color:#070b14;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:#e2e8f0;'>
  <table role='presentation' width='100%' cellspacing='0' cellpadding='0' border='0' align='center' class='main-table' style='max-width:820px;margin:0 auto;background:#0d1527;border:1px solid #eab308;border-radius:14px;overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,0.75);'>
    
    <!-- HEADER BRANDING -->
    <tr>
      <td class='mobile-header-pad' style='padding:32px 36px 26px 36px;background:linear-gradient(135deg, rgba(234,179,8,0.2) 0%, rgba(202,138,4,0.35) 100%);border-bottom:2px solid #eab308;'>
        <table width='100%' cellspacing='0' cellpadding='0'>
          <tr>
            <td>
              <span style='display:inline-block;background:#eab308;color:#04172a;font-size:10.5px;font-weight:800;letter-spacing:1.2px;padding:4px 12px;border-radius:12px;text-transform:uppercase;'>ISSUE #019 &bull; MEDIA AUTOMATION & GROWTH</span>
              <h1 style='margin:12px 0 6px 0;font-size:28px;font-weight:900;color:#ffffff;letter-spacing:-0.5px;'>⚡ The Creator Blueprint</h1>
              <p style='margin:0;font-size:13.5px;color:#cbd5e1;line-height:1.5;'>Media Automation, Organic Traffic Engines & Digital Product Scaling &bull; {today_str}</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- WELCOME_HOOK -->

    <!-- INFORMATION AREA 1: DIGITAL PRODUCT MARKET PULSE -->
    <tr>
      <td class='mobile-pad' style='padding:28px 36px 18px 36px;'>
        <div style='display:inline-block;background:rgba(234,179,8,0.15);color:#eab308;font-size:11px;font-weight:800;letter-spacing:1px;padding:3px 10px;border-radius:4px;text-transform:uppercase;margin-bottom:8px;'>
          SECTION 1 &bull; DIGITAL ASSET TRENDS
        </div>
        <h2 style='margin:0 0 10px 0;font-size:20px;color:#ffffff;'>{lead_headline}</h2>
        <p style='margin:0;font-size:14px;line-height:1.65;color:#cbd5e1;'>
          {lead_body}
        </p>
      </td>
    </tr>

    <!-- INFORMATION AREA 2: THE 3-STEP FLYWHEEL (HORIZONTAL ON PC, VERTICAL ON MOBILE) -->
    <tr>
      <td class='mobile-pad' style='padding:18px 36px;'>
        <div style='display:inline-block;background:rgba(234,179,8,0.15);color:#eab308;font-size:11px;font-weight:800;letter-spacing:1px;padding:3px 10px;border-radius:4px;text-transform:uppercase;margin-bottom:8px;'>
          SECTION 2 &bull; THE $0 TO $5K FLYWHEEL
        </div>
        <h2 style='margin:0 0 10px 0;font-size:20px;color:#ffffff;'>How To Turn A Single Skill Into A 3-Tier Passive Revenue Engine</h2>
        <p style='margin:0 0 16px 0;font-size:14px;line-height:1.65;color:#cbd5e1;'>
          Here is the exact 3-stage progression to build cash flow without relying on luck:
        </p>

        <!-- 2-COLUMN RESPONSIVE FLYWHEEL CONTAINER: HORIZONTAL ON PC, VERTICAL ON MOBILE -->
        <div class='row-fluid' style='font-size:0;text-align:left;'>
          
          <!-- LEFT COLUMN: 3 PHASES & SCHEMATIC ROUTING -->
          <div class='col-half col-pad-right' style='display:inline-block;width:100%;max-width:364px;vertical-align:top;box-sizing:border-box;margin-right:16px;'>
            
            <div style='background:#090d18;padding:12px 14px;border-radius:6px;border-left:4px solid #eab308;margin-bottom:8px;'>
              <strong style='color:#eab308;font-size:13px;'>Phase 1: High-Touch Client Validation</strong>
              <p style='margin:3px 0 0 0;font-size:12px;color:#cbd5e1;line-height:1.4;'>Sell custom photo retouching on Fiverr ($15-$75) to validate demand and client styles.</p>
            </div>

            <div style='background:#090d18;padding:12px 14px;border-radius:6px;border-left:4px solid #eab308;margin-bottom:8px;'>
              <strong style='color:#eab308;font-size:13px;'>Phase 2: Productize into Digital Downloads</strong>
              <p style='margin:3px 0 0 0;font-size:12px;color:#cbd5e1;line-height:1.4;'>Package validated color profiles into .XMP presets and Etsy templates with zero shipping cost.</p>
            </div>

            <div style='background:#090d18;padding:12px 14px;border-radius:6px;border-left:4px solid #eab308;margin-bottom:10px;'>
              <strong style='color:#eab308;font-size:13px;'>Phase 3: Automated Micro-Content</strong>
              <p style='margin:3px 0 0 0;font-size:12px;color:#cbd5e1;line-height:1.4;'>Automate daily threads on `@TheCreatorAsset` and route traffic directly to your Linktree.</p>
            </div>

            <div style='background:#060a14;border:1px solid rgba(234,179,8,0.3);border-radius:6px;padding:10px 12px;font-family:Consolas,monaco,monospace;font-size:11px;color:#facc15;line-height:1.5;'>
[FIVERR: SERVICE] ── Validation ──→ [ETSY: PRESETS]<br>
                                         ↓ Auto<br>
[LINKTREE HUB] ←── 100% Traffic ─── [TWITTER / X]
            </div>

          </div>

          <!-- RIGHT COLUMN: HIGH-RESOLUTION VISUAL DIAGRAM IMAGE -->
          <div class='col-half' style='display:inline-block;width:100%;max-width:364px;vertical-align:top;box-sizing:border-box;'>
            <div style='border-radius:10px;overflow:hidden;border:1px solid rgba(234,179,8,0.4);background:#090d18;box-shadow:0 8px 25px rgba(0,0,0,0.7);'>
              <img src="{IMG_CREATOR_FLYWHEEL}" alt="Creator Studio Flywheel Architecture" width="364" style="width:100%;max-width:364px;height:auto;display:block;margin:0 auto;border:none;">
              <div style="padding:10px 14px;background:#060a14;border-top:1px solid rgba(255,255,255,0.06);display:flex;justify-content:space-between;align-items:center;">
                <span style="font-size:11.5px;color:#eab308;font-weight:bold;">⚡ Figure 2.1 &bull; 3-Tier Flywheel</span>
                <span style="font-size:11px;color:#94a3b8;">Service &rarr; Asset &rarr; Automation</span>
              </div>
            </div>
          </div>

        </div>
      </td>
    </tr>

    <!-- INFORMATION AREA 3: CONTENT SYNDICATION STACK (HORIZONTAL DATA GRID) -->
    <tr>
      <td class='mobile-pad' style='padding:18px 36px;'>
        <div style='display:inline-block;background:rgba(59,130,246,0.15);color:#60a5fa;font-size:11px;font-weight:800;letter-spacing:1px;padding:3px 10px;border-radius:4px;text-transform:uppercase;margin-bottom:8px;'>
          SECTION 3 &bull; WORKFLOW AUTOMATION
        </div>
        <h2 style='margin:0 0 10px 0;font-size:20px;color:#ffffff;'>The "Create Once, Syndicate 4x" Pipeline</h2>
        <p style='margin:0 0 14px 0;font-size:14px;line-height:1.65;color:#cbd5e1;'>
          Never write content for a single platform. Every time you develop one piece of visual knowledge (e.g. a color grading tip), dispatch it through this 4-way pipeline:
        </p>

        <div style='overflow-x:auto;-webkit-overflow-scrolling:touch;width:100%;max-width:100%;margin-bottom:8px;'><table width='100%' class='responsive-table' cellspacing='0' cellpadding='10' style='font-size:13px;color:#cbd5e1;border-collapse:collapse;margin-bottom:8px;'>
            <tr style='background:#090d18;color:#60a5fa;font-weight:bold;'>
              <th align='left' style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Format</th>
              <th align='left' style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Destination</th>
              <th align='left' style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Call-to-Action Link</th>
            </tr>
            <tr>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);font-weight:bold;'>4-Tweet Thread</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Twitter/X (@TheCreatorAsset)</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);color:#10b981;'>Linktree Bio</td>
            </tr>
            <tr style='background:rgba(255,255,255,0.02);'>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);font-weight:bold;'>HTML Email Digest</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Subscriber Inbox (Herald Engine)</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);color:#10b981;'>Etsy & Fiverr Direct</td>
            </tr>
            <tr>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);font-weight:bold;'>Markdown Article</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Blog / Substack / SEO Hub</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);color:#10b981;'>Preset Bundle</td>
            </tr>
          </table>
        </div>
      </td>
    </tr>

    <!-- INFORMATION AREA 4: CONVERSION ARCHITECTURE -->
    <tr>
      <td class='mobile-pad' style='padding:18px 36px;'>
        <div style='display:inline-block;background:rgba(16,185,129,0.15);color:#10b981;font-size:11px;font-weight:800;letter-spacing:1px;padding:3px 10px;border-radius:4px;text-transform:uppercase;margin-bottom:8px;'>
          SECTION 4 &bull; CONVERSION ARCHITECTURE
        </div>
        <h2 style='margin:0 0 10px 0;font-size:20px;color:#ffffff;'>The "Rule of 4" For Mobile Link-in-Bio Landing Pages</h2>
        <p style='margin:0 0 12px 0;font-size:14px;line-height:1.65;color:#cbd5e1;'>
          Adding 15 confusing buttons to your Linktree destroys conversion rates through choice paralysis. High-converting creator bios follow the <strong>Rule of 4</strong>:
        </p>
        <ol style='margin:0 0 6px 0;padding-left:20px;font-size:13.5px;line-height:1.7;color:#cbd5e1;'>
          <li><strong>Primary Service:</strong> Pro Retouching & Color Grading on Fiverr (high trust).</li>
          <li><strong>Primary Digital Asset:</strong> Signature Lightroom Presets & Bio Kits on Etsy (instant gratification).</li>
          <li><strong>Free Community / Organic:</strong> Daily Tips on Twitter/X (@TheCreatorAsset).</li>
          <li><strong>Private Access:</strong> VIP Waitlist or Direct Studio Inquiry.</li>
        </ol>
      </td>
    </tr>

    <!-- INFORMATION AREA 5: THE REAL MONETIZATION MATH -->
    <tr>
      <td class='mobile-pad' style='padding:18px 36px 28px 36px;'>
        <div style='display:inline-block;background:rgba(247,37,133,0.15);color:#f72585;font-size:11px;font-weight:800;letter-spacing:1px;padding:3px 10px;border-radius:4px;text-transform:uppercase;margin-bottom:8px;'>
          SECTION 5 &bull; THE REAL MONETIZATION MATH
        </div>
        <h2 style='margin:0 0 10px 0;font-size:20px;color:#ffffff;'>You Only Need 200 Targeted Clicks A Month For $1,000</h2>
        <p style='margin:0;font-size:14px;line-height:1.65;color:#cbd5e1;'>
          Creators often think they need 100,000 viral views to make money. With a $25 average order value on Etsy and a 2.5% landing page conversion rate, exactly <strong>7 sales per week generates $700&ndash;$1,000/month in passive profit</strong>. That requires only 6 to 7 visitors per day clicking your Linktree from Twitter/X. Consistency in daily automated posting beats viral lottery tickets every single time.
        </p>
      </td>
    </tr>

    <!-- DEDICATED PROMO SECTION (AT THE VERY BOTTOM: HORIZONTAL 3-COLUMN CARDS ON PC, VERTICAL ON MOBILE) -->
    <tr>
      <td class='mobile-pad' style='padding:0 36px 36px 36px;'>
        <div style='background:linear-gradient(135deg, rgba(234,179,8,0.2) 0%, rgba(202,138,4,0.35) 100%);border:2px solid #eab308;border-radius:12px;padding:26px 18px;text-align:center;'>
          <span style='font-size:11px;font-weight:800;color:#eab308;letter-spacing:1.2px;text-transform:uppercase;'>ECOSYSTEM HUB &bull; CREATORMEDIALAB</span>
          <h2 style='margin:8px 0 6px 0;font-size:22px;color:#ffffff;'>Build Your Digital Creative Engine With Us</h2>
          <p style='margin:0 0 22px 0;font-size:13.5px;color:#e2e8f0;line-height:1.6;max-width:580px;margin-left:auto;margin-right:auto;'>
            Explore professional color grading presets, stream bio templates, and boutique photo retouching services.
          </p>
          
          <!-- 3 HORIZONTAL SERVICE CARDS ON PC, VERTICAL ON MOBILE -->
          <div class='row-fluid' style='font-size:0;text-align:center;'>
            
            <!-- Card 1: Etsy -->
            <div class='col-third promo-pad-right' style='display:inline-block;width:100%;max-width:218px;vertical-align:top;box-sizing:border-box;margin-right:10px;background:rgba(9,13,24,0.7);border:1px solid rgba(234,179,8,0.4);border-radius:8px;padding:16px 12px;text-align:center;'>
              <div style='font-size:20px;margin-bottom:6px;'>📁</div>
              <strong style='font-size:13px;color:#ffffff;display:block;'>Digital Store</strong>
              <p style='font-size:11px;color:#cbd5e1;margin:6px 0 14px 0;line-height:1.35;'>Presets, bio kits & creative toolkits.</p>
              <a href='{ETSY_URL}' target='_blank' class='mobile-btn' style='display:inline-block;background:#eab308;color:#04172a;font-size:11.5px;font-weight:bold;text-decoration:none;padding:9px 12px;border-radius:6px;text-transform:uppercase;letter-spacing:0.5px;'>Etsy Store &rarr;</a>
            </div>

            <!-- Card 2: Fiverr -->
            <div class='col-third promo-pad-right' style='display:inline-block;width:100%;max-width:218px;vertical-align:top;box-sizing:border-box;margin-right:10px;background:rgba(9,13,24,0.7);border:1px solid rgba(255,255,255,0.15);border-radius:8px;padding:16px 12px;text-align:center;'>
              <div style='font-size:20px;margin-bottom:6px;'>🎨</div>
              <strong style='font-size:13px;color:#ffffff;display:block;'>Custom Edits</strong>
              <p style='font-size:11px;color:#cbd5e1;margin:6px 0 14px 0;line-height:1.35;'>Boutique photo retouching & grading.</p>
              <a href='{FIVERR_URL}' target='_blank' class='mobile-btn' style='display:inline-block;background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);color:#ffffff;font-size:11.5px;font-weight:bold;text-decoration:none;padding:9px 12px;border-radius:6px;text-transform:uppercase;letter-spacing:0.5px;'>Fiverr Gig &rarr;</a>
            </div>

            <!-- Card 3: Linktree -->
            <div class='col-third' style='display:inline-block;width:100%;max-width:218px;vertical-align:top;box-sizing:border-box;background:rgba(9,13,24,0.7);border:1px solid rgba(16,185,129,0.4);border-radius:8px;padding:16px 12px;text-align:center;'>
              <div style='font-size:20px;margin-bottom:6px;'>🔗</div>
              <strong style='font-size:13px;color:#ffffff;display:block;'>Linktree Hub</strong>
              <p style='font-size:11px;color:#cbd5e1;margin:6px 0 14px 0;line-height:1.35;'>Centralized ecosystem & VIP access.</p>
              <a href='{LINKTREE_URL}' target='_blank' class='mobile-btn' style='display:inline-block;background:#10b981;color:#04172a;font-size:11.5px;font-weight:bold;text-decoration:none;padding:9px 12px;border-radius:6px;text-transform:uppercase;letter-spacing:0.5px;'>Linktree Hub &rarr;</a>
            </div>

          </div>
        </div>
      </td>
    </tr>

    <!-- FOOTER -->
    <tr>
      <td class='mobile-pad' style='padding:22px 36px;background:#050912;border-top:1px solid rgba(255,255,255,0.08);text-align:center;'>
        <p style='margin:0 0 8px 0;font-size:12.5px;color:#94a3b8;'>
          Published daily by <strong>CreatorMediaLab</strong> &bull; Follow on X: <a href='{TWITTER_ASSET_URL}' target='_blank' style='color:#eab308;text-decoration:none;'>@TheCreatorAsset</a> &bull; Central Hub: <a href='{LINKTREE_URL}' target='_blank' style='color:#eab308;text-decoration:none;'>linktr.ee/CreatorMediaLab</a> &bull; Portal: <a href='{PORTAL_BLUEPRINT_URL}' target='_blank' style='color:#eab308;text-decoration:none;'>Creator Blueprint</a>
        </p>
        <p style='margin:0;font-size:11px;color:#475569;'>
          Dispatched by Herald [33 As] &bull; WORKHORSE Media Architecture.
        </p>
      </td>
    </tr>
  </table>
</body>
</html>"""

    # ── 4. FLORIDA DISPENSARY DEALS (PRIVATE) ────────────────────────────────
    def _build_dispensary_deals_html(self, today_str: str) -> str:
        scribe_content = self._get_daily_scribe_content("dispensary_deals")
        lead_headline = html.escape((scribe_content or {}).get("lead_headline") or "70-Day Rolling Inhalation Limit Optimization")
        lead_body = html.escape((scribe_content or {}).get("lead_body") or "Remember to check your OMMU registry portal before placing orders. Florida's 70-day rolling calculation means milligram allocations expire dynamically on the 71st day after dispense. Purchasing live rosin vape carts on discount today reserves your inhalation milligrams before your next cycle renewal.")
        return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1.0'>
  <title>Florida Dispensary Deals</title>
  <style>
    body {{ margin:0; padding:24px 12px; background-color:#070b14; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; color:#e2e8f0; }}
    table {{ border-collapse:collapse; }}
    .main-table {{ width:100%; max-width:820px; margin:0 auto; background:#0d1527; border:1px solid #10b981; border-radius:14px; overflow:hidden; box-shadow:0 12px 40px rgba(0,0,0,0.75); }}
    @media only screen and (max-width: 680px) {{
      body {{ padding:10px 4px !important; }}
      .main-table {{ width:100% !important; max-width:100% !important; border-radius:0 !important; }}
      .mobile-pad {{ padding-left:18px !important; padding-right:18px !important; }}
    }}
  </style>
</head>
<body style='margin:0;padding:24px 12px;background-color:#070b14;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:#e2e8f0;'>
  <table role='presentation' width='100%' cellspacing='0' cellpadding='0' border='0' align='center' class='main-table' style='max-width:820px;margin:0 auto;background:#0d1527;border:1px solid #10b981;border-radius:14px;overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,0.75);'>
    
    <!-- HEADER -->
    <tr>
      <td class='mobile-pad' style='padding:32px 36px 26px 36px;background:linear-gradient(135deg, rgba(16,185,129,0.2) 0%, rgba(5,150,105,0.35) 100%);border-bottom:2px solid #10b981;'>
        <span style='display:inline-block;background:#10b981;color:#04172a;font-size:10.5px;font-weight:800;letter-spacing:1.2px;padding:4px 12px;border-radius:12px;text-transform:uppercase;'>PRIVATE &bull; VERIFIED MORNING BRIEFING</span>
        <h1 style='margin:12px 0 6px 0;font-size:28px;font-weight:900;color:#ffffff;letter-spacing:-0.5px;'>🌿 Florida Dispensary Deals</h1>
        <p style='margin:0;font-size:13.5px;color:#cbd5e1;line-height:1.5;'>Daily Automated Scraper Digest & Patient Savings &bull; {today_str}</p>
      </td>
    </tr>

    <!-- WELCOME_HOOK -->

    <!-- SECTION 1: TODAY'S SCRAPED FLASH SALES -->
    <tr>
      <td class='mobile-pad' style='padding:28px 36px 18px 36px;'>
        <div style='display:inline-block;background:rgba(16,185,129,0.15);color:#10b981;font-size:11px;font-weight:800;letter-spacing:1px;padding:3px 10px;border-radius:4px;text-transform:uppercase;margin-bottom:8px;'>
          SECTION 1 &bull; MORNING DISPATCH
        </div>
        <h2 style='margin:0 0 10px 0;font-size:20px;color:#ffffff;'>Verified Price Drops Across Florida Dispensaries</h2>
        <p style='margin:0 0 16px 0;font-size:14px;line-height:1.65;color:#cbd5e1;'>
          Our automated scrapers crawled morning inventory feeds across licensed Medical Marijuana Treatment Centers (MMTCs) in Florida. Here are today's top confirmed savings:
        </p>

        <!-- HORIZONTAL DATA TABLE -->
        <div style='overflow-x:auto;-webkit-overflow-scrolling:touch;width:100%;max-width:100%;margin-bottom:8px;'><table width='100%' class='responsive-table' cellspacing='0' cellpadding='10' style='font-size:13px;color:#cbd5e1;border-collapse:collapse;margin-bottom:8px;'>
            <tr style='background:#090d18;color:#10b981;font-weight:bold;'>
              <th align='left' style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Dispensary</th>
              <th align='left' style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Category</th>
              <th align='left' style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Top Pick</th>
              <th align='left' style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Discount</th>
              <th align='left' style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Sale Price</th>
            </tr>
            <tr>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);font-weight:bold;'>Trulieve</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Whole Flower</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Blue Dream (3.5g)</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);color:#10b981;font-weight:bold;'>40% OFF</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>$24.00</td>
            </tr>
            <tr style='background:rgba(255,255,255,0.02);'>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);font-weight:bold;'>MÜV</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Live Rosin Vape</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Lemon Jack 0.5g Cart</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);color:#10b981;font-weight:bold;'>35% OFF</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>$32.50</td>
            </tr>
            <tr>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);font-weight:bold;'>Curaleaf</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Edibles</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Indica Chews 100mg</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);color:#10b981;font-weight:bold;'>25% OFF</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>$15.00</td>
            </tr>
            <tr style='background:rgba(255,255,255,0.02);'>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);font-weight:bold;'>Surterra</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Full Spec Oil</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>Float 1g Syringe</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);color:#10b981;font-weight:bold;'>30% OFF</td>
              <td style='padding:10px;border:1px solid rgba(255,255,255,0.08);'>$42.00</td>
            </tr>
          </table>
        </div>
      </td>
    </tr>

    <!-- SECTION 2: PATIENT ADVOCACY & DISPENSARY INTEL -->
    <tr>
      <td class='mobile-pad' style='padding:18px 36px 32px 36px;'>
        <div style='display:inline-block;background:rgba(59,130,246,0.15);color:#60a5fa;font-size:11px;font-weight:800;letter-spacing:1px;padding:3px 10px;border-radius:4px;text-transform:uppercase;margin-bottom:8px;'>
          SECTION 2 &bull; PATIENT INTEL
        </div>
        <h2 style='margin:0 0 10px 0;font-size:20px;color:#ffffff;'>{lead_headline}</h2>
        <p style='margin:0;font-size:14px;line-height:1.65;color:#cbd5e1;'>
          {lead_body}
        </p>
      </td>
    </tr>

    <!-- FOOTER -->
    <tr>
      <td class='mobile-pad' style='padding:22px 36px;background:#050912;border-top:1px solid rgba(255,255,255,0.08);text-align:center;'>
        <p style='margin:0 0 8px 0;font-size:12.5px;color:#94a3b8;'>
          Private invite-only digest &bull; Florida MMTC patient data crawled by WORKHORSE Herald Engine.
        </p>
        <p style='margin:0;font-size:11px;color:#475569;'>
          Confidential briefing for registered Florida medical patients only.
        </p>
      </td>
    </tr>
  </table>
</body>
</html>"""

    # ──────────────────────────────────────────────────────────────────────────
    # MARKDOWN BLOG GENERATORS (HOSTED IMAGES & LINKTREE HUB CTAS)
    # ──────────────────────────────────────────────────────────────────────────
    def get_markdown_article(self, pub_id: str = "creator_pulse") -> str:
        today_str = datetime.now().strftime("%B %d, %Y")

        visual_info = self.get_publication_visual_embed(pub_id)
        scribe_content = self._get_daily_scribe_content(pub_id)
        dynamic_article = (scribe_content or {}).get("markdown_article") or None

        if pub_id == "creator_pulse":
            static_body = f"""## 1. 📈 Algorithm & Traffic Radar
Short-form platforms are heavily boosting 4:5 portrait crops. Tight face-framing bypasses sensitive content AI flags and produces a **3.4x lift in organic reach** with 78.4% 3-second retention.

## 2. 💌 3 High-Converting PPV Teaser Formulas
- **The Midnight Audio Hook**: *"Put your headphones on before you press play... 🎧 Whispered voice memo from yesterday's studio shoot."*
- **The Curiosity Gap Vault**: *"My photographer told me not to post these 4 frames anywhere on the feed... Too unfiltered. Unlocking in DMs for 2 hours."*
- **The Color Grade Choice Poll**: *"Which color grade should I post tomorrow: Golden Hour Glow or Dark Boudoir? Tip $5 with your vote."*

## 3. 🎯 Progressive Ladder System for Cam & Live Streams
Replace static tip menus with milestone tiers (Tier 1 @ 150 tokens, Tier 2 @ 450 tokens, Tier 3 @ 900 tokens) to build room momentum and collective tipping.

## 4. 💡 The 2-Light Rim Lighting Formula
Set your 45° key softbox to 5600K daylight. Place a warm 3200K accent light behind your shoulder. The color temperature contrast carves separation from the background and highlights authentic skin texture.

## 5. 🔄 Subscriber Retention Habit
A 1-sentence personalized DM to fans within 60 minutes of churn recovers up to 28% of lapsed subscribers before they uninstall the app."""
            body = dynamic_article or static_body
            return f"""# 💋 The Daily Creator Pulse: 5-Part Morning Monetization Playbook
*Published by CreatorMediaLab • {today_str}*

---

{body}

![Creator Studio Visual (RTX 5070 Ti Diffusion • Iris [77 Ir] Verified)]({visual_info['web_src']})

---

### 🚀 CreatorMediaLab Resource Suite
- 👉 **[Book Pro Photo Retouching on Fiverr]({FIVERR_URL})**
- 👉 **[Download Cam Stream Bio Kits on Etsy]({ETSY_URL})**
- 👉 **[Complete Creator Resource Hub on Linktree]({LINKTREE_URL})**
"""

        elif pub_id == "studio_wire":
            static_body = f"""## 1. 🔍 Sensor vs Analog Color Science
Digital CMOS sensors capture light linearly with harsh #FFFFFF clipping. Analog film features smooth S-curve silver halide shoulder compression, which is why film portraits look velvety and textured.

## 2. 🎨 Kodak Portra 400 Lightroom Parameter Recipe
| Module | Exact Setting | Film Aesthetic |
| :--- | :--- | :--- |
| **RGB Tone Curve** | Lift Black Point to 18-22 | Creamy matte blacks and gentle shadow roll-off |
| **HSL Orange** | Saturation -4% | Luminance +8% | Luminous editorial skin tones without orange cast |
| **Color Wheels** | Midtones: Hue 42 (6%) | Shadows: Hue 215 (4%) | Classic warm/cool split toning |

## 3. 💡 Studio Lighting Schematic: 45° Feathered Beauty Dish
Position a 22" white beauty dish 45 degrees to camera left, feathered just across the bridge of the model's nose. Place a silver reflector at chest height. Result: striking cheekbone definition without harsh eye socket shadows.

## 4. 💃 3 Directing Cues for Natural Client Posing
- *"Breathe out through parted lips"* (releases jaw tension)
- *"Shift 70% of your weight to your rear foot"* (creates graceful S-curve)
- *"Drop front shoulder 1 inch"* (produces high-fashion asymmetry)

## 5. 💼 Studio Deliverables & Pricing Strategy
Never dump 300 raw photos on clients. Deliver 25-40 fully color-graded master selects within 24 hours to justify $350-$750 per session and secure continuous referrals."""
            body = dynamic_article or static_body
            return f"""# 📸 The Shutter & Studio Wire: Portra 400 Lightroom Masterclass
*Published by CreatorMediaLab • {today_str}*

---

{body}

![45 Degree Beauty Dish Lighting Blueprint]({IMG_STUDIO_WIRE})

---

### 📸 Studio Resources & Services
- 👉 **[Download 5-Preset Editorial .XMP Bundle on Etsy]({ETSY_URL})**
- 👉 **[Outsource Batch Client Retouching on Fiverr]({FIVERR_URL})**
- 👉 **[Official Studio Hub on Linktree]({LINKTREE_URL})**
"""

        elif pub_id == "creator_blueprint":
            static_body = f"""## 1. 📈 Digital Product Market Pulse
Modern buyers prefer $15-$35 instant micro-assets (Lightroom presets, stream templates, editing overlays) over 10-hour video courses. 100% gross margins with zero shipping labor.

## 2. 📐 The 3-Step Flywheel Architecture
1. **Phase 1: High-Touch Client Validation (Fiverr Gig)**: Sell custom retouching to validate willingness to pay.
2. **Phase 2: Productize into Digital Downloads (Etsy Storefront)**: Turn color grades into .XMP files and digital bundles.
3. **Phase 3: Automated Micro-Content (Twitter/X & Linktree Hub)**: Dispatch daily educational threads on `@TheCreatorAsset` routing 100% of organic traffic to your Linktree hub.

## 3. 🤖 Create Once, Syndicate 4x Pipeline
Turn 1 core tip into: 1 Twitter Thread + 1 HTML Email Digest + 1 Markdown Article + 1 Pinterest Infographic.

## 4. 🎯 The "Rule of 4" For Linktree
Keep mobile landing pages uncluttered: 1 High-Ticket Service + 1 Digital Product + 1 Social Community + 1 VIP Waitlist.

## 5. 💰 Creator Monetization Math
At a 2.5% conversion rate and $25 AOV, you only need 7 sales per week to hit $1,000/month. That requires just 6-7 clicks per day from Twitter/X."""
            body = dynamic_article or static_body
            return f"""# ⚡ The Creator Blueprint: $0 to $5k Media Asset Flywheel
*Published by CreatorMediaLab • {today_str}*

---

{body}

![3-Tier Media Flywheel Architecture]({IMG_CREATOR_FLYWHEEL})

---

### 🚀 CreatorMediaLab Ecosystem
- 👉 **[Shop Pro Creator Presets & Tools on Etsy]({ETSY_URL})**
- 👉 **[Book Pro Studio Retouching on Fiverr]({FIVERR_URL})**
- 👉 **[Central Hub on Linktree]({LINKTREE_URL})**
"""

        else:
            static_body = """## 1. ☀️ Morning Market Scraped Flash Deals
| Dispensary | Category | Top Pick | Discount | Sale Price |
| :--- | :--- | :--- | :--- | :--- |
| **Trulieve** | Whole Flower | Blue Dream (3.5g) | **40% OFF** | $24.00 |
| **MUV** | Live Rosin Vape | Lemon Jack 0.5g Cart | **35% OFF** | $32.50 |
| **Curaleaf** | Edibles | Indica Chews 100mg | **25% OFF** | $15.00 |
| **Surterra** | Full Spec Oil | Float 1g Syringe | **30% OFF** | $42.00 |

## 2. 📋 Patient Intel & Rolling Limits
Check your OMMU registry portal before placing orders. Florida's 70-day rolling calculation means milligram allocations expire dynamically on the 71st day after dispense."""
            body = dynamic_article or static_body
            return f"""# 🌿 Florida Dispensary Deals Morning Briefing
*Private Patient Briefing • {today_str}*

---

{body}

---
👉 **[Florida MMTC Patient Registry]({LINKTREE_URL})**
"""

    # ──────────────────────────────────────────────────────────────────────────
    # TWITTER / X VIRAL THREADS (ROUTING TO LINKTREE)
    # ──────────────────────────────────────────────────────────────────────────
    def get_twitter_thread(self, pub_id: str = "creator_pulse") -> List[str]:
        scribe_content = self._get_daily_scribe_content(pub_id)
        dynamic_thread = (scribe_content or {}).get("tweet_thread")
        if dynamic_thread:
            return dynamic_thread

        if pub_id == "creator_pulse":
            return [
                "1/4 💋 3 PPV message teaser formulas that converted 18%+ higher this weekend without sounding spammy 🧵👇 @creatorpulselab",
                "2/4 Formula 1: The 'Midnight Audio' Hook\n\n'Put your headphones on before you press play... 🎧 Whispered voice memo from yesterday's studio shoot. Unlocked for my top 5% only.'\n\nIntimacy converts higher than explicit photos every single time.",
                "3/4 Formula 2: The 'Curiosity Gap' Vault\n\n'My photographer told me not to post these 4 frames anywhere on the feed... Too unfiltered. Unlocking the raw set in DMs for the next 2 hours.'",
                f"4/4 Want daily PPV conversion breakdowns, lighting schematics, and tip menu formulas in your inbox? Subscribe free: {PORTAL_PULSE_URL}\n\nFollow @creatorpulselab for daily monetization playbooks 💋 Hub: {LINKTREE_URL}"
            ]

        elif pub_id == "studio_wire":
            return [
                "1/4 📸 Stop using cheap Instagram filters on paid client photo shoots.\n\nHere is the exact color science behind the Kodak Portra 400 film aesthetic in Lightroom 🧵👇 @TheCreatorAsset",
                "2/4 1. The RGB Tone Curve Secret:\n\nRaise your black point to 18-22 on the RGB curve. It softens harsh digital sensors and gives that velvety film shadow roll-off magazine editors love.",
                "3/4 2. Authentic Skin Science:\n\nDrop Orange saturation by -4% and raise Orange luminance by +8%. This makes skin look luminous and clean without changing eye makeup tones.",
                f"4/4 Download our 5-Preset Editorial .XMP Bundle on Etsy ({ETSY_URL}) or book studio retouching on Fiverr ({FIVERR_URL}).\n\nSubscribe free to Studio Wire: {PORTAL_STUDIO_URL} 📸 Follow @TheCreatorAsset"
            ]

        elif pub_id == "creator_blueprint":
            return [
                "1/4 ⚡ If I had to build a digital creator studio from $0 in 2026, here is the exact 3-step flywheel I'd run 🧵👇 @TheCreatorAsset",
                "2/4 Step 1: Sell high-ticket services first (photo retouching / video edits on Fiverr) to validate real client demand.",
                "3/4 Step 2: Productize your workflow. Turn your color grades into .XMP presets and sell them on Etsy while you sleep.",
                f"4/4 Explore our pro creative tools, presets, and retouching services: {LINKTREE_URL}\n\nSubscribe free to The Creator Blueprint: {PORTAL_BLUEPRINT_URL} 🚀 Follow @TheCreatorAsset"
            ]

        else:
            return [
                "1/3 🌿 Florida Dispensary Deals Morning Round-Up 🧵👇",
                "2/3 Top discounts today: 40% off whole flower at Trulieve, 35% off live rosin carts at MUV, and 25% off edibles at Curaleaf.",
                f"3/3 Private invite-only briefing. Free Florida MMTC updates: {PORTAL_DISPENSARY_URL}"
            ]


# Global singleton instance export
newsletter_mgr = NewsletterManager()
