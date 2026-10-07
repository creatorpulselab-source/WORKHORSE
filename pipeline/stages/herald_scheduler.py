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
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any, List, Optional

sys.path.insert(0, "F:/WORKHORSE")
from pipeline.stages.twitter_poster import TwitterPoster
from pipeline.stages.newsletter_manager import NewsletterManager

logger = logging.getLogger("workhorse.herald_scheduler")

STATE_FILE = Path("F:/WORKHORSE/workspace/daily_schedule_state.json")
LOGS_DIR = Path("F:/WORKHORSE/workspace/newsletter_logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)

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

class HeraldScheduler:
    def __init__(self, config_path: str = "F:/WORKHORSE/config.json"):
        self.config_path = config_path
        self.twitter = TwitterPoster(config_path)
        self.newsletter = NewsletterManager()
        self.is_running = False
        self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    self.state = json.load(f)
                    return self.state
            except Exception:
                pass
        self.state = {
            "last_date": str(date.today()),
            "executed_slots": [],
            "newsletters_sent_today": False,
            "history": []
        }
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
                    # Dynamically look for latest verified ComfyUI 5070 Ti visual to attach to root tweet
                    media_paths = None
                    try:
                        # Strictly enforce brand-specific visual isolation
                        pub_key = "creator_pulse" if "pulse" in handle.lower() else "studio_wire"
                        vis_path = self.newsletter.get_latest_comfy_visual(pub_key)
                        if vis_path and Path(vis_path).exists():
                            media_paths = [str(vis_path)]
                            print(f"[Herald Scheduler] Brand visual selected for @{handle} -> {vis_path.name} (from {vis_path.parent.name})")
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

    def dispatch_newsletters_all(self) -> Dict[str, Any]:
        """Trigger full morning dispatch across all 4 publications."""
        self._check_day_rollover()
        res = self.newsletter.trigger_dispatch()
        self.state["newsletters_sent_today"] = True
        self.state["history"].append({
            "type": "newsletter_dispatch",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "result": res
        })
        self._save_state()
        return res

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

                # Autonomous Morning Trend Radar Sweep (08:00 AM)
                if current_time >= "08:00" and not self.state.get("radar_sweep_done_today"):
                    print("[Herald Scheduler] 08:00 AM window reached: Triggering autonomous morning trend radar sweep...")
                    try:
                        from pipeline.stages.trend_researcher import trend_researcher
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(None, trend_researcher.run_daily_radar_sweep)
                        self.state["radar_sweep_done_today"] = True
                        self._save_state()
                    except Exception as e:
                        print(f"[Herald Scheduler] Radar sweep error: {e}")

                # Check each slot
                for s in DAILY_SLOTS:
                    slot_id = s["slot_id"]
                    target = s["target_time"]
                    
                    # If target time reached and not yet executed today
                    if current_time >= target and slot_id not in self.state.get("executed_slots", []):
                        print(f"[Herald Scheduler] Target time {target} reached for {slot_id}. Triggering automated dispatch...")
                        # In background thread
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(None, lambda s_id=slot_id: self.dispatch_slot(s_id))

                        # If morning slot, also dispatch newsletters
                        if slot_id == "slot_1_morning" and not self.state.get("newsletters_sent_today"):
                            await loop.run_in_executor(None, self.dispatch_newsletters_all)

            except asyncio.CancelledError:
                self.is_running = False
                break
            except Exception as e:
                logger.error(f"[Herald Scheduler] Error in loop: {e}")

# Global singleton
herald_scheduler = HeraldScheduler()
