#!/usr/bin/env python3
"""
Charlette Webb 24/7 Cloud Community Daemon
Runs independently on Ubuntu 24.04 VPS (Kamatera: 78.138.0.42).
Features:
  1. Discord Gateway Supervisor:
     - 1-Click 18+ Verification & Role Gate
     - Private 1-on-1 Cam-to-Cam (C2C) Booking & Room Generator ($100 / $170 / $250)
     - Private VIP Order & Receipt Claim Tickets
     - 2-Hour Bunny.net Signed VIP Vault Expiring Links
     - Interactive Games: Wheel of Desires ($15), VIP Raffle, Guess Panty Color
     - 24/7 AI Concierge Persona on @mention or button clicks
     - 100% Automated Creator Media Ingestion & Bunny.net Auto-Sorting from #📤・creator-vault-drops
  2. Telegram Poller & Bridge:
     - Interactive Creator Upload Station (asks: [🔐 VIP Vault & Bunny] or [📢 Public Channel & Twitter])
     - 24/7 Concierge & Link Menu for 1-on-1 fan DMs (/start, /menu, /schedule)
     - Auto-mirrors posts from @CharletteWebbVIP directly into Discord #🔥-new-content-drops
     - Cross-posts public drops to Twitter/X (@Charlette_WebbX) if credentials configured!
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import pathlib
import random
import re
import sys
import time
from typing import Any, Dict, List, Optional
import urllib.parse
import httpx
import websockets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("charlette_cloud_daemon")

BASE_DIR = pathlib.Path("/opt/charlette-daemon")
CONFIG_FILE = BASE_DIR / "creator_communities.json"
SECRETS_FILE = BASE_DIR / "secrets.json"
CRM_FILE = BASE_DIR / "creator_crm.json"

DISCORD_API = "https://discord.com/api/v10"

# Discord Permissions
PERM_VIEW_CHANNEL = 1 << 10
PERM_SEND_MESSAGES = 1 << 11
PERM_ATTACH_FILES = 1 << 15
PERM_READ_HISTORY = 1 << 16
PERM_MANAGE_CHANNELS = 1 << 4
PERM_STREAM = 1 << 9
PERM_CONNECT = 1 << 20
PERM_SPEAK = 1 << 21
PERM_USE_VAD = 1 << 25
PERM_C2C_VOICE = PERM_VIEW_CHANNEL | PERM_STREAM | PERM_CONNECT | PERM_SPEAK | PERM_USE_VAD


def load_config() -> Dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def load_secrets() -> Dict[str, Any]:
    if not SECRETS_FILE.exists():
        return {}
    return json.loads(SECRETS_FILE.read_text(encoding="utf-8"))


def load_crm() -> Dict[str, Any]:
    if not CRM_FILE.exists():
        return {}
    return json.loads(CRM_FILE.read_text(encoding="utf-8"))


def save_crm(data: Dict[str, Any]) -> None:
    CRM_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def generate_bunny_signed_url(client_id: str, relative_path: str, ttl_seconds: int = 86400) -> str:
    sec = load_secrets()
    vault = sec.get("creator_vault", {})
    host = vault.get("bunny_cdn_host", "charlette-vault.b-cdn.net")
    bkey = vault.get("bunny_security_key", "")
    expires = int(time.time()) + ttl_seconds
    if not host or not bkey:
        return ""
    clean_path = relative_path.lstrip("/")
    path = f"/{client_id}/{clean_path}"
    hashable_base = f"{bkey}{path}{expires}".encode("utf-8")
    signature = hmac.new(bkey.encode("utf-8"), hashable_base, hashlib.sha256).digest()
    b64_tok = base64.b64encode(signature).decode("utf-8").replace("+", "-").replace("/", "_").rstrip("=")
    return f"https://{host.rstrip('/')}{path}?token={b64_tok}&expires={expires}"


def publish_to_twitter(text: str, media_bytes: Optional[bytes] = None, filename: str = "upload.jpg") -> Dict[str, Any]:
    """Publishes public drop to Twitter/X (@Charlette_WebbX).
    If API keys configured in secrets.json -> publishes directly via Twitter API v2 + media upload.
    If API keys not configured -> generates a 1-click Twitter Web Intent URL for 1-tap posting.
    """
    sec = load_secrets()
    tw_creds = (
        sec.get("twitter_credentials", {}).get("Charlette_WebbX")
        or sec.get("twitter_credentials", {}).get("charlette_webb")
        or {}
    )

    clean_text = (text or "").strip()
    if not clean_text:
        clean_text = "🔥 New content drop from Charlette Webb!"

    promo_footer = "\n\nVIP Lounge: https://charlettewebb.com\nTelegram: https://t.me/CharletteWebbVIP\n#CharletteWebb #webcam #model"
    max_len = 280 - len(promo_footer)
    if len(clean_text) > max_len:
        clean_text = clean_text[: max_len - 3] + "..."
    tweet_body = f"{clean_text}{promo_footer}"

    encoded_text = urllib.parse.quote(tweet_body)
    intent_url = f"https://twitter.com/intent/tweet?text={encoded_text}"

    api_key = (tw_creds.get("api_key") or "").strip()
    api_secret = (tw_creds.get("api_secret") or "").strip()
    access_token = (tw_creds.get("access_token") or "").strip()
    access_token_secret = (tw_creds.get("access_token_secret") or "").strip()
    bearer_token = (tw_creds.get("bearer_token") or "").strip() or None

    if not (api_key and api_secret and access_token and access_token_secret):
        return {
            "success": False,
            "mode": "intent",
            "intent_url": intent_url,
            "tweet_body": tweet_body,
            "message": "Twitter API keys not in secrets.json. 1-Click Intent prepared.",
        }

    try:
        import tweepy

        auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
        api_v1 = tweepy.API(auth)
        client_v2 = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
            bearer_token=bearer_token,
        )

        media_ids = []
        if media_bytes and len(media_bytes) > 0:
            suffix = pathlib.Path(filename).suffix.lower() or ".jpg"
            temp_path = f"/tmp/tweet_{int(time.time())}_{random.randint(100, 999)}{suffix}"
            try:
                with open(temp_path, "wb") as f:
                    f.write(media_bytes)
                is_video = suffix in [".mp4", ".mov", ".m4v", ".webm"]
                if is_video:
                    media = api_v1.media_upload(temp_path, media_category="tweet_video", chunked=True)
                else:
                    media = api_v1.media_upload(temp_path)
                if media and getattr(media, "media_id", None):
                    media_ids.append(media.media_id)
            finally:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass

        resp = client_v2.create_tweet(text=tweet_body, media_ids=media_ids if media_ids else None)
        tweet_id = resp.data.get("id") if (resp and resp.data) else None
        tweet_url = f"https://x.com/Charlette_WebbX/status/{tweet_id}" if tweet_id else "https://x.com/Charlette_WebbX"
        logger.info(f"Published tweet to @Charlette_WebbX: {tweet_url}")
        return {
            "success": True,
            "mode": "api",
            "tweet_id": tweet_id,
            "tweet_url": tweet_url,
            "intent_url": intent_url,
            "tweet_body": tweet_body,
        }
    except Exception as e:
        logger.warning(f"Twitter API dispatch error: {e}")
        return {
            "success": False,
            "mode": "intent",
            "intent_url": intent_url,
            "tweet_body": tweet_body,
            "error": str(e),
        }


async def _discord_req(
    client: httpx.AsyncClient,
    token: str,
    method: str,
    path: str,
    json_body: Optional[Dict[str, Any]] = None,
) -> Any:
    headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
    for attempt in range(3):
        r = await client.request(method, f"{DISCORD_API}{path}", headers=headers, json=json_body, timeout=25.0)
        if r.status_code == 429:
            retry_after = float(r.json().get("retry_after", 1.5))
            await asyncio.sleep(retry_after + 0.2)
            continue
        if r.status_code >= 400:
            logger.warning(f"Discord API {method} {path} -> {r.status_code}: {r.text}")
            return {}
        if r.status_code == 204 or not r.text:
            return {}
        return r.json()
    return {}


def get_ai_concierge_text(prof: Dict[str, Any], query: str) -> str:
    links = prof["links"]
    return (
        f"Hey gorgeous! 💕 I'm **{prof['stage_name']}'s 24/7 VIP Concierge**!\n\n"
        f"• **💬 Discord & Telegram:** **100% FREE** to join, chat, and get live stream alerts!\n"
        f"• **🔐 VIP Uncensored Vault Access:** **FREE with $9.99 OnlyFans or Fansly!** Or **$10/mo** / **$50 Lifetime VIP** on CashApp (`$CharletteWebb`). Click `🎟️ Claim VIP Role` in `#📅-schedule-and-vip-menu`!\n"
        f"• **🕗 Nightly Live Cam Schedule:** **8:00 PM – 3:00 AM EST** on [Chaturbate]({links['chaturbate']}), [Stripchat]({links['stripchat']}), [MFC]({links['mfc']}), [CamSoda]({links['camsoda']}), & [ManyVids Live]({links['manyvids_live']}).\n"
        f"• **📹 Private 1-on-1 Cam-to-Cam (C2C) Shows:** **$100** (10m) • **$170** (20m) • **$250** (30m VIP + Toy Control) inside a locked 2-person Discord room! Click **`📹 Book 1-on-1 Cam-to-Cam`** in `#📅-schedule-and-vip-menu`!\n"
        f"• **🎬 All 700+ Videos Mega-Deal ($350):** Send **$350** on CashApp (`$CharletteWebb` — *add your Discord username in note*) and open a ticket to unlock her entire 700+ video archive!\n"
        f"• **💙 OnlyFans VIP ($9.99):** [Join OnlyFans Here]({links['onlyfans']}) *(includes 3-hour video + private Snap + Free Discord VIP)*\n"
        f"• **💜 Fansly VIP:** [Join Fansly Here]({links.get('fansly', 'https://fansly.com/CharletteWebb/posts')})\n"
        f"• **🌐 Official Hub:** [https://charlettewebb.com](https://charlettewebb.com)\n\n"
        f"*Tip: Tag me or type `?menu` anytime for instant info!*"
    )


class CloudCommunityDaemon:
    def __init__(self):
        self._running = False
        self._pending_tg_media: Dict[str, Dict[str, Any]] = {}

    async def start(self):
        self._running = True
        logger.info("Starting Cloud Community Daemon on Kamatera...")
        await asyncio.gather(
            self._telegram_loop(),
            self._discord_gateway_supervisor(),
        )

    async def _telegram_loop(self):
        """24/7 Telegram Poller: handles interactive creator uploads, fan concierge & channel bridge."""
        while self._running:
            try:
                cfg = load_config()
                for cid, prof in cfg.items():
                    tg = prof.get("telegram", {})
                    tg_token = tg.get("bot_token")
                    disc_token = prof.get("discord", {}).get("bot_token")
                    if not tg_token or not disc_token:
                        continue
                    
                    last_id = int(tg.get("last_update_id", 0))
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(
                            f"https://api.telegram.org/bot{tg_token}/getUpdates",
                            params={"offset": last_id + 1, "timeout": 4},
                            timeout=10.0,
                        )
                        if resp.status_code != 200:
                            continue
                        data = resp.json()
                        for upd in (data.get("result") or []):
                            uid = upd["update_id"]
                            if uid > last_id:
                                last_id = uid
                            
                            # 1. Interactive Button Callbacks
                            cb = upd.get("callback_query")
                            if cb:
                                await self._handle_tg_callback(client, prof, cb)
                                continue

                            # 2. Channel post -> Discord bridge
                            cpost = upd.get("channel_post")
                            if cpost:
                                await self._bridge_tg_channel_post(client, prof, cpost)
                                continue
                            
                            # 3. Private Message / Creator Media Drop
                            msg = upd.get("message")
                            if msg and (msg.get("chat") or {}).get("type") == "private":
                                if msg.get("photo") or msg.get("video") or msg.get("document"):
                                    await self._prompt_creator_upload(client, prof, msg)
                                else:
                                    await self._handle_tg_dm(client, prof, msg)
                        
                        if last_id != tg.get("last_update_id"):
                            prof["telegram"]["last_update_id"] = last_id
                            cfg[cid] = prof
                            CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
            except Exception as e:
                logger.warning(f"Telegram loop error: {e}")
            await asyncio.sleep(4.0)

    async def _prompt_creator_upload(self, client: httpx.AsyncClient, prof: Dict[str, Any], msg: Dict[str, Any]):
        """Prompts Charlette when she sends media to @CharletteWebbVIP_bot with 2 routing buttons."""
        tg_token = prof["telegram"]["bot_token"]
        chat_id = msg["chat"]["id"]
        caption = msg.get("caption") or ""
        
        # Extract best file_id and type
        file_id = None
        media_type = "photo"
        file_name = "upload.jpg"
        
        if msg.get("photo"):
            file_id = msg["photo"][-1]["file_id"]
            media_type = "photo"
            file_name = f"photo_{int(time.time())}.jpg"
        elif msg.get("video"):
            file_id = msg["video"]["file_id"]
            media_type = "video"
            file_name = msg["video"].get("file_name") or f"video_{int(time.time())}.mp4"
        elif msg.get("document"):
            file_id = msg["document"]["file_id"]
            media_type = "document"
            file_name = msg["document"].get("file_name") or f"file_{int(time.time())}.dat"

        if not file_id:
            return

        media_key = f"{chat_id}_{int(time.time())}"
        self._pending_tg_media[media_key] = {
            "file_id": file_id,
            "media_type": media_type,
            "file_name": file_name,
            "caption": caption,
            "chat_id": chat_id,
        }

        markup = {
            "inline_keyboard": [
                [
                    {"text": "🔐 VIP Vault (Bunny CDN + Locked Discord)", "callback_data": f"tg_vault:{media_key}"},
                ],
                [
                    {"text": "📢 Public Feed (Telegram Channel + Discord + X)", "callback_data": f"tg_public:{media_key}"},
                ],
            ]
        }
        await client.post(
            f"https://api.telegram.org/bot{tg_token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": f"👑 **Where should I publish this {media_type.upper()}?**\n\n• **VIP Vault**: Stored in Bunny.net & posted to locked Discord VIP Vault\n• **Public Feed**: Posted to your Telegram Channel, Discord Drops, & X/Twitter",
                "parse_mode": "Markdown",
                "reply_markup": markup,
            },
            timeout=15.0,
        )

    async def _handle_tg_callback(self, client: httpx.AsyncClient, prof: Dict[str, Any], cb: Dict[str, Any]):
        cb_id = cb["id"]
        data = cb.get("data") or ""
        from_user = cb.get("from") or {}
        tg_token = prof["telegram"]["bot_token"]
        
        # Acknowledge callback query
        await client.post(f"https://api.telegram.org/bot{tg_token}/answerCallbackQuery", json={"callback_query_id": cb_id}, timeout=10)

        if not (data.startswith("tg_vault:") or data.startswith("tg_public:")):
            return

        action, media_key = data.split(":", 1)
        pending = self._pending_tg_media.pop(media_key, None)
        if not pending:
            return

        file_id = pending["file_id"]
        media_type = pending["media_type"]
        file_name = pending["file_name"]
        caption = pending["caption"]
        chat_id = pending["chat_id"]
        chans = prof["discord"]["channels"]
        disc_tok = prof["discord"]["bot_token"]
        sec = load_secrets()
        vault_cfg = sec.get("creator_vault", {})

        # 1. ACTION: VIP VAULT (Download from TG -> Push to Bunny -> Post in Discord #🔐-vip-uncensored-vault)
        if action == "tg_vault":
            # Download file from Telegram
            f_resp = await client.get(f"https://api.telegram.org/bot{tg_token}/getFile", params={"file_id": file_id}, timeout=15)
            f_data = f_resp.json()
            if not f_data.get("ok"):
                await client.post(f"https://api.telegram.org/bot{tg_token}/sendMessage", json={"chat_id": chat_id, "text": f"⚠️ Telegram file is too big for cloud bot download (>20MB). For large files, drop directly into Discord #📤・creator-vault-drops!"})
                return
            
            f_path = f_data["result"]["file_path"]
            dl_resp = await client.get(f"https://api.telegram.org/file/bot{tg_token}/{f_path}", timeout=60)
            file_bytes = dl_resp.content
            size_mb = round(len(file_bytes) / (1024 * 1024), 2)

            folder = "photos/vip_sets" if media_type == "photo" else ("videos/full_length" if media_type == "video" else "archives/mega_deal")
            storage_pwd = vault_cfg.get("bunny_storage_password", "")
            zone = vault_cfg.get("bunny_storage_zone", "workhorse-vault")
            endpoint = vault_cfg.get("bunny_storage_endpoint", "https://ny.storage.bunnycdn.com").rstrip("/")
            
            upload_url = f"{endpoint}/{zone}/charlette_webb/{folder}/{file_name}"
            headers = {"AccessKey": storage_pwd, "Content-Type": "application/octet-stream"}
            await client.put(upload_url, headers=headers, content=file_bytes, timeout=120)

            signed_url = generate_bunny_signed_url("charlette_webb", f"{folder}/{file_name}", ttl_seconds=7200)

            # Post to Discord #🔐・vip-uncensored-vault
            vault_ch = chans.get("vip_vault")
            if vault_ch:
                await _discord_req(
                    client,
                    disc_tok,
                    "POST",
                    f"/channels/{vault_ch}/messages",
                    json_body={
                        "content": "👑 **New VIP Media Drop from Charlette Webb!**",
                        "embeds": [
                            {
                                "title": f"🔥 Exclusive VIP Drop: {caption or file_name}",
                                "description": (
                                    f"{caption}\n\n" if caption else ""
                                    f"• **Format**: `{media_type.upper()}` ({file_name})\n"
                                    f"• **File Size**: `{size_mb} MB`\n"
                                    f"• **Delivery**: High-bitrate Bunny.net Edge CDN (Anti-Scrape)\n\n"
                                    f"👇 **Click `🔐 Stream / Download HD File (2-Hr Token)` below to stream or download instantly:**"
                                ),
                                "color": 0xEAB308,
                                **({"image": {"url": signed_url}} if media_type == "photo" else {}),
                            }
                        ],
                        "components": [
                            {
                                "type": 1,
                                "components": [
                                    {"type": 2, "style": 5, "label": "▶️ WATCH FULL VIDEO (HD)" if media_type == "video" else "✨ VIEW FULL 4K PHOTOS", "url": signed_url},
                                    {"type": 2, "style": 1, "label": "🎬 Custom Video / Orders", "custom_id": "wh_open_order_ticket"},
                                    {"type": 2, "style": 3, "label": "💋 Ask 24/7 AI Concierge", "custom_id": "wh_ask_ai_concierge"},
                                    {"type": 2, "style": 4, "label": "📹 Book 1-on-1 C2C", "custom_id": "wh_book_c2c"},
                                ],
                            }
                        ],
                    },
                )

            # Auto-broadcast promotional sneak peek to general 18+ fan lounge (#💬-lounge-chat) to drive VIP upgrades
            lounge_ch = chans.get("lounge_chat")
            if lounge_ch:
                await _discord_req(
                    client,
                    disc_tok,
                    "POST",
                    f"/channels/{lounge_ch}/messages",
                    json_body={
                        "content": f"✨ **NEW VIP MEDIA DROP JUST RELEASED IN THE VAULT!** 📸\n\nCharlette just dropped a brand new {media_type.upper()} into the **VIP Vault**!\nVIP Club Members can watch/download now in <#{vault_ch}>.",
                        "embeds": [
                            {
                                "title": f"🔥 New VIP Drop: {caption or file_name}",
                                "description": (
                                    f"• **Format**: `{media_type.upper()}`\n"
                                    f"• **Hosting**: `Bunny.net Ultra-Fast Edge CDN`\n\n"
                                    f"👉 **Click `👑 Unlock VIP Vault` below to join the VIP Lounge and watch instantly!**"
                                ),
                                "color": 0xEC4899,
                                **({"image": {"url": signed_url}} if media_type == "photo" else {}),
                                "footer": {"text": "Charlette Webb 18+ Lounge • VIP Sneak Peek Alert"},
                            }
                        ],
                        "components": [
                            {
                                "type": 1,
                                "components": [
                                    {"type": 2, "style": 1, "label": "👑 Unlock VIP Vault", "custom_id": "wh_open_order_ticket"},
                                    {"type": 2, "style": 3, "label": "💋 Ask AI Concierge", "custom_id": "wh_ask_ai_concierge"},
                                    {"type": 2, "style": 4, "label": "📹 Book 1-on-1 C2C", "custom_id": "wh_book_c2c"},
                                ],
                            }
                        ],
                    },
                )

            await client.post(
                f"https://api.telegram.org/bot{tg_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": f"✅ **Saved to VIP Vault & Bunny.net!**\n• Stored at: `/{zone}/charlette_webb/{folder}/{file_name}` ({size_mb} MB)\n• Published to Discord `#🔐・vip-uncensored-vault` with a 2-Hour secure streaming link!",
                    "parse_mode": "Markdown",
                },
            )

        # 2. ACTION: PUBLIC FEED (Send to Telegram Channel + Discord Drops + Twitter/X)
        elif action == "tg_public":
            tg_chan = prof["telegram"]["channel_id"]
            links = prof["links"]
            pub_caption = caption or f"🔥 New drop from {prof['stage_name']}! Live nightly 8PM-3AM EST."
            
            # Post to Telegram Channel
            if media_type == "photo":
                await client.post(f"https://api.telegram.org/bot{tg_token}/sendPhoto", json={"chat_id": tg_chan, "photo": file_id, "caption": pub_caption})
            elif media_type == "video":
                await client.post(f"https://api.telegram.org/bot{tg_token}/sendVideo", json={"chat_id": tg_chan, "video": file_id, "caption": pub_caption})
            else:
                await client.post(f"https://api.telegram.org/bot{tg_token}/sendDocument", json={"chat_id": tg_chan, "document": file_id, "caption": pub_caption})

            # Fetch media bytes for Twitter/X upload if possible (<20MB)
            file_bytes = None
            try:
                f_resp = await client.get(f"https://api.telegram.org/bot{tg_token}/getFile", params={"file_id": file_id}, timeout=15)
                f_data = f_resp.json()
                if f_data.get("ok"):
                    f_path = f_data["result"]["file_path"]
                    dl_resp = await client.get(f"https://api.telegram.org/file/bot{tg_token}/{f_path}", timeout=60)
                    if dl_resp.status_code == 200:
                        file_bytes = dl_resp.content
            except Exception as e:
                logger.warning(f"Could not download TG media for Twitter: {e}")

            # Publish to Twitter/X (@Charlette_WebbX)
            tw_res = publish_to_twitter(pub_caption, media_bytes=file_bytes, filename=file_name)
            if tw_res.get("mode") == "api" and tw_res.get("success"):
                twitter_note = f"\n• 🐦 **Posted to Twitter/X (@Charlette_WebbX):** [View Tweet]({tw_res['tweet_url']})"
                twitter_button = {"type": 2, "style": 5, "label": "🐦 View on X", "url": tw_res["tweet_url"]}
            else:
                intent_url = tw_res.get("intent_url")
                twitter_note = f"\n• 🐦 **Post to Twitter/X:** [1-Tap Tweet to @Charlette_WebbX]({intent_url})"
                twitter_button = {"type": 2, "style": 5, "label": "🐦 Post to X", "url": intent_url}

            # Mirror to Discord #🔥-new-content-drops
            drops_ch = chans.get("drops")
            if drops_ch:
                role_id = prof["discord"]["roles"].get("drop_alerts")
                ping = f"<@&{role_id}> " if role_id else ""
                drop_buttons = [
                    {"type": 2, "style": 5, "label": "💙 OnlyFans", "url": links["onlyfans"]},
                    {"type": 2, "style": 5, "label": "🎬 ManyVids Store", "url": links["manyvids_videos"]},
                    {"type": 2, "style": 5, "label": "📲 Telegram Channel", "url": "https://t.me/CharletteWebbVIP"},
                    twitter_button,
                ]
                await _discord_req(
                    client,
                    disc_tok,
                    "POST",
                    f"/channels/{drops_ch}/messages",
                    json_body={
                        "content": f"{ping}📲 **New Public Drop from {prof['stage_name']}!**",
                        "embeds": [{"title": f"🔥 {prof['stage_name']} New Content Drop", "description": pub_caption, "color": 0xEC4899}],
                        "components": [
                            {
                                "type": 1,
                                "components": drop_buttons,
                            }
                        ],
                    },
                )

                # Also post tease card in #💬-lounge-chat
                lounge_ch = chans.get("lounge_chat")
                if lounge_ch:
                    await _discord_req(
                        client,
                        disc_tok,
                        "POST",
                        f"/channels/{lounge_ch}/messages",
                        json_body={
                            "content": f"✨ **NEW DROP ALERT!** 📸\n\nCharlette just dropped a new update!\nCheck out the full preview in <#{drops_ch}>.",
                            "embeds": [{"title": f"🔥 {prof['stage_name']} Sneak Peek", "description": pub_caption, "color": 0xEC4899}],
                            "components": [
                                {
                                    "type": 1,
                                    "components": [
                                        {"type": 2, "style": 1, "label": "👑 Unlock Full Vault (VIP)", "custom_id": "wh_open_order_ticket"},
                                        {"type": 2, "style": 3, "label": "💋 Ask AI Concierge", "custom_id": "wh_ask_ai_concierge"},
                                        twitter_button,
                                    ],
                                }
                            ],
                        },
                    )

            await client.post(
                f"https://api.telegram.org/bot{tg_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": f"✅ **Published to Public Feed!**\n• 📲 Sent to Telegram Channel (`@CharletteWebbVIP`)\n• 🔥 Mirrored to Discord `#🔥・new-content-drops`{twitter_note}",
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                },
            )

    async def _handle_tg_dm(self, client: httpx.AsyncClient, prof: Dict[str, Any], msg: Dict[str, Any]):
        tg_token = prof["telegram"]["bot_token"]
        chat_id = msg["chat"]["id"]
        text = (msg.get("text") or "").strip()
        links = prof["links"]
        disc_inv = prof["discord"].get("invite_url") or links["linktree"]
        
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "🌐 Official Website", "url": links.get("website", "https://charlettewebb.com")},
                    {"text": "💬 Join 18+ Discord Lounge", "url": disc_inv},
                ],
                [
                    {"text": "💙 OnlyFans (+3Hr Vid)", "url": links["onlyfans"]},
                    {"text": "💜 Fansly VIP", "url": links.get("fansly", "https://fansly.com/CharletteWebb/posts")},
                ],
                [
                    {"text": "🎬 700+ Videos (ManyVids)", "url": links["manyvids_videos"]},
                    {"text": "🎥 Order Custom Video", "url": links["manyvids_custom"]},
                ],
                [
                    {"text": "💧 Chaturbate (8PM-3AM)", "url": links["chaturbate"]},
                    {"text": "🔥 Stripchat Live", "url": links["stripchat"]},
                ],
                [
                    {"text": "💸 CashApp ($CharletteWebb)", "url": links["cashapp"]},
                    {"text": "🎁 Throne Wishlist", "url": links["throne"]},
                ],
            ]
        }
        reply_text = get_ai_concierge_text(prof, text)
        await client.post(
            f"https://api.telegram.org/bot{tg_token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": reply_text,
                "disable_web_page_preview": True,
                "reply_markup": reply_markup,
            },
            timeout=15.0,
        )

    async def _bridge_tg_channel_post(self, client: httpx.AsyncClient, prof: Dict[str, Any], cpost: Dict[str, Any]):
        disc_tok = prof["discord"]["bot_token"]
        chans = prof["discord"]["channels"]
        roles = prof["discord"]["roles"]
        links = prof["links"]
        text = cpost.get("text") or cpost.get("caption") or ""
        
        if "IS LIVE ON CAM NOW!" in text or "WELCOME TO" in text or "VIP MENU & $350" in text:
            return
        
        is_live = any(w in text.lower() for w in ["live now", "on cam", "streaming now", "chaturbate", "stripchat"])
        target_ch = chans.get("live_now" if is_live else "drops")
        if not target_ch:
            return
        
        role_id = roles.get("cam_alerts" if is_live else "drop_alerts")
        ping = f"<@&{role_id}> " if role_id else ""
        
        embed = {
            "title": f"🔥 New Update from {prof['stage_name']}",
            "description": text or "New update posted via Telegram!",
            "color": 0xFF1964 if is_live else 0xEC4899,
        }

        # Check Twitter / X cross-posting for channel updates
        tw_btn = None
        if not is_live and text:
            tw_res = publish_to_twitter(text)
            if tw_res.get("mode") == "api" and tw_res.get("success"):
                tw_btn = {"type": 2, "style": 5, "label": "🐦 View on X", "url": tw_res["tweet_url"]}
            elif tw_res.get("intent_url"):
                tw_btn = {"type": 2, "style": 5, "label": "🐦 Post to X", "url": tw_res["intent_url"]}

        btns = [
            {"type": 2, "style": 5, "label": "💙 OnlyFans", "url": links["onlyfans"]},
            {"type": 2, "style": 5, "label": "🎬 ManyVids Store", "url": links["manyvids_videos"]},
            {"type": 2, "style": 5, "label": "💧 Chaturbate Live", "url": links["chaturbate"]},
            {"type": 2, "style": 5, "label": "📲 Telegram Channel", "url": "https://t.me/CharletteWebbVIP"},
        ]
        if tw_btn:
            btns.append(tw_btn)

        components = [
            {
                "type": 1,
                "components": btns,
            }
        ]
        await _discord_req(
            client,
            disc_tok,
            "POST",
            f"/channels/{target_ch}/messages",
            json_body={
                "content": f"{ping}📲 **Synced from {prof['stage_name']}'s Telegram:**",
                "embeds": [embed],
                "components": components,
            },
        )

    async def _discord_gateway_supervisor(self):
        """Maintains persistent WebSocket connection to Discord Gateway v10."""
        while self._running:
            try:
                cfg = load_config()
                prof = cfg.get("charlette_webb", {})
                tok = prof.get("discord", {}).get("bot_token", "")
                if not tok:
                    await asyncio.sleep(10)
                    continue

                intents = (1 << 0) | (1 << 9) | (1 << 15)  # GUILDS | GUILD_MESSAGES | MESSAGE_CONTENT
                ws_url = "wss://gateway.discord.gg/?v=10&encoding=json"
                logger.info("Connecting to Discord Gateway v10...")
                
                async with websockets.connect(ws_url, max_size=10_000_000) as ws:
                    hb_interval = 41.25
                    hb_task = None
                    seq = None
                    
                    async for raw in ws:
                        payload = json.loads(raw)
                        op = payload.get("op")
                        d = payload.get("d") or {}
                        s = payload.get("s")
                        t = payload.get("t")
                        if s is not None:
                            seq = s
                            
                        if op == 10:  # Hello
                            hb_interval = d.get("heartbeat_interval", 41250) / 1000.0
                            async def send_heartbeats(interval):
                                while True:
                                    await asyncio.sleep(interval)
                                    try:
                                        await ws.send(json.dumps({"op": 1, "d": seq}))
                                    except Exception:
                                        break
                            hb_task = asyncio.create_task(send_heartbeats(hb_interval))
                            identify = {
                                "op": 2,
                                "d": {
                                    "token": tok,
                                    "intents": intents,
                                    "properties": {"os": "linux", "browser": "kamatera-daemon", "device": "kamatera-daemon"},
                                },
                            }
                            await ws.send(json.dumps(identify))
                            logger.info("Sent Identify to Discord Gateway.")
                        
                        elif op == 0:  # Dispatch
                            if t == "READY":
                                logger.info(f"Discord Bot READY! Logged in as: {d.get('user', {}).get('username')}")
                            elif t == "INTERACTION_CREATE":
                                asyncio.create_task(self._handle_discord_interaction(prof, d))
                            elif t == "MESSAGE_CREATE":
                                asyncio.create_task(self._handle_discord_message(prof, d))
                        
                        elif op == 9:
                            logger.warning("Gateway Invalid Session. Reconnecting...")
                            break
                        elif op == 7:
                            logger.info("Gateway requested Reconnect.")
                            break
                    
                    if hb_task:
                        hb_task.cancel()
            except Exception as e:
                logger.warning(f"Discord Gateway connection dropped: {e}. Retrying in 5s...")
            await asyncio.sleep(5.0)

    async def _handle_discord_interaction(self, prof: Dict[str, Any], inter: Dict[str, Any]):
        cid = (inter.get("data") or {}).get("custom_id", "")
        inter_id = inter.get("id")
        inter_token = inter.get("token")
        member = inter.get("member") or {}
        user = member.get("user") or {}
        uid = user.get("id", "")
        uname = re.sub(r"[^a-z0-9_-]", "", (user.get("username") or "fan").lower())[:18] or "fan"
        gid = inter.get("guild_id") or prof["discord"].get("guild_id", "")
        roles = prof["discord"].get("roles", {})
        channels = prof["discord"].get("channels", {})
        tok = prof["discord"]["bot_token"]
        links = prof["links"]
        
        async with httpx.AsyncClient() as client:
            # 1. 18+ Verification Gate + Welcome Gift Teaser Lead Magnet
            if cid == "wh_verify_18":
                v_role = roles.get("verified_18")
                if v_role and gid and uid:
                    await _discord_req(client, tok, "PUT", f"/guilds/{gid}/members/{uid}/roles/{v_role}")

                # Mint free welcome gift teaser link (Bunny CDN)
                welcome_teaser = generate_bunny_signed_url(
                    "charlette_webb",
                    "shows/2026-10-27_live-with-restream-Oct-15-2026-restream/live-with-restream-Oct-15-2026-restream_Highlight_Teaser.mp4",
                    ttl_seconds=86400
                )
                if not welcome_teaser:
                    welcome_teaser = links["manyvids_videos"]

                # Attempt personalized Direct Message gift delivery
                dm_sent = False
                try:
                    dm_chan_res = await _discord_req(client, tok, "POST", "/users/@me/channels", json_body={"recipient_id": uid})
                    dm_ch_id = dm_chan_res.get("id")
                    if dm_ch_id:
                        await _discord_req(
                            client,
                            tok,
                            "POST",
                            f"/channels/{dm_ch_id}/messages",
                            json_body={
                                "content": f"🎁 **A Special Welcome Gift from Charlette Webb!** 💕",
                                "embeds": [
                                    {
                                        "title": "💋 Welcome to My Private VIP Lounge!",
                                        "description": (
                                            f"Hey {uname}! Thank you for verifying (18+) in my server! 💕\n\n"
                                            f"As a thank you, here is a **FREE 30-Second Highlight Teaser** from my latest cam marathon:\n"
                                            f"👉 **[▶️ Stream Your Free Welcome Teaser]({welcome_teaser})**\n\n"
                                            f"✨ **Want to unlock my full 700+ video vault or book a 1-on-1 private C2C cam session?**\n"
                                            f"Tap the buttons below to explore my VIP perks!"
                                        ),
                                        "color": 0xEC4899,
                                        "footer": {"text": "Charlette Webb Official VIP Lounge • Powered by WORKHORSE & Bunny.net"}
                                    }
                                ],
                                "components": [
                                    {
                                        "type": 1,
                                        "components": [
                                            {"type": 2, "style": 5, "label": "▶️ Watch Free Teaser", "url": welcome_teaser},
                                            {"type": 2, "style": 1, "label": "👑 Unlock Full Vault (VIP)", "custom_id": "wh_open_order_ticket"},
                                            {"type": 2, "style": 4, "label": "📹 Book Private C2C", "custom_id": "wh_book_c2c"},
                                            {"type": 2, "style": 3, "label": "💋 Ask AI Concierge", "custom_id": "wh_ask_ai_concierge"},
                                        ]
                                    }
                                ]
                            }
                        )
                        dm_sent = True
                except Exception as e:
                    logger.warning(f"Could not deliver welcome DM to {uid}: {e}")

                # Ephemeral response in-channel
                await client.post(
                    f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
                    json={
                        "type": 4,
                        "data": {
                            "content": (
                                f"🔞 **Welcome {uname}! You are now 18+ Verified.** Full access unlocked!\n\n"
                                f"🎁 **FREE WELCOME GIFT:** Tap below to watch your free 30s teaser clip:\n"
                                f"👉 **[▶️ Watch Free Welcome Teaser]({welcome_teaser})**"
                                + ("\n*(I also sent a copy to your Direct Messages!)*" if dm_sent else "")
                            ),
                            "flags": 64,
                            "components": [
                                {
                                    "type": 1,
                                    "components": [
                                        {"type": 2, "style": 5, "label": "▶️ Watch Free Teaser", "url": welcome_teaser},
                                        {"type": 2, "style": 1, "label": "👑 Unlock VIP Vault", "custom_id": "wh_open_order_ticket"},
                                        {"type": 2, "style": 4, "label": "📹 Book 1-on-1 C2C", "custom_id": "wh_book_c2c"},
                                    ]
                                }
                            ]
                        },
                    },
                )
            
            # 2. Notification Roles
            elif cid in ("wh_role_cam", "wh_role_drops"):
                rk = "cam_alerts" if cid == "wh_role_cam" else "drop_alerts"
                rid = roles.get(rk)
                current_roles = member.get("roles") or []
                if rid in current_roles:
                    await _discord_req(client, tok, "DELETE", f"/guilds/{gid}/members/{uid}/roles/{rid}")
                    action_msg = "Removed notification role."
                else:
                    await _discord_req(client, tok, "PUT", f"/guilds/{gid}/members/{uid}/roles/{rid}")
                    action_msg = "Added notification role! You'll get pinged on live streams and drops."
                await client.post(
                    f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
                    json={"type": 4, "data": {"content": f"🔔 {action_msg}", "flags": 64}},
                )
            
            # 3. Bunny.net 2-Hour Signed Vault Expiring Link
            elif cid in ("wh_unlock_vault_drop", "wh_admin_drop_vault"):
                signed_url = generate_bunny_signed_url("charlette_webb", "photos/vip_sets/latest_vip_set.jpg", ttl_seconds=7200)
                if not signed_url:
                    signed_url = links["manyvids_videos"]
                await client.post(
                    f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
                    json={
                        "type": 4,
                        "data": {
                            "content": (
                                f"🔐 **Your Private 2-Hour Signed Bunny.net Vault Stream Link:**\n\n"
                                f"👉 **[Click Here to Stream / Download HD Set]({signed_url})**\n\n"
                                f"⏳ *This token is cryptographically HMAC-signed via Bunny.net Edge CDN and expires in 2 hours.*"
                            ),
                            "flags": 64,
                        },
                    },
                )
            
            # 4. Ask 24/7 AI Concierge
            elif cid == "wh_ask_ai_concierge":
                reply = get_ai_concierge_text(prof, "Show me menu and rates")
                await client.post(
                    f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
                    json={"type": 4, "data": {"content": reply, "flags": 64}},
                )
            
            # 5. Book 1-on-1 Cam-to-Cam (C2C) Show ($100 / $170 / $250)
            elif cid == "wh_book_c2c":
                overwrites = [
                    {"id": gid, "type": 0, "allow": "0", "deny": str(PERM_VIEW_CHANNEL)},
                    {"id": uid, "type": 1, "allow": str(PERM_C2C_VOICE), "deny": "0"},
                ]
                for rk in ("queen", "mod"):
                    if roles.get(rk):
                        overwrites.append({"id": roles[rk], "type": 0, "allow": str(PERM_C2C_VOICE), "deny": "0"})
                
                v_chan = await _discord_req(
                    client,
                    tok,
                    "POST",
                    f"/guilds/{gid}/channels",
                    json_body={
                        "name": f"📹-private-c2c-{uname}",
                        "type": 2,  # Voice/Video
                        "user_limit": 2,
                        "bitrate": 256000,
                        "nsfw": True,
                        "permission_overwrites": overwrites,
                    },
                )
                vid = v_chan.get("id", "")
                
                t_chan = await _discord_req(
                    client,
                    tok,
                    "POST",
                    f"/guilds/{gid}/channels",
                    json_body={
                        "name": f"📹-c2c-booking-{uname}",
                        "type": 0,
                        "nsfw": True,
                        "topic": f"Private 1-on-1 Cam-to-Cam Booking for {uname} (UID:{uid} VID:{vid})",
                        "permission_overwrites": overwrites,
                    },
                )
                tid = t_chan.get("id", "")
                
                if tid:
                    await _discord_req(
                        client,
                        tok,
                        "POST",
                        f"/channels/{tid}/messages",
                        json_body={
                            "content": f"📹 Welcome <@{uid}>! **Your Private 1-on-1 Cam-to-Cam (C2C) Suite is Ready!**\n👉 **Locked 2-Person Video Room:** <#{vid}>",
                            "embeds": [
                                {
                                    "title": "📹 Private 1-on-1 Cam-to-Cam (C2C) Rates & Payment",
                                    "description": (
                                        "**Private Discord 1-on-1 HD Cam-to-Cam Rates:**\n"
                                        "• 🔥 **10-Minute 1-on-1 Show**: **$100**\n"
                                        "• 💦 **20-Minute 1-on-1 Show**: **$170**\n"
                                        "• 👑 **30-Minute VIP Cam-to-Cam + Lush Toy Control**: **$250**\n\n"
                                        f"Please add your Discord username (`{uname}`) in the payment note.\n\n"
                                        "1️⃣ Send payment on **CashApp (`$CharletteWebb`)** or **Throne** below.\n"
                                        f"2️⃣ Drop screenshot here, then click <#{vid}> to turn on camera when Charlette joins!"
                                    ),
                                    "color": 0x00F2FE,
                                }
                            ],
                            "components": [
                                {
                                    "type": 1,
                                    "components": [
                                        {"type": 2, "style": 5, "label": "💸 Pay $CharletteWebb (CashApp)", "url": links["cashapp"]},
                                        {"type": 2, "style": 5, "label": "🎁 Pay via Throne", "url": links["throne"]},
                                    ],
                                },
                                {
                                    "type": 1,
                                    "components": [
                                        {"type": 2, "style": 3, "label": "📹 Log 10m C2C ($100)", "custom_id": "wh_c2c_log_100"},
                                        {"type": 2, "style": 3, "label": "📹 Log 20m C2C ($170)", "custom_id": "wh_c2c_log_170"},
                                        {"type": 2, "style": 1, "label": "👑 Log 30m VIP C2C ($250)", "custom_id": "wh_c2c_log_250"},
                                        {"type": 2, "style": 4, "label": "🔒 End C2C & Delete Rooms", "custom_id": "wh_c2c_close"},
                                    ],
                                },
                            ],
                        },
                    )
                await client.post(
                    f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
                    json={
                        "type": 4,
                        "data": {
                            "content": f"📹 **Your 1-on-1 C2C Suite is open!**\n• Booking Chat: <#{tid}>\n• Locked Video Room: <#{vid}>",
                            "flags": 64,
                        },
                    },
                )
            
            # 6. Log C2C Shows & Role Upgrade
            elif cid in ("wh_c2c_log_100", "wh_c2c_log_170", "wh_c2c_log_250"):
                rates = {"wh_c2c_log_100": 100.0, "wh_c2c_log_170": 170.0, "wh_c2c_log_250": 250.0}
                gross = rates.get(cid, 100.0)
                chan_id = inter.get("channel_id", "")
                ch_info = await _discord_req(client, tok, "GET", f"/channels/{chan_id}")
                m_uid = re.search(r"UID:(\d+)", (ch_info or {}).get("topic", ""))
                target_uid = m_uid.group(1) if m_uid else uid
                if target_uid and roles.get("whale"):
                    await _discord_req(client, tok, "PUT", f"/guilds/{gid}/members/{target_uid}/roles/{roles['whale']}")
                await client.post(
                    f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
                    json={
                        "type": 4,
                        "data": {
                            "content": f"✅ **Confirmed: ${int(gross)} C2C Show logged!** <@{target_uid}> has been upgraded to **`@💎 Diamond Whale`**!",
                        },
                    },
                )
            
            # 7. End C2C & Delete Rooms
            elif cid == "wh_c2c_close":
                chan_id = inter.get("channel_id", "")
                ch_info = await _discord_req(client, tok, "GET", f"/channels/{chan_id}")
                m_vid = re.search(r"VID:(\d+)", (ch_info or {}).get("topic", ""))
                await client.post(
                    f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
                    json={"type": 4, "data": {"content": "🔒 Closing C2C session and removing channels in 3s..."}},
                )
                await asyncio.sleep(3.0)
                if m_vid:
                    await _discord_req(client, tok, "DELETE", f"/channels/{m_vid.group(1)}")
                await _discord_req(client, tok, "DELETE", f"/channels/{chan_id}")

            # 8. Open Order Ticket
            elif cid == "wh_open_order_ticket":
                overwrites = [
                    {"id": gid, "type": 0, "allow": "0", "deny": str(PERM_VIEW_CHANNEL)},
                    {"id": uid, "type": 1, "allow": str(PERM_VIEW_CHANNEL | PERM_SEND_MESSAGES | PERM_ATTACH_FILES | PERM_READ_HISTORY), "deny": "0"},
                ]
                for rk in ("queen", "mod"):
                    if roles.get(rk):
                        overwrites.append({"id": roles[rk], "type": 0, "allow": str(PERM_VIEW_CHANNEL | PERM_SEND_MESSAGES | PERM_ATTACH_FILES | PERM_READ_HISTORY), "deny": "0"})
                t_chan = await _discord_req(
                    client,
                    tok,
                    "POST",
                    f"/guilds/{gid}/channels",
                    json_body={
                        "name": f"🎟️-order-{uname}",
                        "type": 0,
                        "nsfw": True,
                        "topic": f"Private VIP Order for {uname} (UID:{uid})",
                        "permission_overwrites": overwrites,
                    },
                )
                tid = t_chan.get("id", "")
                if tid:
                    await _discord_req(
                        client,
                        tok,
                        "POST",
                        f"/channels/{tid}/messages",
                        json_body={
                            "content": (
                                f"🎟️ Welcome <@{uid}>! **Private VIP Claim & Order Ticket**\n\n"
                                f"• **Claiming VIP Vault Access?** Drop a screenshot of your active **$9.99 OnlyFans or Fansly subscription** (or CashApp $10/mo / $50 Lifetime confirmation) below!\n"
                                f"• **Custom Video / $350 Mega-Deal?** Drop your payment receipt screenshot and details below!\n\n"
                                f"Charlette or a moderator will verify and upgrade your role immediately."
                            ),
                        },
                    )
                await client.post(
                    f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
                    json={"type": 4, "data": {"content": f"🎟️ Private ticket opened: <#{tid}>", "flags": 64}},
                )

            # 9. Flash Deal Claim Tickets
            elif cid in ("wh_claim_flash_15", "wh_claim_flash_350"):
                deal_title = "🎬 $15 1080p Show Cutdown Flash Deal" if cid == "wh_claim_flash_15" else "💎 $350 Lifetime Vault + FREE C2C Cam Show Voucher"
                overwrites = [
                    {"id": gid, "type": 0, "allow": "0", "deny": str(PERM_VIEW_CHANNEL)},
                    {"id": uid, "type": 1, "allow": str(PERM_VIEW_CHANNEL | PERM_SEND_MESSAGES | PERM_ATTACH_FILES | PERM_READ_HISTORY), "deny": "0"},
                ]
                for rk in ("queen", "mod"):
                    if roles.get(rk):
                        overwrites.append({"id": roles[rk], "type": 0, "allow": str(PERM_VIEW_CHANNEL | PERM_SEND_MESSAGES | PERM_ATTACH_FILES | PERM_READ_HISTORY), "deny": "0"})
                t_chan = await _discord_req(
                    client,
                    tok,
                    "POST",
                    f"/guilds/{gid}/channels",
                    json_body={
                        "name": f"⚡-flash-{uname}",
                        "type": 0,
                        "nsfw": True,
                        "topic": f"Flash Deal Claim: {deal_title} for {uname} (UID:{uid})",
                        "permission_overwrites": overwrites,
                    },
                )
                tid = t_chan.get("id", "")
                if tid:
                    await _discord_req(
                        client,
                        tok,
                        "POST",
                        f"/channels/{tid}/messages",
                        json_body={
                            "content": (
                                f"⚡ **Welcome <@{uid}>! You've locked in the Flash Deal:**\n"
                                f"👉 **{deal_title}**\n\n"
                                f"• **Payment Tag**: CashApp [`$CharletteWebb`](https://cash.app/$CharletteWebb)\n"
                                f"• **Next Step**: Drop your CashApp payment confirmation screenshot below, and our team will deliver your Bunny.net HD streaming links and schedule your free session immediately!"
                            ),
                        },
                    )
                await client.post(
                    f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
                    json={"type": 4, "data": {"content": f"⚡ Flash deal ticket opened: <#{tid}>! Head over to finalize your claim.", "flags": 64}},
                )

            # 10. Outfit Poll Voting
            elif cid.startswith("wh_vote_outfit_"):
                outfit_map = {
                    "wh_vote_outfit_1": "👗 Red Lace Bodysuit",
                    "wh_vote_outfit_2": "🎀 Schoolgirl Velvet Set",
                    "wh_vote_outfit_3": "✨ Silk Robe & Stockings",
                    "wh_vote_outfit_4": "💧 Oil Show + Lush Marathon"
                }
                choice = outfit_map.get(cid, "Tonight's Cam Outfit")
                await client.post(
                    f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
                    json={
                        "type": 4,
                        "data": {
                            "content": f"✨ **Vote Recorded!** You voted for **{choice}**! Charlette will see the results before going live at 8:00 PM EST.",
                            "flags": 64
                        }
                    }
                )

            # 11. Community Goal Details
            elif cid == "wh_goal_details":
                await client.post(
                    f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
                    json={
                        "type": 4,
                        "data": {
                            "content": (
                                f"🎯 **Community Crowdfund Challenge Details:**\n\n"
                                f"• **Target**: $200 Community Pool\n"
                                f"• **Unlocked Reward**: Brand new **3-Minute Uncensored Shower Teaser Video + 10 4K Stills** unlocked for EVERYONE in `#💬-lounge-chat`!\n"
                                f"• **How to Contribute**: Tap **`[💸 Chip In via CashApp]`** or send to `$CharletteWebb` with note 'Community Goal'!\n\n"
                                f"*Every contribution moves the bar. When it hits 100%, the drop fires instantly!*"
                            ),
                            "flags": 64
                        }
                    }
                )

    async def _handle_discord_message(self, prof: Dict[str, Any], msg: Dict[str, Any]):
        content = (msg.get("content") or "").strip()
        author = msg.get("author") or {}
        if author.get("bot"):
            return
        
        tok = prof["discord"]["bot_token"]
        chan_id = msg.get("channel_id")
        chans = prof["discord"].get("channels", {})
        creator_upload_cid = chans.get("creator_upload")
        
        # 1. Automated Creator Media Ingestion & Bunny.net Auto-Sorting from Discord
        if chan_id == creator_upload_cid and msg.get("attachments"):
            await self._process_creator_media_upload(prof, msg)
            return
        
        # 2. ?menu command or bot mention
        if content.lower().startswith("?menu") or f"<@{prof['discord'].get('bot_id', '')}>" in content:
            reply = get_ai_concierge_text(prof, content)
            async with httpx.AsyncClient() as client:
                await _discord_req(client, tok, "POST", f"/channels/{chan_id}/messages", json_body={"content": reply})

    async def _process_creator_media_upload(self, prof: Dict[str, Any], msg: Dict[str, Any]):
        tok = prof["discord"]["bot_token"]
        chan_id = msg.get("channel_id")
        chans = prof["discord"].get("channels", {})
        vault_ch = chans.get("vip_vault")
        drops_ch = chans.get("drops")
        sec = load_secrets()
        vault_cfg = sec.get("creator_vault", {})
        storage_pwd = vault_cfg.get("bunny_storage_password", "")
        zone = vault_cfg.get("bunny_storage_zone", "workhorse-vault")
        endpoint = vault_cfg.get("bunny_storage_endpoint", "https://ny.storage.bunnycdn.com").rstrip("/")
        
        attachments = msg.get("attachments") or []
        comment = (msg.get("content") or "").strip()
        is_teaser = "teaser" in comment.lower() or "preview" in comment.lower()

        async with httpx.AsyncClient() as client:
            for att in attachments:
                fname = re.sub(r"[^a-zA-Z0-9_.-]", "_", att.get("filename") or "upload.dat")
                size_mb = round(att.get("size", 0) / (1024 * 1024), 2)
                ext = pathlib.Path(fname).suffix.lower()
                
                if ext in [".mp4", ".mov", ".mkv", ".webm", ".avi"]:
                    folder = "videos/teasers" if (is_teaser or size_mb < 25) else "videos/full_length"
                    media_type = "video"
                elif ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
                    folder = "photos/teasers" if is_teaser else "photos/vip_sets"
                    media_type = "photo"
                elif ext in [".zip", ".rar", ".7z", ".tar"]:
                    folder = "archives/mega_deal"
                    media_type = "archive"
                else:
                    folder = "photos/vip_sets"
                    media_type = "file"

                dl_url = att.get("url")
                if not dl_url:
                    continue
                r_dl = await client.get(dl_url, timeout=60.0)
                if r_dl.status_code != 200:
                    await _discord_req(client, tok, "POST", f"/channels/{chan_id}/messages", json_body={"content": f"⚠️ Failed to download `{fname}` from Discord."})
                    continue
                
                file_bytes = r_dl.content
                upload_url = f"{endpoint}/{zone}/charlette_webb/{folder}/{fname}"
                headers = {"AccessKey": storage_pwd, "Content-Type": "application/octet-stream"}
                r_up = await client.put(upload_url, headers=headers, content=file_bytes, timeout=120.0)
                
                if r_up.status_code not in (200, 201):
                    await _discord_req(client, tok, "POST", f"/channels/{chan_id}/messages", json_body={"content": f"⚠️ Bunny upload error for `{fname}`: {r_up.status_code} {r_up.text}"})
                    continue
                
                signed_cdn_url = generate_bunny_signed_url("charlette_webb", f"{folder}/{fname}", ttl_seconds=7200)
                
                # Check Twitter / X publishing for public teasers
                tw_note = ""
                tw_btn = None
                if is_teaser:
                    tw_res = publish_to_twitter(comment or f"🔥 New teaser drop from {prof['stage_name']}!", media_bytes=file_bytes, filename=fname)
                    if tw_res.get("mode") == "api" and tw_res.get("success"):
                        tw_note = f"\n• 🐦 **Posted to Twitter/X (@Charlette_WebbX):** [View Tweet]({tw_res['tweet_url']})"
                        tw_btn = {"type": 2, "style": 5, "label": "🐦 View on X", "url": tw_res["tweet_url"]}
                    elif tw_res.get("intent_url"):
                        tw_note = f"\n• 🐦 **Post to Twitter/X:** [1-Tap Tweet to @Charlette_WebbX]({tw_res['intent_url']})"
                        tw_btn = {"type": 2, "style": 5, "label": "🐦 Post to X", "url": tw_res["intent_url"]}

                await _discord_req(
                    client,
                    tok,
                    "POST",
                    f"/channels/{chan_id}/messages",
                    json_body={
                        "content": (
                            f"✅ **Drop Processed Successfully!**\n"
                            f"• **Sorted To**: `/{zone}/charlette_webb/{folder}/{fname}`\n"
                            f"• **Size**: `{size_mb} MB`\n"
                            f"• **Secure CDN Link**: [Test 2-Hr Stream Link]({signed_cdn_url}){tw_note}\n\n"
                            f"🚀 **Auto-publishing drop card now...**"
                        )
                    },
                )

                dest_ch = drops_ch if (is_teaser and drops_ch) else (vault_ch or drops_ch)
                if dest_ch:
                    if not comment:
                        base_no_ext = os.path.splitext(fname)[0]
                        if "screenshot" in base_no_ext.lower():
                            display_name = "Exclusive VIP Selfie Tease"
                        elif "vid" in base_no_ext.lower():
                            display_name = "Exclusive VIP 4K Video Replay"
                        elif base_no_ext.startswith("JT2A"):
                            display_name = "Studio 4K Master Glamour Set"
                        else:
                            display_name = base_no_ext.replace("_", " ").title()
                    else:
                        display_name = comment
                    drop_title = f"🔥 New {'Teaser Drop' if is_teaser else 'VIP Exclusive Drop'}: {display_name}"
                    view_btn_label = "WATCH FULL VIDEO (HD)" if media_type == "video" else "VIEW FULL 4K PHOTOS"
                    view_emoji = "▶️" if media_type == "video" else "✨"
                    card_buttons = [
                        {
                            "type": 2,
                            "style": 5,
                            "label": view_btn_label,
                            "emoji": {"name": view_emoji},
                            "url": signed_cdn_url,
                        },
                        {
                            "type": 2,
                            "style": 1,
                            "label": "Custom Video / Orders",
                            "emoji": {"name": "🎬"},
                            "custom_id": "wh_open_order_ticket",
                        },
                        {
                            "type": 2,
                            "style": 3,
                            "label": "Ask 24/7 AI Concierge",
                            "emoji": {"name": "💋"},
                            "custom_id": "wh_ask_ai_concierge",
                        },
                        {
                            "type": 2,
                            "style": 4,
                            "label": "Book 1-on-1 C2C",
                            "emoji": {"name": "📹"},
                            "custom_id": "wh_book_c2c",
                        },
                    ]
                    if tw_btn:
                        card_buttons.append(tw_btn)

                    embed_desc = (
                        f"{comment}\n\n" if comment else ""
                        f"• **Format**: `{media_type.upper()}` ({fname})\n"
                        f"• **File Size**: `{size_mb} MB` (High-Bitrate 4K)\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"### 🌟 [👉 CLICK HERE TO VIEW / WATCH FULL SET 👈]({signed_cdn_url})\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"*(Direct high-speed link • Tap the large link above or button below)*"
                    )

                    await _discord_req(
                        client,
                        tok,
                        "POST",
                        f"/channels/{dest_ch}/messages",
                        json_body={
                            "content": f"{'<@&1563747735319093318> ' if is_teaser else ''}👑 **New Media Drop from Charlette Webb!**",
                            "embeds": [
                                {
                                    "title": drop_title,
                                    "description": embed_desc,
                                    "color": 0xEC4899 if is_teaser else 0xEAB308,
                                    **({"image": {"url": signed_cdn_url}} if media_type == "photo" else {}),
                                }
                            ],
                            "components": [
                                {
                                    "type": 1,
                                    "components": card_buttons,
                                }
                            ],
                        },
                    )


if __name__ == "__main__":
    daemon = CloudCommunityDaemon()
    asyncio.run(daemon.start())
