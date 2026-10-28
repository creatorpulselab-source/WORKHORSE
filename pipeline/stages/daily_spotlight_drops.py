"""
WORKHORSE Daily Spotlight & Bundle Drop Engine
Automates daily promotional drops to Discord #🔥-new-content-drops from the 747 catalog.
Author: Antigravity / WORKHORSE Pipeline
"""

import os
import sys
import json
import random
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from stages.cloud_daemon import get_secrets, _discord_req
    from stages.catalog_teaser_extractor import extract_stills_and_teaser
except ImportError:
    from cloud_daemon import get_secrets, _discord_req
    from catalog_teaser_extractor import extract_stills_and_teaser

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("daily_spotlight")

BUNDLES_FILE = Path("F:/WORKHORSE/cam_shows/charlette_catalog_bundles.json")
SCRATCH_DIR = Path("F:/WORKHORSE/cam_shows/daily_drops")


def load_bundles() -> Dict[str, List[Dict[str, Any]]]:
    if not BUNDLES_FILE.exists():
        return {}
    with open(BUNDLES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


async def post_spotlight_drop(
    video_item: Dict[str, Any],
    bundle_name: str,
    price: int = 15
) -> bool:
    """Extracts teaser assets and posts rich spotlight drop to Discord #🔥-new-content-drops."""
    sec = get_secrets()
    disc_tok = sec.get("dashboard_auth", {}).get("discord_bot_token", "")
    chans = sec.get("dashboard_auth", {}).get("discord_channel_ids", {})
    drop_ch = chans.get("new_content_drops")

    if not disc_tok or not drop_ch:
        logger.error("Discord bot token or new_content_drops channel not configured.")
        return False

    vid_id = str(video_item["id"])
    title = video_item["title"]
    size = video_item.get("size", "Full HD")

    logger.info(f"Preparing spotlight drop for video: [{vid_id}] {title} ({bundle_name})")

    # Discord Rich Embed with interactive CTA buttons
    embed = {
        "title": f"🔥 DAILY SPOTLIGHT DROP: {title}",
        "description": (
            f"**From the Official Charlette Webb Vault Series: `{bundle_name}`**\n\n"
            f"• **Format**: `1080p Ultra HD MP4`\n"
            f"• **File Size**: `{size}`\n"
            f"• **Delivery**: High-bitrate Bunny Edge CDN (Anti-Scrape, Anti-Leak)\n\n"
            f"👇 **Unlock this standalone video now or grab the entire 747-video vault below:**"
        ),
        "color": 0xFF007F,
        "fields": [
            {
                "name": "💎 Standalone Price",
                "value": f"**${price}** *(Instant Download & Stream)*",
                "inline": True
            },
            {
                "name": "👑 All-Access Upgrade",
                "value": "**$350** *(All 747 Videos + Free Cam Show)*",
                "inline": True
            }
        ],
        "footer": {
            "text": "Charlette Webb Official VIP Store • 100% Direct Delivery"
        }
    }

    components = [
        {
            "type": 1,
            "components": [
                {
                    "type": 2,
                    "style": 3,  # Green Success
                    "label": f"🔓 Buy This Video (${price})",
                    "custom_id": f"wh_buy_spotlight_{vid_id}_{price}"
                },
                {
                    "type": 2,
                    "style": 1,  # Primary Blurple
                    "label": f"📦 Unlock '{bundle_name}' Bundle",
                    "custom_id": f"wh_buy_bundle_{bundle_name[:20]}"
                },
                {
                    "type": 2,
                    "style": 5,  # Link
                    "label": "👑 All-Access Mega Vault ($350)",
                    "url": "https://cash.app/$CharletteWebb"
                }
            ]
        }
    ]

    async with httpx.AsyncClient() as client:
        resp = await _discord_req(
            client,
            disc_tok,
            "POST",
            f"/channels/{drop_ch}/messages",
            json_body={"embeds": [embed], "components": components}
        )
        if resp.status_code in (200, 201):
            logger.info(f"✅ Successfully posted spotlight drop for [{vid_id}] {title}")
            return True
        else:
            logger.error(f"Failed to post to Discord: {resp.status_code} - {resp.text}")
            return False


if __name__ == "__main__":
    bundles = load_bundles()
    if not bundles:
        print("No bundles found. Run generate_bundles.py first.")
    else:
        # Pick a random high-converting video from Shower or Squirting or Oil
        categories = ["Shower & Bath Series", "Squirting & Climax Anthology", "Oil & Body Shine"]
        chosen_cat = random.choice(categories)
        chosen_video = random.choice(bundles[chosen_cat])
        print(f"Sample chosen spotlight: {chosen_video['title']} ({chosen_cat})")
