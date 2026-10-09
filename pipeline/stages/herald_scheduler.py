from shared.atomic_writer import atomic_write_json, safe_read_json
"""
WORKHORSE AUTONOMOUS DAILY SCHEDULER & DISPATCHER (AGENT: HERALD [33 As])
Manages automated daily multi-publication newsletters and 3-5 daily tweets/threads
per account for both:
  - @TheCreatorAsset (Studio Photography, Color Grading, Presets)
  - @creatorpulselab (Adult Creators, PPV Strategies, Cam Tip Menus)
"""

import os
import sys
import json
import time
import asyncio
import logging
import random
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any, List, Optional

sys.path.insert(0, "F:/WORKHORSE")
from pipeline.stages.twitter_poster import TwitterPoster
from pipeline.stages.newsletter_manager import NewsletterManager
from pipeline.stages.pinterest_poster import PinterestPoster

logger = logging.getLogger("workhorse.herald_scheduler")

# Each brand has its own distinct visual "vibe" since @creatorpulselab and @TheCreatorAsset
# serve different audiences - Herald generates a FRESH on-brand image per post rather than
# reusing a leftover/test render, and every render still passes through the Iris QC gate.
BRAND_VIBES = {
    "creator_pulse_lab": {
        "brand_target": "creator_pulse_lab",
        "prompts": [
            "Luxury boudoir photography, intimate warm rim lighting, satin and velvet fabric textures, sensual confident pose, soft romantic shadows, high-end editorial glamour, photorealistic, 85mm lens, shallow depth of field",
            "Sultry studio boudoir portrait, golden hour warm key light, silk sheets and velvet backdrop, intimate close framing, soft glowing skin tones, luxury glamour photography, photorealistic, shallow depth of field",
            "Seductive cam-studio glamour shot, moody warm rim lighting, lace and satin lingerie texture, confident alluring gaze, cinematic shadow play, high-end boudoir editorial, photorealistic, 85mm portrait lens",
            "Moody neon-lit boudoir scene, magenta and cyan gel rim lighting, sheer mesh and satin fabric, confident over-the-shoulder pose, cinematic nightclub glamour atmosphere, photorealistic, 50mm lens, shallow depth of field",
            "Sunset-lit penthouse boudoir portrait, warm amber window light, silk robe and velvet chaise, relaxed intimate pose, soft golden haze, editorial glamour photography, photorealistic, 85mm lens",
            "High-contrast chiaroscuro boudoir studio shot, single hard key light with deep black shadows, black lace and leather textures, dramatic confident pose, moody gothic glamour editorial, photorealistic, 85mm lens"
        ],
        "negative_prompt": "extra limbs, deformed hands, mutated fingers, bad anatomy, blurry, low quality, watermark, text, cartoon, illustration"
    },
    "creator_media_lab": {
        "brand_target": "creator_media_lab",
        "prompts": [
            "Editorial studio photography, 5600K key light, Kodak Portra 400 film color grading, magazine-quality shallow depth of field, professional photographer backdrop, crisp clean composition, photorealistic, 50mm lens",
            "High-fashion studio portrait, softbox lighting setup, Kodak Portra 400 color science, clean minimalist backdrop, sharp focus editorial composition, photorealistic, 85mm lens",
            "Professional studio headshot photography, three-point lighting, film emulation color grade, magazine cover composition, polished commercial aesthetic, photorealistic, 50mm lens",
            "Natural window-light studio portrait, soft diffused daylight, Fujifilm color science, clean editorial backdrop, relaxed candid composition, photorealistic, 35mm lens, shallow depth of field",
            "Dramatic rembrandt-lit studio portrait, single key light with reflector fill, Cinestill 800T color grade, moody dark backdrop, confident editorial pose, photorealistic, 85mm lens",
            "Outdoor golden-hour environmental portrait, warm backlit rim glow, Kodak Gold film emulation, bokeh-rich natural backdrop, candid lifestyle composition, photorealistic, 50mm lens"
        ],
        "negative_prompt": "extra limbs, deformed hands, mutated fingers, bad anatomy, blurry, low quality, watermark, text, cartoon, illustration"
    }
}

STATE_FILE = Path("F:/WORKHORSE/workspace/daily_schedule_state.json")
LOGS_DIR = Path("F:/WORKHORSE/workspace/newsletter_logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Public newsletters that previously had NO automated send path at all - only
# dispensary_deals (private) was ever actually dispatched by trigger_dispatch().
PUBLICATION_SCHEDULE = {
    "studio_wire": "08:30",
    "creator_pulse": "09:00",
    "creator_blueprint": "10:00",
}

# dispensary_deals is dispatched via its own legacy flag name (newsletters_sent_today)
# for backward compat with the dashboard, but is monitored the same way as the rest.
ALL_MONITORED_PUBLICATIONS = {"dispensary_deals": "09:00", **PUBLICATION_SCHEDULE}

# A dispatch isn't marked "done" until real delivery is verified. Failed dispatches are
# auto-retried up to this many times before Synapse gives up and alerts the Commander.
MAX_DISPATCH_RETRIES = 3

# Pipe 3 - Autonomous AI Model Content Engine (Cipher -> RTX 5070 Ti -> Forge -> Scribe).
# One hands-off content drop per day; output is staged for manual review, never auto-posted.
CONTENT_ENGINE_SCHEDULE_TIME = "11:30"

# How long Herald keeps retrying the morning radar sweep (every ~60s) when it comes back
# degraded/fallback before giving up and accepting whatever content it has for the day.
RADAR_SWEEP_RETRY_CUTOFF = "10:30"

DAILY_SLOTS = [
    {
        "slot_id": "slot_1_morning",
        "name": "Morning Masterclass & Newsletter Drop",
        "target_time": "09:00",
        "description": "Daily 4-tweet deep-dive educational thread & morning newsletter release",
        "tweets": {
            "creatorpulselab": [
                "1/4 💋 3 PPV message teaser formulas that converted 18%+ higher this weekend without sounding spammy 🧵👇 @creatorpulselab",
                "2/4 Formula 1: The 'Banned Angle' Hook.\n\nNever say 'Buy my video'. Say: 'My editor said I couldn't post this clip publicly... so I hid the uncensored 4K cut in your vault.' Add a 3-second blurred preview.",
                "3/4 Formula 2: The 'Micro-Unlock' Pricing Ladder.\n\nTier 1 ($8-$12): High-converting impulse buy (teaser + 2 photos).\nTier 2 ($25-$35): Full scene + audio voice note.\nTier 3 ($65+): Complete VIP bundle + personal sign-off.",
                "4/4 💎 Tip: High-paying spenders buy for intimacy, not just visuals. Check our profile for the complete morning monetization blueprint & free daily newsletter 👇\nhttps://digitalcreatorassets-source.github.io/creatormedialab/?pub=creator_pulse"
            ],
            "TheCreatorAsset": [
                "1/4 📸 Stop using cheap Instagram filters on paid client photo shoots.\n\nHere is the exact color science behind the Kodak Portra 400 film aesthetic in Lightroom 🧵👇 @TheCreatorAsset",
                "2/4 Portra 400 Tone Curve Breakdown:\n\n1. Lift the black point on the RGB curve by +8 to +12 for that matte film floor.\n2. Drop shadows slightly (-5) to preserve dynamic contrast.\n3. Keep midtone skin values linear to avoid harsh digital clipping.",
                "3/4 HSL Color Calibration:\n\n- Orange Hue: +2 to +4 (warms natural skin tones without looking artificial)\n- Red Luminance: +6 (creates that healthy, glowing studio look)\n- Green Saturation: -18 (eliminates harsh digital foliage tint)",
                "4/4 ✨ Download our master studio preset pack (.XMP) and explore the full editorial retouching suite:\nhttps://www.etsy.com/shop/CreatorMediaLab\nhttps://digitalcreatorassets-source.github.io/creatormedialab/?pub=studio_wire"
            ]
        }
    },
    {
        "slot_id": "slot_2_midday",
        "name": "Mid-Day Creator Tip & Lightroom Science",
        "target_time": "13:00",
        "description": "High-converting quick tip and before-and-after breakdown",
        "tweets": {
            "creatorpulselab": [
                "⚡ Quick Cam Tip: Tip menus with fewer than 8 items convert 32% faster than 25-item menus.\n\nDecision fatigue is real. Group your menu into: Quick Teases (25-75 tks), Sensual Action (100-300 tks), and VIP Domination (500-1000 tks).\n\nKeep it punchy, Commander. 👑 @creatorpulselab"
            ],
            "TheCreatorAsset": [
                "📸 Studio Lighting Rule of Thumb: If your key light is less than 3 feet from your subject, feather it 45 degrees across their shoulder rather than pointing directly at their face.\n\nSoft light is created by apparent light size, not lower wattage. #StudioPhotography #CreatorMediaLab"
            ]
        }
    },
    {
        "slot_id": "slot_3_afternoon",
        "name": "Afternoon Monetization & Service Spotlight",
        "target_time": "17:00",
        "description": "Spotlight on live Fiverr gigs and high-earning digital products",
        "tweets": {
            "creatorpulselab": [
                "✨ Upgrading your cam profile or OnlyFans tip menu? A high-converting visual design pays for itself in your first 2 hours live.\n\nWe design custom Chaturbate, MFC & Fansly tip menus with interactive Lovense badges:\nhttp://www.fiverr.com/s/GPPxKB3 💋 @creatorpulselab"
            ],
            "TheCreatorAsset": [
                "🎨 Editorial Photo Retouching & Film Color Grading for creators and photographers.\n\nFrequency separation, non-destructive dodge & burn, and Portra/Cinestill film emulation starting at $20:\nhttps://www.fiverr.com/s/GPz71VL 📸 @TheCreatorAsset"
            ]
        }
    },
    {
        "slot_id": "slot_4_evening",
        "name": "Prime Evening Video Cuts & Asset Flywheel",
        "target_time": "20:30",
        "description": "Video trailer teasers, 9:16 vertical cuts & multi-channel promo",
        "tweets": {
            "creatorpulselab": [
                "🎬 Turn your long-form shoots into 60s viral teasers, 9:16 TikTok crops, and high-retention PPV previews.\n\nAll media processed 100% locally with NVENC 60fps hardware encoding:\nhttp://www.fiverr.com/s/emmRYZm ⚡ @creatorpulselab"
            ],
            "TheCreatorAsset": [
                "⚡ The Creator Media Asset Flywheel: Shoot once. Cut 60s trailers. Extract 6 high-res poses. Synthesize platform copy. Distribute across 5 channels.\n\nRead our full media automation guide:\nhttps://digitalcreatorassets-source.github.io/creatormedialab/ 📸 @TheCreatorAsset"
            ]
        }
    },
    {
        "slot_id": "slot_5_latenight",
        "name": "Late Night Community Engagement",
        "target_time": "23:00",
        "description": "Late-night discussion, engagement polls and creator insights",
        "tweets": {
            "creatorpulselab": [
                "🌙 Night-shift question for creators: What is your #1 highest-converting PPV message price point: $12, $18, or $28?\n\nDrop your thoughts below 👇💋 @creatorpulselab"
            ],
            "TheCreatorAsset": [
                "🌙 Night studio tip: Always calibrate your monitor to 120 cd/m² when editing in dim lighting. Over-bright screens lead to dark, muddy exports on client phones. Goodnight creators. ✨ @TheCreatorAsset"
            ]
        }
    }
]

# Pinterest content pool - CreatorMediaLab / @TheCreatorAsset (mainstream brand) ONLY.
# There is deliberately no equivalent list for the adult_creator_brand ("creatorpulselab") -
# Pinterest's Community Guidelines prohibit sexual content, nudity, and promotion of cam/
# webcam services, so that brand must never have a Pinterest content source at all. Every
# entry here still passes through PinterestPoster.is_pinterest_safe() before publishing as
# defense-in-depth, with content_type hardcoded to "general".
PINTEREST_DAILY_CONTENT = [
    {
        "title": "Kodak Portra 400 Film Color Grade Tutorial",
        "description": "Studio photography color science: how to recreate the Kodak Portra 400 film look in Lightroom with tone curve and HSL adjustments. Free masterclass from CreatorMediaLab.",
        "link": "https://digitalcreatorassets-source.github.io/creatormedialab/?pub=studio_wire"
    },
    {
        "title": "45-Degree Studio Lighting Setup Guide",
        "description": "A simple studio lighting rule of thumb for soft, flattering portrait light using key light feathering and apparent light size. #StudioPhotography",
        "link": "https://www.etsy.com/shop/CreatorMediaLab"
    },
    {
        "title": "Editorial Photo Retouching & Film Emulation Presets",
        "description": "Frequency separation, non-destructive dodge & burn, and Portra/Cinestill film color grading presets for photographers and creators.",
        "link": "https://www.fiverr.com/s/GPz71VL"
    },
    {
        "title": "The Creator Media Asset Flywheel",
        "description": "Shoot once, cut trailers, extract poses, synthesize platform copy, and distribute across channels. A full media automation guide for creators.",
        "link": "https://digitalcreatorassets-source.github.io/creatormedialab/"
    },
    {
        "title": "Lightroom Preset Pack for Studio Portraits",
        "description": "Master studio preset pack (.XMP) for editorial-quality portrait photography and color grading.",
        "link": "https://www.etsy.com/shop/CreatorMediaLab"
    }
]

class HeraldScheduler:
    def __init__(self, config_path: str = "F:/WORKHORSE/config.json"):
        self.config_path = config_path
        self.twitter = TwitterPoster(config_path)
        self.pinterest = PinterestPoster(config_path)
        self.newsletter = NewsletterManager()
        self.is_running = False
        self._load_state()

    def _pick_image_prompt(self, brand_key: str) -> str:
        """Selects an image prompt for this brand while avoiding recent repeats - the same
        prompt won't be reused until every other variant in the pool has had a turn, so a
        week of daily posts doesn't end up visually samey even though each individual
        generation is already a fresh render with its own random seed."""
        prompts = BRAND_VIBES[brand_key]["prompts"]
        recent_map = self.state.setdefault("recent_image_prompts", {})
        recent = recent_map.setdefault(brand_key, [])

        lookback = max(0, len(prompts) - 1)
        recently_used = set(recent[-lookback:]) if lookback else set()
        available = [i for i in range(len(prompts)) if i not in recently_used]
        if not available:
            available = list(range(len(prompts)))

        chosen_idx = random.choice(available)
        recent.append(chosen_idx)
        recent_map[brand_key] = recent[-20:]
        self._save_state()
        return prompts[chosen_idx]

    def _get_brand_visual_for_post(self, handle: str) -> Optional[str]:
        """
        Generates a FRESH, on-brand image for this specific post (each account has its
        own distinct vibe/audience) rather than reusing a leftover render. The render
        goes through the standard Iris QC gate; only a passed image is ever returned.
        Falls back to the latest already-verified render for this brand if ComfyUI is
        offline or the fresh generation fails/fails QC - never returns an unverified file.
        """
        is_pulse = "pulse" in handle.lower()
        brand_key = "creator_pulse_lab" if is_pulse else "creator_media_lab"
        pub_key = "creator_pulse" if is_pulse else "studio_wire"
        vibe = BRAND_VIBES[brand_key]

        try:
            from pipeline.stages.comfyui_bridge import comfy_bridge
            prompt = self._pick_image_prompt(brand_key)
            gen_res = comfy_bridge.generate_and_audit(
                positive_prompt=prompt,
                negative_prompt=vibe["negative_prompt"],
                brand_target=vibe["brand_target"],
                auto_qc=True
            )
            if gen_res.get("success") and gen_res.get("qc_audit", {}).get("passed", gen_res.get("qc_bypassed")):
                print(f"[Herald Scheduler] Fresh on-brand visual generated for @{handle}: {gen_res.get('filename')}")
                return gen_res.get("file_path")
            print(f"[Herald Scheduler] Fresh visual for @{handle} did not pass Iris QC, falling back to last verified render.")
        except Exception as e:
            print(f"[Herald Scheduler] Fresh visual generation unavailable for @{handle} ({e}), falling back to last verified render.")

        # Safety net: last known IRIS-verified render for this brand (never an unaudited file)
        vis_path = self.newsletter.get_latest_comfy_visual(pub_key)
        return str(vis_path) if vis_path else None

    def _load_state(self) -> Dict[str, Any]:
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    self.state = json.load(f)
                for pub_id in ALL_MONITORED_PUBLICATIONS:
                    self.state.setdefault(f"{pub_id}_attempts", 0)
                    self.state.setdefault(f"{pub_id}_alerted_today", False)
                self.state.setdefault("content_engine_sent_today", False)
                self.state.setdefault("content_engine_attempts", 0)
                self.state.setdefault("content_engine_alerted_today", False)
                return self.state
            except Exception:
                pass
        self.state = {
            "last_date": str(date.today()),
            "executed_slots": [],
            "newsletters_sent_today": False,
            "studio_wire_sent_today": False,
            "creator_pulse_sent_today": False,
            "creator_blueprint_sent_today": False,
            "content_engine_sent_today": False,
            "content_engine_attempts": 0,
            "content_engine_alerted_today": False,
            "history": []
        }
        for pub_id in ALL_MONITORED_PUBLICATIONS:
            self.state.setdefault(f"{pub_id}_attempts", 0)
            self.state.setdefault(f"{pub_id}_alerted_today", False)
        self._save_state()
        return self.state

    def _save_state(self):
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save schedule state: {e}")

    def _check_day_rollover(self):
        today_str = str(date.today())
        if self.state.get("last_date") != today_str:
            self.state["last_date"] = today_str
            self.state["executed_slots"] = []
            self.state["newsletters_sent_today"] = False
            self.state["radar_sweep_done_today"] = False
            self.state["studio_wire_sent_today"] = False
            self.state["creator_pulse_sent_today"] = False
            self.state["creator_blueprint_sent_today"] = False
            self.state["content_engine_sent_today"] = False
            self.state["content_engine_attempts"] = 0
            self.state["content_engine_alerted_today"] = False
            self.state["pinterest_posted_today"] = False
            for pub_id in ALL_MONITORED_PUBLICATIONS:
                self.state[f"{pub_id}_attempts"] = 0
                self.state[f"{pub_id}_alerted_today"] = False
            self._save_state()
            print(f"[Herald Scheduler] Day rollover to {today_str}. Schedule reset for 5 new slots.")

    def get_status(self) -> Dict[str, Any]:
        self._check_day_rollover()
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")
        
        slots_status = []
        for s in DAILY_SLOTS:
            is_done = s["slot_id"] in self.state.get("executed_slots", [])
            slots_status.append({
                "slot_id": s["slot_id"],
                "name": s["name"],
                "target_time": s["target_time"],
                "executed": is_done,
                "due": not is_done and current_time_str >= s["target_time"]
            })

        return {
            "status": "active" if self.is_running else "standby",
            "date": str(date.today()),
            "current_time": current_time_str,
            "newsletters_sent_today": self.state.get("newsletters_sent_today", False),
            "publications_sent_today": {
                pub_id: self.state.get(f"{pub_id}_sent_today", False)
                for pub_id in PUBLICATION_SCHEDULE
            },
            "content_engine_sent_today": self.state.get("content_engine_sent_today", False),
            "content_engine_attempts": self.state.get("content_engine_attempts", 0),
            "executed_slots_count": len(self.state.get("executed_slots", [])),
            "total_slots": len(DAILY_SLOTS),
            "slots": slots_status,
            "recent_history": self.state.get("history", [])[-10:]
        }

    def dispatch_slot(self, slot_id: str) -> Dict[str, Any]:
        """Execute a specific tweet slot across both Twitter accounts."""
        self._check_day_rollover()
        slot = next((s for s in DAILY_SLOTS if s["slot_id"] == slot_id), None)
        if not slot:
            return {"status": "error", "message": f"Slot {slot_id} not found"}

        results = {"slot_id": slot_id, "timestamp": datetime.now().isoformat(), "accounts": {}}
        tweets_dict = dict(slot.get("tweets", {}))

        # Dynamically inject today's synthesized trend tweets from daily_trends_vault.json
        try:
            from pipeline.stages.trend_researcher import trend_researcher
            vault = trend_researcher.load_vault()
            if vault.get("today_date") != str(date.today()):
                # Vault predates today (e.g. this morning's radar sweep hasn't run/completed
                # yet) - never silently reuse a prior day's "dynamic" tweets as if they were
                # fresh. Fall through to the static slot content instead.
                print(f"[Herald Scheduler] Trend vault is stale (today_date={vault.get('today_date')!r}, expected {date.today()}) - using static content for {slot_id}.")
            else:
                daily_synth = vault.get("daily_synthesis", {})
                dynamic_slots = daily_synth.get("daily_slots", {})
                if slot_id in dynamic_slots:
                    dyn = dynamic_slots[slot_id]
                    for handle, dyn_tweets in dyn.items():
                        if dyn_tweets and len(dyn_tweets) > 0:
                            tweets_dict[handle] = dyn_tweets
                            print(f"[Herald Scheduler] Using dynamic trending tweets for @{handle} in {slot_id}")
        except Exception as e:
            print(f"[Herald Scheduler] Error reading dynamic tweets from vault: {e}")

        for handle, tweets in tweets_dict.items():
            if tweets:
                try:
                    media_paths = None
                    try:
                        vis_path = self._get_brand_visual_for_post(handle)
                        if vis_path and Path(vis_path).exists():
                            media_paths = [str(vis_path)]
                            print(f"[Herald Scheduler] Brand visual attached for @{handle} -> {Path(vis_path).name}")
                    except Exception as ve:
                        print(f"[Herald Scheduler] Visual lookup notice: {ve}")

                    post_res = self.twitter.post_thread(handle, tweets, media_paths=media_paths)
                    results["accounts"][handle] = post_res
                    print(f"[Herald Scheduler] Posted {slot_id} to @{handle} (media={bool(media_paths)}): {post_res.get('success')}")
                except Exception as e:
                    results["accounts"][handle] = {"success": False, "error": str(e)}

        if slot_id not in self.state["executed_slots"]:
            self.state["executed_slots"].append(slot_id)

        self.state["history"].append({
            "type": "twitter_slot",
            "slot_id": slot_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "results": results
        })
        self._save_state()
        return results

    def dispatch_pinterest_daily(self) -> Dict[str, Any]:
        """
        Publishes one pin per day to the mainstream CreatorMediaLab/@TheCreatorAsset
        Pinterest board, sourced exclusively from PINTEREST_DAILY_CONTENT (general-brand
        content only). content_type is hardcoded to "general" here and re-verified inside
        PinterestPoster.create_pin()'s TOS safety gate - there is no path for
        adult_creator_brand content to reach this method.
        """
        self._check_day_rollover()

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception as e:
            return {"status": "error", "message": f"Failed to read config.json: {e}"}

        pin_cfg = cfg.get("marketing_channels", {}).get("main_brand", {}).get("pinterest", {})
        if not pin_cfg.get("enabled"):
            return {"status": "skipped", "reason": "pinterest_disabled", "message": "Pinterest publishing is disabled in config.json (marketing_channels.main_brand.pinterest.enabled)."}

        board_id = pin_cfg.get("default_board_id", "").strip()
        if not board_id:
            return {"status": "skipped", "reason": "no_board_id", "message": "No default_board_id configured under marketing_channels.main_brand.pinterest."}

        day_index = date.today().toordinal() % len(PINTEREST_DAILY_CONTENT)
        content = PINTEREST_DAILY_CONTENT[day_index]

        vis_path = None
        try:
            vis_path = self._get_brand_visual_for_post("TheCreatorAsset")
        except Exception as e:
            print(f"[Herald Scheduler] Pinterest visual lookup notice: {e}")

        if not vis_path or not Path(vis_path).exists():
            result = {"status": "error", "message": "No verified brand visual available for Pinterest pin (ComfyUI unavailable and no fallback render found)."}
        else:
            post_res = self.pinterest.create_pin(
                board_id=board_id,
                title=content["title"],
                description=content["description"],
                link=content.get("link", ""),
                image_path=vis_path,
                content_type="general"
            )
            result = {"status": "ok" if post_res.get("success") else "error", "content": content, "result": post_res}
            print(f"[Herald Scheduler] Pinterest daily pin dispatched: {post_res.get('success')} ({post_res.get('status', post_res.get('pin_url'))})")

        self.state["pinterest_posted_today"] = True
        self.state["history"].append({
            "type": "pinterest_pin",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "results": result
        })
        self._save_state()
        return result

    def _verify_dispensary_dispatch(self, timeout_s: int = 180) -> Dict[str, Any]:
        """Blocks until the dispensary_deals.py subprocess finishes, then inspects its
        captured log output for a real '[Email] Sent to' line. A clean exit code alone
        does NOT prove the email was actually sent - a 2026-10-07 bug had the script
        exit 0 while silently skipping send_email() entirely, with SMS masking it."""
        waited = 0
        while self.newsletter.run_status == "running" and waited < timeout_s:
            time.sleep(2)
            waited += 2
        status = self.newsletter.get_run_status()
        logs = status.get("recent_logs", "")
        email_confirmed = "[Email] Sent to" in logs
        email_disabled = "[Email] No recipients configured" in logs
        return {
            "success": status.get("status") == "completed" and (email_confirmed or email_disabled),
            "email_confirmed": email_confirmed,
            "process_status": status.get("status"),
            "logs_tail": logs[-800:]
        }

    def dispatch_newsletters_all(self) -> Dict[str, Any]:
        """Trigger the private Dispensary Deals dispatch (dispensary_deals.py subprocess),
        then BLOCK until it finishes and verify real email delivery before marking today's
        dispatch successful - a launched-OK subprocess is not proof the email went out."""
        self._check_day_rollover()
        launch_res = self.newsletter.trigger_dispatch()
        verify_res = self._verify_dispensary_dispatch()
        res = {**launch_res, **verify_res}
        if verify_res["success"]:
            self.state["newsletters_sent_today"] = True
        self.state["history"].append({
            "type": "newsletter_dispatch",
            "pub_id": "dispensary_deals",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "result": res
        })
        self._save_state()
        return res

    def dispatch_publication(self, pub_id: str) -> Dict[str, Any]:
        """Sends a public newsletter (studio_wire / creator_pulse / creator_blueprint) to its
        real subscriber list. Only marks today's send as successful if send_publication_now()
        confirms recipients were actually emailed - success=False or sent=0 must NOT be
        silently treated as 'done for today' (see 2026-10-07 dispatch-gap incident)."""
        self._check_day_rollover()
        res = self.newsletter.send_publication_now(pub_id)
        if bool(res.get("success")) and res.get("sent", 0) > 0:
            self.state[f"{pub_id}_sent_today"] = True
        self.state["history"].append({
            "type": "newsletter_dispatch",
            "pub_id": pub_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "result": res
        })
        self._save_state()
        return res

    def _monitor_and_remediate_publications(self):
        """Autonomous watchdog - called every 60s from run_loop(). For any publication
        whose target time has passed and hasn't been VERIFIED sent today, retries the
        dispatch (up to MAX_DISPATCH_RETRIES). Once retries are exhausted, logs a
        'needs_attention' incident and texts the Commander directly via Synapse's
        notify_commander - added 2026-10-07 so a dispatch failure can never again go
        unnoticed just because nothing checked back on it."""
        current_time = datetime.now().strftime("%H:%M")
        for pub_id, target in ALL_MONITORED_PUBLICATIONS.items():
            if current_time < target:
                continue

            sent_key = "newsletters_sent_today" if pub_id == "dispensary_deals" else f"{pub_id}_sent_today"
            if self.state.get(sent_key):
                continue

            attempts_key = f"{pub_id}_attempts"
            alerted_key = f"{pub_id}_alerted_today"
            attempts = self.state.get(attempts_key, 0)

            if attempts >= MAX_DISPATCH_RETRIES:
                if not self.state.get(alerted_key):
                    msg = (f"WORKHORSE ALERT: '{pub_id}' newsletter failed to send after "
                           f"{MAX_DISPATCH_RETRIES} automatic retries today. Manual check needed.")
                    print(f"[Herald Scheduler] {msg}")
                    try:
                        from pipeline.stages.ai_operator import ai_operator
                        ai_operator.log_incident(
                            f"newsletter_{pub_id}",
                            f"Failed to dispatch after {MAX_DISPATCH_RETRIES} attempts",
                            "Auto-retry exhausted - Commander notified via SMS.",
                            status="needs_attention"
                        )
                        ai_operator.notify_commander(msg)
                    except Exception as e:
                        print(f"[Herald Scheduler] Failed to notify commander: {e}")
                    self.state[alerted_key] = True
                    self._save_state()
                continue

            print(f"[Herald Scheduler] '{pub_id}' not yet confirmed sent today "
                  f"(attempt {attempts + 1}/{MAX_DISPATCH_RETRIES}). Dispatching...")
            self.state[attempts_key] = attempts + 1
            self._save_state()
            if pub_id == "dispensary_deals":
                self.dispatch_newsletters_all()
            else:
                self.dispatch_publication(pub_id)

    def dispatch_content_engine(self) -> Dict[str, Any]:
        """Runs one Pipe 3 autonomous content drop (Cipher -> RTX 5070 Ti -> Forge -> Scribe).
        Only marks today's run successful if the full chain actually produced a manifest -
        a render that fails partway (e.g. ComfyUI offline) must NOT be silently treated as done."""
        self._check_day_rollover()
        from pipeline.stages.content_engine import content_engine
        res = content_engine.run_autonomous_cycle()
        if res.get("success"):
            self.state["content_engine_sent_today"] = True
        self.state["history"].append({
            "type": "content_engine_cycle",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "result": {k: v for k, v in res.items() if k != "copy_kit"}  # copy kit is large, keep history compact
        })
        self._save_state()
        return res

    def _monitor_and_remediate_content_engine(self):
        """Autonomous watchdog for Pipe 3, mirroring _monitor_and_remediate_publications:
        retries a failed/missed daily content drop up to MAX_DISPATCH_RETRIES, then alerts
        the Commander via Synapse's notify_commander once retries are exhausted."""
        current_time = datetime.now().strftime("%H:%M")
        if current_time < CONTENT_ENGINE_SCHEDULE_TIME:
            return
        if self.state.get("content_engine_sent_today"):
            return

        attempts = self.state.get("content_engine_attempts", 0)
        if attempts >= MAX_DISPATCH_RETRIES:
            if not self.state.get("content_engine_alerted_today"):
                msg = (f"WORKHORSE ALERT: Autonomous content engine (Pipe 3) failed to produce "
                       f"today's drop after {MAX_DISPATCH_RETRIES} automatic retries. Manual check needed.")
                print(f"[Herald Scheduler] {msg}")
                try:
                    from pipeline.stages.ai_operator import ai_operator
                    ai_operator.log_incident(
                        "content_engine",
                        f"Failed to complete autonomous content cycle after {MAX_DISPATCH_RETRIES} attempts",
                        "Auto-retry exhausted - Commander notified via SMS.",
                        status="needs_attention"
                    )
                    ai_operator.notify_commander(msg)
                except Exception as e:
                    print(f"[Herald Scheduler] Failed to notify commander: {e}")
                self.state["content_engine_alerted_today"] = True
                self._save_state()
            return

        print(f"[Herald Scheduler] Content engine not yet confirmed done today "
              f"(attempt {attempts + 1}/{MAX_DISPATCH_RETRIES}). Running cycle...")
        self.state["content_engine_attempts"] = attempts + 1
        self._save_state()
        self.dispatch_content_engine()

    def dispatch_today_all_now(self) -> Dict[str, Any]:
        """
        Instant catch-up: Dispatches today's newsletters AND posts the current/pending
        tweets across both accounts immediately.
        """
        self._check_day_rollover()
        results = {
            "timestamp": datetime.now().isoformat(),
            "newsletters": self.dispatch_newsletters_all(),
            "twitter_slots_dispatched": []
        }

        # Dispatch Slot 1 (Morning Masterclass Thread)
        slot1_res = self.dispatch_slot("slot_1_morning")
        results["twitter_slots_dispatched"].append(slot1_res)

        return results

    async def run_loop(self):
        """Continuous background loop running inside FastAPI."""
        self.is_running = True
        print("[Herald Scheduler] Background Autonomous Daily Dispatcher online. Checking slots every 60s...")
        while True:
            try:
                await asyncio.sleep(60)
                self._check_day_rollover()
                now = datetime.now()
                current_time = now.strftime("%H:%M")

                # Autonomous Morning Trend Radar Sweep (08:00 AM). If the sweep comes back
                # degraded/fallback content (LLM hiccup, incomplete JSON, etc.) it is NOT
                # marked done - Herald keeps retrying every ~60s until RADAR_SWEEP_RETRY_CUTOFF,
                # so a single transient failure doesn't silently stick Herald with repeated
                # static content for the whole day.
                if current_time >= "08:00" and not self.state.get("radar_sweep_done_today"):
                    print("[Herald Scheduler] 08:00 AM window reached: Triggering autonomous morning trend radar sweep...")
                    try:
                        from pipeline.stages.trend_researcher import trend_researcher
                        loop = asyncio.get_event_loop()
                        vault_result = await loop.run_in_executor(None, trend_researcher.run_daily_radar_sweep)
                        used_fallback = vault_result.get("daily_synthesis", {}).get("used_fallback", False)
                        if used_fallback and current_time < RADAR_SWEEP_RETRY_CUTOFF:
                            print(f"[Herald Scheduler] Radar sweep returned degraded/fallback content - will retry next cycle (before {RADAR_SWEEP_RETRY_CUTOFF} cutoff).")
                        else:
                            if used_fallback:
                                print(f"[Herald Scheduler] Radar sweep still degraded past {RADAR_SWEEP_RETRY_CUTOFF} cutoff - accepting fallback content for today.")
                                try:
                                    from pipeline.stages.ai_operator import ai_operator
                                    ai_operator.log_incident(
                                        "trend_researcher",
                                        "Daily radar sweep used degraded/fallback content after repeated retries (LLM synthesis failed or returned incomplete slots)",
                                        f"Accepted fallback content past the {RADAR_SWEEP_RETRY_CUTOFF} retry cutoff - some tweet slots today may repeat prior static copy.",
                                        status="needs_attention"
                                    )
                                except Exception:
                                    pass
                            self.state["radar_sweep_done_today"] = True
                            self._save_state()
                    except Exception as e:
                        print(f"[Herald Scheduler] Radar sweep error: {e}")

                # Check each Twitter slot
                for s in DAILY_SLOTS:
                    slot_id = s["slot_id"]
                    target = s["target_time"]

                    # If target time reached and not yet executed today
                    if current_time >= target and slot_id not in self.state.get("executed_slots", []):
                        print(f"[Herald Scheduler] Target time {target} reached for {slot_id}. Triggering automated dispatch...")
                        # In background thread
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(None, lambda s_id=slot_id: self.dispatch_slot(s_id))

                # Daily Pinterest pin (mainstream brand only; no-op if disabled/unconfigured)
                try:
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        pin_target = json.load(f).get("marketing_channels", {}).get("main_brand", {}).get("pinterest", {}).get("daily_slot_time", "12:00")
                except Exception:
                    pin_target = "12:00"
                if current_time >= pin_target and not self.state.get("pinterest_posted_today"):
                    print(f"[Herald Scheduler] Target time {pin_target} reached for Pinterest daily pin. Triggering automated dispatch...")
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self.dispatch_pinterest_daily)

                # Autonomous newsletter dispatch, retry, and Commander alerting (Dispensary
                # Deals, Studio Wire, Creator Pulse, Creator Blueprint) - verifies ACTUAL
                # delivery every pass instead of trusting a one-shot "launched" flag.
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._monitor_and_remediate_publications)

                # Pipe 3 - Autonomous AI Model Content Engine: same verify/retry/alert
                # pattern, once per day at CONTENT_ENGINE_SCHEDULE_TIME.
                await loop.run_in_executor(None, self._monitor_and_remediate_content_engine)

            except asyncio.CancelledError:
                self.is_running = False
                break
            except Exception as e:
                logger.error(f"[Herald Scheduler] Error in loop: {e}")

# Global singleton
herald_scheduler = HeraldScheduler()
