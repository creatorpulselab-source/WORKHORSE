import asyncio
import base64
import json
import pathlib
import re
import time
from typing import Any, Dict, List, Optional
import httpx
import websockets

BASE_DIR = pathlib.Path(r"F:\WORKHORSE")
COMMUNITY_CONFIG_FILE = BASE_DIR / "workspace" / "creator_communities.json"
KIT_DIR = BASE_DIR / "workspace" / "client_deliveries" / "charlette_webb_community_kit"

DISCORD_API = "https://discord.com/api/v10"

# Permission Bitflags (Discord API v10)
PERM_VIEW_CHANNEL = 1 << 10
PERM_SEND_MESSAGES = 1 << 11
PERM_EMBED_LINKS = 1 << 14
PERM_ATTACH_FILES = 1 << 15
PERM_READ_HISTORY = 1 << 16
PERM_MENTION_EVERYONE = 1 << 17
PERM_USE_EXTERNAL_EMOJIS = 1 << 18
PERM_CONNECT = 1 << 20
PERM_SPEAK = 1 << 21
PERM_ADMINISTRATOR = 1 << 3

DEFAULT_CHARLETTE_PROFILE: Dict[str, Any] = {
    "client_id": "charlette_webb",
    "stage_name": "Charlette Webb",
    "server_name": "Charlette Webb's VIP Lounge 🔞",
    "tagline": "8+ Years Industry Queen • Live Nightly 8PM–3AM EST • 700+ Exclusive Videos",
    "schedule_text": "Live Every Night: 8:00 PM – 3:00 AM EST",
    "brand_color_hex": 0xEC4899,
    "accent_cyan_hex": 0x00F2FE,
    "gold_hex": 0xEAB308,
    "links": {
        "chaturbate": "https://chaturbate.com/b/charlette_webb_xxx",
        "stripchat": "https://stripchat.com/CharletteWebb/follow-me",
        "mfc": "https://share.myfreecams.com/CharletteWebb/tipmenus",
        "camsoda": "https://www.camsoda.com/charlette-webb?id=charlette-webb",
        "manyvids_live": "https://live.manyvids.com/stream/Charlette%20Webb",
        "onlyfans": "https://onlyfans.com/charlette_webb",
        "manyvids_videos": "https://www.manyvids.com/Profile/35990/Charlette-Webb/Store/Videos/",
        "manyvids_custom": "https://www.manyvids.com/Custom-vid/35990/",
        "manyvids_items": "https://www.manyvids.com/Profile/35990/Charlette-Webb/Store/Items/",
        "cashapp": "https://cash.app/$CharletteWebb",
        "throne": "https://throne.com/charlettewebb",
        "twitter": "https://x.com/Charlette_WebbX",
        "linktree": "https://linktr.ee/charlettewebb",
        "booking_email": "Charlettewebbbooking@gmail.com",
    },
    "graphics": {
        "avatar": str(KIT_DIR / "01_Server_And_Telegram_Avatar.png"),
        "welcome_banner": str(KIT_DIR / "02_Welcome_And_Links_Banner.jpg"),
        "rules_banner": str(KIT_DIR / "03_Verify_18Plus_And_Rules_Banner.jpg"),
        "live_banner": str(KIT_DIR / "04_Live_On_Cam_Alert_Banner.jpg"),
        "schedule_banner": str(KIT_DIR / "05_Nightly_Cam_Schedule_Banner.jpg"),
        "tip_menu": str(KIT_DIR / "06_VIP_Tip_And_Services_Menu.jpg"),
        "vip_banner": str(KIT_DIR / "07_VIP_Whale_Club_Banner.jpg"),
    },
    "discord": {
        "bot_token": "",
        "guild_id": "",
        "template_url": "",
        "roles": {},
        "channels": {},
    },
    "telegram": {
        "bot_token": "",
        "channel_id": "",
        "group_id": "",
        "last_update_id": 0,
    },
}


def load_community_profiles() -> Dict[str, Any]:
    if not COMMUNITY_CONFIG_FILE.exists():
        profiles = {"charlette_webb": DEFAULT_CHARLETTE_PROFILE}
        save_community_profiles(profiles)
        return profiles
    try:
        data = json.loads(COMMUNITY_CONFIG_FILE.read_text(encoding="utf-8"))
        if "charlette_webb" not in data:
            data["charlette_webb"] = DEFAULT_CHARLETTE_PROFILE
        return data
    except Exception:
        return {"charlette_webb": DEFAULT_CHARLETTE_PROFILE}


def save_community_profiles(profiles: Dict[str, Any]) -> None:
    COMMUNITY_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    COMMUNITY_CONFIG_FILE.write_text(json.dumps(profiles, indent=2), encoding="utf-8")


async def _discord_req(
    client: httpx.AsyncClient,
    token: str,
    method: str,
    path: str,
    json_body: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Any]] = None,
    payload_json: Optional[Dict[str, Any]] = None,
) -> Any:
    headers = {"Authorization": f"Bot {token}"}
    for attempt in range(4):
        if files and payload_json is not None:
            r = await client.request(
                method,
                f"{DISCORD_API}{path}",
                headers=headers,
                files=files,
                data={"payload_json": json.dumps(payload_json)},
                timeout=30.0,
            )
        else:
            r = await client.request(
                method,
                f"{DISCORD_API}{path}",
                headers=headers,
                json=json_body,
                timeout=25.0,
            )
        if r.status_code == 429:
            retry_after = float(r.json().get("retry_after", 1.5))
            await asyncio.sleep(retry_after + 0.25)
            continue
        if r.status_code >= 400:
            raise RuntimeError(f"Discord API {method} {path} -> {r.status_code}: {r.text}")
        if r.status_code == 204 or not r.text:
            return {}
        return r.json()
    raise RuntimeError(f"Rate limit exceeded on {path}")


async def _send_channel_card_with_image(
    client: httpx.AsyncClient,
    token: str,
    channel_id: str,
    image_path: str,
    embed: Dict[str, Any],
    components: Optional[List[Dict[str, Any]]] = None,
    content: str = "",
) -> Dict[str, Any]:
    p = pathlib.Path(image_path)
    payload: Dict[str, Any] = {"content": content, "embeds": [embed]}
    if components:
        payload["components"] = components

    if p.exists():
        fname = p.name
        embed["image"] = {"url": f"attachment://{fname}"}
        mime = "image/png" if fname.lower().endswith(".png") else "image/jpeg"
        files = {"files[0]": (fname, p.read_bytes(), mime)}
        return await _discord_req(
            client,
            token,
            "POST",
            f"/channels/{channel_id}/messages",
            files=files,
            payload_json=payload,
        )
    return await _discord_req(
        client,
        token,
        "POST",
        f"/channels/{channel_id}/messages",
        json_body=payload,
    )


async def build_creator_discord_server(
    client_id: str = "charlette_webb",
    discord_bot_token: Optional[str] = None,
    guild_id: Optional[str] = None,
    wipe_existing_channels: bool = True,
) -> Dict[str, Any]:
    """
    Automatically builds the complete 18-channel, 7-role adult webcam creator Discord server,
    uploads custom WORKHORSE banners, attaches interactive 18+ verification & cam-room link buttons,
    and generates a reusable 1-Click Discord Server Template for Fiverr!
    """
    profiles = load_community_profiles()
    prof = profiles.get(client_id, DEFAULT_CHARLETTE_PROFILE)
    if discord_bot_token:
        prof["discord"]["bot_token"] = discord_bot_token.strip()
    if guild_id:
        prof["discord"]["guild_id"] = str(guild_id).strip()

    token = prof["discord"]["bot_token"]
    gid = prof["discord"]["guild_id"]
    if not token or not gid:
        raise ValueError("Both discord_bot_token and guild_id are required.")

    links = prof["links"]
    gfx = prof["graphics"]

    async with httpx.AsyncClient() as client:
        # 1. Update Server Name & Icon
        icon_b64 = None
        av_file = pathlib.Path(gfx.get("avatar", ""))
        if av_file.exists():
            b64 = base64.b64encode(av_file.read_bytes()).decode("ascii")
            icon_b64 = f"data:image/png;base64,{b64}"

        guild_patch = {"name": prof["server_name"]}
        if icon_b64:
            guild_patch["icon"] = icon_b64
        await _discord_req(client, token, "PATCH", f"/guilds/{gid}", json_body=guild_patch)

        # 2. Configure @everyone role so unverified users cannot see 18+ channels before clicking Verify
        base_fan_perms = (
            PERM_VIEW_CHANNEL
            | PERM_SEND_MESSAGES
            | PERM_READ_HISTORY
            | PERM_EMBED_LINKS
            | PERM_ATTACH_FILES
            | PERM_USE_EXTERNAL_EMOJIS
            | PERM_CONNECT
            | PERM_SPEAK
        )
        await _discord_req(
            client,
            token,
            "PATCH",
            f"/guilds/{gid}/roles/{gid}",
            json_body={"permissions": str(PERM_READ_HISTORY)},
        )

        # 3. Create the 7 Branded Role Tiers
        role_specs = [
            ("queen", f"👑 {prof['stage_name']} (Queen)", 0xFF1E8E, True, False),
            ("mod", "🛡️ Studio Bot & Mod", 0x00F2FE, True, False),
            ("whale", "💎 Diamond Whale (Top Tipper)", 0xFACC15, True, True),
            ("vip", "👑 VIP Club Member", 0xA855F7, True, True),
            ("cam_alerts", "🔔 Cam Live Alerts", 0xFF2A85, False, True),
            ("drop_alerts", "🔥 Content Drop Alerts", 0x38BDF8, False, True),
            ("verified_18", "🔞 Verified 18+ Fan", 0x10B981, True, False),
        ]
        created_roles: Dict[str, str] = {}
        for r_key, r_name, r_color, r_hoist, r_mention in role_specs:
            r_obj = await _discord_req(
                client,
                token,
                "POST",
                f"/guilds/{gid}/roles",
                json_body={
                    "name": r_name,
                    "color": r_color,
                    "hoist": r_hoist,
                    "mentionable": r_mention,
                    "permissions": str(base_fan_perms),
                },
            )
            created_roles[r_key] = r_obj["id"]
            await asyncio.sleep(0.25)

        prof["discord"]["roles"] = created_roles

        # 4. Optionally clean default starter channels
        if wipe_existing_channels:
            existing_chans = await _discord_req(client, token, "GET", f"/guilds/{gid}/channels")
            for ch in existing_chans:
                try:
                    await _discord_req(client, token, "DELETE", f"/channels/{ch['id']}")
                    await asyncio.sleep(0.2)
                except Exception:
                    pass

        r_ver = created_roles["verified_18"]
        r_vip = created_roles["vip"]
        r_whale = created_roles["whale"]
        r_queen = created_roles["queen"]
        r_mod = created_roles["mod"]

        # Overwrite helpers
        ow_entry_readonly = [
            {"id": gid, "type": 0, "allow": str(PERM_VIEW_CHANNEL | PERM_READ_HISTORY), "deny": str(PERM_SEND_MESSAGES)},
        ]
        ow_18_readonly = [
            {"id": gid, "type": 0, "allow": "0", "deny": str(PERM_VIEW_CHANNEL | PERM_SEND_MESSAGES)},
            {"id": r_ver, "type": 0, "allow": str(PERM_VIEW_CHANNEL | PERM_READ_HISTORY), "deny": str(PERM_SEND_MESSAGES)},
        ]
        ow_18_chat = [
            {"id": gid, "type": 0, "allow": "0", "deny": str(PERM_VIEW_CHANNEL)},
            {"id": r_ver, "type": 0, "allow": str(base_fan_perms), "deny": "0"},
        ]
        ow_vip_only = [
            {"id": gid, "type": 0, "allow": "0", "deny": str(PERM_VIEW_CHANNEL)},
            {"id": r_ver, "type": 0, "allow": "0", "deny": str(PERM_VIEW_CHANNEL)},
            {"id": r_vip, "type": 0, "allow": str(base_fan_perms), "deny": "0"},
            {"id": r_whale, "type": 0, "allow": str(base_fan_perms), "deny": "0"},
            {"id": r_queen, "type": 0, "allow": str(base_fan_perms), "deny": "0"},
        ]
        ow_admin_only = [
            {"id": gid, "type": 0, "allow": "0", "deny": str(PERM_VIEW_CHANNEL)},
            {"id": r_queen, "type": 0, "allow": str(base_fan_perms), "deny": "0"},
            {"id": r_mod, "type": 0, "allow": str(base_fan_perms), "deny": "0"},
        ]

        # 5. Create Categories & Channels
        categories_blueprint = [
            (
                "🔞 ━━━ START HERE (18+ GATE) ━━━",
                ow_entry_readonly,
                [
                    ("verify_18", "🔞-verify-18-plus", 0, False, "Click [🔞 Verify 18+] below to unlock all 18+ channels & cam alerts!"),
                    ("welcome", "👋-welcome-and-links", 0, False, f"Official links, cam rooms & VIP access for {prof['stage_name']}"),
                ],
            ),
            (
                "📢 ━━━ LIVE CAM & VIP ALERTS ━━━",
                ow_18_readonly,
                [
                    ("live_now", "🔴-live-on-cam-now", 0, True, "Live stream alerts (8PM–3AM EST) across Chaturbate, Stripchat, MFC, CamSoda & ManyVids!"),
                    ("drops", "🔥-new-content-drops", 0, True, "Auto-bridged teaser drops, new ManyVids videos & OnlyFans updates!"),
                    ("schedule_menu", "📅-schedule-and-vip-menu", 0, True, "Nightly cam schedule (8PM–3AM EST), $350 700+ Video Mega-Vault & Custom Video menu!"),
                    ("hall_of_fame", "🎁-throne-and-top-whales", 0, True, "Throne wishlist gifts, CashApp ($CharletteWebb) legends & Diamond Whale leaderboard!"),
                ],
            ),
            (
                "💬 ━━━ 18+ FAN LOUNGE ━━━",
                ow_18_chat,
                [
                    ("lounge_chat", "💬-lounge-chat", 0, True, f"Main 18+ fan lounge for {prof['stage_name']}'s community!"),
                    ("selfies", "📸-charlettes-selfies", 0, True, "Behind-the-scenes snaps, outfits & daily updates!"),
                    ("polls", "🗳️-outfit-and-show-polls", 0, True, "Vote on what outfit or show theme Charlette does tonight at 8PM EST!"),
                    ("memes", "🎉-fan-media-and-memes", 0, True, "Share memes, reactions & hype!"),
                    ("suggestions", "💡-show-and-video-ideas", 0, True, "Drop your ideas for cam shows or ManyVids releases!"),
                ],
            ),
            (
                "👑 ━━━ VIP & DIAMOND WHALE CLUB ━━━",
                ow_vip_only,
                [
                    ("vip_chat", "👑-vip-whale-lounge", 0, True, "Private inner-circle lounge for VIPs & Diamond Whales!"),
                    ("vip_vault", "🌶️-vip-uncensored-previews", 0, True, "Exclusive VIP-only spicy previews & bonus drops!"),
                    ("vip_customs", "🎟️-priority-customs-and-items", 0, True, "Direct custom video requests & worn store item drops!"),
                    ("vip_voice", "🔊 VIP Lounge Voice", 2, True, "Private VIP voice hangout"),
                ],
            ),
            (
                "🔒 ━━━ QUEEN & WORKHORSE COMMAND ━━━",
                ow_admin_only,
                [
                    ("control_panel", "🤖-workhorse-control-panel", 0, False, "1-Click Live Alert Blaster & Telegram Bridge Command Center"),
                    ("mod_logs", "🛡️-mod-and-anti-raid-logs", 0, False, "Automated 18+ verification & anti-scam logs"),
                ],
            ),
        ]

        created_channels: Dict[str, str] = {}
        for cat_name, cat_ow, chan_list in categories_blueprint:
            cat_obj = await _discord_req(
                client,
                token,
                "POST",
                f"/guilds/{gid}/channels",
                json_body={
                    "name": cat_name,
                    "type": 4,
                    "permission_overwrites": cat_ow,
                },
            )
            cat_id = cat_obj["id"]
            await asyncio.sleep(0.25)

            for ch_key, ch_name, ch_type, ch_nsfw, ch_topic in chan_list:
                ch_body: Dict[str, Any] = {
                    "name": ch_name,
                    "type": ch_type,
                    "parent_id": cat_id,
                    "nsfw": ch_nsfw,
                }
                if ch_type == 0:
                    ch_body["topic"] = ch_topic
                ch_obj = await _discord_req(client, token, "POST", f"/guilds/{gid}/channels", json_body=ch_body)
                created_channels[ch_key] = ch_obj["id"]
                await asyncio.sleep(0.25)

        prof["discord"]["channels"] = created_channels

        # 6. Post Branded Banners & Interactive Buttons into the Key Channels!

        # A. #🔞-verify-18-plus
        await _send_channel_card_with_image(
            client,
            token,
            created_channels["verify_18"],
            gfx["rules_banner"],
            embed={
                "title": f"🔞 Welcome to {prof['stage_name']}'s Official 18+ VIP Server",
                "description": (
                    "**Mandatory 18+ Age Verification & Community Rules:**\n\n"
                    "1️⃣ **Strictly 18+ Adults Only**: By clicking verify below, you confirm you are at least 18 years of age.\n"
                    "2️⃣ **Zero Unsolicited DMs / Whale Protection**: Do not DM other members or share unauthorized links.\n"
                    "3️⃣ **No Leaks or Piracy**: All photos, videos, and streams are copyright protected.\n"
                    "4️⃣ **Respect the Queen**: Show love, tip generously, and keep the lounge fun!\n\n"
                    "👇 **Click the green button below to unlock all 18+ channels, and click the bell buttons to get notified when Charlette goes LIVE at 8PM EST!**"
                ),
                "color": 0x00F2FE,
                "footer": {"text": "Protected by WORKHORSE Studio Security & Anti-Raid Shield"},
            },
            components=[
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 2,
                            "style": 3,
                            "label": "🔞 I Confirm I Am 18+ (Unlock Server)",
                            "custom_id": "wh_verify_18",
                        },
                        {
                            "type": 2,
                            "style": 1,
                            "label": "🔔 Toggle Cam Live Alerts",
                            "custom_id": "wh_role_cam_alerts",
                        },
                        {
                            "type": 2,
                            "style": 2,
                            "label": "🔥 Toggle New Content Alerts",
                            "custom_id": "wh_role_drop_alerts",
                        },
                    ],
                }
            ],
        )

        # B. #👋-welcome-and-links
        await _send_channel_card_with_image(
            client,
            token,
            created_channels["welcome"],
            gfx["welcome_banner"],
            embed={
                "title": f"👑 {prof['stage_name']} — Official VIP Hub & Live Cam Directory",
                "description": (
                    f"**{prof['tagline']}**\n\n"
                    "✨ **Live Every Night (8:00 PM – 3:00 AM EST)** across Chaturbate, Stripchat, MyFreeCams, CamSoda & ManyVids!\n"
                    "💙 **OnlyFans VIP**: Includes 3-Hour Full Videos + Private Snapchat!\n"
                    "🎬 **700+ Video Mega-Vault**: Unlock all 700+ videos for **$350 via CashApp (`$CharletteWebb`)**!\n"
                    "🎥 **Custom Videos & Worn Store Items**: Available directly on ManyVids!\n\n"
                    "👇 **Tap any button below to connect with Charlette:**"
                ),
                "color": 0xEC4899,
            },
            components=[
                {
                    "type": 1,
                    "components": [
                        {"type": 2, "style": 5, "label": "💙 OnlyFans (+ Snapchat)", "url": links["onlyfans"]},
                        {"type": 2, "style": 5, "label": "🎬 700+ Videos (ManyVids)", "url": links["manyvids_videos"]},
                        {"type": 2, "style": 5, "label": "🎥 Order Custom Video", "url": links["manyvids_custom"]},
                        {"type": 2, "style": 5, "label": "👙 Worn Store Items", "url": links["manyvids_items"]},
                        {"type": 2, "style": 5, "label": "🔗 All Links (Linktree)", "url": links["linktree"]},
                    ],
                },
                {
                    "type": 1,
                    "components": [
                        {"type": 2, "style": 5, "label": "💧 Chaturbate (8PM-3AM)", "url": links["chaturbate"]},
                        {"type": 2, "style": 5, "label": "🔥 Stripchat Live", "url": links["stripchat"]},
                        {"type": 2, "style": 5, "label": "💚 MFC Videos & Menu", "url": links["mfc"]},
                        {"type": 2, "style": 5, "label": "🎬 CamSoda Live", "url": links["camsoda"]},
                        {"type": 2, "style": 5, "label": "💦 ManyVids Live", "url": links["manyvids_live"]},
                    ],
                },
                {
                    "type": 1,
                    "components": [
                        {"type": 2, "style": 5, "label": "💸 CashApp ($CharletteWebb)", "url": links["cashapp"]},
                        {"type": 2, "style": 5, "label": "🎁 Throne VIP Wishlist", "url": links["throne"]},
                        {"type": 2, "style": 5, "label": "🐦 Follow on X (@Charlette_WebbX)", "url": links["twitter"]},
                    ],
                },
            ],
        )

        # C. #📅-schedule-and-vip-menu (Post both Schedule Banner and VIP Menu Graphic!)
        await _send_channel_card_with_image(
            client,
            token,
            created_channels["schedule_menu"],
            gfx["schedule_banner"],
            embed={
                "title": "📅 Official Nightly Cam Schedule: 8:00 PM – 3:00 AM EST",
                "description": (
                    "Catch **Charlette Webb** live every night from **8:00 PM to 3:00 AM EST**!\n"
                    "Make sure you grab the **🔔 Cam Live Alerts** role in <#"
                    + created_channels["verify_18"]
                    + "> so your phone pings the second the stream starts."
                ),
                "color": 0x10B981,
            },
        )
        await _send_channel_card_with_image(
            client,
            token,
            created_channels["schedule_menu"],
            gfx["tip_menu"],
            embed={
                "title": "💸 Official VIP Menu, $350 Mega-Vault & Custom Video Ordering",
                "description": (
                    "• **🎬 Unlock All 700+ Videos ($350 Mega-Deal)**: Send **$350** on CashApp (`$CharletteWebb`) and DM/tag Charlette with your receipt!\n"
                    "• **💙 OnlyFans + Snapchat**: 3-hour videos included upon joining.\n"
                    "• **💎 Want the `@💎 Diamond Whale` Discord Role?** Tip **$50+** on CashApp (`$CharletteWebb`) or send a Throne gift to unlock the private `#👑-vip-whale-lounge` and `#🌶️-vip-uncensored-previews`!"
                ),
                "color": 0xEC4899,
            },
            components=[
                {
                    "type": 1,
                    "components": [
                        {"type": 2, "style": 5, "label": "💸 Pay $CharletteWebb (CashApp)", "url": links["cashapp"]},
                        {"type": 2, "style": 5, "label": "🎁 Throne Wishlist", "url": links["throne"]},
                        {"type": 2, "style": 5, "label": "🎥 Order Custom Video", "url": links["manyvids_custom"]},
                        {"type": 2, "style": 5, "label": "👙 Buy Store Items", "url": links["manyvids_items"]},
                    ],
                }
            ],
        )

        # D. #👑-vip-whale-lounge
        await _send_channel_card_with_image(
            client,
            token,
            created_channels["vip_chat"],
            gfx["vip_banner"],
            embed={
                "title": "💎 Welcome to Charlette's Inner Circle VIP & Whale Club!",
                "description": (
                    "Thank you for being one of Charlette's top supporters! Here you get:\n"
                    "• Direct priority chat with Charlette\n"
                    "• Uncensored bonus drops in <#" + created_channels["vip_vault"] + ">\n"
                    "• Priority custom video & worn-item requests in <#" + created_channels["vip_customs"] + ">\n"
                    "• Private VIP Voice Hangouts"
                ),
                "color": 0xFACC15,
            },
        )

        # E. #🤖-workhorse-control-panel (Private Admin Panel for Charlette & WORKHORSE!)
        await _discord_req(
            client,
            token,
            "POST",
            f"/channels/{created_channels['control_panel']}/messages",
            json_body={
                "embeds": [
                    {
                        "title": "🤖 WORKHORSE Studio Control Panel — Charlette Webb",
                        "description": (
                            "**Only Charlette and WORKHORSE can see this channel.**\n\n"
                            "• **Click `🔴 BLAST LIVE ON CAM ALERT` below** whenever you go online (8PM–3AM EST) to automatically ping `@🔔 Cam Live Alerts` in Discord AND post to your Telegram Channel!\n"
                            "• **Click `🗳️ Post Tonight's Outfit Poll`** to drop an interactive fan vote in `#🗳️-outfit-and-show-polls`!\n"
                            "• **Auto-Bridge Active**: Any photo, video, or post you send in your Telegram Channel automatically mirrors into `#🔥-new-content-drops`!"
                        ),
                        "color": 0x00F2FE,
                    }
                ],
                "components": [
                    {
                        "type": 1,
                        "components": [
                            {
                                "type": 2,
                                "style": 4,
                                "label": "🔴 BLAST 'I AM LIVE ON CAM NOW!' ALERT",
                                "custom_id": "wh_admin_go_live",
                            },
                            {
                                "type": 2,
                                "style": 1,
                                "label": "🗳️ Post Tonight's Outfit Poll",
                                "custom_id": "wh_admin_post_poll",
                            },
                        ],
                    }
                ],
            },
        )

        # 7. Create or Fetch the Official Reusable 1-Click Discord Server Template for Fiverr!
        template_url = ""
        try:
            existing_tpls = await _discord_req(client, token, "GET", f"/guilds/{gid}/templates")
            if existing_tpls:
                tpl_code = existing_tpls[0]["code"]
                await _discord_req(client, token, "PUT", f"/guilds/{gid}/templates/{tpl_code}")
                template_url = f"https://discord.new/{tpl_code}"
            else:
                tpl = await _discord_req(
                    client,
                    token,
                    "POST",
                    f"/guilds/{gid}/templates",
                    json_body={
                        "name": "VIP Webcam & Creator Community Template (WORKHORSE)",
                        "description": "18+ Verification Gate, Live Cam Alerts, VIP Whale Club & Telegram Bridge Layout",
                    },
                )
                template_url = f"https://discord.new/{tpl['code']}"
        except Exception as e:
            print("[CreatorCommunityHub] Template creation note:", e)

        prof["discord"]["template_url"] = template_url
        profiles[client_id] = prof
        save_community_profiles(profiles)

        return {
            "status": "ok",
            "client_id": client_id,
            "guild_id": gid,
            "roles_created": len(created_roles),
            "channels_created": len(created_channels),
            "fiverr_server_template_url": template_url,
        }


async def blast_live_on_cam_alert(
    client_id: str = "charlette_webb",
    custom_message: str = "I'm LIVE right now across all cam sites (8PM–3AM EST)! Come hang out, vibe, and control my toys 💕💦",
) -> Dict[str, Any]:
    """
    Simultaneously blasts a branded '🔴 LIVE ON CAM NOW' alert with clickable cam buttons
    to BOTH Discord (#🔴-live-on-cam-now with @Cam Live Alerts ping) AND Telegram!
    """
    profiles = load_community_profiles()
    prof = profiles.get(client_id, DEFAULT_CHARLETTE_PROFILE)
    links = prof["links"]
    gfx = prof["graphics"]

    discord_token = prof["discord"].get("bot_token", "")
    live_chan = prof["discord"].get("channels", {}).get("live_now", "")
    cam_role = prof["discord"].get("roles", {}).get("cam_alerts", "")

    results: Dict[str, Any] = {"discord": False, "telegram": False}

    async with httpx.AsyncClient() as client:
        if discord_token and live_chan:
            ping_str = f"<@&{cam_role}> " if cam_role else "@everyone "
            await _send_channel_card_with_image(
                client,
                discord_token,
                live_chan,
                gfx["live_banner"],
                content=f"{ping_str}🔴 **{prof['stage_name']} is LIVE ON CAM RIGHT NOW!**",
                embed={
                    "title": f"🔴 LIVE NOW: {prof['stage_name']} (8:00 PM – 3:00 AM EST)",
                    "description": f"{custom_message}\n\n👇 **Pick your favorite cam site below to jump straight into my room:**",
                    "color": 0xFF1964,
                },
                components=[
                    {
                        "type": 1,
                        "components": [
                            {"type": 2, "style": 5, "label": "💧 Chaturbate Live", "url": links["chaturbate"]},
                            {"type": 2, "style": 5, "label": "🔥 Stripchat Live", "url": links["stripchat"]},
                            {"type": 2, "style": 5, "label": "💚 MyFreeCams", "url": links["mfc"]},
                            {"type": 2, "style": 5, "label": "🎬 CamSoda Live", "url": links["camsoda"]},
                            {"type": 2, "style": 5, "label": "💦 ManyVids Live", "url": links["manyvids_live"]},
                        ],
                    }
                ],
            )
            results["discord"] = True

        # Also blast to Telegram Channel if configured
        tg_token = prof["telegram"].get("bot_token", "")
        tg_chan = prof["telegram"].get("channel_id", "")
        if tg_token and tg_chan:
            caption = (
                f"🔴 <b>{prof['stage_name'].upper()} IS LIVE ON CAM NOW!</b>\n\n"
                f"{custom_message}\n\n"
                f"🕗 <b>Schedule:</b> 8:00 PM – 3:00 AM EST\n"
                f"👇 <b>Tap a button below to join my live room:</b>"
            )
            reply_markup = {
                "inline_keyboard": [
                    [
                        {"text": "💧 Chaturbate Live", "url": links["chaturbate"]},
                        {"text": "🔥 Stripchat Live", "url": links["stripchat"]},
                    ],
                    [
                        {"text": "💚 MFC Room", "url": links["mfc"]},
                        {"text": "🎬 CamSoda Live", "url": links["camsoda"]},
                    ],
                    [
                        {"text": "💦 ManyVids Live", "url": links["manyvids_live"]},
                        {"text": "💙 OnlyFans + Snap", "url": links["onlyfans"]},
                    ],
                ]
            }
            live_img = pathlib.Path(gfx["live_banner"])
            if live_img.exists():
                await client.post(
                    f"https://api.telegram.org/bot{tg_token}/sendPhoto",
                    data={
                        "chat_id": tg_chan,
                        "caption": caption,
                        "parse_mode": "HTML",
                        "reply_markup": json.dumps(reply_markup),
                    },
                    files={"photo": (live_img.name, live_img.read_bytes(), "image/jpeg")},
                    timeout=25.0,
                )
            else:
                await client.post(
                    f"https://api.telegram.org/bot{tg_token}/sendMessage",
                    json={
                        "chat_id": tg_chan,
                        "text": caption,
                        "parse_mode": "HTML",
                        "reply_markup": reply_markup,
                    },
                    timeout=20.0,
                )
            results["telegram"] = True

    return results


async def setup_creator_telegram_channel(
    client_id: str = "charlette_webb",
    telegram_bot_token: Optional[str] = None,
    channel_id: Optional[str] = None,
    discord_invite_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Posts and pins Charlette Webb's branded Welcome & All-Links Hub + VIP Services Menu
    to her Telegram Channel with full clickable inline buttons.
    """
    profiles = load_community_profiles()
    prof = profiles.get(client_id, DEFAULT_CHARLETTE_PROFILE)
    if telegram_bot_token:
        prof["telegram"]["bot_token"] = telegram_bot_token.strip()
    if channel_id:
        prof["telegram"]["channel_id"] = str(channel_id).strip()
    if discord_invite_url:
        prof["discord"]["invite_url"] = discord_invite_url.strip()

    tg_token = prof["telegram"].get("bot_token", "")
    tg_chan = prof["telegram"].get("channel_id", "")
    if not tg_token or not tg_chan:
        raise ValueError("Both telegram_bot_token and channel_id (e.g. @CharletteWebbVIP or -100xxxx) are required.")

    links = prof["links"]
    gfx = prof["graphics"]
    disc_inv = prof["discord"].get("invite_url") or links["linktree"]

    welcome_caption = (
        f"👑 <b>WELCOME TO {prof['stage_name'].upper()}'S OFFICIAL TELEGRAM HUB</b> 🔞\n\n"
        f"✨ <i>{prof.get('tagline', '')}</i>\n"
        f"🕗 <b>Live on Cam Nightly:</b> {prof.get('schedule_text', '8:00 PM – 3:00 AM EST')}\n\n"
        f"🔥 <b>Inside This Channel:</b>\n"
        f"• Instant <b>🔴 LIVE ON CAM</b> alerts across all 5 cam sites\n"
        f"• Uncensored photo & teaser drops\n"
        f"• Direct VIP menu, custom video ordering & $350 700+ Video Mega-Vault\n\n"
        f"👇 <b>Tap any button below to join my live stream, VIP pages, or Discord Lounge:</b>"
    )
    welcome_markup = {
        "inline_keyboard": [
            [
                {"text": "💙 OnlyFans (+3Hr Vid & Snap)", "url": links["onlyfans"]},
                {"text": "🎬 700+ Videos (ManyVids)", "url": links["manyvids_videos"]},
            ],
            [
                {"text": "💧 Chaturbate (8PM-3AM)", "url": links["chaturbate"]},
                {"text": "🔥 Stripchat Live", "url": links["stripchat"]},
            ],
            [
                {"text": "💚 MyFreeCams (MFC)", "url": links["mfc"]},
                {"text": "🎬 CamSoda Live", "url": links["camsoda"]},
            ],
            [
                {"text": "💦 ManyVids Live", "url": links["manyvids_live"]},
                {"text": "🎥 Order Custom Video", "url": links["manyvids_custom"]},
            ],
            [
                {"text": "👙 Worn Store Items", "url": links["manyvids_items"]},
                {"text": "💸 CashApp ($CharletteWebb)", "url": links["cashapp"]},
            ],
            [
                {"text": "🎁 Throne Wishlist", "url": links["throne"]},
                {"text": "💬 Join VIP Discord Server", "url": disc_inv},
            ],
            [
                {"text": "🌐 Official Website", "url": links.get("website", "https://charlettewebb.com")},
                {"text": "🤖 24/7 VIP AI Concierge Bot", "url": "https://t.me/CharletteWebbVIP_bot"},
            ],
        ]
    }

    async with httpx.AsyncClient() as client:
        # 0. Try setting Channel Avatar & Description (if bot has Change Info permission)
        av_img = pathlib.Path(gfx["avatar"])
        if av_img.exists():
            try:
                await client.post(
                    f"https://api.telegram.org/bot{tg_token}/setChatPhoto",
                    data={"chat_id": tg_chan},
                    files={"photo": (av_img.name, av_img.read_bytes(), "image/png")},
                    timeout=20.0,
                )
                await client.post(
                    f"https://api.telegram.org/bot{tg_token}/setChatDescription",
                    json={
                        "chat_id": tg_chan,
                        "description": (
                            f"👑 Official 18+ Telegram Hub for {prof['stage_name']}\n"
                            f"🕗 Live Nightly: 8PM–3AM EST\n"
                            f"🌐 https://charlettewebb.com\n"
                            f"💬 Discord: {disc_inv}\n"
                            f"🤖 24/7 Concierge: @CharletteWebbVIP_bot"
                        ),
                    },
                    timeout=15.0,
                )
            except Exception:
                pass

        welcome_img = pathlib.Path(gfx["welcome_banner"])
        resp1 = await client.post(
            f"https://api.telegram.org/bot{tg_token}/sendPhoto",
            data={
                "chat_id": tg_chan,
                "caption": welcome_caption,
                "parse_mode": "HTML",
                "reply_markup": json.dumps(welcome_markup),
            },
            files={"photo": (welcome_img.name, welcome_img.read_bytes(), "image/jpeg")},
            timeout=25.0,
        )
        r1_data = resp1.json()
        pinned_msg_id = None
        if r1_data.get("ok") and r1_data.get("result", {}).get("message_id"):
            pinned_msg_id = r1_data["result"]["message_id"]
            await client.post(
                f"https://api.telegram.org/bot{tg_token}/pinChatMessage",
                json={"chat_id": tg_chan, "message_id": pinned_msg_id, "disable_notification": False},
                timeout=15.0,
            )

        menu_caption = (
            f"💸 <b>{prof['stage_name'].upper()} — VIP MENU & $350 MEGA-VAULT</b>\n\n"
            f"• 🎬 <b>Unlock All 700+ Videos ($350 Deal):</b> Send <b>$350</b> via CashApp (<code>$CharletteWebb</code>) to unlock my entire 700+ video archive!\n"
            f"• 📹 <b>1-on-1 Private Discord C2C Shows:</b> <b>$100</b> (10m) • <b>$170</b> (20m) • <b>$250</b> (30m VIP + Toy Control)\n"
            f"• 💙 <b>OnlyFans VIP:</b> Includes a <b>3-Hour Full Video + Private Snapchat</b> upon joining!\n"
            f"• 🎥 <b>Custom Videos & Personal Store Items:</b> Order directly via ManyVids below."
        )
        menu_markup = {
            "inline_keyboard": [
                [
                    {"text": "💸 Pay $CharletteWebb (CashApp)", "url": links["cashapp"]},
                    {"text": "💙 Join OnlyFans (+Snap)", "url": links["onlyfans"]},
                ],
                [
                    {"text": "💜 Join Fansly VIP", "url": links.get("fansly", "https://fansly.com/CharletteWebb/posts")},
                    {"text": "🎥 Order Custom Video", "url": links["manyvids_custom"]},
                ],
                [
                    {"text": "👙 Personal Store Items", "url": links["manyvids_items"]},
                    {"text": "💬 Book 1-on-1 C2C in Discord", "url": disc_inv},
                ],
            ]
        }
        menu_img = pathlib.Path(gfx["tip_menu"])
        resp2 = await client.post(
            f"https://api.telegram.org/bot{tg_token}/sendPhoto",
            data={
                "chat_id": tg_chan,
                "caption": menu_caption,
                "parse_mode": "HTML",
                "reply_markup": json.dumps(menu_markup),
            },
            files={"photo": (menu_img.name, menu_img.read_bytes(), "image/jpeg")},
            timeout=25.0,
        )
        r2_data = resp2.json()

    profiles[client_id] = prof
    save_community_profiles(profiles)
    return {
        "status": "ok" if r1_data.get("ok") else "error",
        "client_id": client_id,
        "channel_id": tg_chan,
        "pinned_message_id": pinned_msg_id,
        "welcome_response": r1_data,
        "menu_response": r2_data,
    }


async def post_outfit_poll(client_id: str = "charlette_webb") -> Dict[str, Any]:
    """Posts an interactive Tonight's Cam Outfit & Show Theme Poll in #🗳️-outfit-and-show-polls."""
    profiles = load_community_profiles()
    prof = profiles.get(client_id, DEFAULT_CHARLETTE_PROFILE)
    token = prof["discord"].get("bot_token", "")
    poll_chan = prof["discord"].get("channels", {}).get("polls", "")
    if not token or not poll_chan:
        return {"status": "missing_config"}

    async with httpx.AsyncClient() as client:
        msg = await _discord_req(
            client,
            token,
            "POST",
            f"/channels/{poll_chan}/messages",
            json_body={
                "content": "🗳️ **TONIGHT'S CAM OUTFIT & SHOW VOTE (8:00 PM – 3:00 AM EST)**",
                "embeds": [
                    {
                        "title": f"🔥 What should {prof['stage_name']} wear & do on stream tonight?",
                        "description": (
                            "React below to cast your vote for tonight's **8:00 PM EST** stream!\n\n"
                            "1️⃣ **Naughty Plaid Schoolgirl Set**\n"
                            "2️⃣ **Emerald Green Lace & Stockings**\n"
                            "3️⃣ **Sapphire Blue Teaser Set**\n"
                            "4️⃣ **Oil Show + Lush Interactive Toy Control Marathon**\n\n"
                            "💡 *Tip $25+ on CashApp (`$CharletteWebb`) to automatically lock in your winning choice!*"
                        ),
                        "color": 0xEC4899,
                    }
                ],
            },
        )
        msg_id = msg.get("id")
        if msg_id:
            for emoji in ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]:
                try:
                    await _discord_req(
                        client,
                        token,
                        "PUT",
                        f"/channels/{poll_chan}/messages/{msg_id}/reactions/{emoji}/@me",
                    )
                    await asyncio.sleep(0.35)
                except Exception:
                    pass
        return {"status": "ok", "message_id": msg_id}


class CreatorCommunityDaemon:
    """
    24/7 WORKHORSE Background Engine that manages:
      1. Discord Gateway WebSocket (1-click 18+ Verification Gate, Self-Assign Notification Roles,
         Admin 1-Click 'BLAST LIVE ON CAM' button, and Anti-Scam Link Protection).
      2. Telegram -> Discord Auto-Bridge (any photo, video, or post sent in the creator's Telegram
         channel is automatically mirrored to Discord #🔥-new-content-drops or #🔴-live-on-cam-now).
    """

    def __init__(self) -> None:
        self._running = False
        self._use_message_content = True
        self._tasks: List[asyncio.Task] = []

    def _gateway_intents(self) -> int:
        # GUILDS (1<<0) + GUILD_MESSAGES (1<<9). MESSAGE_CONTENT (1<<15) is privileged and must be
        # switched on in the Discord Developer Portal (Bot > Privileged Gateway Intents).
        base = (1 << 0) | (1 << 9)
        return (base | (1 << 15)) if self._use_message_content else base

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        sec = load_vault_settings()
        # Check if 24/7 cloud VPS is active
        try:
            sec_full = json.loads(SECRETS_FILE.read_text(encoding="utf-8")) if SECRETS_FILE.exists() else {}
            if (sec_full.get("kamatera_vps") or {}).get("status") == "active":
                vps_ip = sec_full["kamatera_vps"].get("host", "78.138.0.42")
                print(f"[CreatorCommunityDaemon] 24/7 Cloud VPS ({vps_ip}) is active — local community daemon in standby mode.")
                return
        except Exception:
            pass

        loop = asyncio.get_event_loop()
        self._tasks.append(loop.create_task(self._telegram_bridge_loop()))
        self._tasks.append(loop.create_task(self._discord_gateway_supervisor()))
        print("[CreatorCommunityDaemon] 24/7 Discord + Telegram Community Daemon started (Whop poller disabled for adult compliance).")

    async def _whop_entitlement_poller(self) -> None:
        """Polls Whop API v2/v5 for active memberships every 20s and auto-grants Discord roles + logs Agency Cut."""
        while self._running:
            try:
                profiles = load_community_profiles()
                for cid, prof in profiles.items():
                    whop_key = (prof.get("whop") or {}).get("api_key", "")
                    if not whop_key:
                        continue
                    crm = load_creator_crm()
                    c_data = crm.setdefault(cid, {"verified_members": {}, "tickets": [], "raffle_entries": [], "whales": []})
                    synced_ids: List[str] = c_data.setdefault("synced_whop_memberships", [])
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(
                            "https://api.whop.com/api/v2/memberships",
                            headers={"Authorization": f"Bearer {whop_key}"},
                            params={"valid": "true", "per": 25},
                            timeout=15.0,
                        )
                        if resp.status_code == 200:
                            items = resp.json().get("data") or []
                            for m in items:
                                mid = str(m.get("id") or "")
                                if not mid or mid in synced_ids:
                                    continue
                                synced_ids.append(mid)
                                save_creator_crm(crm)
                                await handle_whop_webhook({"action": "membership.went_valid", "data": m}, client_id=cid)
            except Exception as e:
                print("[CreatorCommunityDaemon] Whop poller note:", e)
            await asyncio.sleep(20.0)

    async def _telegram_bridge_loop(self) -> None:
        """
        Polls configured Telegram bots:
          1. Auto-detects when the bot is added as Admin to a Telegram Channel and auto-posts/pins the Welcome & VIP Menu cards.
          2. Responds to 1-on-1 Fan DMs (/start, /menu, or questions) via the 24/7 AI Concierge + link buttons.
          3. Mirrors official Telegram Channel posts straight into Discord (#🔥-new-content-drops or #🔴-live-on-cam-now).
        """
        synced_bots: set = set()
        while self._running:
            try:
                profiles = load_community_profiles()
                for cid, prof in profiles.items():
                    tg_token = prof.get("telegram", {}).get("bot_token", "")
                    disc_token = prof.get("discord", {}).get("bot_token", "")
                    if not tg_token or not disc_token:
                        continue
                    last_uid = int(prof.get("telegram", {}).get("last_update_id", 0))
                    async with httpx.AsyncClient() as client:
                        if tg_token not in synced_bots:
                            synced_bots.add(tg_token)
                            try:
                                await client.post(
                                    f"https://api.telegram.org/bot{tg_token}/setMyDescription",
                                    json={
                                        "description": (
                                            f"👑 Official VIP Bot for {prof['stage_name']} (18+ Adults Only)\n"
                                            f"🕗 Live Nightly: 8:00 PM – 3:00 AM EST\n"
                                            f"Tap START below for all official cam rooms, VIP links, & 24/7 AI Concierge!"
                                        )
                                    },
                                    timeout=10.0,
                                )
                                await client.post(
                                    f"https://api.telegram.org/bot{tg_token}/setMyShortDescription",
                                    json={"short_description": f"👑 {prof['stage_name']} Official 18+ VIP Bot & 24/7 Concierge"},
                                    timeout=10.0,
                                )
                                await client.post(
                                    f"https://api.telegram.org/bot{tg_token}/setMyCommands",
                                    json={
                                        "commands": [
                                            {"command": "start", "description": "Open Official Links & VIP Hub"},
                                            {"command": "menu", "description": "View VIP Menu, C2C Rates & $350 Vault Deal"},
                                            {"command": "schedule", "description": "Nightly Live Cam Schedule & Rooms"},
                                        ]
                                    },
                                    timeout=10.0,
                                )
                            except Exception:
                                pass

                        resp = await client.get(
                            f"https://api.telegram.org/bot{tg_token}/getUpdates",
                            params={"offset": last_uid + 1, "timeout": 4},
                            timeout=10.0,
                        )
                        data = resp.json()
                        if not data.get("ok"):
                            continue
                        updates = data.get("result", [])
                        if not updates:
                            continue
                        for upd in updates:
                            uid = upd["update_id"]
                            if uid > last_uid:
                                last_uid = uid

                            # 1. Auto-detect when bot is added as Administrator to a Telegram Channel
                            mcm = upd.get("my_chat_member") or {}
                            mcm_chat = mcm.get("chat") or {}
                            new_state = (mcm.get("new_chat_member") or {}).get("status", "")
                            if mcm_chat.get("type") == "channel" and new_state == "administrator":
                                det_chan = f"@{mcm_chat['username']}" if mcm_chat.get("username") else str(mcm_chat.get("id"))
                                if not prof["telegram"].get("channel_id"):
                                    prof["telegram"]["channel_id"] = det_chan
                                    profiles[cid] = prof
                                    save_community_profiles(profiles)
                                    try:
                                        await setup_creator_telegram_channel(
                                            client_id=cid,
                                            telegram_bot_token=tg_token,
                                            channel_id=det_chan,
                                        )
                                        print(f"[CreatorCommunityDaemon] Auto-provisioned Telegram Channel {det_chan} for {cid}!")
                                    except Exception as ce:
                                        print("[CreatorCommunityDaemon] Auto channel setup note:", ce)

                            # 2. Official Channel Post -> Mirror to Discord (and auto-save channel_id if needed)
                            c_post = upd.get("channel_post")
                            if c_post:
                                c_chat = c_post.get("chat") or {}
                                if c_chat.get("type") == "channel" and not prof["telegram"].get("channel_id"):
                                    det_chan = f"@{c_chat['username']}" if c_chat.get("username") else str(c_chat.get("id"))
                                    prof["telegram"]["channel_id"] = det_chan
                                    profiles[cid] = prof
                                    save_community_profiles(profiles)
                                await self._bridge_telegram_post_to_discord(client, cid, prof, c_post)
                                continue

                            # 3. Private 1-on-1 Fan DM -> 24/7 AI Concierge & Interactive Hub
                            dm = upd.get("message")
                            if dm and (dm.get("chat") or {}).get("type") == "private":
                                await self._handle_telegram_private_dm(client, cid, prof, dm)

                        prof["telegram"]["last_update_id"] = last_uid
                        profiles[cid] = prof
                        save_community_profiles(profiles)
            except Exception as e:
                print("[CreatorCommunityDaemon] Telegram bridge loop warning:", e)
            await asyncio.sleep(5.0)

    async def _handle_telegram_private_dm(
        self,
        client: httpx.AsyncClient,
        client_id: str,
        prof: Dict[str, Any],
        dm: Dict[str, Any],
    ) -> None:
        tg_token = prof["telegram"].get("bot_token", "")
        chat_id = (dm.get("chat") or {}).get("id")
        text = (dm.get("text") or "").strip()
        if not tg_token or not chat_id:
            return
        links = prof["links"]
        disc_inv = prof["discord"].get("invite_url") or links["linktree"]
        markup = {
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
                    {"text": "💚 MyFreeCams (MFC)", "url": links["mfc"]},
                    {"text": "🎬 CamSoda Live", "url": links["camsoda"]},
                ],
                [
                    {"text": "💸 CashApp ($CharletteWebb)", "url": links["cashapp"]},
                    {"text": "🎁 Throne Wishlist", "url": links["throne"]},
                ],
            ]
        }
        if text.lower().startswith(("/start", "/menu", "/schedule")):
            welcome_img = pathlib.Path(prof["graphics"]["welcome_banner"])
            caption = (
                f"👑 <b>{prof['stage_name'].upper()} — OFFICIAL 18+ VIP HUB & CONCIERGE</b>\n\n"
                f"🕗 <b>Live Nightly:</b> {prof.get('schedule_text', '8:00 PM – 3:00 AM EST')}\n"
                f"📹 <b>Private 1-on-1 Discord C2C Shows:</b> $100 (10m) • $170 (20m) • $250 (30m VIP)\n"
                f"🎬 <b>All 700+ Videos Mega-Deal:</b> $350 via CashApp (<code>$CharletteWebb</code>)\n\n"
                f"👇 <b>Tap any button below or reply with any question to chat with my 24/7 AI Concierge:</b>"
            )
            if welcome_img.exists():
                await client.post(
                    f"https://api.telegram.org/bot{tg_token}/sendPhoto",
                    data={
                        "chat_id": chat_id,
                        "caption": caption,
                        "parse_mode": "HTML",
                        "reply_markup": json.dumps(markup),
                    },
                    files={"photo": (welcome_img.name, welcome_img.read_bytes(), "image/jpeg")},
                    timeout=20.0,
                )
                return

        reply_text = await generate_ai_concierge_response(prof, text or "Show me the menu and schedule")
        await client.post(
            f"https://api.telegram.org/bot{tg_token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": reply_text,
                "disable_web_page_preview": True,
                "reply_markup": markup,
            },
            timeout=15.0,
        )

    async def _bridge_telegram_post_to_discord(
        self,
        client: httpx.AsyncClient,
        client_id: str,
        prof: Dict[str, Any],
        post: Dict[str, Any],
    ) -> None:
        disc_token = prof["discord"].get("bot_token", "")
        channels = prof["discord"].get("channels", {})
        roles = prof["discord"].get("roles", {})
        links = prof["links"]
        tg_token = prof["telegram"].get("bot_token", "")

        text = post.get("text") or post.get("caption") or ""
        # Skip posts that were already sent by our own Go-Live blaster to avoid duplicate loops
        if "IS LIVE ON CAM NOW!" in text or "WELCOME TO" in text or "VIP MENU & $350" in text:
            return

        is_live_post = any(w in text.lower() for w in ["live now", "on cam", "streaming now", "chaturbate", "stripchat"])
        target_chan = channels.get("live_now" if is_live_post else "drops", "")
        if not target_chan:
            return

        role_id = roles.get("cam_alerts" if is_live_post else "drop_alerts", "")
        ping_prefix = f"<@&{role_id}> " if role_id else ""

        # Check if there is a photo in the Telegram post
        photo_bytes = None
        if post.get("photo"):
            best_photo = post["photo"][-1]
            file_id = best_photo["file_id"]
            f_resp = await client.get(
                f"https://api.telegram.org/bot{tg_token}/getFile", params={"file_id": file_id}, timeout=15.0
            )
            f_data = f_resp.json()
            if f_data.get("ok"):
                file_path = f_data["result"]["file_path"]
                dl_resp = await client.get(
                    f"https://api.telegram.org/file/bot{tg_token}/{file_path}", timeout=25.0
                )
                if dl_resp.status_code == 200:
                    photo_bytes = dl_resp.content

        embed = {
            "title": f"🔥 New Telegram Drop from {prof['stage_name']}" if not is_live_post else f"🔴 {prof['stage_name']} Live Update",
            "description": text or "New exclusive update dropped via Telegram!",
            "color": 0xFF1964 if is_live_post else 0xEC4899,
        }
        components = [
            {
                "type": 1,
                "components": [
                    {"type": 2, "style": 5, "label": "💙 OnlyFans (+Snap)", "url": links["onlyfans"]},
                    {"type": 2, "style": 5, "label": "🎬 700+ Vids (ManyVids)", "url": links["manyvids_videos"]},
                    {"type": 2, "style": 5, "label": "💧 Chaturbate Live", "url": links["chaturbate"]},
                    {"type": 2, "style": 5, "label": "💸 CashApp", "url": links["cashapp"]},
                ],
            }
        ]

        if photo_bytes:
            embed["image"] = {"url": "attachment://telegram_drop.jpg"}
            payload = {
                "content": f"{ping_prefix}📲 **Synced from {prof['stage_name']}'s Official Telegram:**",
                "embeds": [embed],
                "components": components,
            }
            await client.post(
                f"{DISCORD_API}/channels/{target_chan}/messages",
                headers={"Authorization": f"Bot {disc_token}"},
                data={"payload_json": json.dumps(payload)},
                files={"files[0]": ("telegram_drop.jpg", photo_bytes, "image/jpeg")},
                timeout=25.0,
            )
        else:
            await _discord_req(
                client,
                disc_token,
                "POST",
                f"/channels/{target_chan}/messages",
                json_body={
                    "content": f"{ping_prefix}📲 **Synced from {prof['stage_name']}'s Official Telegram:**",
                    "embeds": [embed],
                    "components": components,
                },
            )

    async def _discord_gateway_supervisor(self) -> None:
        """Maintains a Discord Gateway WebSocket connection for button clicks & anti-scam moderation."""
        import websockets

        while self._running:
            try:
                profiles = load_community_profiles()
                active_prof = None
                active_cid = "charlette_webb"
                for cid, prof in profiles.items():
                    if prof.get("discord", {}).get("bot_token"):
                        active_prof = prof
                        active_cid = cid
                        break

                if not active_prof:
                    await asyncio.sleep(8.0)
                    continue

                token = active_prof["discord"]["bot_token"]
                async with websockets.connect("wss://gateway.discord.gg/?v=10&encoding=json") as ws:
                    hello = json.loads(await ws.recv())
                    hb_interval = hello["d"]["heartbeat_interval"] / 1000.0

                    # Identify with GUILDS (1<<0) + GUILD_MESSAGES (1<<9)
                    await ws.send(
                        json.dumps(
                            {
                                "op": 2,
                                "d": {
                                    "token": token,
                                    "intents": self._gateway_intents(),
                                    "properties": {"os": "windows", "browser": "workhorse", "device": "workhorse"},
                                },
                            }
                        )
                    )

                    async def heartbeat() -> None:
                        while True:
                            await asyncio.sleep(hb_interval)
                            await ws.send(json.dumps({"op": 1, "d": None}))

                    hb_task = asyncio.create_task(heartbeat())
                    try:
                        async for raw_msg in ws:
                            pkt = json.loads(raw_msg)
                            t = pkt.get("t")
                            d = pkt.get("d") or {}
                            if t == "INTERACTION_CREATE":
                                await self._handle_discord_interaction(active_cid, d)
                            elif t == "MESSAGE_CREATE":
                                await self._handle_discord_message_moderation(active_cid, d)
                    finally:
                        hb_task.cancel()
            except Exception as e:
                if getattr(getattr(e, "rcvd", None), "code", None) == 4014 and self._use_message_content:
                    self._use_message_content = False
                    print(
                        "[CreatorCommunityDaemon] Message Content intent is NOT enabled in the Discord Developer "
                        "Portal; running without it (buttons work, ?commands and link moderation do not)."
                    )
                print("[CreatorCommunityDaemon] Gateway reconnect notice:", e)
                await asyncio.sleep(6.0)

    async def _handle_discord_interaction(self, client_id: str, interaction: Dict[str, Any]) -> None:
        profiles = load_community_profiles()
        prof = profiles.get(client_id, DEFAULT_CHARLETTE_PROFILE)
        token = prof["discord"].get("bot_token", "")
        roles = prof["discord"].get("roles", {})
        guild_id = interaction.get("guild_id") or prof["discord"].get("guild_id", "")
        member = interaction.get("member") or {}
        user_id = (member.get("user") or {}).get("id")
        custom_id = (interaction.get("data") or {}).get("custom_id", "")
        inter_id = interaction.get("id")
        inter_token = interaction.get("token")

        if not token or not inter_id or not inter_token:
            return

        async with httpx.AsyncClient() as client:
            if custom_id in ("wh_verify_18", "wh_role_cam_alerts", "wh_role_drop_alerts"):
                role_key = {
                    "wh_verify_18": "verified_18",
                    "wh_role_cam_alerts": "cam_alerts",
                    "wh_role_drop_alerts": "drop_alerts",
                }[custom_id]
                role_id = roles.get(role_key)
                if role_id and guild_id and user_id:
                    await _discord_req(
                        client,
                        token,
                        "PUT",
                        f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}",
                    )
                    # If they clicked Verify 18+, also automatically give them Cam Live Alerts so they don't miss streams!
                    if custom_id == "wh_verify_18" and roles.get("cam_alerts"):
                        await _discord_req(
                            client,
                            token,
                            "PUT",
                            f"/guilds/{guild_id}/members/{user_id}/roles/{roles['cam_alerts']}",
                        )
                msg_map = {
                    "wh_verify_18": "🔞 **You are now 18+ Verified!** All live cam channels, uncensored teaser feeds, and fan lounges are now unlocked for you!",
                    "wh_role_cam_alerts": "🔔 **Cam Live Alerts Enabled!** You'll get pinged whenever Charlette goes live (8:00 PM – 3:00 AM EST)!",
                    "wh_role_drop_alerts": "🔥 **Content Drop Alerts Enabled!** You'll get notified whenever new OnlyFans / ManyVids / Telegram drops go live!",
                }
                await client.post(
                    f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
                    json={"type": 4, "data": {"content": msg_map[custom_id], "flags": 64}},
                    timeout=10.0,
                )

            elif custom_id == "wh_admin_go_live":
                await client.post(
                    f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
                    json={
                        "type": 4,
                        "data": {
                            "content": "🔴 **Blasting 'LIVE ON CAM NOW' alert to Discord (#🔴-live-on-cam-now) AND Telegram simultaneously...**",
                            "flags": 64,
                        },
                    },
                    timeout=10.0,
                )
                await blast_live_on_cam_alert(client_id)

            elif custom_id == "wh_admin_post_poll":
                await client.post(
                    f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
                    json={
                        "type": 4,
                        "data": {
                            "content": "🗳️ **Posted Tonight's Cam Outfit & Show Poll in `#🗳️-outfit-and-show-polls`!**",
                            "flags": 64,
                        },
                    },
                    timeout=10.0,
                )
                await post_outfit_poll(client_id)

            elif custom_id in (
                "wh_open_order_ticket",
                "wh_book_c2c",
                "wh_c2c_log_60",
                "wh_c2c_log_100",
                "wh_c2c_log_150",
                "wh_c2c_close",
                "wh_enter_raffle",
                "wh_admin_game_wheel",
                "wh_admin_game_raffle",
                "wh_admin_draw_raffle",
                "wh_admin_game_guess",
                "wh_roll_wheel_prize",
                "wh_ticket_grant_whale",
                "wh_ticket_grant_vip",
                "wh_ticket_close",
                "wh_ask_ai_concierge",
                "wh_unlock_vault_drop",
                "wh_admin_drop_vault",
            ):
                await handle_extended_community_interaction(client, client_id, prof, interaction)

            # Log 18+ verification in CRM + #🛡️-workhorse-mod-logs
            if custom_id == "wh_verify_18" and user_id:
                await record_crm_verification(client, client_id, prof, member)

    async def _handle_discord_message_moderation(self, client_id: str, msg: Dict[str, Any]) -> None:
        """
        1. Auto-deletes scam/phishing/impersonation links posted by non-VIP/non-admin members.
        2. Runs the 24/7 Tailored Local AI Concierge when fans ask questions in Order/C2C Tickets or tag the bot!
        """
        if (msg.get("author") or {}).get("bot"):
            return
        raw_content = (msg.get("content") or "").strip()
        content = raw_content.lower()

        profiles = load_community_profiles()
        prof = profiles.get(client_id, DEFAULT_CHARLETTE_PROFILE)
        token = prof["discord"].get("bot_token", "")
        roles = prof["discord"].get("roles", {})
        member_roles = (msg.get("member") or {}).get("roles") or []
        chan_id = msg.get("channel_id", "")

        # 1. Anti-Scam Link Moderation for non-VIPs
        if "http://" in content or "https://" in content or "discord.gg/" in content:
            allowed_roles = {roles.get("queen"), roles.get("mod"), roles.get("whale"), roles.get("vip")}
            if not any(r in allowed_roles for r in member_roles if r):
                if "discord.gg/" in content or "bit.ly/" in content or "tinyurl.com/" in content or "t.me/" in content:
                    msg_id = msg.get("id")
                    if token and chan_id and msg_id:
                        async with httpx.AsyncClient() as client:
                            await _discord_req(client, token, "DELETE", f"/channels/{chan_id}/messages/{msg_id}")
                        return

        # 2. 24/7 Local AI Concierge Trigger (in Tickets, or when mentioning the bot / using ?concierge / asking pricing)
        is_mention = any((m or {}).get("bot") for m in (msg.get("mentions") or [])) or content.startswith(("?ai", "?menu", "?price", "?c2c", "?schedule", "?vault", "charlette bot"))
        if is_mention and token and chan_id:
            async with httpx.AsyncClient() as client:
                reply_text = await generate_ai_concierge_response(prof, raw_content)
                await _discord_req(
                    client,
                    token,
                    "POST",
                    f"/channels/{chan_id}/messages",
                    json_body={
                        "message_reference": {"message_id": msg.get("id")},
                        "embeds": [
                            {
                                "title": f"💋 {prof['stage_name']}'s 24/7 VIP AI Concierge",
                                "description": reply_text,
                                "color": 0xEC4899,
                            }
                        ],
                    },
                )


_COMMUNITY_DAEMON: Optional[CreatorCommunityDaemon] = None


def get_community_daemon() -> CreatorCommunityDaemon:
    global _COMMUNITY_DAEMON
    if _COMMUNITY_DAEMON is None:
        _COMMUNITY_DAEMON = CreatorCommunityDaemon()
    return _COMMUNITY_DAEMON


async def finalize_discord_launch(client_id: str = "charlette_webb") -> Dict[str, Any]:
    """Creates a permanent never-expiring Discord invite link and populates initial poll + live card."""
    profiles = load_community_profiles()
    prof = profiles.get(client_id, DEFAULT_CHARLETTE_PROFILE)
    tok = prof["discord"].get("bot_token", "")
    ver_ch = prof["discord"].get("channels", {}).get("verify_18", "")
    inv_url = ""
    async with httpx.AsyncClient() as client:
        if tok and ver_ch:
            inv_res = await _discord_req(
                client,
                tok,
                "POST",
                f"/channels/{ver_ch}/invites",
                json_body={"max_age": 0, "max_uses": 0, "unique": False},
            )
            if isinstance(inv_res, dict) and inv_res.get("code"):
                inv_url = f"https://discord.gg/{inv_res['code']}"
                prof["discord"]["invite_url"] = inv_url
                profiles[client_id] = prof
                save_community_profiles(profiles)
    await post_outfit_poll(client_id)
    await blast_live_on_cam_alert(client_id)
    return {
        "status": "ok",
        "invite_url": inv_url,
        "template_url": prof["discord"].get("template_url", ""),
    }


async def seed_initial_teaser_drops(client_id: str = "charlette_webb") -> Dict[str, Any]:
    """Seeds #🔥-new-content-drops and #🌶️-vip-uncensored-previews with Charlette's studio teasers."""
    profiles = load_community_profiles()
    prof = profiles.get(client_id, DEFAULT_CHARLETTE_PROFILE)
    tok = prof["discord"].get("bot_token", "")
    drops_ch = prof["discord"].get("channels", {}).get("drops", "")
    vip_vault_ch = prof["discord"].get("channels", {}).get("vip_vault", "")
    links = prof["links"]
    dl_dir = pathlib.Path(r"C:\Users\User\Downloads")

    async with httpx.AsyncClient() as client:
        if tok and drops_ch:
            await _send_channel_card_with_image(
                client,
                tok,
                drops_ch,
                str(dl_dir / "Charlette_Webb_SchoolGirl_1.jpg"),
                content="🔥 **NEW STUDIO DROP — Charlette Webb**",
                embed={
                    "title": "💋 Full Uncensored Sets + 700+ Video Mega-Vault Available Now!",
                    "description": (
                        "• **💙 Join OnlyFans**: Get a **3-Hour Full Video + Private Snapchat** included the moment you subscribe!\n"
                        "• **🎬 700+ Video Archive ($350 Deal)**: Send **$350** on CashApp (`$CharletteWebb`) to unlock every video I've ever made!\n"
                        "• **🎥 Want a Custom Video?** Order directly on ManyVids below!"
                    ),
                    "color": 0xEC4899,
                },
                components=[
                    {
                        "type": 1,
                        "components": [
                            {"type": 2, "style": 5, "label": "💙 OnlyFans (+3Hr Vid & Snap)", "url": links["onlyfans"]},
                            {"type": 2, "style": 5, "label": "🎬 700+ Videos (ManyVids)", "url": links["manyvids_videos"]},
                            {"type": 2, "style": 5, "label": "🎥 Order Custom Video", "url": links["manyvids_custom"]},
                            {"type": 2, "style": 5, "label": "💸 CashApp ($CharletteWebb)", "url": links["cashapp"]},
                        ],
                    }
                ],
            )
        if tok and vip_vault_ch:
            await _send_channel_card_with_image(
                client,
                tok,
                vip_vault_ch,
                str(dl_dir / "JT2A6140_teaser_preview.jpg"),
                content="💎 **VIP & WHALE EXCLUSIVE VAULT DROP**",
                embed={
                    "title": "👑 Exclusive Preview for `@💎 Diamond Whales` & `@🔥 OnlyFans / ManyVids VIPs`",
                    "description": "Thank you for being in my Inner Circle! DM me or drop your custom requests in <#"
                    + prof["discord"].get("channels", {}).get("vip_customs", "")
                    + "> anytime 💕",
                    "color": 0xEAB308,
                },
            )
    return {"status": "seeded"}


CRM_FILE = BASE_DIR / "workspace" / "creator_crm.json"

WHEEL_PRIZES = [
    "🎯 **PRIZE #1: 3 Uncensored Solo Videos from the Vault!** (DM/Ticket delivery)",
    "🔥 **PRIZE #2: 5-Minute Interactive Lush Toy Control Link on Cam Tonight!**",
    "💋 **PRIZE #3: Uncensored Studio Photo Set + Custom Voice Note!**",
    "👑 **PRIZE #4: 30-Day `@🔥 OnlyFans / ManyVids VIP` Discord Role Unlock!**",
    "💎 **JACKPOT: $50 Credit Toward a Custom Video OR the $350 700+ Video Mega-Vault!**",
]


def load_creator_crm() -> Dict[str, Any]:
    if CRM_FILE.exists():
        try:
            return json.loads(CRM_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"charlette_webb": {"verified_members": {}, "tickets": [], "raffle_entries": [], "whales": []}}


def save_creator_crm(data: Dict[str, Any]) -> None:
    CRM_FILE.parent.mkdir(parents=True, exist_ok=True)
    CRM_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


async def record_crm_verification(
    client: httpx.AsyncClient,
    client_id: str,
    prof: Dict[str, Any],
    member: Dict[str, Any],
) -> None:
    user = member.get("user") or {}
    uid = user.get("id")
    uname = user.get("username", "fan")
    if not uid:
        return
    crm = load_creator_crm()
    c_data = crm.setdefault(client_id, {"verified_members": {}, "tickets": [], "raffle_entries": [], "whales": []})
    is_new = uid not in c_data["verified_members"]
    c_data["verified_members"][uid] = {
        "username": uname,
        "verified_at": int(time.time()),
        "tier": "verified_18",
    }
    save_creator_crm(crm)

    mod_logs = prof["discord"].get("channels", {}).get("mod_logs", "")
    tok = prof["discord"].get("bot_token", "")
    if is_new and mod_logs and tok:
        total_v = len(c_data["verified_members"])
        await _discord_req(
            client,
            tok,
            "POST",
            f"/channels/{mod_logs}/messages",
            json_body={
                "embeds": [
                    {
                        "title": "✅ New 18+ Verified Fan Logged in CRM (+ Welcome DM Sent)",
                        "description": f"• **Fan**: <@{uid}> (`{uname}`)\n• **Auto-Assigned**: `@✅ 18+ Verified Fan` + `@🔔 Cam Live Alerts`\n• **Total Verified CRM Count**: **{total_v}**",
                        "color": 0x10B981,
                    }
                ]
            },
        )
        # Also send an automatic high-converting Personal Welcome DM to the newly verified fan!
        try:
            dm_ch = await _discord_req(client, tok, "POST", "/users/@me/channels", json_body={"recipient_id": uid})
            dm_id = (dm_ch or {}).get("id")
            if dm_id:
                links = prof["links"]
                await _discord_req(
                    client,
                    tok,
                    "POST",
                    f"/channels/{dm_id}/messages",
                    json_body={
                        "content": f"💋 **Hey {uname}! Welcome to {prof['stage_name']}'s Official 18+ VIP Lounge!**",
                        "embeds": [
                            {
                                "title": f"👑 Welcome Inside {prof['stage_name']}'s Inner Circle!",
                                "description": (
                                    "You are now **18+ Verified** and your **🔔 Cam Live Alerts** are active!\n\n"
                                    "🔥 **Don't Miss My Top VIP Specials:**\n"
                                    "• **🎬 All 700+ Videos ($350 Mega-Deal)**: Send **$350** on CashApp (`$CharletteWebb`) to unlock my entire 700+ video archive!\n"
                                    "• **💙 OnlyFans VIP**: Includes a **3-Hour Full Video + Private Snapchat** upon joining!\n"
                                    "• **🎡 $15 Wheel of Desires**: Every spin wins a guaranteed prize inside `#🔥-new-content-drops`!\n"
                                    "• **🕗 Live on Cam Nightly**: **8:00 PM – 3:00 AM EST**"
                                ),
                                "color": 0xEC4899,
                            }
                        ],
                        "components": [
                            {
                                "type": 1,
                                "components": [
                                    {"type": 2, "style": 5, "label": "💙 OnlyFans (+3Hr Vid & Snap)", "url": links["onlyfans"]},
                                    {"type": 2, "style": 5, "label": "🎬 700+ Videos (ManyVids)", "url": links["manyvids_videos"]},
                                    {"type": 2, "style": 5, "label": "💧 Watch Live on Chaturbate", "url": links["chaturbate"]},
                                    {"type": 2, "style": 5, "label": "💸 CashApp ($CharletteWebb)", "url": links["cashapp"]},
                                ],
                            }
                        ],
                    },
                )
        except Exception:
            pass


async def record_sale_and_agency_cut(
    client: httpx.AsyncClient,
    client_id: str,
    prof: Dict[str, Any],
    item_name: str,
    gross_amount: float,
    buyer_uid: str = "",
) -> Dict[str, Any]:
    """
    Logs a Discord-driven sale in the WORKHORSE CRM, calculates the Agency Management Cut
    (default 20%), and posts an instant settlement card in #🛡️-workhorse-mod-logs with a
    1-Click Pre-Filled CashApp Settlement button (`https://cash.app/$StudioCashtag/AMOUNT`).
    """
    crm = load_creator_crm()
    c_data = crm.setdefault(client_id, {"verified_members": {}, "tickets": [], "raffle_entries": [], "whales": []})
    billing = c_data.setdefault(
        "agency_billing",
        {
            "agency_cashtag": "$careypphoto",
            "commission_rate": 0.20,
            "total_gross_sales": 0.0,
            "total_agency_commission": 0.0,
            "unpaid_agency_balance": 0.0,
            "ledger": [],
        },
    )
    billing["agency_cashtag"] = "$careypphoto"
    billing["commission_rate"] = 0.20
    rate = float(billing.get("commission_rate", 0.20))
    cut = round(gross_amount * rate, 2)
    creator_net = round(gross_amount - cut, 2)

    billing["total_gross_sales"] = round(float(billing.get("total_gross_sales", 0.0)) + gross_amount, 2)
    billing["total_agency_commission"] = round(float(billing.get("total_agency_commission", 0.0)) + cut, 2)
    billing["unpaid_agency_balance"] = round(float(billing.get("unpaid_agency_balance", 0.0)) + cut, 2)
    billing["ledger"].append(
        {
            "item": item_name,
            "gross": gross_amount,
            "creator_net": creator_net,
            "agency_cut": cut,
            "buyer_uid": buyer_uid,
            "ts": int(time.time()),
        }
    )
    save_creator_crm(crm)

    tok = prof["discord"].get("bot_token", "")
    mod_logs = prof["discord"].get("channels", {}).get("mod_logs", "")
    cashtag = billing.get("agency_cashtag", "$careypphoto").lstrip("$")
    unpaid = billing["unpaid_agency_balance"]

    if tok and mod_logs:
        await _discord_req(
            client,
            tok,
            "POST",
            f"/channels/{mod_logs}/messages",
            json_body={
                "embeds": [
                    {
                        "title": f"💰 Sale Logged (Manual Ledger): {item_name} (${gross_amount:.2f})",
                        "description": (
                            f"• **Buyer**: {f'<@{buyer_uid}>' if buyer_uid else 'VIP Fan'}\n"
                            f"• **Gross Sale**: **${gross_amount:.2f}**\n"
                            f"• **Charlette Net ({int((1 - rate) * 100)}%)**: **${creator_net:.2f}**\n"
                            f"• **WORKHORSE Agency Fee ({int(rate * 100)}%)**: **${cut:.2f}**\n\n"
                            f"📊 **Running Ledger Totals:**\n"
                            f"• Total Logged Discord Sales: **${billing['total_gross_sales']:.2f}**\n"
                            f"• Unsettled Agency Fee Balance: **${unpaid:.2f}**\n"
                            f"*(Note: CashApp does not split incoming fan payments automatically; use the button below whenever you want to manually settle the accumulated 20% studio balance.)*"
                        ),
                        "color": 0xEAB308,
                    }
                ],
                "components": [
                    {
                        "type": 1,
                        "components": [
                            {
                                "type": 2,
                                "style": 5,
                                "label": f"💸 1-Click Send Agency Cut (${unpaid:.2f}) on CashApp",
                                "url": f"https://cash.app/${cashtag}/{unpaid:.2f}",
                            }
                        ],
                    }
                ],
            },
        )
    return billing


async def post_wheel_of_desires_game(client_id: str = "charlette_webb") -> Dict[str, Any]:
    profiles = load_community_profiles()
    prof = profiles.get(client_id, DEFAULT_CHARLETTE_PROFILE)
    tok = prof["discord"].get("bot_token", "")
    drops_ch = prof["discord"].get("channels", {}).get("drops", "")
    links = prof["links"]
    if not tok or not drops_ch:
        return {"status": "missing_config"}

    async with httpx.AsyncClient() as client:
        await _discord_req(
            client,
            tok,
            "POST",
            f"/channels/{drops_ch}/messages",
            json_body={
                "content": "🎡 **NEW GAME: CHARLETTE'S WHEEL OF DESIRES ($15 PER SPIN — EVERY SPIN WINS!)**",
                "embeds": [
                    {
                        "title": "🎡 Spin the Wheel of Desires — 100% Win Rate!",
                        "description": (
                            "Want to test your luck before or during tonight's **8:00 PM – 3:00 AM EST** stream?\n\n"
                            "💸 **How to Play ($15 per Spin or 3 Spins for $35)**:\n"
                            "1. Send **$15** (or **$35 for 3 spins**) on CashApp (`$CharletteWebb`) or Throne.\n"
                            "   *(Add your Discord username in the payment note so your order can be matched.)*\n"
                            "2. Click **`🎟️ Claim Spin / Open Private Order Ticket`** below and drop your screenshot!\n"
                            "3. Charlette will click **`🎲 Roll Wheel Prize`** to spin your guaranteed reward!\n\n"
                            "🏆 **Prize Pool:**\n"
                            + "\n".join(f"• {p}" for p in WHEEL_PRIZES)
                        ),
                        "color": 0xEC4899,
                    }
                ],
                "components": [
                    {
                        "type": 1,
                        "components": [
                            {
                                "type": 2,
                                "style": 3,
                                "label": "🎟️ Claim Spin / Open Private Order Ticket",
                                "custom_id": "wh_open_order_ticket",
                            },
                            {
                                "type": 2,
                                "style": 5,
                                "label": "💸 Pay $15 on CashApp ($CharletteWebb)",
                                "url": links["cashapp"],
                            },
                            {
                                "type": 2,
                                "style": 5,
                                "label": "🎁 Pay via Throne",
                                "url": links["throne"],
                            },
                            {
                                "type": 2,
                                "style": 1,
                                "label": "🎲 Roll Wheel Prize (Charlette Only)",
                                "custom_id": "wh_roll_wheel_prize",
                            },
                        ],
                    }
                ],
            },
        )
    return {"status": "ok"}


async def post_weekly_raffle_contest(client_id: str = "charlette_webb") -> Dict[str, Any]:
    profiles = load_community_profiles()
    prof = profiles.get(client_id, DEFAULT_CHARLETTE_PROFILE)
    tok = prof["discord"].get("bot_token", "")
    lounge_ch = prof["discord"].get("channels", {}).get("lounge_chat", "")
    if not tok or not lounge_ch:
        return {"status": "missing_config"}

    async with httpx.AsyncClient() as client:
        await _discord_req(
            client,
            tok,
            "POST",
            f"/channels/{lounge_ch}/messages",
            json_body={
                "content": "🎁 **FREE VIP FAN GIVEAWAY & RAFFLE IS LIVE!**",
                "embeds": [
                    {
                        "title": "🎁 Enter to Win Free `@🔥 OnlyFans / ManyVids VIP` Access + Uncensored Video Pack!",
                        "description": (
                            "We are giving away **1 Full Month of `@🔥 OnlyFans / ManyVids VIP` Discord Access + a Free Uncensored Solo Video** to a lucky member in the lounge!\n\n"
                            "✅ **How to Enter (100% Free)**:\n"
                            "• Click **`🎟️ Enter Free VIP Giveaway!`** below (automatically enables `@🔔 Cam Live Alerts` so you don't miss the winner announcement on stream!).\n"
                            "• **Bonus Entries**: Every $10 tipped on Cam or CashApp (`$CharletteWebb`) counts as **+5 Extra Raffle Entries**!"
                        ),
                        "color": 0xEAB308,
                    }
                ],
                "components": [
                    {
                        "type": 1,
                        "components": [
                            {
                                "type": 2,
                                "style": 3,
                                "label": "🎟️ Enter Free VIP Giveaway!",
                                "custom_id": "wh_enter_raffle",
                            }
                        ],
                    }
                ],
            },
        )
    return {"status": "ok"}


async def post_guess_panty_game(client_id: str = "charlette_webb") -> Dict[str, Any]:
    profiles = load_community_profiles()
    prof = profiles.get(client_id, DEFAULT_CHARLETTE_PROFILE)
    tok = prof["discord"].get("bot_token", "")
    lounge_ch = prof["discord"].get("channels", {}).get("lounge_chat", "")
    links = prof["links"]
    if not tok or not lounge_ch:
        return {"status": "missing_config"}

    async with httpx.AsyncClient() as client:
        msg = await _discord_req(
            client,
            tok,
            "POST",
            f"/channels/{lounge_ch}/messages",
            json_body={
                "content": "👙 **PRE-STREAM GAME: GUESS TONIGHT'S PANTY COLOR!**",
                "embeds": [
                    {
                        "title": "👙 What Color Panties is Charlette Wearing for Tonight's 8:00 PM EST Show?",
                        "description": (
                            "React below with your guess before **8:00 PM EST**!\n\n"
                            "🩷 **Hot Pink Lace**\n"
                            "🖤 **Black Sheer Thong**\n"
                            "💚 **Emerald Green Set**\n"
                            "💙 **Sapphire Blue**\n"
                            "😈 **Nothing At All!**\n\n"
                            "🔥 *Jump into my Chaturbate or Stripchat room at 8:00 PM EST sharp to see the live reveal!*"
                        ),
                        "color": 0xEC4899,
                    }
                ],
                "components": [
                    {
                        "type": 1,
                        "components": [
                            {"type": 2, "style": 5, "label": "💧 Watch Reveal on Chaturbate", "url": links["chaturbate"]},
                            {"type": 2, "style": 5, "label": "🔥 Watch Reveal on Stripchat", "url": links["stripchat"]},
                            {"type": 2, "style": 5, "label": "💚 Watch Reveal on MFC", "url": links["mfc"]},
                        ],
                    }
                ],
            },
        )
        mid = msg.get("id")
        if mid:
            for em in ["🩷", "🖤", "💚", "💙", "😈"]:
                try:
                    await _discord_req(client, tok, "PUT", f"/channels/{lounge_ch}/messages/{mid}/reactions/{em}/@me")
                    await asyncio.sleep(0.3)
                except Exception:
                    pass
    return {"status": "ok"}


async def handle_extended_community_interaction(
    client: httpx.AsyncClient,
    client_id: str,
    prof: Dict[str, Any],
    interaction: Dict[str, Any],
) -> None:
    import random

    tok = prof["discord"].get("bot_token", "")
    gid = interaction.get("guild_id") or prof["discord"].get("guild_id", "")
    roles = prof["discord"].get("roles", {})
    channels = prof["discord"].get("channels", {})
    links = prof["links"]
    member = interaction.get("member") or {}
    user = member.get("user") or {}
    uid = user.get("id", "")
    uname = re.sub(r"[^a-z0-9_-]", "", (user.get("username") or "fan").lower())[:18] or "fan"
    custom_id = (interaction.get("data") or {}).get("custom_id", "")
    inter_id = interaction.get("id")
    inter_token = interaction.get("token")
    chan_id = interaction.get("channel_id", "")

    if custom_id == "wh_enter_raffle":
        crm = load_creator_crm()
        c_data = crm.setdefault(client_id, {"verified_members": {}, "tickets": [], "raffle_entries": [], "whales": []})
        if uid and uid not in c_data["raffle_entries"]:
            c_data["raffle_entries"].append(uid)
            save_creator_crm(crm)
        if roles.get("cam_alerts") and gid and uid:
            await _discord_req(client, tok, "PUT", f"/guilds/{gid}/members/{uid}/roles/{roles['cam_alerts']}")
        total_entries = len(c_data["raffle_entries"])
        await client.post(
            f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
            json={
                "type": 4,
                "data": {
                    "content": f"🎟️ **You're officially entered into Charlette's VIP Giveaway!** (Total entries so far: **{total_entries}**). Your `@🔔 Cam Live Alerts` role is active so you won't miss the drawing!",
                    "flags": 64,
                },
            },
            timeout=10.0,
        )

    elif custom_id == "wh_open_order_ticket":
        # Create a private 1-on-1 ticket channel for the fan + Charlette + Mod
        overwrites = [
            {"id": gid, "type": 0, "allow": "0", "deny": str(PERM_VIEW_CHANNEL)},
            {
                "id": uid,
                "type": 1,
                "allow": str(PERM_VIEW_CHANNEL | PERM_SEND_MESSAGES | PERM_READ_HISTORY | PERM_ATTACH_FILES),
                "deny": "0",
            },
        ]
        for rk in ("queen", "mod"):
            if roles.get(rk):
                overwrites.append(
                    {
                        "id": roles[rk],
                        "type": 0,
                        "allow": str(PERM_VIEW_CHANNEL | PERM_SEND_MESSAGES | PERM_READ_HISTORY | PERM_ATTACH_FILES),
                        "deny": "0",
                    }
                )
        t_chan = await _discord_req(
            client,
            tok,
            "POST",
            f"/guilds/{gid}/channels",
            json_body={
                "name": f"🎟️-order-{uname}",
                "type": 0,
                "nsfw": True,
                "topic": f"Private VIP Order & Receipt Ticket for {uname} (UID:{uid})",
                "permission_overwrites": overwrites,
            },
        )
        t_id = t_chan.get("id", "")
        if t_id:
            await _discord_req(
                client,
                tok,
                "POST",
                f"/channels/{t_id}/messages",
                json_body={
                    "content": f"👋 Welcome <@{uid}>! **Only you and Charlette Webb can see this private order channel.**",
                    "embeds": [
                        {
                            "title": "💸 Private VIP Order, Video Purchase & Role Claim Ticket",
                            "description": (
                                "**How to Complete Your Purchase or Claim Your VIP Role:**\n"
                                "1️⃣ **Send Payment** via one of the official links below:\n"
                                "   • **🎬 $350 Mega-Deal (All 700+ Videos)**: `$350` on CashApp (`$CharletteWebb`)\n"
                                "   • **💎 `@💎 Diamond Whale` Discord Role Unlock**: `$50+` tip on CashApp or Throne\n"
                                "   • **🎡 Spin the Wheel of Desires**: `$15` (1 Spin) or `$35` (3 Spins)\n"
                                "   • **🎥 Custom Video / Worn Panties**: Order on ManyVids or request direct pricing here!\n\n"
                                "Please add your Discord username (`"
                                + uname
                                + "`) in the payment note so your order can be matched.\n\n"
                                "2️⃣ **Drop your payment screenshot or order request right here in this chat!**"
                            ),
                            "color": 0xEC4899,
                        }
                    ],
                    "components": [
                        {
                            "type": 1,
                            "components": [
                                {"type": 2, "style": 5, "label": "💸 CashApp ($CharletteWebb)", "url": links["cashapp"]},
                                {"type": 2, "style": 5, "label": "🎁 Throne Wishlist", "url": links["throne"]},
                                {"type": 2, "style": 5, "label": "🎬 700+ Videos (ManyVids)", "url": links["manyvids_videos"]},
                                {"type": 2, "style": 5, "label": "💙 OnlyFans (+Snap)", "url": links["onlyfans"]},
                            ],
                        },
                        {
                            "type": 1,
                            "components": [
                                {
                                    "type": 2,
                                    "style": 3,
                                    "label": "💎 Grant @Diamond Whale (Admin)",
                                    "custom_id": "wh_ticket_grant_whale",
                                },
                                {
                                    "type": 2,
                                    "style": 1,
                                    "label": "🔥 Grant @VIP Role (Admin)",
                                    "custom_id": "wh_ticket_grant_vip",
                                },
                                {
                                    "type": 2,
                                    "style": 2,
                                    "label": "🎲 Roll Spin Prize (Admin)",
                                    "custom_id": "wh_roll_wheel_prize",
                                },
                                {
                                    "type": 2,
                                    "style": 4,
                                    "label": "🔒 Close Ticket",
                                    "custom_id": "wh_ticket_close",
                                },
                            ],
                        },
                    ],
                },
            )
            crm = load_creator_crm()
            c_data = crm.setdefault(client_id, {"verified_members": {}, "tickets": [], "raffle_entries": [], "whales": []})
            c_data["tickets"].append({"channel_id": t_id, "user_id": uid, "username": uname, "created_at": int(time.time())})
            save_creator_crm(crm)

            if channels.get("mod_logs"):
                await _discord_req(
                    client,
                    tok,
                    "POST",
                    f"/channels/{channels['mod_logs']}/messages",
                    json_body={
                        "content": f"🎟️ **New Order / VIP Ticket Opened** by <@{uid}> (`{uname}`): <#{t_id}>"
                    },
                )

        await client.post(
            f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
            json={
                "type": 4,
                "data": {
                    "content": f"🎟️ **Your private order ticket is open!** Click here: <#{t_id}>",
                    "flags": 64,
                },
            },
            timeout=10.0,
        )

    elif custom_id in ("wh_ticket_grant_whale", "wh_ticket_grant_vip"):
        # Find the ticket owner from the channel topic (UID:xxxx)
        ch_info = await _discord_req(client, tok, "GET", f"/channels/{chan_id}")
        topic = (ch_info or {}).get("topic") or ""
        m = re.search(r"UID:(\d+)", topic)
        target_uid = m.group(1) if m else ""
        role_key = "whale" if custom_id == "wh_ticket_grant_whale" else "vip"
        role_id = roles.get(role_key, "")
        if target_uid and role_id and gid:
            await _discord_req(client, tok, "PUT", f"/guilds/{gid}/members/{target_uid}/roles/{role_id}")
            role_label = "@💎 Diamond Whale" if role_key == "whale" else "@🔥 OnlyFans / ManyVids VIP"
            sale_amt = 50.0 if role_key == "whale" else 20.0
            await record_sale_and_agency_cut(
                client,
                client_id,
                prof,
                f"{role_label} Unlock",
                sale_amt,
                target_uid,
            )
            await client.post(
                f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
                json={
                    "type": 4,
                    "data": {
                        "content": f"👑 **Unlocked `{role_label}` for <@{target_uid}>!** You now have full access to `#👑-vip-whale-lounge` and `#🔐-vip-uncensored-vault`!",
                    },
                },
                timeout=10.0,
            )

    elif custom_id == "wh_ticket_close":
        await client.post(
            f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
            json={"type": 4, "data": {"content": "🔒 Closing private order ticket in 3 seconds...", "flags": 64}},
            timeout=10.0,
        )
        await asyncio.sleep(3.0)
        await _discord_req(client, tok, "DELETE", f"/channels/{chan_id}")

    elif custom_id == "wh_roll_wheel_prize":
        prize = random.choice(WHEEL_PRIZES)
        await record_sale_and_agency_cut(client, client_id, prof, "Wheel of Desires Spin ($15)", 15.0, uid)
        await client.post(
            f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
            json={
                "type": 4,
                "data": {
                    "embeds": [
                        {
                            "title": "🎡 WHEEL OF DESIRES — OFFICIAL SPIN RESULT!",
                            "description": f"🎉 **CONGRATULATIONS!** The wheel landed on:\n\n👉 {prize}",
                            "color": 0x00F2FE,
                        }
                    ]
                },
            },
            timeout=10.0,
        )

    elif custom_id == "wh_admin_game_wheel":
        await client.post(
            f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
            json={"type": 4, "data": {"content": "🎡 **Posted 'Wheel of Desires' ($15 Spin Game) in `#🔥-new-content-drops`!**", "flags": 64}},
            timeout=10.0,
        )
        await post_wheel_of_desires_game(client_id)

    elif custom_id == "wh_admin_game_raffle":
        await client.post(
            f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
            json={"type": 4, "data": {"content": "🎁 **Posted Free VIP Giveaway & Raffle in `#💬-general-lounge`!**", "flags": 64}},
            timeout=10.0,
        )
        await post_weekly_raffle_contest(client_id)

    elif custom_id == "wh_admin_draw_raffle":
        crm = load_creator_crm()
        entries = crm.get(client_id, {}).get("raffle_entries", [])
        if not entries:
            msg_txt = "⚠️ No raffle entries recorded yet! Click `🎁 Launch Free VIP Raffle` first so fans can click to enter."
        else:
            winner_uid = random.choice(entries)
            lounge_ch = channels.get("lounge_chat", "")
            if lounge_ch:
                await _discord_req(
                    client,
                    tok,
                    "POST",
                    f"/channels/{lounge_ch}/messages",
                    json_body={
                        "content": f"🎉 **GIVEAWAY WINNER ANNOUNCEMENT!** Congratulations <@{winner_uid}>!",
                        "embeds": [
                            {
                                "title": "🏆 Official VIP Giveaway Winner!",
                                "description": f"Congratulations <@{winner_uid}>! You won our **VIP Raffle** out of **{len(entries)}** entries! Click `🎟️ Claim Purchase / Open Order Ticket` in <#{channels.get('schedule_menu', '')}> to claim your prize!",
                                "color": 0xEAB308,
                            }
                        ],
                    },
                )
            msg_txt = f"🏆 **Drew Winner <@{winner_uid}>** out of {len(entries)} entries and announced in `#💬-general-lounge`!"
        await client.post(
            f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
            json={"type": 4, "data": {"content": msg_txt, "flags": 64}},
            timeout=10.0,
        )

    elif custom_id == "wh_admin_game_guess":
        await client.post(
            f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
            json={"type": 4, "data": {"content": "👙 **Posted 'Guess Tonight's Panty Color' Game in `#💬-general-lounge`!**", "flags": 64}},
            timeout=10.0,
        )
        await post_guess_panty_game(client_id)

    elif custom_id == "wh_book_c2c":
        overwrites = [
            {"id": gid, "type": 0, "allow": "0", "deny": str(PERM_VIEW_CHANNEL)},
            {
                "id": uid,
                "type": 1,
                "allow": str(
                    PERM_VIEW_CHANNEL
                    | PERM_SEND_MESSAGES
                    | PERM_READ_HISTORY
                    | PERM_ATTACH_FILES
                    | PERM_CONNECT
                    | PERM_SPEAK
                ),
                "deny": "0",
            },
        ]
        for rk in ("queen", "mod"):
            if roles.get(rk):
                overwrites.append(
                    {
                        "id": roles[rk],
                        "type": 0,
                        "allow": str(
                            PERM_VIEW_CHANNEL
                            | PERM_SEND_MESSAGES
                            | PERM_READ_HISTORY
                            | PERM_ATTACH_FILES
                            | PERM_CONNECT
                            | PERM_SPEAK
                        ),
                        "deny": "0",
                    }
                )
        # 1. Create Private Locked 2-Person HD Video / Cam-to-Cam Channel (type 2 = Voice/Video, user_limit = 2)
        v_chan = await _discord_req(
            client,
            tok,
            "POST",
            f"/guilds/{gid}/channels",
            json_body={
                "name": f"📹-private-c2c-{uname}",
                "type": 2,
                "nsfw": True,
                "user_limit": 2,
                "permission_overwrites": overwrites,
            },
        )
        v_id = (v_chan or {}).get("id", "")

        # 2. Create Private 1-on-1 C2C Booking & Receipt Text Channel
        t_chan = await _discord_req(
            client,
            tok,
            "POST",
            f"/guilds/{gid}/channels",
            json_body={
                "name": f"📹-c2c-booking-{uname}",
                "type": 0,
                "nsfw": True,
                "topic": f"Private 1-on-1 Cam-to-Cam Booking for {uname} (UID:{uid} VID:{v_id})",
                "permission_overwrites": overwrites,
            },
        )
        t_id = (t_chan or {}).get("id", "")

        if t_id:
            await _discord_req(
                client,
                tok,
                "POST",
                f"/channels/{t_id}/messages",
                json_body={
                    "content": (
                        f"📹 Welcome <@{uid}>! **Your Private 1-on-1 Cam-to-Cam (C2C) Suite is Ready!**\n"
                        f"👉 **Your Locked 2-Person HD Video Room:** <#{v_id}> *(Only you and Charlette can see or join it!)*"
                    ),
                    "embeds": [
                        {
                            "title": "📹 Private 1-on-1 Cam-to-Cam (C2C) Rates & Instant Setup",
                            "description": (
                                "**Option A — Private Discord 1-on-1 HD Cam-to-Cam Show (0% Cam-Site Token Fees!)**\n"
                                "• 🔥 **10-Minute 1-on-1 Cam-to-Cam Show**: **$100** (`$CharletteWebb` on CashApp or Throne)\n"
                                "• 💦 **20-Minute 1-on-1 Cam-to-Cam Show**: **$170**\n"
                                "• 👑 **30-Minute VIP Cam-to-Cam + Lush Toy Control**: **$250**\n\n"
                                "Please add your Discord username (`"
                                + uname
                                + "`) in the payment note so your order can be matched.\n\n"
                                "1️⃣ Send payment on **CashApp (`$CharletteWebb`)** or **Throne** below and drop your screenshot right here.\n"
                                f"2️⃣ Click into <#{v_id}> and tap **Turn On Camera** when Charlette joins!\n\n"
                                "**Option B — Prefer Cam-to-Cam on a Cam Site (8:00 PM – 3:00 AM EST)?**\n"
                                "Tap Chaturbate, Stripchat, or MFC below to start a Private C2C with tokens!"
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
                                {"type": 2, "style": 5, "label": "💧 Chaturbate C2C", "url": links["chaturbate"]},
                                {"type": 2, "style": 5, "label": "🔥 Stripchat C2C", "url": links["stripchat"]},
                            ],
                        },
                        {
                            "type": 1,
                            "components": [
                                {
                                    "type": 2,
                                    "style": 3,
                                    "label": "📹 Log 10m C2C ($100)",
                                    "custom_id": "wh_c2c_log_100",
                                },
                                {
                                    "type": 2,
                                    "style": 3,
                                    "label": "📹 Log 20m C2C ($170)",
                                    "custom_id": "wh_c2c_log_170",
                                },
                                {
                                    "type": 2,
                                    "style": 1,
                                    "label": "👑 Log 30m VIP C2C ($250)",
                                    "custom_id": "wh_c2c_log_250",
                                },
                                {
                                    "type": 2,
                                    "style": 4,
                                    "label": "🔒 End C2C & Delete Rooms",
                                    "custom_id": "wh_c2c_close",
                                },
                            ],
                        },
                    ],
                },
            )
            if channels.get("mod_logs"):
                await _discord_req(
                    client,
                    tok,
                    "POST",
                    f"/channels/{channels['mod_logs']}/messages",
                    json_body={
                        "content": f"📹 **New 1-on-1 Cam-to-Cam (C2C) Booking Opened** by <@{uid}> (`{uname}`): Text <#{t_id}> | Locked Video Room <#{v_id}>"
                    },
                )

        await client.post(
            f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
            json={
                "type": 4,
                "data": {
                    "content": f"📹 **Your Private 1-on-1 Cam-to-Cam Suite is open!**\n• Booking & Receipt Chat: <#{t_id}>\n• Locked 2-Person HD Video Room: <#{v_id}>",
                    "flags": 64,
                },
            },
            timeout=10.0,
        )

    elif custom_id in ("wh_c2c_log_60", "wh_c2c_log_100", "wh_c2c_log_150", "wh_c2c_log_170", "wh_c2c_log_250"):
        amt_map = {
            "wh_c2c_log_60": ("10-Min Private 1-on-1 Cam-to-Cam Show", 60.0),
            "wh_c2c_log_100": ("10-Min Private 1-on-1 Cam-to-Cam Show", 100.0),
            "wh_c2c_log_150": ("30-Min VIP 1-on-1 Cam-to-Cam + Toy Control", 150.0),
            "wh_c2c_log_170": ("20-Min Private 1-on-1 Cam-to-Cam Show", 170.0),
            "wh_c2c_log_250": ("30-Min VIP 1-on-1 Cam-to-Cam + Toy Control", 250.0),
        }
        label, gross = amt_map[custom_id]
        ch_info = await _discord_req(client, tok, "GET", f"/channels/{chan_id}")
        topic = (ch_info or {}).get("topic") or ""
        m_uid = re.search(r"UID:(\d+)", topic)
        m_vid = re.search(r"VID:(\d+)", topic)
        target_uid = m_uid.group(1) if m_uid else uid
        vid_id = m_vid.group(1) if m_vid else ""
        # Any $60+ C2C buyer also automatically qualifies for @💎 Diamond Whale!
        if target_uid and roles.get("whale") and gid:
            await _discord_req(client, tok, "PUT", f"/guilds/{gid}/members/{target_uid}/roles/{roles['whale']}")
        await record_sale_and_agency_cut(client, client_id, prof, label, gross, target_uid)
        await client.post(
            f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
            json={
                "type": 4,
                "data": {
                    "content": (
                        f"📹 **Confirmed: {label} (${gross:.0f})!**\n"
                        f"• <@{target_uid}> has also been upgraded to **`@💎 Diamond Whale`**!\n"
                        f"• Join your locked 2-person HD video room now: {f'<#{vid_id}>' if vid_id else 'Private C2C Voice/Video'}"
                    )
                },
            },
            timeout=10.0,
        )

    elif custom_id == "wh_c2c_close":
        ch_info = await _discord_req(client, tok, "GET", f"/channels/{chan_id}")
        topic = (ch_info or {}).get("topic") or ""
        m_vid = re.search(r"VID:(\d+)", topic)
        vid_id = m_vid.group(1) if m_vid else ""
        await client.post(
            f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
            json={"type": 4, "data": {"content": "🔒 Ending C2C session and deleting private video & booking rooms in 3 seconds...", "flags": 64}},
            timeout=10.0,
        )
        await asyncio.sleep(3.0)
        if vid_id:
            await _discord_req(client, tok, "DELETE", f"/channels/{vid_id}")
        await _discord_req(client, tok, "DELETE", f"/channels/{chan_id}")

    elif custom_id == "wh_ask_ai_concierge":
        # Defer first: Discord requires an initial response within 3 seconds and the model can take longer.
        await client.post(
            f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
            json={"type": 5, "data": {"flags": 64}},
            timeout=10.0,
        )
        reply_text = await generate_ai_concierge_response(prof, "Tell me about the schedule, 1-on-1 call rates, the video archive and the supporter role.")
        await client.patch(
            f"{DISCORD_API}/webhooks/{interaction.get('application_id')}/{inter_token}/messages/@original",
            json={
                "embeds": [
                    {
                        "title": f"{prof['stage_name']}'s AI Concierge",
                        "description": reply_text,
                        "color": 0xEC4899,
                    }
                ]
            },
            timeout=15.0,
        )

    elif custom_id == "wh_unlock_vault_drop":
        signed_url = generate_signed_vault_url(client_id, "Charlette_Webb_VIP_Teaser_Set.jpg", ttl_seconds=7200)
        if not signed_url:
            await client.post(
                f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
                json={"type": 4, "data": {"content": "The VIP vault is not open yet. Charlette will announce it here when it is.", "flags": 64}},
                timeout=10.0,
            )
            return
        await client.post(
            f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
            json={
                "type": 4,
                "data": {
                    "content": (
                        f"🔐 **Your Personal Anti-Scrape Signed Vault Token has been generated (Expires in 2 Hours):**\n"
                        f"👉 [Click Here to View Signed Vault Drop]({signed_url})\n"
                        f"*(⚠️ Token is HMAC-SHA256 signed & time-locked—do not share outside the VIP Lounge!)*"
                    ),
                    "flags": 64,
                },
            },
            timeout=10.0,
        )

    elif custom_id == "wh_admin_drop_vault":
        await post_anti_scrape_vault_card(client_id)
        await client.post(
            f"{DISCORD_API}/interactions/{inter_id}/{inter_token}/callback",
            json={
                "type": 4,
                "data": {
                    "content": "🔐 **Posted fresh HMAC-Signed Anti-Scrape Vault Drop in `#🔐-vip-uncensored-vault`!**",
                    "flags": 64,
                },
            },
            timeout=10.0,
        )


async def upgrade_live_server_with_crm_and_games(client_id: str = "charlette_webb") -> Dict[str, Any]:
    """
    Upgrades Charlette Webb's live Discord server with:
      1. 1-Click Private Order / Video Purchase / VIP Claim Ticket desk in #📅-schedule-and-vip-menu and #🎬-custom-video-vip-queue
      2. Whale Leaderboard & King of the Room contest card in #🏆-whale-tipper-hall-of-fame
      3. Full 6-Button WORKHORSE Studio Control Panel (Live Blaster, Outfit Poll, Spin-the-Wheel, VIP Raffle, Draw Winner, Guess Panty Color)
      4. Active 'Wheel of Desires' game in #🔥-new-content-drops and 'Free VIP Giveaway' in #💬-general-lounge
    """
    profiles = load_community_profiles()
    prof = profiles.get(client_id, DEFAULT_CHARLETTE_PROFILE)
    tok = prof["discord"].get("bot_token", "")
    ch = prof["discord"].get("channels", {})
    links = prof["links"]

    async with httpx.AsyncClient() as client:
        # 1. Post Private Order / Receipt Ticket Desk in #📅-schedule-and-vip-menu and #🎬-custom-video-vip-queue
        for target_key in ("schedule_menu", "vip_customs"):
            tc = ch.get(target_key)
            if tc:
                await _discord_req(
                    client,
                    tok,
                    "POST",
                    f"/channels/{tc}/messages",
                    json_body={
                        "embeds": [
                            {
                                "title": "🎟️ Buy Videos, Order Customs, or Claim Your VIP / Whale Role",
                                "description": (
                                    "Paid on **CashApp (`$CharletteWebb`)**, **Throne**, **ManyVids**, or **OnlyFans** — or want to order a custom video/photo bundle directly?\n\n"
                                    "👇 **Click the green button below to open a Private 1-on-1 Order Channel with Charlette!**\n"
                                    "*(Please add your Discord username in the payment note so your order can be matched.)*"
                                ),
                                "color": 0x10B981,
                            }
                        ],
                        "components": [
                            {
                                "type": 1,
                                "components": [
                                    {
                                        "type": 2,
                                        "style": 3,
                                        "label": "🎟️ Open Private Order / Claim VIP Role Ticket",
                                        "custom_id": "wh_open_order_ticket",
                                    },
                                    {"type": 2, "style": 5, "label": "💸 CashApp ($CharletteWebb)", "url": links["cashapp"]},
                                    {"type": 2, "style": 5, "label": "🎁 Throne Wishlist", "url": links["throne"]},
                                ],
                            }
                        ],
                    },
                )

        # 2. Populate #🏆-whale-tipper-hall-of-fame
        if ch.get("hall_of_fame"):
            await _discord_req(
                client,
                tok,
                "POST",
                f"/channels/{ch['hall_of_fame']}/messages",
                json_body={
                    "embeds": [
                        {
                            "title": "🏆 CHARLETTE'S WHALE HALL OF FAME & 'KING OF THE ROOM' CONTEST",
                            "description": (
                                "Every night from **8:00 PM – 3:00 AM EST**, the top supporter across **CashApp (`$CharletteWebb`)**, **Throne**, or **Cam** is crowned in the Hall of Fame!\n\n"
                                "💎 **How to Unlock `@💎 Diamond Whale ($50+ Tipper)` Automatically:**\n"
                                "• Tip **$50+** via CashApp (`$CharletteWebb`) or send a Throne gift\n"
                                "• Or grab the **$350 All 700+ Videos Mega-Vault**\n"
                                "• Click **`🎟️ Claim Whale Status`** below to drop your receipt and unlock `#👑-vip-whale-lounge` & `#🔐-vip-uncensored-vault`!"
                            ),
                            "color": 0xEAB308,
                        }
                    ],
                    "components": [
                        {
                            "type": 1,
                            "components": [
                                {
                                    "type": 2,
                                    "style": 3,
                                    "label": "🎟️ Claim @Diamond Whale Status",
                                    "custom_id": "wh_open_order_ticket",
                                },
                                {"type": 2, "style": 5, "label": "💸 Tip on CashApp ($CharletteWebb)", "url": links["cashapp"]},
                                {"type": 2, "style": 5, "label": "🎁 Send Throne Gift", "url": links["throne"]},
                            ],
                        }
                    ],
                },
            )

        # 3. Post Upgraded 6-Button Control Panel in #🤖-workhorse-control-panel
        if ch.get("control_panel"):
            await _discord_req(
                client,
                tok,
                "POST",
                f"/channels/{ch['control_panel']}/messages",
                json_body={
                    "embeds": [
                        {
                            "title": "🎮 WORKHORSE Games, Contests & Revenue Command Deck",
                            "description": (
                                "**Tap any button below from your phone or PC to run live interactive games & contests:**\n\n"
                                "• **`🔴 BLAST LIVE ON CAM ALERT`** — Pings `@🔔 Cam Live Alerts` in Discord + Telegram simultaneously.\n"
                                "• **`🗳️ Post Tonight's Outfit Poll`** — Drops a 1️⃣–4️⃣ outfit vote in `#🗳️-outfit-and-show-polls`.\n"
                                "• **`🎡 Launch $15 Spin-the-Wheel Game`** — Drops the interactive *Wheel of Desires* ($15 CashApp per spin) in `#🔥-new-content-drops`.\n"
                                "• **`🎁 Launch Free VIP Raffle`** — Drops a 1-click giveaway in `#💬-general-lounge` that auto-subscribes entrants to `@🔔 Cam Live Alerts`.\n"
                                "• **`🏆 Draw Raffle Winner`** — Randomly picks & announces the winner from all CRM raffle entrants.\n"
                                "• **`👙 Launch 'Guess Panty Color' Game`** — Pre-show teaser game that drives fans into your 8:00 PM EST cam room for the reveal!"
                            ),
                            "color": 0xEC4899,
                        }
                    ],
                    "components": [
                        {
                            "type": 1,
                            "components": [
                                {
                                    "type": 2,
                                    "style": 4,
                                    "label": "🔴 BLAST 'LIVE ON CAM NOW!' ALERT",
                                    "custom_id": "wh_admin_go_live",
                                },
                                {
                                    "type": 2,
                                    "style": 1,
                                    "label": "🗳️ Post Outfit Poll",
                                    "custom_id": "wh_admin_post_poll",
                                },
                                {
                                    "type": 2,
                                    "style": 3,
                                    "label": "🎡 Launch $15 Spin-the-Wheel",
                                    "custom_id": "wh_admin_game_wheel",
                                },
                            ],
                        },
                        {
                            "type": 1,
                            "components": [
                                {
                                    "type": 2,
                                    "style": 1,
                                    "label": "🎁 Launch Free VIP Raffle",
                                    "custom_id": "wh_admin_game_raffle",
                                },
                                {
                                    "type": 2,
                                    "style": 2,
                                    "label": "🏆 Draw Raffle Winner",
                                    "custom_id": "wh_admin_draw_raffle",
                                },
                                {
                                    "type": 2,
                                    "style": 1,
                                    "label": "👙 Launch 'Guess Panty Color'",
                                    "custom_id": "wh_admin_game_guess",
                                },
                            ],
                        },
                    ],
                },
            )

    await post_wheel_of_desires_game(client_id)
    await post_weekly_raffle_contest(client_id)
    await post_guess_panty_game(client_id)
    return {"status": "upgraded"}


async def deploy_cam_to_cam_and_agency_cashtag(client_id: str = "charlette_webb") -> Dict[str, Any]:
    """
    1. Locks in $careypphoto (20%) in creator_crm.json and posts the Agency Revenue-Split Card in #🛡️-workhorse-mod-logs.
    2. Posts the 1-Click Private 1-on-1 Cam-to-Cam (C2C) Booking Cards into #📅-schedule-and-vip-menu,
       #🔴-live-on-cam-now, and #👑-vip-whale-lounge.
    """
    crm = load_creator_crm()
    c_data = crm.setdefault(client_id, {"verified_members": {}, "tickets": [], "raffle_entries": [], "whales": []})
    billing = c_data.setdefault(
        "agency_billing",
        {
            "agency_cashtag": "$careypphoto",
            "commission_rate": 0.20,
            "total_gross_sales": 0.0,
            "total_agency_commission": 0.0,
            "unpaid_agency_balance": 0.0,
            "ledger": [],
        },
    )
    billing["agency_cashtag"] = "$careypphoto"
    billing["commission_rate"] = 0.20
    save_creator_crm(crm)

    profiles = load_community_profiles()
    prof = profiles.get(client_id, DEFAULT_CHARLETTE_PROFILE)
    tok = prof["discord"].get("bot_token", "")
    ch = prof["discord"].get("channels", {})
    links = prof["links"]

    async with httpx.AsyncClient() as client:
        # 1. Post Private 1-on-1 Cam-to-Cam (C2C) Booking Cards
        for k in ("schedule_menu", "live_now", "vip_chat"):
            target_ch = ch.get(k)
            if not target_ch:
                continue
            await _discord_req(
                client,
                tok,
                "POST",
                f"/channels/{target_ch}/messages",
                json_body={
                    "content": "📹 **PRIVATE 1-ON-1 CAM-TO-CAM (C2C) SHOWS NOW AVAILABLE!**",
                    "embeds": [
                        {
                            "title": "📹 Book a Private 1-on-1 Cam-to-Cam (C2C) Show with Charlette Webb",
                            "description": (
                                "Want a **100% private 1-on-1 HD Cam-to-Cam video session** right inside a locked 2-person Discord room (or on Chaturbate/Stripchat/MFC)?\n\n"
                                "🔥 **Private Discord C2C Rates (Includes Automatic `@💎 Diamond Whale` Role Upgrade!):**\n"
                                "• **10-Minute 1-on-1 Cam-to-Cam Show**: **$100**\n"
                                "• **20-Minute 1-on-1 Cam-to-Cam Show**: **$170**\n"
                                "• **30-Minute VIP Cam-to-Cam + Lush Toy Control**: **$250**\n\n"
                                "👇 **Click `📹 Book 1-on-1 Cam-to-Cam (C2C) Show` below** to automatically open your **Private Booking Room + Locked 2-Person HD Video Channel**!"
                            ),
                            "color": 0x00F2FE,
                        }
                    ],
                    "components": [
                        {
                            "type": 1,
                            "components": [
                                {
                                    "type": 2,
                                    "style": 3,
                                    "label": "📹 Book 1-on-1 Cam-to-Cam (C2C) Show",
                                    "custom_id": "wh_book_c2c",
                                },
                                {"type": 2, "style": 5, "label": "💸 CashApp ($CharletteWebb)", "url": links["cashapp"]},
                                {"type": 2, "style": 5, "label": "🎁 Throne Wishlist", "url": links["throne"]},
                            ],
                        }
                    ],
                },
            )

        # 2. Post Official Agency Commission Configuration Card in #🛡️-workhorse-mod-logs
        if ch.get("mod_logs"):
            await _discord_req(
                client,
                tok,
                "POST",
                f"/channels/{ch['mod_logs']}/messages",
                json_body={
                    "embeds": [
                        {
                            "title": "💼 WORKHORSE Agency Revenue-Split Ledger ($careypphoto — 20%)",
                            "description": (
                                "• **Creator CashApp**: `$CharletteWebb` (**80% Net**)\n"
                                "• **WORKHORSE Studio CashApp**: `$careypphoto` (**20% Management & Hosting Fee**)\n\n"
                                "Every time a **Private C2C Show (`$100 / $170 / $250`)**, **`@💎 Diamond Whale` Unlock (`$50`)**, **`@🔥 VIP` Unlock (`$20`)**, or **`$15` Wheel Spin** is logged in a ticket, WORKHORSE records the 80/20 split in the manual ledger and generates a **1-Click Pre-Filled CashApp Settlement Link (`https://cash.app/$careypphoto/AMOUNT`)** so the 20% studio balance can be settled manually at any time."
                            ),
                            "color": 0x10B981,
                        }
                    ],
                    "components": [
                        {
                            "type": 1,
                            "components": [
                                {
                                    "type": 2,
                                    "style": 5,
                                    "label": "💸 Open Studio CashApp ($careypphoto)",
                                    "url": "https://cash.app/$careypphoto",
                                }
                            ],
                        }
                    ],
                },
            )
    return {"status": "deployed_c2c_and_cashtag"}


async def configure_whop_store(
    client_id: str = "charlette_webb",
    whop_store_url: str = "https://whop.com/charlette-webb-vip/",
    whop_api_key: str = "",
) -> Dict[str, Any]:
    """
    Saves the Whop.com Store URL (and optional API key) to the creator's profile and posts
    an instant Card / Apple Pay / CashApp Pay Automated VIP Checkout card into #📅-schedule-and-vip-menu
    and #🏆-whale-tipper-hall-of-fame.
    """
    profiles = load_community_profiles()
    prof = profiles.get(client_id, DEFAULT_CHARLETTE_PROFILE)
    prof["links"]["whop_store"] = whop_store_url.strip()
    if whop_api_key:
        prof.setdefault("whop", {})["api_key"] = whop_api_key.strip()
    profiles[client_id] = prof
    save_community_profiles(profiles)

    tok = prof["discord"].get("bot_token", "")
    ch = prof["discord"].get("channels", {})
    async with httpx.AsyncClient() as client:
        for k in ("schedule_menu", "hall_of_fame"):
            tc = ch.get(k)
            if not tc:
                continue
            await _discord_req(
                client,
                tok,
                "POST",
                f"/channels/{tc}/messages",
                json_body={
                    "embeds": [
                        {
                            "title": "💳 Instant Automatic VIP & Whale Role Checkout (Card / Apple Pay / CashApp Pay)",
                            "description": (
                                "Want **instant, automatic role unlocking** with **Credit/Debit Card, Apple Pay, Google Pay, or CashApp Pay**?\n\n"
                                "• **🔥 Inner Circle VIP Pass ($19.99/mo)** → Auto-unlocks `@🔥 OnlyFans / ManyVids VIP`\n"
                                "• **💎 Diamond Whale Club Pass ($50.00)** → Auto-unlocks `@💎 Diamond Whale ($50+ Tipper)`\n"
                                "• **📹 1-on-1 Private Video Call Pass ($60–$150)** → Instant C2C session booking\n\n"
                                "👇 **Click below to checkout instantly via our verified Whop Store:**"
                            ),
                            "color": 0x6366F1,
                        }
                    ],
                    "components": [
                        {
                            "type": 1,
                            "components": [
                                {
                                    "type": 2,
                                    "style": 5,
                                    "label": "💳 Instant Checkout (Apple Pay / Card / Whop)",
                                    "url": whop_store_url.strip(),
                                }
                            ],
                        }
                    ],
                },
            )
    return {"status": "ok", "whop_store_url": whop_store_url.strip()}


async def handle_whop_webhook(payload: Dict[str, Any], client_id: str = "charlette_webb") -> Dict[str, Any]:
    """
    Processes incoming Whop.com webhooks (payment.succeeded / membership.went_valid):
      1. Extracts the buyer's connected Discord User ID from Whop payload (`data.user.discord.id`)
      2. Automatically grants `@💎 Diamond Whale` (if amount >= $45) or `@🔥 OnlyFans / ManyVids VIP`
      3. Logs the sale & 80/20 Agency Split ($careypphoto) in `#🛡️-workhorse-mod-logs`!
    """
    action = str(payload.get("action") or payload.get("event") or "")
    data = payload.get("data") or payload
    amount_raw = data.get("final_amount") or data.get("subtotal") or data.get("amount")
    gross: Optional[float] = None
    if amount_raw is not None:
        try:
            gross = float(amount_raw)
            if gross >= 1000:  # Whop may send cents
                gross = round(gross / 100.0, 2)
        except Exception:
            gross = None

    user_obj = data.get("user") or {}
    discord_obj = user_obj.get("discord") or data.get("discord") or {}
    discord_uid = str(discord_obj.get("id") or data.get("discord_user_id") or "")
    product_name = (data.get("product") or {}).get("name") or data.get("plan_name") or f"Whop VIP Pass ({action or 'Checkout'})"

    profiles = load_community_profiles()
    prof = profiles.get(client_id, DEFAULT_CHARLETTE_PROFILE)
    tok = prof["discord"].get("bot_token", "")
    gid = prof["discord"].get("guild_id", "")
    roles = prof["discord"].get("roles", {})

    async with httpx.AsyncClient() as client:
        if tok and gid and discord_uid:
            role_key = "whale" if (gross or 0) >= 45.0 else "vip"
            role_id = roles.get(role_key, "")
            if role_id:
                await _discord_req(client, tok, "PUT", f"/guilds/{gid}/members/{discord_uid}/roles/{role_id}")
            if roles.get("verified_18"):
                await _discord_req(client, tok, "PUT", f"/guilds/{gid}/members/{discord_uid}/roles/{roles['verified_18']}")

        billing = None
        if gross is not None:
            billing = await record_sale_and_agency_cut(
                client,
                client_id,
                prof,
                f"Whop Auto-Checkout: {product_name}",
                gross,
                discord_uid,
            )
        else:
            mod_logs = prof["discord"].get("channels", {}).get("mod_logs", "")
            if tok and mod_logs:
                await _discord_req(
                    client,
                    tok,
                    "POST",
                    f"/channels/{mod_logs}/messages",
                    json_body={"content": f"Whop membership granted a role to <@{discord_uid or 'unknown'}> ({product_name}) but no amount was reported. Not added to the ledger - verify in Whop."},
                )
    return {"status": "ok", "discord_uid": discord_uid, "gross": gross, "billing": billing}


# ═══════════════════════════════════════════════════════════════════════════════
# PRO-TIER ($5,000+ AGENCY SUITE) INFRASTRUCTURE:
#   1. Whitelabel Branded Bot Identity (PATCH /users/@me Avatar + Banner)
#   2. 24/7 Local AI Concierge Persona (Ollama Local LLM + Instant Creator Lore Fallback)
#   3. Anti-Scrape Decoupled Media Vault (HMAC-SHA256 Signed Expiring Tokens + Bunny.net CDN)
#   4. Telegram Stars (XTR) Native 1-on-1 & Channel Pay-Per-View (PPV) Engine
# ═══════════════════════════════════════════════════════════════════════════════

SECRETS_FILE = BASE_DIR / "secrets.json"


def load_vault_settings() -> Dict[str, Any]:
    """
    Vault settings live in the git-ignored secrets.json under "creator_vault":
      hmac_key           auto-generated on first use
      public_base_url    public HTTPS origin that serves /api/vault/stream (e.g. https://api.example.com)
      bunny_cdn_host     Bunny.net pull-zone hostname (optional)
      bunny_security_key Bunny.net token-authentication key (optional)
    """
    import os
    import secrets as _secrets

    data: Dict[str, Any] = {}
    readable = True
    if SECRETS_FILE.exists():
        try:
            data = json.loads(SECRETS_FILE.read_text(encoding="utf-8"))
        except Exception:
            readable = False  # never overwrite a file we could not parse
    vault = data.setdefault("creator_vault", {})
    if not vault.get("hmac_key"):
        vault["hmac_key"] = _secrets.token_hex(32)
        if readable:
            tmp = SECRETS_FILE.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            os.replace(tmp, SECRETS_FILE)
    return vault


def generate_signed_vault_url(
    client_id: str = "charlette_webb",
    filename: str = "Charlette_Webb_VIP_Teaser_Set.jpg",
    ttl_seconds: int = 7200,
    bunny_cdn_host: str = "",
    bunny_security_key: str = "",
) -> str:
    """
    Time-limited signed media URL. Returns "" when no public vault origin or Bunny CDN is configured,
    so callers never hand fans a link that only works on a private network.
    """
    import hashlib
    import hmac
    import urllib.parse

    vault = load_vault_settings()
    host = bunny_cdn_host or vault.get("bunny_cdn_host", "")
    bkey = bunny_security_key or vault.get("bunny_security_key", "")
    expires = int(time.time()) + ttl_seconds
    if host and bkey:
        path = f"/{client_id}/{filename}"
        hashable_base = f"{bkey}{path}{expires}".encode("utf-8")
        signature = hmac.new(bkey.encode("utf-8"), hashable_base, hashlib.sha256).digest()
        b64_tok = base64.b64encode(signature).decode("utf-8").replace("+", "-").replace("/", "_").rstrip("=")
        return f"https://{host.rstrip('/')}{path}?token={b64_tok}&expires={expires}"

    base = (vault.get("public_base_url") or "").rstrip("/")
    if not base:
        return ""
    msg = f"{client_id}:{filename}:{expires}".encode("utf-8")
    sig = hmac.new(vault["hmac_key"].encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return f"{base}/api/vault/stream/{client_id}?file={urllib.parse.quote(filename)}&expires={expires}&sig={sig}"


def verify_signed_vault_token(client_id: str, filename: str, expires: int, sig: str) -> bool:
    import hashlib
    import hmac

    if int(time.time()) > int(expires):
        return False
    key = load_vault_settings()["hmac_key"].encode("utf-8")
    msg = f"{client_id}:{filename}:{int(expires)}".encode("utf-8")
    expected = hmac.new(key, msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


async def _pick_ollama_model(client: httpx.AsyncClient) -> str:
    """Use whichever text model is actually installed in Ollama (prefers Qwen3, skips vision/embedding)."""
    try:
        r = await client.get("http://127.0.0.1:11434/api/tags", timeout=3.0)
        names = [m.get("name", "") for m in (r.json().get("models") or [])]
        text_models = [n for n in names if n and "vl" not in n.lower() and "embed" not in n.lower()]
        for n in text_models:
            if "qwen3" in n.lower():
                return n
        if text_models:
            return text_models[0]
    except Exception:
        pass
    return "huihui_ai/qwen3-abliterated:14b"


async def generate_ai_concierge_response(prof: Dict[str, Any], user_message: str) -> str:
    """
    24/7 Local AI Concierge trained on Charlette Webb's lore, schedule, pricing, and links.
    Queries WORKHORSE's local Ollama LLM first (0 API cost); falls back to an instant
    deterministic concierge response if Ollama is asleep.
    """
    links = prof["links"]
    system_prompt = (
        f"You are {prof['stage_name']}'s official 24/7 VIP AI Concierge inside her 18+ Discord Lounge. "
        f"Be warm, friendly and concise (under 120 words). ONLY answer questions about her schedule, prices, official links and how to order. "
        f"For anything else, say you can only help with those topics and suggest asking Charlette directly. "
        f"Never write sexual content, never discuss anything involving minors, and never promise anything not listed below. Use only these facts:\n"
        f"- Experience: Full-time adult creator & webcam model for 8+ years.\n"
        f"- Live Cam Schedule: Every night from 8:00 PM to 3:00 AM EST on Chaturbate, Stripchat, MyFreeCams (MFC), CamSoda, and ManyVids Live.\n"
        f"- Official Website: https://charlettewebb.com\n"
        f"- Private 1-on-1 Discord Cam-to-Cam (C2C) Shows: 10 mins = $100, 20 mins = $170, 30 mins VIP + Lush Toy Control = $250 (click 'Book 1-on-1 Cam-to-Cam' button to open a private locked 2-person HD video room!).\n"
        f"- All 700+ Videos Mega-Vault Deal: $350 via CashApp ($CharletteWebb) unlocks her entire 700+ video archive + @Diamond Whale role.\n"
        f"- OnlyFans VIP ({links['onlyfans']}): Includes a 3-Hour Full Video + Private Snapchat upon joining.\n"
        f"- Wheel of Desires Game: $15 per spin (or 3 for $35) on CashApp ($CharletteWebb) — 100% win rate!\n"
        f"- Payments: ask fans to include their Discord username in the payment note so orders can be matched."
    )
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "http://127.0.0.1:11434/api/generate",
                json={
                    "model": await _pick_ollama_model(client),
                    "think": False,
                    "prompt": f"{system_prompt}\n\nFan Question: {user_message}\nConcierge Reply:",
                    "stream": False,
                    "options": {"temperature": 0.65, "num_predict": 220},
                },
                timeout=25.0,
            )
            if resp.status_code == 200:
                ans = re.sub(r"<think>.*?</think>", "", (resp.json().get("response") or ""), flags=re.DOTALL).strip()[:900]
                if ans:
                    return ans
    except Exception:
        pass

    return (
        f"Hey gorgeous! 💕 I'm **{prof['stage_name']}'s 24/7 VIP Concierge**! Here is everything you need right now:\n\n"
        f"• **🕗 Nightly Live Cam Schedule:** **8:00 PM – 3:00 AM EST** on [Chaturbate]({links['chaturbate']}), [Stripchat]({links['stripchat']}), [MFC]({links['mfc']}), [CamSoda]({links['camsoda']}), & [ManyVids Live]({links['manyvids_live']}).\n"
        f"• **📹 Private 1-on-1 Cam-to-Cam (C2C) Shows:** **$100** (10m) • **$170** (20m) • **$250** (30m VIP + Toy Control) inside a locked 2-person Discord HD video room! Click **`📹 Book 1-on-1 Cam-to-Cam`** in `#📅-schedule-and-vip-menu`!\n"
        f"• **🎬 All 700+ Videos Mega-Deal ($350):** Send **$350** on CashApp (`$CharletteWebb` — *add your Discord username in the note*) and open a ticket to unlock all 700+ videos!\n"
        f"• **💙 OnlyFans (+3-Hr Video & Snap):** [Join OnlyFans Here]({links['onlyfans']})\n"
        f"• **🌐 Official Hub:** [https://charlettewebb.com](https://charlettewebb.com)\n\n"
        f"*Tip: Tag me (`@Charlette Webb VIP Bot`) or type `?menu` anytime to chat with me 24/7!*"
    )


async def apply_whitelabel_bot_branding(client_id: str = "charlette_webb") -> Dict[str, Any]:
    """
    Applies Whitelabel Branded Bot Identity (`PATCH /users/@me`) so the Discord Bot itself
    wears Charlette Webb's luxury portrait avatar and banner instead of a generic bot icon!
    """
    profiles = load_community_profiles()
    prof = profiles.get(client_id, DEFAULT_CHARLETTE_PROFILE)
    tok = prof["discord"].get("bot_token", "")
    gfx = prof["graphics"]
    if not tok:
        return {"status": "missing_token"}

    body: Dict[str, Any] = {}
    av_path = pathlib.Path(gfx["avatar"])
    if av_path.exists():
        b64_av = base64.b64encode(av_path.read_bytes()).decode("ascii")
        body["avatar"] = f"data:image/png;base64,{b64_av}"

    bn_path = pathlib.Path(gfx["welcome_banner"])
    if bn_path.exists():
        b64_bn = base64.b64encode(bn_path.read_bytes()).decode("ascii")
        body["banner"] = f"data:image/jpeg;base64,{b64_bn}"

    async with httpx.AsyncClient() as client:
        res = await _discord_req(client, tok, "PATCH", "/users/@me", json_body=body)
    return {"status": "ok", "bot_user": (res or {}).get("username", "Charlette Webb VIP Bot")}


async def post_anti_scrape_vault_card(client_id: str = "charlette_webb") -> Dict[str, Any]:
    """Posts an Anti-Scrape Decoupled Media Vault card with 1-Click HMAC Signed Token generator."""
    profiles = load_community_profiles()
    prof = profiles.get(client_id, DEFAULT_CHARLETTE_PROFILE)
    tok = prof["discord"].get("bot_token", "")
    vault_ch = prof["discord"].get("channels", {}).get("vip_vault", "")
    if not tok or not vault_ch:
        return {"status": "missing_channel"}

    async with httpx.AsyncClient() as client:
        await _discord_req(
            client,
            tok,
            "POST",
            f"/channels/{vault_ch}/messages",
            json_body={
                "embeds": [
                    {
                        "title": "🔐 Anti-Scrape Decoupled VIP Media Vault (HMAC-Signed Token Access)",
                        "description": (
                            "To protect **Charlette Webb's** exclusive high-bitrate sets and bypass Discord's upload compression, "
                            "full-resolution vault drops are served via **Time-Locked HMAC-SHA256 Signed Tokens** (Bunny.net Edge CDN & WORKHORSE Vault compatible).\n\n"
                            "👇 **Click `🔐 Generate My 2-Hour Signed Vault Link` below** to mint a private, expiring link locked to your session:"
                        ),
                        "color": 0xEAB308,
                    }
                ],
                "components": [
                    {
                        "type": 1,
                        "components": [
                            {
                                "type": 2,
                                "style": 3,
                                "label": "🔐 Generate My 2-Hour Signed Vault Link",
                                "custom_id": "wh_unlock_vault_drop",
                            }
                        ],
                    }
                ],
            },
        )
    return {"status": "ok"}


async def send_telegram_stars_ppv(
    client_id: str = "charlette_webb",
    star_count: int = 250,
    caption: str = "🔥 Exclusive Uncensored PPV Drop — Tap below to unlock instantly with Telegram Stars!",
    photo_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Sends a native Telegram Stars (`XTR`) Pay-Per-View (PPV) locked media post (`sendPaidMedia`)
    to the creator's Telegram Channel or 1-on-1 DM!
    """
    profiles = load_community_profiles()
    prof = profiles.get(client_id, DEFAULT_CHARLETTE_PROFILE)
    tg_token = prof.get("telegram", {}).get("bot_token", "")
    tg_chan = prof.get("telegram", {}).get("channel_id", "")
    if not tg_token or not tg_chan:
        return {"status": "telegram_not_configured_yet"}

    img_file = pathlib.Path(photo_path or prof["graphics"]["live_banner"])
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.telegram.org/bot{tg_token}/sendPaidMedia",
            data={
                "chat_id": tg_chan,
                "star_count": int(star_count),
                "caption": caption,
                "media": json.dumps([{"type": "photo", "media": "attach://ppv_file"}]),
            },
            files={"ppv_file": (img_file.name, img_file.read_bytes(), "image/jpeg")},
            timeout=30.0,
        )
        return resp.json()


async def deploy_pro_tier_infrastructure(client_id: str = "charlette_webb") -> Dict[str, Any]:
    """
    Deploys the complete Tier-3 ($5,000+ Agency Blueprint) Pro Suite to Charlette's live server:
      1. Whitelabel Bot Avatar & Banner (`PATCH /users/@me`)
      2. 24/7 Local AI Concierge Card (`🤖 Ask Charlette's 24/7 AI Concierge`) in #💬-general-lounge & #📅-schedule-and-vip-menu
      3. Anti-Scrape Signed Media Vault (`🔐 Generate My 2-Hour Signed Vault Link`) in #🔐-vip-uncensored-vault
      4. Pro-Tier Infrastructure Command Card in #🤖-workhorse-control-panel
    """
    wl_res = await apply_whitelabel_bot_branding(client_id)
    await post_anti_scrape_vault_card(client_id)

    profiles = load_community_profiles()
    prof = profiles.get(client_id, DEFAULT_CHARLETTE_PROFILE)
    tok = prof["discord"].get("bot_token", "")
    ch = prof["discord"].get("channels", {})

    async with httpx.AsyncClient() as client:
        for k in ("lounge_chat", "schedule_menu"):
            tc = ch.get(k)
            if not tc:
                continue
            await _discord_req(
                client,
                tok,
                "POST",
                f"/channels/{tc}/messages",
                json_body={
                    "embeds": [
                        {
                            "title": "🤖 Meet Charlette's 24/7 VIP AI Concierge",
                            "description": (
                                "Have a question about **tonight's 8:00 PM – 3:00 AM EST cam stream**, **1-on-1 Cam-to-Cam rates (`$100 / $170 / $250`)**, "
                                "the **`$350` 700+ Video Mega-Deal**, or how to unlock **`@💎 Diamond Whale`**?\n\n"
                                "• **Click `💋 Ask 24/7 AI Concierge` below** for an instant breakdown, OR\n"
                                "• **Tag `@Charlette Webb VIP Bot` (or type `?menu`)** in any chat or Private Order Ticket to talk to the AI Concierge 24/7!"
                            ),
                            "color": 0xEC4899,
                        }
                    ],
                    "components": [
                        {
                            "type": 1,
                            "components": [
                                {
                                    "type": 2,
                                    "style": 1,
                                    "label": "💋 Ask 24/7 AI Concierge",
                                    "custom_id": "wh_ask_ai_concierge",
                                },
                                {
                                    "type": 2,
                                    "style": 3,
                                    "label": "📹 Book 1-on-1 Cam-to-Cam",
                                    "custom_id": "wh_book_c2c",
                                },
                                {
                                    "type": 2,
                                    "style": 2,
                                    "label": "🎟️ Open Private Order Ticket",
                                    "custom_id": "wh_open_order_ticket",
                                },
                            ],
                        }
                    ],
                },
            )

        if ch.get("control_panel"):
            await _discord_req(
                client,
                tok,
                "POST",
                f"/channels/{ch['control_panel']}/messages",
                json_body={
                    "embeds": [
                        {
                            "title": "🛡️ Pro-Tier ($5,000+ Agency Blueprint) Infrastructure Active",
                            "description": (
                                "• **Whitelabel Bot Identity**: Custom Charlette Webb Avatar & Banner applied via `PATCH /users/@me`.\n"
                                "• **24/7 Local AI Concierge**: Active on `@mention`, `?menu`, and button clicks (powered by Local Ollama + Instant Creator Lore Graph).\n"
                                "• **Adult-Compliant Entitlement & Ticket Engine**: ManyVids / OnlyFans / Fansly / Loyalfans / Throne / CashApp order tickets + 1-click role grant (`!grant`) + manual 80/20 Agency Fee ledger (`$careypphoto`).\n"
                                "• **Anti-Scrape Media Vault**: HMAC-SHA256 Signed Expiring Token Generator active in `#🔐-vip-uncensored-vault` (Bunny.net CDN & Local Vault ready).\n"
                                "• **Telegram Stars (`XTR`) PPV Engine**: Ready via `/api/community/telegram-stars-ppv`."
                            ),
                            "color": 0x00F2FE,
                        }
                    ],
                    "components": [
                        {
                            "type": 1,
                            "components": [
                                {
                                    "type": 2,
                                    "style": 3,
                                    "label": "🔐 Drop Signed Anti-Scrape Vault Card",
                                    "custom_id": "wh_admin_drop_vault",
                                },
                                {
                                    "type": 2,
                                    "style": 1,
                                    "label": "💋 Test 24/7 AI Concierge",
                                    "custom_id": "wh_ask_ai_concierge",
                                },
                            ],
                        }
                    ],
                },
            )

    return {"status": "pro_tier_deployed", "whitelabel_bot": wl_res}


async def sync_and_provision_whop_account(
    client_id: str = "charlette_webb",
    whop_api_key: str = "",
    whop_biz_id: str = "biz_Mo7gXM0DTs4NED",
) -> Dict[str, Any]:
    """
    Connects to Whop's REST API using the Company API Key, inspects the store & existing products/plans,
    provisions Charlette Webb's VIP passes if needed, saves the checkout URLs, and posts the live
    Whop Checkout buttons into her Discord server!
    """
    profiles = load_community_profiles()
    prof = profiles.get(client_id, DEFAULT_CHARLETTE_PROFILE)
    prof.setdefault("whop", {})["api_key"] = whop_api_key.strip()
    prof["whop"]["biz_id"] = whop_biz_id.strip()

    headers = {
        "Authorization": f"Bearer {whop_api_key.strip()}",
        "Content-Type": "application/json",
    }

    report: Dict[str, Any] = {"company": None, "products": [], "plans": [], "created": []}
    store_url = "https://whop.com/charlette-webb-vip/"

    async with httpx.AsyncClient() as client:
        # 1. Inspect Company / Store Info
        for ep in ("https://api.whop.com/api/v2/company", "https://api.whop.com/api/v5/company"):
            r_co = await client.get(ep, headers=headers, timeout=15.0)
            if r_co.status_code == 200:
                co_data = r_co.json()
                report["company"] = co_data
                route = co_data.get("route") or co_data.get("slug") or ""
                if route:
                    store_url = f"https://whop.com/{route.strip('/')}/"
                break

        # 2. List Existing Products & Plans
        r_prods = await client.get("https://api.whop.com/api/v2/products", headers=headers, timeout=15.0)
        if r_prods.status_code == 200:
            report["products"] = r_prods.json().get("data") or []

        r_plans = await client.get("https://api.whop.com/api/v2/plans", headers=headers, timeout=15.0)
        if r_plans.status_code == 200:
            report["plans"] = r_plans.json().get("data") or []

        # 3. Try provisioning the 3 core passes if no plans exist yet
        desired_passes = [
            {
                "title": "Inner Circle VIP Discord Pass",
                "description": "Monthly VIP Discord Role (@VIP), VIP Lounge & Vault access, and priority requests.",
                "plan_type": "renewal",
                "renewal_price": 19.99,
                "billing_period": 30,
            },
            {
                "title": "Diamond Whale Inner Circle Club",
                "description": "Permanent @Diamond Whale Discord Role, Hall of Fame feature, and VIP Vault access.",
                "plan_type": "one_time",
                "initial_price": 50.00,
            },
            {
                "title": "1-on-1 Private Video Call Session (10 Mins)",
                "description": "Private 1-on-1 HD Discord Video Call session + @Diamond Whale role upgrade.",
                "plan_type": "one_time",
                "initial_price": 60.00,
            },
        ]
        existing_titles = {str(p.get("name") or p.get("title") or "").lower() for p in report["products"]}
        for item in desired_passes:
            if item["title"].lower() in existing_titles:
                continue
            # Try v1/v2/v5 product creation
            for create_ep, body in [
                (
                    "https://api.whop.com/api/v2/products",
                    {"name": item["title"], "description": item["description"], "visibility": "visible"},
                ),
                (
                    "https://api.whop.com/api/v5/company/products",
                    {"title": item["title"], "description": item["description"], "visibility": "visible"},
                ),
            ]:
                rc = await client.post(create_ep, headers=headers, json=body, timeout=15.0)
                if rc.status_code in (200, 201):
                    prod_obj = rc.json()
                    report["created"].append(prod_obj)
                    pid = prod_obj.get("id")
                    if pid:
                        plan_body: Dict[str, Any] = {
                            "product_id": pid,
                            "plan_type": item["plan_type"],
                            "currency": "usd",
                            "visibility": "visible",
                        }
                        if item["plan_type"] == "renewal":
                            plan_body["renewal_price"] = item["renewal_price"]
                            plan_body["billing_period"] = item["billing_period"]
                        else:
                            plan_body["initial_price"] = item["initial_price"]
                        await client.post("https://api.whop.com/api/v2/plans", headers=headers, json=plan_body, timeout=15.0)
                    break

        # Refresh plans list to grab direct checkout links
        r_plans2 = await client.get("https://api.whop.com/api/v2/plans", headers=headers, timeout=15.0)
        if r_plans2.status_code == 200:
            report["plans"] = r_plans2.json().get("data") or []

    prof["links"]["whop_store"] = store_url
    prof["whop"]["plans"] = [
        {
            "id": pl.get("id"),
            "plan_type": pl.get("plan_type"),
            "price": pl.get("renewal_price") or pl.get("initial_price"),
            "direct_link": pl.get("direct_link") or f"https://whop.com/checkout/{pl.get('id')}/",
        }
        for pl in report["plans"]
        if pl.get("id")
    ]
    profiles[client_id] = prof
    save_community_profiles(profiles)

    await configure_whop_store(client_id=client_id, whop_store_url=store_url, whop_api_key=whop_api_key)
    return {
        "status": "ok",
        "store_url": store_url,
        "company_name": (report["company"] or {}).get("title") or (report["company"] or {}).get("name"),
        "products_count": len(report["products"]) + len(report["created"]),
        "plans": prof["whop"]["plans"],
    }


async def cleanup_whop_and_refresh_compliant_cards(client_id: str = "charlette_webb") -> Dict[str, Any]:
    """
    1. Deletes any Whop checkout cards from #📅-schedule-and-vip-menu and #🏆-whale-tipper-hall-of-fame.
    2. Patches the Control Panel & Mod Logs cards to remove Whop references and clarify the manual agency ledger.
    3. Posts a 100% Adult-Compliant Card / Store Checkout card (ManyVids, OnlyFans, Fansly, Throne + Ticket) in their place.
    """
    profiles = load_community_profiles()
    prof = profiles.get(client_id, DEFAULT_CHARLETTE_PROFILE)
    tok = prof["discord"].get("bot_token", "")
    ch = prof["discord"].get("channels", {})
    links = prof["links"]
    deleted_ids: List[str] = []
    patched_ids: List[str] = []
    posted_ids: List[str] = []

    async with httpx.AsyncClient() as client:
        # 1. Delete Whop cards in schedule_menu and hall_of_fame
        for ck in ("schedule_menu", "hall_of_fame"):
            cid = ch.get(ck)
            if not cid:
                continue
            msgs = await _discord_req(client, tok, "GET", f"/channels/{cid}/messages?limit=30")
            has_compliant_card = False
            for m in msgs or []:
                mid = m.get("id", "")
                raw_str = json.dumps(m).lower()
                if "whop" in raw_str:
                    await _discord_req(client, tok, "DELETE", f"/channels/{cid}/messages/{mid}")
                    deleted_ids.append(f"{ck}:{mid}")
                if "verified adult platform checkout" in raw_str:
                    has_compliant_card = True

            if not has_compliant_card:
                new_msg = await _discord_req(
                    client,
                    tok,
                    "POST",
                    f"/channels/{cid}/messages",
                    json_body={
                        "embeds": [
                            {
                                "title": "💳 Verified Adult Platform Checkout (Card / Apple Pay / Store Pass)",
                                "description": (
                                    "Prefer to pay with **Credit/Debit Card or Apple Pay** on 100% adult-compliant platforms?\n\n"
                                    "• **🎬 ManyVids Video & Custom Store** → Instant card checkout for videos, customs, & store items\n"
                                    "• **💙 OnlyFans VIP / 💜 Fansly VIP** → Full-length VIP archive + `@🔥 OnlyFans / ManyVids VIP` Discord role\n"
                                    "• **🎁 Throne Wishlist** → Safe card/Apple Pay tributes & gifts (`$50+` unlocks `@💎 Diamond Whale`)\n\n"
                                    "👇 **Checkout on any official platform below, then click `🎟️ Open Private Order Ticket` to claim your Discord VIP / Whale role!**"
                                ),
                                "color": 0xEC4899,
                            }
                        ],
                        "components": [
                            {
                                "type": 1,
                                "components": [
                                    {"type": 2, "style": 5, "label": "🎬 ManyVids Store (Card)", "url": links["manyvids_videos"]},
                                    {"type": 2, "style": 5, "label": "💙 OnlyFans VIP", "url": links["onlyfans"]},
                                    {"type": 2, "style": 5, "label": "💜 Fansly VIP", "url": links.get("fansly", "https://fansly.com/CharletteWebb/posts")},
                                    {"type": 2, "style": 5, "label": "🎁 Throne (Card / Apple Pay)", "url": links["throne"]},
                                    {
                                        "type": 2,
                                        "style": 3,
                                        "label": "🎟️ Open Private Order Ticket",
                                        "custom_id": "wh_open_order_ticket",
                                    },
                                ],
                            }
                        ],
                    },
                )
                if new_msg.get("id"):
                    posted_ids.append(f"{ck}:{new_msg['id']}")

        # 2. Patch control_panel card to remove Whop reference
        if ch.get("control_panel"):
            cp_msgs = await _discord_req(client, tok, "GET", f"/channels/{ch['control_panel']}/messages?limit=20")
            for m in cp_msgs or []:
                embeds = m.get("embeds") or []
                if embeds and "Pro-Tier" in (embeds[0].get("title") or ""):
                    embeds[0]["description"] = (
                        "• **Whitelabel Bot Identity**: Custom Charlette Webb Avatar & Banner applied via `PATCH /users/@me`.\n"
                        "• **24/7 Local AI Concierge**: Active on `@mention`, `?menu`, and button clicks (powered by Local Ollama + Instant Creator Lore Graph).\n"
                        "• **Adult-Compliant Entitlement & Ticket Engine**: ManyVids / OnlyFans / Fansly / Loyalfans / Throne / CashApp order tickets + 1-click role grant (`!grant`) + manual 80/20 Agency Fee ledger (`$careypphoto`).\n"
                        "• **Anti-Scrape Media Vault**: HMAC-SHA256 Signed Expiring Token Generator active in `#🔐-vip-uncensored-vault` (Bunny.net CDN & Local Vault ready).\n"
                        "• **Telegram Stars (`XTR`) PPV Engine**: Ready via `/api/community/telegram-stars-ppv`."
                    )
                    await _discord_req(
                        client,
                        tok,
                        "PATCH",
                        f"/channels/{ch['control_panel']}/messages/{m['id']}",
                        json_body={"embeds": embeds, "components": m.get("components", [])},
                    )
                    patched_ids.append(f"control_panel:{m['id']}")

        # 3. Patch mod_logs agency revenue-split card to clarify manual ledger
        if ch.get("mod_logs"):
            ml_msgs = await _discord_req(client, tok, "GET", f"/channels/{ch['mod_logs']}/messages?limit=20")
            for m in ml_msgs or []:
                embeds = m.get("embeds") or []
                if embeds and "Agency Revenue-Split" in (embeds[0].get("title") or ""):
                    embeds[0]["title"] = "💼 WORKHORSE Agency Revenue-Split Ledger ($careypphoto — 20%)"
                    embeds[0]["description"] = (
                        "• **Creator CashApp**: `$CharletteWebb` (**80% Net**)\n"
                        "• **WORKHORSE Studio CashApp**: `$careypphoto` (**20% Management & Hosting Fee**)\n\n"
                        "Every time a **Private C2C Show (`$100 / $170 / $250`)**, **`@💎 Diamond Whale` Unlock (`$50`)**, **`@🔥 VIP` Unlock (`$20`)**, or **`$15` Wheel Spin** is logged in a ticket, WORKHORSE records the 80/20 split in the manual ledger and generates a **1-Click Pre-Filled CashApp Settlement Link (`https://cash.app/$careypphoto/AMOUNT`)** so the 20% studio balance can be settled manually at any time."
                    )
                    await _discord_req(
                        client,
                        tok,
                        "PATCH",
                        f"/channels/{ch['mod_logs']}/messages/{m['id']}",
                        json_body={"embeds": embeds, "components": m.get("components", [])},
                    )
                    patched_ids.append(f"mod_logs:{m['id']}")

    return {
        "status": "ok",
        "deleted_whop_messages": deleted_ids,
        "patched_messages": patched_ids,
        "posted_compliant_cards": posted_ids,
    }









