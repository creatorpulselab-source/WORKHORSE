"""
Prism — AI Social Media Content Studio
Local AI social media caption and prompt studio.
Focused on Instagram, TikTok, Facebook, and X (Twitter).
"""

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, Response, HTMLResponse
from pydantic import BaseModel
from typing import Optional
import base64, json, sqlite3, uuid, io, hashlib, secrets, os, tempfile, shutil, subprocess, time, threading
import httpx
from datetime import datetime, date, timedelta, UTC
from pathlib import Path

try:
    import ollama as ollama_client
    HAS_OLLAMA = True
except ImportError:
    ollama_client = None  # type: ignore
    HAS_OLLAMA = False

try:
    from pywebpush import webpush, WebPushException
    from py_vapid import Vapid01
    HAS_WEBPUSH = True
except ImportError:
    webpush = WebPushException = Vapid01 = None  # type: ignore
    HAS_WEBPUSH = False

try:
    from PIL import Image, ImageDraw, ImageFilter
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

try:
    import cv2 as _cv2
    HAS_CV2 = True
except ImportError:
    _cv2 = None  # type: ignore
    HAS_CV2 = False


def _utcnow() -> datetime:
    # Naive-UTC replacement for the deprecated datetime.utcnow() — keeps the exact
    # same value/format as before so existing stored date strings stay comparable.
    return datetime.now(UTC).replace(tzinfo=None)


_whisper_model = None
try:
    from faster_whisper import WhisperModel as _WhisperModel
    HAS_WHISPER = True
except ImportError:
    _WhisperModel = None  # type: ignore
    HAS_WHISPER = False

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Prism", docs_url=None, redoc_url=None)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BASE_DIR   = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
DB_PATH    = BASE_DIR / "history.db"
CONFIG_PATH = BASE_DIR / "config.json"
USERS_PATH  = BASE_DIR / "users.json"
VAPID_KEY_PATH = BASE_DIR / "vapid_private_key.pem"
VAPID_PUB_PATH = BASE_DIR / "vapid_public_key.txt"
VAPID_CONTACT = os.environ.get("VAPID_CONTACT_EMAIL", "mailto:info@prismaicreator.com")

# True when running on Fly.io/Railway (both are HTTPS-terminated) — used to mark
# the session cookie Secure in production while still allowing plain-HTTP local dev.
IS_PRODUCTION = bool(os.environ.get("FLY_APP_NAME") or os.environ.get("RAILWAY_ENVIRONMENT"))

# Use Fly.io persistent volume at /data when available — prevents data loss on container restart
# To enable: run `fly volumes create que_data --size 1` then add [mounts] to fly.toml
_fly_data = Path("/data")
if _fly_data.exists() and os.access(str(_fly_data), os.W_OK):
    import shutil as _shu
    DB_PATH = _fly_data / "history.db"
    _vol_users = _fly_data / "users.json"
    if not _vol_users.exists() and (BASE_DIR / "users.json").exists():
        _shu.copy2(str(BASE_DIR / "users.json"), str(_vol_users))
    USERS_PATH = _vol_users
    # config.json (provider + API keys saved via the Settings UI) is gitignored/dockerignored,
    # so without this redirect it only ever lives on the ephemeral container disk and gets
    # silently wiped on every redeploy or machine restart.
    _vol_config = _fly_data / "config.json"
    if not _vol_config.exists() and (BASE_DIR / "config.json").exists():
        _shu.copy2(str(BASE_DIR / "config.json"), str(_vol_config))
    CONFIG_PATH = _vol_config
    VAPID_KEY_PATH = _fly_data / "vapid_private_key.pem"
    VAPID_PUB_PATH = _fly_data / "vapid_public_key.txt"

STATIC_DIR.mkdir(exist_ok=True)


def _compute_asset_version() -> str:
    # Hash app.js + enhancements.css so any edit automatically busts client caches —
    # no need to remember to bump a version number by hand on every deploy.
    h = hashlib.sha256()
    for name in ("app.js", "enhancements.css"):
        try:
            h.update((STATIC_DIR / name).read_bytes())
        except FileNotFoundError:
            pass
    return h.hexdigest()[:10]


ASSET_VERSION = _compute_asset_version()

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def _hash_pw(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260000).hex()


def _load_users() -> dict:
    if USERS_PATH.exists():
        return json.loads(USERS_PATH.read_text())
    return {"users": {}, "session_hours": 24}


def _save_users(data: dict):
    USERS_PATH.write_text(json.dumps(data, indent=2))


def _ensure_users():
    data = _load_users()
    if not data.get("users"):
        pw   = os.environ.get("ADMIN_PASSWORD") or ("prism" + secrets.token_hex(4))
        salt = secrets.token_hex(16)
        data["users"] = {"admin": {"salt": salt, "hash": _hash_pw(pw, salt), "enabled": True}}
        _save_users(data)
        print(f"\n  ★  Prism — first run, default login created:")
        print(f"     Username : admin")
        print(f"     Password : {pw}")
        print(f"  Change with: py add_user.py add admin <new-password>\n")


_ensure_users()


def _verify_pw(password: str, user_record: dict) -> bool:
    return secrets.compare_digest(_hash_pw(password, user_record["salt"]), user_record["hash"])


def _create_session(username: str, hours: int = 24) -> str:
    token = secrets.token_urlsafe(32)
    expires = (_utcnow() + timedelta(hours=hours)).isoformat()
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("INSERT OR REPLACE INTO sessions VALUES (?,?,?)", (token, username, expires))
    conn.execute("DELETE FROM sessions WHERE expires < ?", (_utcnow().isoformat(),))
    conn.commit()
    conn.close()
    return token


def _get_session(token: str) -> dict | None:
    if not token:
        return None
    conn = sqlite3.connect(DB_PATH, timeout=10)
    row = conn.execute("SELECT username, expires FROM sessions WHERE token=?", (token,)).fetchone()
    conn.close()
    if not row:
        return None
    username, expires_str = row
    if _utcnow() > datetime.fromisoformat(expires_str):
        conn2 = sqlite3.connect(DB_PATH, timeout=10)
        conn2.execute("DELETE FROM sessions WHERE token=?", (token,))
        conn2.commit()
        conn2.close()
        return None
    return {"username": username, "expires": datetime.fromisoformat(expires_str)}


def _is_admin(username: str) -> bool:
    user = _load_users().get("users", {}).get(username, {})
    return user.get("is_admin", username == "admin")


DEFAULT_USER_SETTINGS = {
    "enabled_modes": ["flux_image", "wan_video", "pose_series"], "gender": "neutral",
    "signature": "", "brand_voice": "", "daily_limit": 0,
    "notifications_enabled": False,
    "notify_streak_risk": True,
    "notify_scheduled_due": True,
    "notify_limit_reset": True,
    "notify_inactivity": True,
    "notify_streak_milestone": True,
    "notify_weekly_recap": True,
    "notify_personal_best": True,
    "notify_holiday_idea": True,
    "notify_trend_alert": True,
    "niche": "",
}


def _get_user_settings(username: str) -> dict:
    s = _load_users().get("users", {}).get(username, {}).get("settings", {})
    return {
        "enabled_modes": s.get("enabled_modes", DEFAULT_USER_SETTINGS["enabled_modes"]),
        "gender": s.get("gender", DEFAULT_USER_SETTINGS["gender"]),
        "signature": s.get("signature", ""),
        "brand_voice": s.get("brand_voice", ""),
        "daily_limit": int(s.get("daily_limit", 0)),
        "notifications_enabled": bool(s.get("notifications_enabled", False)),
        "notify_streak_risk": bool(s.get("notify_streak_risk", True)),
        "notify_scheduled_due": bool(s.get("notify_scheduled_due", True)),
        "notify_limit_reset": bool(s.get("notify_limit_reset", True)),
        "notify_inactivity": bool(s.get("notify_inactivity", True)),
        "notify_streak_milestone": bool(s.get("notify_streak_milestone", True)),
        "notify_weekly_recap": bool(s.get("notify_weekly_recap", True)),
        "notify_personal_best": bool(s.get("notify_personal_best", True)),
        "notify_holiday_idea": bool(s.get("notify_holiday_idea", True)),
        "notify_trend_alert": bool(s.get("notify_trend_alert", True)),
        "niche": s.get("niche", ""),
    }


_PUBLIC_PATHS = {"/", "/login", "/api/login", "/api/health", "/privacy.html", "/terms.html"}
_PUBLIC_EXTS = {".js", ".css", ".json", ".png", ".ico", ".svg", ".webmanifest", ".woff", ".woff2"}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    # Static assets (JS, CSS, manifest, fonts) are always public — they contain no user data
    is_public = path in _PUBLIC_PATHS or Path(path).suffix.lower() in _PUBLIC_EXTS
    if not is_public:
        token = request.cookies.get("que_session")
        if not (token and _get_session(token)):
            if path.startswith("/api/"):
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
            return RedirectResponse(url="/login", status_code=302)
    response = await call_next(request)
    # Force revalidation on JS/CSS/sw.js so edits show up immediately instead of
    # sitting in the browser's heuristic HTTP cache for an unpredictable amount of time.
    if path == "/sw.js" or Path(path).suffix.lower() in (".js", ".css"):
        response.headers["Cache-Control"] = "no-cache"
    return response

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = {"ollama_host": "http://127.0.0.1:11434", "vision_model": "qwen2.5vl:7b", "server_port": 7861,
                  "provider": "ollama", "api_key": "", "cloud_model": "",
                  "gemini_api_key": "", "grok_api_key": "", "openai_api_key": ""}

# Cloud providers occasionally get overloaded (HTTP 503) and their SDKs have no
# default request timeout, which can leave a "Generate" call hanging silently
# for several minutes with no error surfaced to the user. Bound every outbound
# call so a slow/overloaded provider fails fast and the existing fallback /
# error-handling logic kicks in instead of the UI spinning forever.
GEMINI_TIMEOUT_S = 45
GEMINI_TIMEOUT_MS = GEMINI_TIMEOUT_S * 1000
# "gemini-flash-latest" alias has been observed hanging/timing out for 15-30s+ before
# failing outright (Google backend issue with that specific alias). The non-lite
# "flash"/"pro" tier models (gemini-3.6-flash, gemini-3.5-flash) are also currently
# unstable — measured 8-40s+ per call, occasionally timing out entirely — while the
# "lite" tier responds consistently in 1-4s with comparable caption quality for this
# app's use case, so default to lite instead of chasing the flagship alias.
DEFAULT_GEMINI_MODEL = "gemini-flash-lite-latest"
# OpenAI/Grok client (OpenAI SDK) has no default timeout either — bound it the same way.
OPENAI_TIMEOUT_S = 30.0
# Image generation/edit calls (gpt-image-2, Grok Imagine) are much slower than chat/vision
# calls — OpenAI's own docs say complex edits can take up to ~2 minutes — so give them a
# separate, longer timeout instead of the 30s used for quick text/vision calls.
OPENAI_IMAGE_TIMEOUT_S = 120.0

# --- Login brute-force protection -------------------------------------------------
# In-memory, per-process sliding-window lockout (fine for Fly.io's single-instance
# deployment). Keyed by "client_ip:username" so one bad actor can't lock out a
# legitimate user from a different IP, and vice versa.
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_S = 5 * 60
_login_attempts: dict[str, list[float]] = {}
_login_lock = threading.Lock()


def _login_rate_limited(key: str) -> bool:
    now = time.monotonic()
    with _login_lock:
        attempts = [t for t in _login_attempts.get(key, []) if now - t < LOGIN_WINDOW_S]
        _login_attempts[key] = attempts
        return len(attempts) >= LOGIN_MAX_ATTEMPTS


def _record_login_failure(key: str) -> None:
    with _login_lock:
        _login_attempts.setdefault(key, []).append(time.monotonic())


def _clear_login_attempts(key: str) -> None:
    with _login_lock:
        _login_attempts.pop(key, None)


def load_config() -> dict:
    base = DEFAULT_CONFIG.copy()
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            base = {**base, **json.load(f)}
    # Environment variables override config.json (critical for Railway/cloud deployment)
    env_map = {
        "GEMINI_API_KEY": "gemini_api_key",
        "OPENAI_API_KEY": "openai_api_key",
        "GROK_API_KEY":   "grok_api_key",
        "OLLAMA_HOST":    "ollama_host",
        "VISION_MODEL":   "vision_model",
        "AI_PROVIDER":    "provider",
    }
    for env_key, cfg_key in env_map.items():
        val = os.environ.get(env_key)
        if val:
            base[cfg_key] = val
    # Auto-detect provider from whichever API key is set (so Railway just needs GEMINI_API_KEY)
    if base.get("provider") == "ollama":
        if base.get("gemini_api_key"):
            base["provider"] = "gemini"
        elif base.get("openai_api_key"):
            base["provider"] = "openai"
        elif base.get("grok_api_key"):
            base["provider"] = "grok"
    return base


def save_config(cfg: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_HASHTAG_ON  = "End with exactly 5 relevant trending hashtags on a new line. "
_HASHTAG_OFF = "No hashtags. "

CAPTION_PROMPTS = {
    "general": (
        "You are a professional social media content creator writing for Instagram, TikTok, Facebook, and X. "
        "Study this image carefully. Write the caption AS the person in it, first-person present tense. "
        "Reference what they are actually doing or experiencing right now. "
        "Make it relatable, authentic, and engaging. SHORT punchy lines with intentional line breaks. "
        "Natural emojis placed mid-text. Sound like a real person not a brand. "
        "End with a natural call to action. "
        "BANNED WORDS: captivating, mesmerizing, stunning, breathtaking, sophisticated, ethereal, timeless. "
        "Never describe the photo from outside. Never say 'this image shows'. "
        "{hashtag_line}"
        "Output ONLY the caption, nothing else."
    ),
    "instagram": (
        "You are an Instagram content creator. "
        "Study this image carefully. Write the caption AS the person in it, first-person present tense. "
        "Hook the reader in the very first line. Build a visual story or relatable moment in the middle. "
        "End with a CTA ('save this', 'double tap', 'drop a comment', 'tag someone who needs this'). "
        "Short punchy lines with intentional line breaks. Natural emojis mid-text. Authentic relatable tone. "
        "BANNED WORDS: captivating, mesmerizing, stunning, breathtaking, sophisticated. "
        "Write FROM inside the moment, not about it. "
        "{hashtag_line}"
        "Output ONLY the caption, nothing else."
    ),
    "tiktok": (
        "You are a TikTok content creator. "
        "Study this image carefully. Write a caption AS the person in it. "
        "The FIRST LINE must stop the scroll — an immediate hook that creates curiosity or strong relatability. "
        "Be casual, fun, trend-aware, and energetic. Short punchy lines. "
        "End with a CTA (follow, comment your thoughts, stitch this, etc.). 1-3 natural emojis. "
        "Sound like you typed this in 30 seconds on your phone. Genuine not polished. "
        "BANNED: captivating, mesmerizing, stunning, breathtaking, sophisticated. "
        "{hashtag_line}"
        "Output ONLY the caption, nothing else."
    ),
    "facebook": (
        "You are a Facebook content creator. "
        "Study this image carefully. Write a warm friendly first-person caption. "
        "Be genuine, conversational, and community-oriented. 2-4 sentences is perfectly fine here. "
        "Share a real thought, feeling, or story from this moment. "
        "End with a question that invites comments — this drives Facebook reach significantly. "
        "Tone like you are posting to friends. A few emojis where they naturally fit. "
        "BANNED: captivating, mesmerizing, stunning, breathtaking, sophisticated. "
        "{hashtag_line}"
        "Output ONLY the caption, nothing else."
    ),
    "twitter": (
        "You are a Twitter/X content creator. "
        "Study this image carefully. Write a punchy tweet-style caption. "
        "Keep it tight — ideally under 240 characters. Strong hook, clever angle, or hot take. "
        "Witty, relatable, or thought-provoking. 1-3 emojis maximum. "
        "End with a bold statement, question, or conversational hook. "
        "BANNED: captivating, mesmerizing, stunning, breathtaking, sophisticated. "
        "{hashtag_line}"
        "Output ONLY the caption, nothing else."
    ),
}

FLUX_PROMPT = (
    "You are an expert Flux.1 and Flux.2 image generation prompt engineer. "
    "Study this image carefully and write a detailed single paragraph prompt that recreates it exactly.\n\n"
    "Include in order in one flowing paragraph:\n"
    "SUBJECT: age appearance, "
    "hair (exact color + length + texture + style + parting — e.g. 'long straight platinum blonde hair with center part'), "
    "body type, skin tone, facial expression. "
    "NECK/JEWELRY: any choker, necklace, collar, or bare neck.\n"
    "POSE: identify the photography pose category — "
    "frontal (facing camera directly) / three-quarter turn (body at 45 degrees, note which shoulder is closer to camera) / profile (90 degrees). "
    "Which leg bears weight, which knee is slightly bent. "
    "Hips pushed which direction, which hip higher, lower back arched with ass out (anterior tilt) or flat. "
    "Foot distance (together / hip-width / wide stance / very wide). "
    "Each arm described separately (angle, where elbow points, hand position). "
    "Head direction and gaze. Shoulder tilt.\n"
    "OUTFIT: tops and bottoms described separately with full fabric+color+fit. "
    "Strap types (spaghetti/halter/cross-back/thick/none). "
    "If bodysuit: neckline + strap + fabric + bottom cut (thong-cut/high-cut/regular). "
    "If layered (lace over satin etc.) describe both layers. "
    "Fabric vocabulary: sheer / wet-look glossy / latex / PVC / patent leather / fishnet / lace / satin / mesh / velvet. "
    "SHOES: identify exact type — platform heels (thick platform + separate heel, note heights) / stilettos / wedges / block heels / "
    "strappy sandals / boots (ankle/knee/thigh) / clear-lucite / mules. Include material + color + height.\n"
    "SETTING: actual wall/floor materials visible (do not infer location from lighting style). "
    "LIGHTING: direction, hardness, color temperature, likely source (window/skylight/studio/neon). "
    "CAMERA: framing and angle.\n"
    "TEXT: any text visible on clothing, products, or background — write it exactly.\n"
    "End with: photorealistic, highly detailed, 8k, professional photography, sharp focus, cinematic lighting. "
    "Output ONLY the prompt as one paragraph, nothing else."
)

WAN_PROMPT = (
    "You are an expert WAN2.1 and WAN2.2 video generation prompt engineer. "
    "Based on this image write a cinematic video prompt for a 3 to 6 second clip. "
    "Include: opening scene description, natural subject movement (gesture, turn, walk, expression change), "
    "camera movement (dolly, pan, track), atmospheric mood and lighting. "
    "Keep under 90 words. Make it cinematic and dynamic. "
    "Output ONLY the prompt as one flowing paragraph, nothing else."
)

POSE_PROMPT = (
    "You are a professional photo shoot creative director shooting a single continuous photo set. "
    "You are an expert Flux.1 image generation prompt engineer and photography director. "
    "Based on this image of a person, create a series of exactly 6 completely distinct Flux.1 image prompts "
    "from the SAME photo shoot. "
    "CRITICAL: All 6 prompts MUST use the EXACT SAME background, location, environment, and lighting as the "
    "original photo — describe that same setting identically in every one of the 6 prompts. Do NOT invent a "
    "new location, backdrop, or lighting setup for any pose. ONLY vary the subject's pose, posture, body "
    "angle, and camera angle/framing between the 6 prompts — never the setting. "
    "The 6 poses MUST be dramatically different from each other, not minor variations of the same stance: "
    "vary the body's rotation relative to the camera by large amounts (e.g. facing camera directly, "
    "three-quarter turn, near-profile, looking back over one shoulder), vary the camera framing between shots "
    "(e.g. tight close-up, medium/waist-up, full-body wide), and vary arm/hand position, weight distribution, "
    "and head tilt substantially between every pose. No two of the 6 prompts should describe a similar "
    "silhouette or the same camera framing. "
    "Maintain the subject's exact physical appearance (face, body, outfit) in every prompt. Do not add jewelry, "
    "props, phones, or any held item unless the original photo clearly shows the subject already holding or "
    "wearing that exact item, and only include it in poses where it would still naturally stay in place. "
    "If any text is visible on clothing or props in the original image, preserve it in each pose prompt. "
    "Each must be a complete self-contained Flux.1 compatible prompt with full subject, outfit, the SAME "
    "setting, the SAME lighting, and camera details for that pose — put the pose description and camera "
    "angle/framing details early in each prompt so they are never lost to truncation. "
    "You MUST output exactly 6 prompts. You MUST use exactly this numbered format, with no intro or outro text:\n"
    "[1] <full prompt here>\n"
    "[2] <full prompt here>\n"
    "[3] <full prompt here>\n"
    "[4] <full prompt here>\n"
    "[5] <full prompt here>\n"
    "[6] <full prompt here>"
)

GENDER_SUFFIX = {
    "male":   {"post": " The subject is male. Write the caption in first-person masculine voice as a man.",
               "flux_image": " The subject is male. Include masculine build, features, and styling.",
               "wan_video":  " The subject is male. Describe confident masculine movements.",
               "pose_series": " The subject is male. Create strong masculine pose variations."},
    "female": {"post": " The subject is female. Write in first-person feminine voice as a woman.",
               "flux_image": " The subject is female. Include feminine features, styling, and grace.",
               "wan_video":  " The subject is female. Describe graceful feminine movements.",
               "pose_series": " The subject is female. Create elegant feminine pose variations."},
}


def _apply_gender(prompt: str, mode: str, gender: str) -> str:
    suffix = GENDER_SUFFIX.get(gender, {}).get(mode, "")
    return (prompt.rstrip() + suffix) if suffix else prompt


# Language and variants constants
LANGUAGES = {
    "en": "",
    "es": " Write the entire caption in Spanish.",
    "fr": " Write the entire caption in French.",
    "de": " Write the entire caption in German.",
    "pt": " Write the entire caption in Brazilian Portuguese.",
    "it": " Write the entire caption in Italian.",
    "ja": " Write the entire caption in Japanese.",
}

VARIANTS_SUFFIX = (
    "\n\nCRITICAL INSTRUCTION: You MUST generate exactly 3 completely different versions of this caption. "
    "Make them feel like 3 different creators wrote them, each with a unique tone and angle. "
    "You MUST separate each version with exactly '---' on its own line. "
    "Output ONLY the 3 captions separated by '---'. Do not output any intro, outro, or conversational text."
)

CAPTION_STYLES = {
    "hook": (
        " CAPTION STYLE — THE HOOK: Your FIRST LINE is everything. "
        "It must be a single scroll-stopping sentence — surprising, bold, or so relatable they can't scroll past. "
        "Everything after supports and builds on that opening line."
    ),
    "story": (
        " CAPTION STYLE — STORYTELLING: Structure as a micro-story. "
        "Set the scene → build to a tension, turning point, or realization → land on a resolution or takeaway. "
        "Each line should pull the reader to the next."
    ),
    "question": (
        " CAPTION STYLE — THE QUESTION: Open or close with a direct engaging question "
        "that genuinely invites the audience to comment their answer. "
        "The rest of the caption should make them WANT to respond."
    ),
    "hot_take": (
        " CAPTION STYLE — HOT TAKE: Lead with a bold, slightly controversial or counter-intuitive opinion. "
        "Take a clear confident stance. Don't hedge. "
        "Make people either strongly agree or want to argue back."
    ),
    "tips": (
        " CAPTION STYLE — TIPS / TUTORIAL: Format as a quick useful lesson or numbered tips. "
        "Make it genuinely actionable so people save it. "
        "Open with why they need to know this."
    ),
    "bts": (
        " CAPTION STYLE — BEHIND THE SCENES: Candid and confessional tone. "
        "Pull back the curtain on what really happened or how you really felt. "
        "Raw, real, and slightly vulnerable. Makes the audience feel like insiders."
    ),
    "soft_sell": (
        " CAPTION STYLE — SOFT SELL: Lead with genuine value or a relatable moment first, "
        "then naturally weave in the promotion, offer, or CTA. "
        "Make it feel like a helpful recommendation, not an ad."
    ),
    "relatable": (
        " CAPTION STYLE — RELATABLE: Open with a universal feeling, frustration, or experience "
        "your audience instantly connects with — 'we've all been here', 'why is this so me'. "
        "Use warm humor or genuine empathy. Make them feel seen."
    ),
}

CAPTION_STYLE_LABELS = {
    "hook": "🎣 The Hook",
    "story": "📖 Storytelling",
    "question": "❓ The Question",
    "hot_take": "🔥 Hot Take",
    "tips": "💡 Tips / Tutorial",
    "bts": "🎬 Behind the Scenes",
    "soft_sell": "🤝 Soft Sell",
    "relatable": "😅 Relatable",
}

THREAD_PROMPT = (
    "You are an expert Twitter/X content creator who specializes in thread writing. "
    "Based on this image, write a compelling Twitter thread with exactly 5 tweets. "
    "Tweet 1: A powerful hook that makes people want to keep reading. "
    "Tweets 2-4: Expand the story, insight, or message — each tweet stands alone but flows naturally. "
    "Tweet 5: A strong closing with a memorable CTA or thought-provoking statement. "
    "Each tweet must be under 240 characters. "
    "Format exactly as:\n"
    "[1] <tweet text>\n"
    "[2] <tweet text>\n"
    "[3] <tweet text>\n"
    "[4] <tweet text>\n"
    "[5] <tweet text>"
)


HASHTAG_PROMPT = (
    "You are a social media hashtag strategist with expert knowledge of trending tags. "
    "Analyze this image and generate exactly 30 relevant hashtags in 3 tiers.\n\n"
    "TIER 1 \u2014 HIGH REACH (10 tags, 500k\u20135M posts): broad popular tags for maximum discovery\n"
    "TIER 2 \u2014 ENGAGEMENT (10 tags, 50k\u2013500k posts): mid-range tags with strong engagement rates\n"
    "TIER 3 \u2014 NICHE (10 tags, under 50k posts): highly specific tags for better ranking and targeted reach\n\n"
    "Output ONLY in this exact format, nothing else:\n"
    "HIGH REACH: #tag #tag #tag #tag #tag #tag #tag #tag #tag #tag\n"
    "ENGAGEMENT: #tag #tag #tag #tag #tag #tag #tag #tag #tag #tag\n"
    "NICHE: #tag #tag #tag #tag #tag #tag #tag #tag #tag #tag"
)

# ---------------------------------------------------------------------------
# Content-type specific prompts
# ---------------------------------------------------------------------------

PRODUCT_CAPTION_PROMPTS = {
    "general": (
        "You are a professional product marketing copywriter for social media. "
        "Study this product image carefully. Identify the product, its features, aesthetic, and appeal. "
        "Write an engaging product caption that highlights benefits, evokes desire, and drives action. "
        "Sound like a real brand people actually like \u2014 NOT corporate-speak. "
        "Mix product features with lifestyle benefits. SHORT punchy lines with line breaks. "
        "Natural emojis. End with a CTA (shop link in bio, DM to order, limited stock, etc.). "
        "BANNED: innovative, revolutionary, game-changing, disruptive, elevate, curated, artisanal. "
        "{hashtag_line}"
        "Output ONLY the caption, nothing else."
    ),
    "instagram": (
        "You are an Instagram product brand account. "
        "Study this product image. Write a caption that makes someone WANT this product. "
        "Lead with the emotional benefit or lifestyle hook, not the specs. Build desire. "
        "End with a clear CTA (link in bio, drop a \ud83d\uded2 to get yours). "
        "Short punchy lines, intentional line breaks, 2\u20134 emojis. "
        "Sound like a brand people follow because they love the vibe. "
        "BANNED: revolutionary, innovative, game-changing, curated, elevated. "
        "{hashtag_line}"
        "Output ONLY the caption, nothing else."
    ),
    "tiktok": (
        "You are a TikTok product creator. "
        "Study this product image. Write a caption that makes people stop and investigate. "
        "First line is a HOOK \u2014 'wait this is actually insane', 'okay but why doesn\u2019t everyone have this' energy. "
        "Be enthusiastic but genuine. Short, punchy. End with CTA or question. 1\u20133 emojis. "
        "{hashtag_line}"
        "Output ONLY the caption, nothing else."
    ),
    "facebook": (
        "You are a Facebook product brand. "
        "Study this product. Write a warm informative caption like you\u2019re recommending to a friend. "
        "Share what makes it special in 2\u20133 sentences. End with a question to drive comments. "
        "BANNED: revolutionary, innovative, game-changing. "
        "{hashtag_line}"
        "Output ONLY the caption, nothing else."
    ),
    "twitter": (
        "You are a Twitter/X product account. "
        "Study this product. Write a punchy product tweet under 240 characters. "
        "Hot take, compelling product fact, or pure desirability. Make someone RT to share it. 1\u20132 emojis max. "
        "{hashtag_line}"
        "Output ONLY the caption, nothing else."
    ),
}

UGC_CAPTION_PROMPTS = {
    "general": (
        "You are writing a UGC (User Generated Content) caption for a brand collaboration. "
        "Study this image of a person using or featuring a product. "
        "Identify the product. Write an authentic first-person caption AS the creator in the image. "
        "Sound like a REAL person who genuinely loves this product \u2014 not a paid ad. "
        "Mention the product naturally as part of your story or experience. "
        "Be specific about what you love, how you use it, how it makes you feel. "
        "Short punchy lines. Relatable tone. Natural emojis. End with a soft product CTA or question. "
        "BANNED: gifted, ad, sponsored, collab, partnership (as words in the caption), game-changer, revolutionary. "
        "{hashtag_line}"
        "Output ONLY the caption, nothing else."
    ),
    "instagram": (
        "You are writing a UGC Instagram caption for a brand collaboration. "
        "Study this image \u2014 identify the product the person is using/holding. "
        "Write an authentic first-person caption AS that creator, naturally featuring the product. "
        "Read like an organic post from someone who genuinely loves this. "
        "Lead with a relatable moment or feeling, weave the product in naturally. "
        "End with a question or soft CTA that doesn\u2019t scream advertisement. "
        "Short punchy lines, line breaks, natural emojis. Authentic voice. "
        "{hashtag_line}"
        "Output ONLY the caption, nothing else."
    ),
    "tiktok": (
        "You are writing a TikTok UGC caption for a creator + product collab. "
        "Study this image. Identify the product. Write a caption AS the creator in the image. "
        "Hook: 'okay this [product] has me obsessed', 'tell me why I only just found this' energy. "
        "Super authentic, casual, like a creator who genuinely loves something. "
        "Short punchy lines. End with CTA. 1\u20133 emojis. "
        "{hashtag_line}"
        "Output ONLY the caption, nothing else."
    ),
    "facebook": (
        "You are writing a Facebook UGC post for a brand collaboration. "
        "Study this image. Identify the product. Write an authentic caption AS the person in the image. "
        "Sound like a real person sharing something they love with their friends. "
        "Mention the product genuinely. Share a real benefit or experience. "
        "End with a question to encourage comments. Warm, friendly, authentic tone. "
        "{hashtag_line}"
        "Output ONLY the caption, nothing else."
    ),
    "twitter": (
        "You are writing a Twitter/X UGC tweet for a brand collaboration. "
        "Study this image. Identify the product. Write an authentic tweet under 240 characters. "
        "Sound like a real person recommending something they love. Opinion-based, personal, genuine. 1\u20132 emojis. "
        "{hashtag_line}"
        "Output ONLY the caption, nothing else."
    ),
}

GENERAL_CAPTION_PROMPTS = {
    "general": (
        "You are a professional social media content creator. "
        "Study this image carefully. Identify what it contains \u2014 food, a pet, a landscape, an interior, "
        "an object, an event, or anything else. "
        "Write an engaging caption that captures the mood, story, or appeal of what you see. "
        "Adapt voice and tone to match the image content. "
        "SHORT punchy lines with line breaks. Natural emojis. Authentic tone. "
        "End with an engaging CTA or question relevant to the image. "
        "BANNED: captivating, mesmerizing, stunning, breathtaking, sophisticated, ethereal. "
        "{hashtag_line}"
        "Output ONLY the caption, nothing else."
    ),
    "instagram": (
        "You are an Instagram content creator. "
        "Study this image. Identify what it shows \u2014 food, pets, landscape, interior, event, object, or other. "
        "Write a caption that perfectly matches the energy and content of the image. "
        "Hook the reader. Build the story. End with a CTA or engagement question. "
        "Short punchy lines. Natural emojis. Tone that matches the image vibe. "
        "{hashtag_line}"
        "Output ONLY the caption, nothing else."
    ),
    "tiktok": (
        "You are a TikTok content creator. "
        "Study this image. Identify what it shows. Write a caption that matches its energy. "
        "First line is a strong hook. Casual, genuine, trend-aware. "
        "Match tone to image \u2014 cozy for food, playful for pets, awe for landscapes. "
        "1\u20133 emojis. End with CTA or question. "
        "{hashtag_line}"
        "Output ONLY the caption, nothing else."
    ),
    "facebook": (
        "You are a Facebook content creator. "
        "Study this image. Write a warm engaging caption that matches what you see. "
        "Conversational and genuine. Share a thought, feeling, or story inspired by the image. "
        "End with a question to drive comments. "
        "{hashtag_line}"
        "Output ONLY the caption, nothing else."
    ),
    "twitter": (
        "You are a Twitter/X content creator. "
        "Study this image. Write a punchy tweet under 240 characters. "
        "Match the energy \u2014 witty for clever images, warm for cozy content, bold for dramatic shots. 1\u20132 emojis. "
        "{hashtag_line}"
        "Output ONLY the caption, nothing else."
    ),
}

PRODUCT_ANGLES_PROMPT = (
    "You are a product photography creative director specializing in social media-ready product shots. "
    "Based on this product image, create exactly 6 Flux image prompts for distinct product photography angles. "
    "Accurately describe the product\u2019s appearance, color, size, material, and packaging as you see it. "
    "Use this exact format with nothing else before or after:\n"
    "[1] HERO: 3/4 angle shot, product fills 70% of frame, clean minimal background, "
    "studio key lighting with soft fill, below eye level, sharp focus on product details, "
    "photorealistic, commercial product photography, 8k\n"
    "[2] FLAT LAY: overhead top-down view, product centered, complementary lifestyle props arranged, "
    "soft even lighting, clean surface, photorealistic, 8k\n"
    "[3] DETAIL: extreme close-up on the product\u2019s most distinctive feature or texture, "
    "shallow depth of field, sharp focus on key detail, studio lighting, 8k macro photography\n"
    "[4] LIFESTYLE: product in natural real-world use context, authentic environment that matches its purpose, "
    "lifestyle photography feel, natural lighting, 8k\n"
    "[5] FEATURE: angle chosen to highlight the product\u2019s unique selling point, "
    "label or branding clearly visible if present, clean professional background, 8k\n"
    "[6] SCALE: product with clear size context reference, shows actual proportions, "
    "clean neutral background, natural soft lighting, 8k commercial photography"
)

UGC_ANGLES_PROMPT = (
    "You are a UGC (User Generated Content) creative director for brand partnerships. "
    "Based on this image of a person with a product, create exactly 6 Flux image prompts for UGC variations. "
    "CRITICAL RULE: The product MUST be held, used, or prominently featured in EVERY single variation. "
    "The product\u2019s identity, color, size, and type must remain exactly consistent across all 6 shots. "
    "Describe the product accurately based on what you see. "
    "Use this exact format with nothing else before or after:\n"
    "[1] HERO UGC: person holding product up/toward camera prominently, direct eye contact, "
    "eye-level shot, natural setting, warm authentic lighting, product clearly identifiable, "
    "photorealistic, lifestyle photography, 8k\n"
    "[2] INTERACTION: close-up on hands actively using/holding the product, "
    "person\u2019s face softly visible in background looking at product, "
    "authentic use moment, natural light, 8k lifestyle photography\n"
    "[3] LIFESTYLE: wider shot, person and product in relevant natural environment, "
    "product fits naturally into scene, authentic documentary feel, 8k\n"
    "[4] TESTIMONIAL: person looking directly at camera while holding/displaying product, "
    "genuine warm expression, product at chest height, clean relatable background, "
    "talking-to-camera UGC angle, photorealistic, 8k\n"
    "[5] PRODUCT FEATURE: tight shot with product filling 40-50% of frame, "
    "person\u2019s hands or body partially visible holding it, "
    "focus on product details while person adds human context, 8k\n"
    "[6] ENVIRONMENTAL: person with product integrated into their daily routine or lifestyle context, "
    "candid natural moment, authentic setting matching the product\u2019s use case, product clearly visible, "
    "lifestyle documentary photography, 8k"
)

GENERAL_SCENE_VARIATIONS_PROMPT = (
    "You are a professional creative director for social media content photography. "
    "Based on this image, create exactly 6 Flux image prompts for different scene variations. "
    "Identify the main subject (food, pet, landscape, interior, object, event, etc.) and create "
    "6 distinct angles or compositions that showcase it at its best. "
    "Vary: camera angle, framing, lighting, and composition while keeping the subject consistent. "
    "Each must be a complete self-contained Flux.1 compatible prompt. "
    "Use this exact format with nothing else before or after:\n"
    "[1] <full prompt here>\n"
    "[2] <full prompt here>\n"
    "[3] <full prompt here>\n"
    "[4] <full prompt here>\n"
    "[5] <full prompt here>\n"
    "[6] <full prompt here>"
)

# Comprehensive scene description used for context caching — one vision call, all modes reuse it
SCENE_DESCRIBE_PROMPT = (
    "You are an expert image analyst. Study this image and write a comprehensive factual description.\n\n"
    "Cover ALL of the following in one flowing paragraph:\n"
    "PEOPLE: age, gender, face (shape/eyes/nose/lips/features), hair (exact color+length+texture+style), "
    "skin tone, body type, expression, activity.\n"
    "POSE: camera angle (frontal/three-quarter/profile), weight distribution, hip position, "
    "arm positions, hand placement, head direction, shoulder tilt, foot stance.\n"
    "OUTFIT: every garment separately (fabric/color/fit/cut/straps/layers). "
    "Shoes: exact type (platform/stiletto/boots/sandals/mules), material, color, heel height.\n"
    "ACCESSORIES: jewelry (choker/necklace/earrings), bags, hats, glasses.\n"
    "SETTING: exact wall/floor/surface materials, furniture, props, objects visible.\n"
    "LIGHTING: direction, hardness (hard/soft), color temperature, likely source type.\n"
    "TEXT: any text visible on clothing, products, signs — transcribe exactly.\n"
    "MOOD/ACTION: what is happening, overall energy and vibe.\n\n"
    "Be specific and factual. Do not infer what is not visible. "
    "Output ONLY the description as one dense paragraph, nothing else."
)


TREND_PROMPT = (
    "You are a social media trend researcher. Use Google Search to find what is CURRENTLY "
    "trending this week in the \"{niche}\" niche on {platform} (or social media generally if "
    "platform is 'general'). Focus on: trending audio/formats, trending topics people are posting "
    "about, and any newsworthy hooks creators in this niche are using right now.\n\n"
    "Respond ONLY with valid JSON in this exact shape, nothing else, no markdown fences:\n"
    "{{\"trends\": [\"<trend 1>\", \"<trend 2>\", \"<trend 3>\"], "
    "\"angles\": [\"<suggested caption angle 1>\", \"<suggested caption angle 2>\"]}}"
)


def _extract_last_json_object(text: str):
    """Scan backward from the last '}' to find the last balanced {...} object in text
    and parse it as JSON. Handles verbose model output that narrates its reasoning and/or
    includes markdown-fenced example JSON before the final real JSON answer."""
    end = text.rfind("}")
    while end != -1:
        depth = 0
        for i in range(end, -1, -1):
            ch = text[i]
            if ch == "}":
                depth += 1
            elif ch == "{":
                depth -= 1
                if depth == 0:
                    candidate = text[i:end + 1]
                    try:
                        return json.loads(candidate)
                    except Exception:
                        break
        end = text.rfind("}", 0, end)
    return None


def _parse_trends(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    data = _extract_last_json_object(text)
    if data is not None:
        trends = data.get("trends", [])
        angles = data.get("angles", [])
        if not isinstance(trends, list):
            trends = []
        if not isinstance(angles, list):
            angles = []
        return {"trends": [str(t)[:200] for t in trends][:5], "angles": [str(a)[:200] for a in angles][:3]}
    return {"trends": [], "angles": [], "raw": raw.strip()[:500]}


HOOK_SCORE_PROMPT = (
    "You are a social media copywriting coach. Score the OPENING HOOK LINE of a caption "
    "on a 1-10 scale based on three criteria: curiosity gap, specificity, and pattern interrupt "
    "(does it stop someone mid-scroll?). Then give exactly 2 alternative hook lines that would "
    "score higher.\n\n"
    "HOOK LINE TO SCORE:\n\"{hook}\"\n\n"
    "Respond ONLY with valid JSON in this exact shape, nothing else, no markdown fences:\n"
    "{{\"score\": <integer 1-10>, \"feedback\": \"<one or two sentence critique>\", "
    "\"alternatives\": [\"<alt 1>\", \"<alt 2>\"]}}"
)


def _parse_hook_score(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    data = _extract_last_json_object(text)
    if data is not None:
        try:
            score = max(1, min(10, int(data.get("score", 0))))
            alternatives = data.get("alternatives", [])
            if not isinstance(alternatives, list):
                alternatives = []
            return {
                "score": score,
                "feedback": str(data.get("feedback", ""))[:400],
                "alternatives": [str(a)[:200] for a in alternatives][:2],
            }
        except Exception:
            pass
    return {"score": None, "feedback": raw.strip()[:500], "alternatives": []}


def _top_performer_examples(platform: str, limit: int = 2) -> list:
    """Return up to `limit` past 'post' captions the user marked as posted + rated highly
    (rating >= 4), most recent first, to use as few-shot style examples in future prompts."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        rows = conn.execute(
            "SELECT platform, results FROM history WHERE posted=1 AND rating>=4 "
            "ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
        conn.close()
    except Exception:
        return []
    out = []
    for row_platform, results_json in rows:
        if row_platform != platform:
            continue
        try:
            results = json.loads(results_json)
        except Exception:
            continue
        caption = results.get("post") if isinstance(results, dict) else None
        if caption and isinstance(caption, str):
            out.append(caption.strip())
        if len(out) >= limit:
            break
    return out


def _build_prompt(mode: str, platform: str, hashtags: bool, style: str = "", content_type: str = "creator") -> str:
    hl = _HASHTAG_ON if hashtags else _HASHTAG_OFF

    if mode == "post":
        if content_type == "product":
            base = PRODUCT_CAPTION_PROMPTS.get(platform, PRODUCT_CAPTION_PROMPTS["general"]).replace("{hashtag_line}", hl)
        elif content_type == "ugc":
            base = UGC_CAPTION_PROMPTS.get(platform, UGC_CAPTION_PROMPTS["general"]).replace("{hashtag_line}", hl)
        elif content_type == "general":
            base = GENERAL_CAPTION_PROMPTS.get(platform, GENERAL_CAPTION_PROMPTS["general"]).replace("{hashtag_line}", hl)
        else:  # creator (default)
            base = CAPTION_PROMPTS.get(platform, CAPTION_PROMPTS["general"]).replace("{hashtag_line}", hl)
        if style and style in CAPTION_STYLES:
            base = base.rstrip() + CAPTION_STYLES[style]
        return base

    if mode == "thread":
        return THREAD_PROMPT

    if mode == "pose_series":
        if content_type == "product":
            return PRODUCT_ANGLES_PROMPT
        elif content_type == "ugc":
            return UGC_ANGLES_PROMPT
        elif content_type == "general":
            return GENERAL_SCENE_VARIATIONS_PROMPT
        return POSE_PROMPT  # creator

    if mode == "flux_image":
        base = FLUX_PROMPT
        if content_type == "product":
            base = base.rstrip() + " Focus on the product: describe its color, shape, material, and setting in detail."
        elif content_type == "ugc":
            base = base.rstrip() + " Include both the person and the product they are holding/using. Describe the product accurately."
        return base

    if mode == "wan_video":
        base = WAN_PROMPT
        if content_type == "product":
            base = base.rstrip() + " This is a product video: highlight the product with revealing camera movement."
        elif content_type == "ugc":
            base = base.rstrip() + " Feature both the person and the product. Show authentic product interaction."
        return base

    return ""


EXPAND_PROMPTS_FLUX = (
    "You are an expert Flux.1 image generation prompt engineer. "
    'Expand these keywords: "{keywords}" into a complete Flux.1 prompt. '
    "Include subject, pose, styling, setting, lighting, camera angle. "
    "End with: photorealistic, highly detailed, 8k, professional photography, sharp focus. "
    "Output ONLY the prompt as one paragraph, nothing else."
)

EXPAND_PROMPTS_WAN = (
    "You are an expert WAN2.2 video generation prompt engineer. "
    'Expand these keywords: "{keywords}" into a cinematic video prompt for a 3-6 second clip. '
    "Include scene, subject movement, camera movement, mood. Keep under 90 words. "
    "Output ONLY the prompt as one paragraph, nothing else."
)

EXPAND_CAPTIONS = {
    "general":   'You are a social media content creator. Write an engaging first-person caption inspired by: "{keywords}". Relatable, authentic, punchy lines, natural emojis, CTA. {hashtag_line}Output ONLY the caption.',
    "instagram": 'You are an Instagram creator. Write a first-person Instagram caption inspired by: "{keywords}". Hook, story, CTA format. Line breaks. Natural emojis. {hashtag_line}Output ONLY the caption.',
    "tiktok":    'You are a TikTok creator. Write a caption with a scroll-stopping first line inspired by: "{keywords}". Casual, fun, punchy. CTA. {hashtag_line}Output ONLY the caption.',
    "facebook":  'You are a Facebook creator. Write a warm friendly caption inspired by: "{keywords}". 2-3 sentences, end with a question. {hashtag_line}Output ONLY the caption.',
    "twitter":   'You are a Twitter/X creator. Write a punchy tweet under 240 chars inspired by: "{keywords}". Hook or hot take. {hashtag_line}Output ONLY the caption.',
}

# ---------------------------------------------------------------------------
# Seasonal / holiday ideas (SFW)
# ---------------------------------------------------------------------------

HOLIDAY_IDEAS = [
    {"name": "New Year's",      "icon": "🥂", "month": 1,  "day": 1,  "window_days": 14, "ideas": ["new year energy, fresh start aesthetic, champagne and goals", "new chapter vibes, reflection and gratitude post", "countdown night, celebration with friends, party energy"]},
    {"name": "Valentine's Day", "icon": "💕", "month": 2,  "day": 14, "window_days": 21, "ideas": ["self-love day, treating yourself, cozy pink aesthetic", "galentines with friends, flowers and brunch", "romantic dinner table, candles and roses, date night"]},
    {"name": "St. Patrick's",   "icon": "🍀", "month": 3,  "day": 17, "window_days": 10, "ideas": ["green outfit, lucky vibes, spring outdoor celebration", "shamrock aesthetic, Irish pub energy, fun with friends"]},
    {"name": "Easter",          "icon": "🐣", "month": 4,  "day": 20, "window_days": 14, "ideas": ["spring brunch, pastel flowers and fresh vibes", "Easter basket, outdoor spring garden, family gathering"]},
    {"name": "Independence Day","icon": "🎆", "month": 7,  "day": 4,  "window_days": 10, "ideas": ["summer cookout, patriotic energy, fireworks with friends", "red white and blue, beach day, outdoor celebration"]},
    {"name": "Halloween",       "icon": "🎃", "month": 10, "day": 31, "window_days": 21, "ideas": ["creative costume, pumpkin patch content", "spooky autumn aesthetic, Halloween party vibes", "carved pumpkins and fall decor, cozy October"]},
    {"name": "Thanksgiving",    "icon": "🍂", "month": 11, "day": 27, "window_days": 10, "ideas": ["gratitude post, family table, warm autumn vibes", "cozy fall harvest, golden hour, thankful energy"]},
    {"name": "Christmas",       "icon": "🎄", "month": 12, "day": 25, "window_days": 21, "ideas": ["holiday decor, cozy Christmas morning aesthetic", "gift unwrapping, family gathering, festive vibes", "twinkling lights, hot cocoa, winter cozy content"]},
]

SEASON_IDEAS = {
    "Winter": {"icon": "❄️", "months": [12, 1, 2], "ideas": ["cozy winter aesthetic, fireplace, warm drinks", "snow day content, bundled up outfit vibes", "winter morning routine, frost and warmth"]},
    "Spring": {"icon": "🌸", "months": [3, 4, 5],  "ideas": ["blooming flowers, golden hour walk, fresh energy", "spring refresh aesthetic, pastel tones and sunshine", "outdoor brunch, florals and fresh air"]},
    "Summer": {"icon": "☀️", "months": [6, 7, 8],  "ideas": ["beach day energy, sun sand and waves", "summer rooftop, golden hour good vibes", "pool day aesthetic, fresh and glowing"]},
    "Fall":   {"icon": "🍁", "months": [9, 10, 11], "ideas": ["pumpkin spice season, cozy cafe aesthetic", "fall foliage walk, warm earth tones", "harvest market, sweater weather, autumn vibes"]},
}

EVERGREEN_IDEAS = [
    {"theme": "Golden Hour",    "icon": "🌅", "idea": "golden hour glow, warm backlight, minimal styling, perfect light"},
    {"theme": "Coffee Shop",    "icon": "☕", "idea": "cozy cafe morning, latte art, working or reading, warm ambient"},
    {"theme": "Fitness",        "icon": "💪", "idea": "gym aesthetic, post-workout energy, active wear, motivated mindset"},
    {"theme": "Travel",         "icon": "✈️", "idea": "adventure aesthetic, new destination, wanderlust, explore mindset"},
    {"theme": "Fashion / OOTD", "icon": "👗", "idea": "outfit of the day, fashion editorial, street style, style details"},
    {"theme": "Nature",         "icon": "🌿", "idea": "outdoor nature content, forest or park, peaceful and grounded"},
    {"theme": "Food",           "icon": "🍽️", "idea": "food photography, restaurant or homemade, beautiful presentation"},
    {"theme": "Wellness",       "icon": "🧘", "idea": "mindfulness and self-care, calm peaceful energy, wellness routine"},
    {"theme": "Work / Hustle",  "icon": "💻", "idea": "productive workspace, desk setup, focus aesthetic, hustle energy"},
    {"theme": "Friends",        "icon": "🤝", "idea": "friendship content, group energy, candid fun moments together"},
    {"theme": "Home Aesthetic", "icon": "🏡", "idea": "interior styling, cozy home content, beautiful living space"},
    {"theme": "Creativity",     "icon": "🎨", "idea": "creative process content, artistic workspace, making something"},
]


# ---------------------------------------------------------------------------
# Feature Page Discovery & Targeting Engine — curated data (Instagram hubs are
# user/admin-submitted via /api/hubs, never scraped; Reddit panel is static
# curated data — no live Reddit API call).
# ---------------------------------------------------------------------------

HUB_TIERS = {
    "micro": "Micro (under 25k followers) — higher acceptance rate, tight-knit niche community",
    "mid":   "Mid-Tier (25k\u2013250k followers) — balanced reach and acceptance rate",
    "mega":  "Mega (250k+ followers) — highest reach, lowest acceptance rate",
}

# Curated, hand-maintained subreddit research panel. Matched against the user's
# niche text via simple keyword matching in _match_reddit_niche — no live Reddit
# API integration, purely a research/hook-generator reference panel.
REDDIT_NICHE_PANELS = {
    "fitness":     [{"subreddit": "Fitness", "desc": "General fitness discussion and progress posts.", "norms": "No blatant self-promo; read pinned rules before posting."},
                    {"subreddit": "xxfitness", "desc": "Fitness community, women-focused.", "norms": "Flair required on posts; self-promo restricted to certain days."}],
    "food":        [{"subreddit": "food", "desc": "Photogenic food posts, no recipe required.", "norms": "Title must simply describe the dish; no watermarks/logos on images."},
                    {"subreddit": "foodporn", "desc": "Purely visual food photography.", "norms": "High-quality image required; no text overlays."}],
    "travel":      [{"subreddit": "travel", "desc": "Travel photos, stories, and trip planning.", "norms": "Include location in title; no link shorteners."},
                    {"subreddit": "earthporn", "desc": "Landscape/nature photography (SFW despite the name).", "norms": "Must be your own photo or properly credited; no people as main subject."}],
    "fashion":     [{"subreddit": "streetwear", "desc": "Streetwear fit checks and outfit posts.", "norms": "Fit check flair + full outfit breakdown in comments."},
                    {"subreddit": "femalefashionadvice", "desc": "Outfit feedback and fashion discussion.", "norms": "Detailed outfit info required in comments, not just image."}],
    "beauty":      [{"subreddit": "MakeupAddiction", "desc": "Makeup looks and tutorials.", "norms": "Detailed product list encouraged in comments."},
                    {"subreddit": "SkincareAddiction", "desc": "Skincare routines and results.", "norms": "Routine/progress details required, not just a selfie."}],
    "pets":        [{"subreddit": "aww", "desc": "Wholesome pet & animal photos, huge reach.", "norms": "No text overlays; simple/no caption titles perform best."},
                    {"subreddit": "cats", "desc": "Cat-focused community.", "norms": "Original photos only; be ready for 'tax' comment requests."}],
    "home":        [{"subreddit": "InteriorDesign", "desc": "Interior design feedback and inspiration.", "norms": "Include room dimensions/budget in comments if asking for feedback."},
                    {"subreddit": "CozyPlaces", "desc": "Cozy home aesthetic photos.", "norms": "Simple descriptive titles; no overt self-promotion."}],
    "art":         [{"subreddit": "Art", "desc": "General art sharing, all mediums.", "norms": "Title format: '[Medium], [Subject], [Artist], [Year]'."},
                    {"subreddit": "gallery", "desc": "Curated visual art / photography feed.", "norms": "High effort/quality bar; low-effort posts removed."}],
    "photography": [{"subreddit": "photography", "desc": "General photography discussion & sharing.", "norms": "Include camera/settings info in comments when asked."},
                    {"subreddit": "itookapicture", "desc": "Simple photo sharing, any subject.", "norms": "Title format '[Subject] I took I [camera]'."}],
    "business":    [{"subreddit": "smallbusiness", "desc": "Small business owners discussing growth/marketing.", "norms": "No direct advertising; participate genuinely before posting."},
                    {"subreddit": "Entrepreneur", "desc": "Startup and business-building discussion.", "norms": "Self-promo largely restricted to designated threads."}],
    "wellness":    [{"subreddit": "getmotivated", "desc": "Motivational content, image + text overlay common.", "norms": "Follow the [Image]/[Text] flair convention."},
                    {"subreddit": "DecidingToBeBetter", "desc": "Self-improvement discussion.", "norms": "Text posts favored over pure images."}],
    "general":     [{"subreddit": "InternetIsBeautiful", "desc": "Broad interesting content, high traffic.", "norms": "Strict rules on titles describing exactly what it is."},
                    {"subreddit": "mildlyinteresting", "desc": "Broad casual content community.", "norms": "No editorializing in titles."}],
}


def _match_reddit_niche(niche: str) -> list:
    n = (niche or "").strip().lower()
    if not n:
        return REDDIT_NICHE_PANELS["general"]
    for key, panel in REDDIT_NICHE_PANELS.items():
        if key == "general":
            continue
        if key in n or n in key:
            return panel
    return REDDIT_NICHE_PANELS["general"]


def _hub_hashtag_suffix(hub_hashtags: list) -> str:
    """Format selected Distribution & Tags hub hashtags as an appendable caption suffix."""
    tags = [f"#{h.lstrip('#').strip()}" for h in (hub_hashtags or []) if h and h.strip()]
    return ("\n\n" + " ".join(tags)) if tags else ""


def days_until(month: int, day: int, today: date) -> int:
    try:
        target = today.replace(month=month, day=day)
    except ValueError:
        target = today.replace(month=month, day=28)
    if target <= today:
        try:
            target = target.replace(year=target.year + 1)
        except ValueError:
            target = target.replace(year=target.year + 1, day=28)
    return (target - today).days

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------


def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")   # better concurrent read/write
    conn.execute("PRAGMA synchronous=NORMAL") # safe + faster than FULL
    conn.execute("""CREATE TABLE IF NOT EXISTS history (
        id TEXT PRIMARY KEY, created_at TEXT, thumb TEXT,
        mode TEXT, platform TEXT, results TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS usage (
        username TEXT, date TEXT, count INTEGER DEFAULT 0,
        PRIMARY KEY (username, date)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        expires TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS hubs (
        id TEXT PRIMARY KEY, platform TEXT, handle TEXT, niche TEXT,
        tier TEXT, bio_snippet TEXT, submission_rule TEXT, hashtags TEXT,
        status TEXT DEFAULT 'active', added_by TEXT, created_at TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS vaults (
        id TEXT PRIMARY KEY, name TEXT, niche TEXT, hubs TEXT, hashtags TEXT,
        owner TEXT, created_at TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS hub_reports (
        id TEXT PRIMARY KEY, hub_id TEXT NOT NULL, reason TEXT, note TEXT,
        reported_by TEXT, created_at TEXT,
        UNIQUE(hub_id, reported_by)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS creators (
        owner TEXT PRIMARY KEY, platform TEXT, handle TEXT, niche TEXT,
        tier TEXT, pitch TEXT, created_at TEXT, updated_at TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS scheduled_posts (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL, history_id TEXT,
        platform TEXT, mode TEXT, content TEXT, thumb TEXT,
        scheduled_for TEXT NOT NULL, status TEXT DEFAULT 'pending',
        notes TEXT, created_at TEXT, updated_at TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS post_metrics (
        history_id TEXT PRIMARY KEY, likes INTEGER DEFAULT 0,
        views INTEGER DEFAULT 0, comments INTEGER DEFAULT 0,
        shares INTEGER DEFAULT 0, updated_at TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS push_subscriptions (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL, endpoint TEXT NOT NULL UNIQUE,
        p256dh TEXT, auth TEXT, created_at TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS notification_log (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL, kind TEXT NOT NULL,
        ref TEXT, sent_at TEXT
    )""")
    _ensure_column(conn, "history", "posted", "INTEGER DEFAULT 0")
    _ensure_column(conn, "history", "rating", "INTEGER DEFAULT 0")
    _ensure_column(conn, "history", "posted_at", "TEXT")
    _ensure_column(conn, "history", "style", "TEXT")
    conn.commit()
    conn.close()


def _ensure_column(conn, table: str, column: str, coltype_default: str):
    """Add a column to an existing table if it doesn't already exist (simple migration helper)."""
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype_default}")


init_db()


# ---------------------------------------------------------------------------
# Push Notifications (Web Push / VAPID) — reminders for posting consistency
# ---------------------------------------------------------------------------


def _ensure_vapid_keys() -> str:
    """Generate a persistent VAPID key pair on first run and return the base64url
    public key the frontend needs for pushManager.subscribe(). Keys live on the
    Fly.io /data volume when available so subscriptions survive restarts —
    regenerating the private key would silently invalidate every subscription."""
    if VAPID_KEY_PATH.exists() and VAPID_PUB_PATH.exists():
        return VAPID_PUB_PATH.read_text().strip()
    if not HAS_WEBPUSH:
        return ""
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    vapid = Vapid01()
    vapid.generate_keys()
    VAPID_KEY_PATH.write_bytes(vapid.private_pem())
    pub_raw = vapid.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    pub_b64 = base64.urlsafe_b64encode(pub_raw).decode().rstrip("=")
    VAPID_PUB_PATH.write_text(pub_b64)
    return pub_b64


def _send_push(username: str, title: str, body: str, url: str = "/") -> None:
    """Send a Web Push notification to every device the user has subscribed on.
    Silently drops dead subscriptions (404/410 from the push service)."""
    if not HAS_WEBPUSH:
        return
    conn = sqlite3.connect(DB_PATH, timeout=10)
    rows = conn.execute("SELECT endpoint, p256dh, auth FROM push_subscriptions WHERE owner=?", (username,)).fetchall()
    conn.close()
    if not rows:
        return
    payload = json.dumps({"title": title, "body": body, "url": url})
    dead = []
    for endpoint, p256dh, auth in rows:
        try:
            webpush(
                subscription_info={"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}},
                data=payload,
                vapid_private_key=str(VAPID_KEY_PATH),
                vapid_claims={"sub": VAPID_CONTACT},
            )
        except WebPushException as e:
            status = getattr(e.response, "status_code", None)
            if status in (404, 410):
                dead.append(endpoint)
        except Exception:
            pass
    if dead:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.executemany("DELETE FROM push_subscriptions WHERE endpoint=?", [(e,) for e in dead])
        conn.commit()
        conn.close()


def _already_notified(username: str, kind: str, ref: str) -> bool:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    row = conn.execute("SELECT 1 FROM notification_log WHERE owner=? AND kind=? AND ref=?", (username, kind, ref)).fetchone()
    conn.close()
    return row is not None


def _mark_notified(username: str, kind: str, ref: str) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute(
        "INSERT OR IGNORE INTO notification_log (id, owner, kind, ref, sent_at) VALUES (?,?,?,?,?)",
        (f"{username}:{kind}:{ref}", username, kind, ref, _utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def _notify_streak_risk(username: str, settings: dict, now: datetime) -> None:
    """Nudge the user if they had an active streak coming into today and still
    haven't generated anything today, once it's getting late (>= 8pm UTC)."""
    if not settings.get("notify_streak_risk", True) or now.hour < 20:
        return
    today, yesterday = now.date(), now.date() - timedelta(days=1)
    if _already_notified(username, "streak_risk", today.isoformat()):
        return
    conn = sqlite3.connect(DB_PATH, timeout=10)
    row_today = conn.execute("SELECT count FROM usage WHERE username=? AND date=?", (username, today.isoformat())).fetchone()
    row_yday = conn.execute("SELECT count FROM usage WHERE username=? AND date=?", (username, yesterday.isoformat())).fetchone()
    conn.close()
    posted_today = bool(row_today and row_today[0] > 0)
    posted_yday = bool(row_yday and row_yday[0] > 0)
    if posted_yday and not posted_today:
        _send_push(username, "Don't lose your streak! 🔥", "You haven't posted today yet — generate something to keep your streak alive.", "/")
        _mark_notified(username, "streak_risk", today.isoformat())


def _notify_scheduled_due(username: str, settings: dict, now: datetime) -> None:
    """Nudge once when a pending Schedule Queue item's time has arrived."""
    if not settings.get("notify_scheduled_due", True):
        return
    conn = sqlite3.connect(DB_PATH, timeout=10)
    rows = conn.execute(
        "SELECT id, platform, scheduled_for FROM scheduled_posts WHERE owner=? AND status='pending'", (username,)
    ).fetchall()
    conn.close()
    for post_id, platform, scheduled_for in rows:
        if _already_notified(username, "sched_due", post_id):
            continue
        try:
            due_at = datetime.fromisoformat(scheduled_for)
        except ValueError:
            continue
        if due_at <= now:
            _send_push(username, "Scheduled post is due 📅", f"Your {platform} post from the Schedule Queue is ready to go out.", "/")
            _mark_notified(username, "sched_due", post_id)


def _notify_limit_reset(username: str, settings: dict, now: datetime) -> None:
    """Let the user know their daily generation limit has reset, if they hit it yesterday."""
    if not settings.get("notify_limit_reset", True) or now.hour != 0:
        return
    daily_limit = settings.get("daily_limit", 0)
    if not daily_limit:
        return
    today, yesterday = now.date(), now.date() - timedelta(days=1)
    if _already_notified(username, "limit_reset", today.isoformat()):
        return
    conn = sqlite3.connect(DB_PATH, timeout=10)
    row = conn.execute("SELECT count FROM usage WHERE username=? AND date=?", (username, yesterday.isoformat())).fetchone()
    conn.close()
    if row and row[0] >= daily_limit:
        _send_push(username, "Your daily limit reset ✨", "A new day, a fresh batch of generations — jump back in.", "/")
        _mark_notified(username, "limit_reset", today.isoformat())


def _notify_inactivity(username: str, settings: dict, now: datetime) -> None:
    """Gentle nudge if the user hasn't generated anything in 3+ days, at most once every 3 days."""
    if not settings.get("notify_inactivity", True) or now.hour != 15:
        return
    conn = sqlite3.connect(DB_PATH, timeout=10)
    last_row = conn.execute("SELECT MAX(created_at) FROM history").fetchone()
    last_notified_row = conn.execute(
        "SELECT MAX(sent_at) FROM notification_log WHERE owner=? AND kind='inactivity'", (username,)
    ).fetchone()
    conn.close()
    last_created = last_row[0] if last_row else None
    if not last_created:
        return
    try:
        last_dt = datetime.fromisoformat(last_created)
    except ValueError:
        return
    if now - last_dt < timedelta(days=3):
        return
    last_notified = last_notified_row[0] if last_notified_row else None
    if last_notified:
        try:
            if now - datetime.fromisoformat(last_notified) < timedelta(days=3):
                return
        except ValueError:
            pass
    _send_push(username, "We miss you! 👋", "It's been a few days — come generate some fresh content ideas.", "/")
    _mark_notified(username, "inactivity", now.date().isoformat())


_STREAK_MILESTONES = (7, 30, 100, 365)


def _notify_streak_milestone(username: str, settings: dict, now: datetime) -> None:
    """Celebrate hitting a streak milestone on the day it's reached."""
    if not settings.get("notify_streak_milestone", True):
        return
    streak = _compute_streak(username)
    if not streak["active_today"] or streak["current_streak"] not in _STREAK_MILESTONES:
        return
    current = streak["current_streak"]
    ref = f"{now.date().isoformat()}:{current}"
    if _already_notified(username, "streak_milestone", ref):
        return
    _send_push(username, f"🎉 {current}-day streak!", f"You've generated content {current} days in a row — amazing consistency.", "/")
    _mark_notified(username, "streak_milestone", ref)


def _notify_weekly_recap(username: str, settings: dict, now: datetime) -> None:
    """Monday morning summary of the past 7 days' generation activity."""
    if not settings.get("notify_weekly_recap", True) or now.weekday() != 0 or now.hour != 9:
        return
    week_key = now.date().isoformat()  # this Monday's date uniquely identifies the week
    if _already_notified(username, "weekly_recap", week_key):
        return
    conn = sqlite3.connect(DB_PATH, timeout=10)
    since = (now.date() - timedelta(days=7)).isoformat()
    row = conn.execute("SELECT SUM(count) FROM usage WHERE username=? AND date>=?", (username, since)).fetchone()
    conn.close()
    total = row[0] or 0
    if total == 0:
        return  # nothing to recap
    streak = _compute_streak(username)
    plural_gen = "" if total == 1 else "s"
    plural_day = "" if streak["current_streak"] == 1 else "s"
    _send_push(
        username, "Your week in review 📊",
        f"{total} generation{plural_gen} in the last 7 days · current streak: {streak['current_streak']} day{plural_day}.",
        "/",
    )
    _mark_notified(username, "weekly_recap", week_key)


def _notify_holiday_idea(username: str, settings: dict, now: datetime) -> None:
    """Nudge with a content idea 10-14 days before an upcoming holiday (reuses HOLIDAY_IDEAS)."""
    if not settings.get("notify_holiday_idea", True) or now.hour != 10:
        return
    today = now.date()
    for h in HOLIDAY_IDEAS:
        days_left = days_until(h["month"], h["day"], today)
        if 10 <= days_left <= 14:
            key = f"{today.year}:{h['name']}"
            if _already_notified(username, "holiday_idea", key):
                continue
            idea = h["ideas"][0] if h["ideas"] else ""
            _send_push(username, f"{h['icon']} {h['name']} is coming up", f"In {days_left} days — idea: {idea}", "/")
            _mark_notified(username, "holiday_idea", key)


def _notify_trend_alert(username: str, settings: dict, now: datetime) -> None:
    """Once-daily push surfacing one real, current trend in the user's niche.
    Requires Google Search grounding, so this only fires when the instance is
    configured to use Gemini (grounding isn't available for local/Ollama)."""
    if not settings.get("notify_trend_alert", True) or now.hour != 11:
        return
    niche = (settings.get("niche") or "").strip()
    if not niche:
        return
    cfg = load_config()
    api_key = cfg.get("gemini_api_key") or cfg.get("api_key", "")
    if cfg.get("provider") != "gemini" or not api_key:
        return
    today = now.date().isoformat()
    if _already_notified(username, "trend_alert", today):
        return
    prompt = (
        f"Use Google Search to find ONE real, currently trending topic, sound, format, or news item "
        f"relevant to a content creator whose niche is: \"{niche}\". "
        "Reply with just 1-2 short sentences naming the trend and a one-line content idea using it. "
        "No preamble, no markdown, no citations."
    )
    try:
        text = _call_gemini_grounded(api_key, cfg.get("cloud_model") or DEFAULT_GEMINI_MODEL, prompt, None, max_tokens=200)
    except Exception as e:
        print(f"[Prism] trend alert lookup failed for {username}: {e}")
        return
    text = (text or "").strip()
    if not text:
        return
    _send_push(username, "🔥 Trending in your niche", text[:180], "/")
    _mark_notified(username, "trend_alert", today)


_NOTIFY_CHECK_INTERVAL_S = 15 * 60  # check every 15 minutes; each helper self-throttles


def _run_notification_checks() -> None:
    if not HAS_WEBPUSH:
        return
    now = _utcnow()
    users = _load_users().get("users", {})
    for username in users:
        settings = _get_user_settings(username)
        if not settings.get("notifications_enabled"):
            continue
        conn = sqlite3.connect(DB_PATH, timeout=10)
        has_sub = conn.execute("SELECT 1 FROM push_subscriptions WHERE owner=? LIMIT 1", (username,)).fetchone()
        conn.close()
        if not has_sub:
            continue
        _notify_streak_risk(username, settings, now)
        _notify_scheduled_due(username, settings, now)
        _notify_limit_reset(username, settings, now)
        _notify_inactivity(username, settings, now)
        _notify_streak_milestone(username, settings, now)
        _notify_weekly_recap(username, settings, now)
        _notify_holiday_idea(username, settings, now)
        _notify_trend_alert(username, settings, now)


def _notification_worker() -> None:
    while True:
        try:
            _run_notification_checks()
        except Exception:
            pass
        time.sleep(_NOTIFY_CHECK_INTERVAL_S)


if HAS_WEBPUSH:
    _ensure_vapid_keys()
    threading.Thread(target=_notification_worker, daemon=True).start()


# ---------------------------------------------------------------------------
# Image helpers: resize + context cache
# ---------------------------------------------------------------------------

def _resize_for_ai(image_bytes: bytes, max_w: int = 854, max_h: int = 480) -> bytes:
    """Scale image down to 854×480 max (matches video pipeline resolution). Never upscales."""
    if not HAS_PILLOW:
        return image_bytes
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.width <= max_w and img.height <= max_h:
            return image_bytes
        img = img.convert("RGB")  # drop alpha for JPEG output
        img.thumbnail((max_w, max_h), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()
    except Exception:
        return image_bytes


def _inject_description(prompt: str, description: str) -> str:
    """Prepend cached image description so the model needs no image bytes."""
    return (
        "[IMAGE DESCRIPTION — use this as your visual reference for the task below]\n"
        f"{description}\n"
        "[END DESCRIPTION]\n\n"
        + prompt
    )


_CACHE_TTL = 600  # seconds (10 minutes)


class _DescCacheEntry:
    __slots__ = ("description", "expires")

    def __init__(self, description: str) -> None:
        self.description = description
        self.expires = time.monotonic() + _CACHE_TTL


_image_desc_cache: dict = {}
_prefetch_events: dict = {}   # key → threading.Event, set when description is ready
_prefetch_mutex = threading.Lock()


def _cache_key(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()[:20]


def _get_cached_description(image_bytes: bytes, cfg: dict) -> str:
    """Return cached description. Deduplicates concurrent calls — only ONE Ollama call runs per image."""
    key = _cache_key(image_bytes)
    now = time.monotonic()
    # Fast path: already cached
    entry = _image_desc_cache.get(key)
    if entry and now < entry.expires:
        return entry.description
    # Check if another thread/request is already computing this
    with _prefetch_mutex:
        if key in _prefetch_events:
            ev = _prefetch_events[key]
            am_computing = False
        else:
            ev = threading.Event()
            _prefetch_events[key] = ev
            am_computing = True
    if not am_computing:
        # Wait for the in-progress call to finish, then return its result
        ev.wait(timeout=90)
        entry = _image_desc_cache.get(key)
        if entry and time.monotonic() < entry.expires:
            return entry.description
        raise RuntimeError("Description computation did not complete")
    # We are responsible for computing it
    try:
        desc = _call_provider(
            cfg, SCENE_DESCRIBE_PROMPT, image_bytes,
            {"num_ctx": 2048, "num_predict": 200},  # concise — faster generation
        )
        _image_desc_cache[key] = _DescCacheEntry(desc)
        stale = [k for k, v in list(_image_desc_cache.items()) if time.monotonic() > v.expires]
        for k in stale:
            _image_desc_cache.pop(k, None)
        return desc
    finally:
        with _prefetch_mutex:
            _prefetch_events.pop(key, None)
        ev.set()


def make_thumb(image_bytes: bytes) -> str:
    if HAS_PILLOW:
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.thumbnail((150, 150), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
        except Exception:
            pass
    return ""


# ---------------------------------------------------------------------------
# AI Provider abstraction (Ollama / Gemini / Grok / OpenAI)
# ---------------------------------------------------------------------------

def _call_provider(cfg: dict, prompt: str, image_bytes: bytes | None, options: dict) -> str:
    provider = cfg.get("provider", "ollama") or "ollama"
    if provider == "gemini":
        api_key = cfg.get("gemini_api_key") or cfg.get("api_key", "")
        max_tok = int(options.get("num_predict", 0))
        return _call_gemini(api_key, cfg.get("cloud_model") or DEFAULT_GEMINI_MODEL, prompt, image_bytes, max_tok)
    if provider in ("grok", "openai"):
        if provider == "grok":
            api_key = cfg.get("grok_api_key") or cfg.get("api_key", "")
            # grok-2-vision-1212 was retired; grok-4.6 is xAI's current chat+vision model
            default_m, base_url = "grok-4.6", "https://api.x.ai/v1"
        else:
            api_key = cfg.get("openai_api_key") or cfg.get("api_key", "")
            # gpt-4o was OpenAI's flagship; gpt-5.6-terra balances capability/cost for the current GPT-5.6 family
            default_m, base_url = "gpt-5.6-terra", None
        return _call_openai_compat(api_key, cfg.get("cloud_model") or default_m, prompt, image_bytes, base_url)
    client = ollama_client.Client(host=cfg["ollama_host"]) if HAS_OLLAMA else None
    model = cfg["vision_model"]
    if not HAS_OLLAMA and provider == "ollama":
        raise HTTPException(503, "Ollama is not available on this server. Configure a cloud provider (Gemini/OpenAI) in Settings.")
    if image_bytes:
        resp = client.chat(model=model, messages=[{"role": "user", "content": prompt, "images": [image_bytes]}], options=options)
        return resp.message.content.strip()
    try:
        resp2 = client.generate(model=model, prompt=prompt, options=options)
        return resp2.response.strip()
    except Exception:
        resp = client.chat(model=model, messages=[{"role": "user", "content": prompt}], options=options)
        return resp.message.content.strip()


def _is_gemini_overloaded(e: Exception) -> bool:
    """True for transient Gemini errors worth retrying: 500/503/504 server errors,
    and client-side read timeouts (httpx), which show up as plain TimeoutError-style
    exceptions with no .code attribute at all."""
    if getattr(e, "code", None) in (500, 503, 504):
        return True
    if isinstance(e, (httpx.TimeoutException, httpx.ConnectError)):
        return True
    msg = str(e)
    return any(s in msg for s in ("503", "504", "UNAVAILABLE", "DEADLINE_EXCEEDED", "timed out")) or "overloaded" in msg.lower()


def _gemini_retry(fn, max_attempts: int = 3, base_delay: float = 1.0):
    """Gemini occasionally returns 503 'model is overloaded' for a few seconds under
    load — retry with a short exponential backoff before giving up."""
    delay = base_delay
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as e:
            if attempt == max_attempts - 1 or not _is_gemini_overloaded(e):
                raise
            print(f"[Prism] Gemini overloaded, retrying ({attempt + 1}/{max_attempts - 1}) in {delay}s")
            time.sleep(delay)
            delay *= 2


def _call_gemini(api_key: str, model: str, prompt: str, image_bytes: bytes | None, max_tokens: int = 0) -> str:
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise HTTPException(503, "Install: pip install google-genai")
    if not api_key:
        raise HTTPException(400, "Gemini API key not set in Settings")
    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MS))
    parts = []
    if image_bytes and HAS_PILLOW:
        buf = io.BytesIO()
        Image.open(io.BytesIO(image_bytes)).convert("RGB").save(buf, format="JPEG")
        parts.append(types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=buf.getvalue())))
    parts.append(types.Part(text=prompt))
    cfg_kw: dict = {"max_output_tokens": max_tokens} if max_tokens > 0 else {}
    try:
        resp = _gemini_retry(lambda: client.models.generate_content(
            model=model,
            contents=[types.Content(parts=parts, role="user")],
            config=types.GenerateContentConfig(**cfg_kw),
        ))
        return resp.text.strip()
    except ValueError as ve:
        # Gemini returns a blocked response — .text raises ValueError
        raise HTTPException(400, f"Gemini content filtered: {ve}")
    except Exception as ge:
        print(f"[Prism] Gemini error: {ge}")
        raise HTTPException(503, f"Gemini error: {ge}")


def _call_openai_compat(api_key: str, model: str, prompt: str, image_bytes: bytes | None, base_url: str | None) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        raise HTTPException(503, "Install: pip install openai")
    if not api_key: raise HTTPException(400, "API key not set in Settings")
    kw: dict = {"api_key": api_key, "timeout": OPENAI_TIMEOUT_S}
    if base_url: kw["base_url"] = base_url
    cl = OpenAI(**kw)
    content = [{"type": "text", "text": prompt},
               {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(image_bytes).decode()}"}}] if image_bytes else prompt  # type: ignore
    return cl.chat.completions.create(model=model, messages=[{"role": "user", "content": content}]).choices[0].message.content.strip()  # type: ignore

# ---------------------------------------------------------------------------
# Image generation helpers (Pose Series preview)
# ---------------------------------------------------------------------------

def _gen_image_openai(cfg: dict, prompt: str, reference_bytes: bytes | None = None) -> dict:
    """Generate a preview image using OpenAI's gpt-image-2, editing from a reference image if provided."""
    try:
        from openai import OpenAI
    except ImportError:
        print("[Prism] openai package not found in venv — run: F:\\QUE\\.venv\\Scripts\\pip.exe install openai")
        raise HTTPException(400, "openai package not installed. Run: F:\\QUE\\.venv\\Scripts\\pip.exe install openai")
    api_key = cfg.get("openai_api_key") or cfg.get("api_key", "")
    if not api_key:
        raise HTTPException(400, "OpenAI API key not set in Settings")
    try:
        cl = OpenAI(api_key=api_key, timeout=OPENAI_IMAGE_TIMEOUT_S)
        # If a reference image is provided, use gpt-image-2's edit endpoint for face/body consistency.
        # gpt-image-2 always processes inputs at high fidelity and doesn't require square inputs.
        if reference_bytes:
            try:
                png_buf = io.BytesIO(reference_bytes)
                if HAS_PILLOW:
                    png_buf = io.BytesIO()
                    Image.open(io.BytesIO(reference_bytes)).convert("RGBA").save(png_buf, format="PNG")
                png_buf.seek(0)
                png_buf.name = "reference.png"
                # 4000 chars (not the old 1000) — the pose-specific instructions and consistency
                # rules are appended AFTER a long subject-appearance preamble, so a short cap
                # was silently truncating away the actual per-pose pose/camera direction and the
                # background/held-item consistency rules on every call.
                edit_resp = cl.images.edit(model="gpt-image-2", image=png_buf, prompt=prompt[:4000], n=1, size="1024x1024")
                b64 = edit_resp.data[0].b64_json
                if b64:
                    return {"image_b64": f"data:image/png;base64,{b64}"}
            except Exception as ref_err:
                print(f"[Prism] gpt-image-2 edit failed ({ref_err}), falling back to generate")
        # gpt-image-2 always returns b64_json (no response_format/url option like dall-e-3 had)
        resp = cl.images.generate(model="gpt-image-2", prompt=prompt, n=1, size="1024x1024", quality="high")
        b64 = resp.data[0].b64_json
        if b64:
            return {"image_b64": f"data:image/png;base64,{b64}"}
        raise ValueError("gpt-image-2 returned no image data")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Prism] OpenAI image gen error: {e}")
        raise HTTPException(503, f"OpenAI image generation failed: {e}")


def _gen_image_gemini(cfg: dict, prompt: str, reference_bytes: bytes | None = None) -> dict:
    """Generate a preview image using Gemini's native image generation via google-genai package.
    When reference_bytes is given, the original photo is sent as an actual image input alongside
    the prompt so the model edits it directly (image-to-image) instead of generating from text
    alone — this is what keeps the face/tattoos pixel-anchored to the source photo."""
    try:
        from google import genai as gai
        from google.genai import types as gtypes
    except ImportError:
        raise HTTPException(400, "google-genai package not installed. Run: pip install google-genai")
    api_key = cfg.get("gemini_api_key") or cfg.get("api_key", "")
    if not api_key:
        raise HTTPException(400, "Gemini API key not set in Settings")
    try:
        client = gai.Client(api_key=api_key)
        parts = []
        if reference_bytes:
            img_bytes = reference_bytes
            if HAS_PILLOW:
                buf = io.BytesIO()
                Image.open(io.BytesIO(reference_bytes)).convert("RGB").save(buf, format="JPEG")
                img_bytes = buf.getvalue()
            parts.append(gtypes.Part(inline_data=gtypes.Blob(mime_type="image/jpeg", data=img_bytes)))
        parts.append(gtypes.Part(text=prompt))
        response = client.models.generate_content(
            model="gemini-3.1-flash-image",
            contents=[gtypes.Content(parts=parts, role="user")],
            config=gtypes.GenerateContentConfig(response_modalities=["Image"]),
        )
        for part in response.candidates[0].content.parts:
            if getattr(part, "inline_data", None) and part.inline_data.data:
                b64 = base64.b64encode(part.inline_data.data).decode()
                mime = part.inline_data.mime_type or "image/png"
                return {"image_b64": f"data:{mime};base64,{b64}"}
        raise ValueError("Gemini returned no image data")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Prism] Gemini image gen error: {e}")
        raise HTTPException(503, f"Gemini image generation failed: {e}")


def _gen_image_grok(cfg: dict, prompt: str, reference_bytes: bytes | None = None) -> dict:
    """Generate a preview image using xAI's Grok Imagine model.
    When reference_bytes is given, calls xAI's dedicated /v1/images/edits REST endpoint
    (not exposed by the OpenAI SDK's images.edit(), which expects a different multipart
    shape) with the source photo as a base64 data URI, so Grok edits the real pixels
    instead of generating a fresh image from a text description alone."""
    api_key = cfg.get("grok_api_key") or cfg.get("api_key", "")
    if not api_key:
        raise HTTPException(400, "Grok API key not set in Settings")
    try:
        if reference_bytes:
            img_bytes = reference_bytes
            if HAS_PILLOW:
                buf = io.BytesIO()
                Image.open(io.BytesIO(reference_bytes)).convert("RGB").save(buf, format="JPEG")
                img_bytes = buf.getvalue()
            data_uri = f"data:image/jpeg;base64,{base64.b64encode(img_bytes).decode()}"
            resp = httpx.post(
                "https://api.x.ai/v1/images/edits",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": "grok-imagine-image-2.0", "prompt": prompt[:4000],
                      "image": {"url": data_uri, "type": "image_url"}},
                timeout=OPENAI_IMAGE_TIMEOUT_S,
            )
            resp.raise_for_status()
            item = resp.json()["data"][0]
        else:
            from openai import OpenAI
            cl = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1", timeout=OPENAI_IMAGE_TIMEOUT_S)
            resp2 = cl.images.generate(model="grok-imagine-image-2.0", prompt=prompt, n=1)
            item = resp2.data[0].model_dump() if hasattr(resp2.data[0], "model_dump") else resp2.data[0]
        b64 = item.get("b64_json") if isinstance(item, dict) else getattr(item, "b64_json", None)
        if b64:
            return {"image_b64": f"data:image/png;base64,{b64}"}
        url = item.get("url") if isinstance(item, dict) else getattr(item, "url", None)
        if url:
            import urllib.request as _ur
            # some CDNs reject requests with urllib's default User-Agent
            req = _ur.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with _ur.urlopen(req, timeout=30) as r:
                b64 = base64.b64encode(r.read()).decode()
            return {"image_b64": f"data:image/png;base64,{b64}"}
        raise ValueError("Grok Imagine returned neither b64_json nor url")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Prism] Grok image gen error: {e}")
        raise HTTPException(503, f"Grok image generation failed: {e}")

# ---------------------------------------------------------------------------
# Two-pass pose editing: pose-change providers (above) often distort or drop
# small fine details (face identity, tattoos, logos, on-image text) when they
# move the subject. These helpers detect those regions in the pose-changed
# image and re-render just those regions to match the original photo, via a
# mask-guided OpenAI edit. Held items/products are only included when the
# caller opts in (content_type product/ugc) — forcing them back in for a
# plain creator pose series caused hallucinated objects in hands when a new
# pose no longer naturally held the original item.
# ---------------------------------------------------------------------------

def _detect_edit_regions(cfg: dict, image_bytes: bytes, include_product: bool = False) -> list:
    """Ask Gemini to locate faces, tattoos, logos, and readable text in image_bytes (plus
    the held/worn product when include_product is set, for product/UGC content), returning
    bounding boxes normalized to 0-1000 (Gemini's convention). Best-effort: returns [] if
    Gemini isn't configured or detection fails, so callers can just skip the restoration
    pass rather than fail the whole request."""
    api_key = cfg.get("gemini_api_key", "")
    if not (api_key and HAS_PILLOW):
        return []
    try:
        from google import genai as gai
        from google.genai import types as gtypes
    except ImportError:
        return []
    try:
        client = gai.Client(api_key=api_key, http_options=gtypes.HttpOptions(timeout=GEMINI_TIMEOUT_MS))
        buf = io.BytesIO()
        Image.open(io.BytesIO(image_bytes)).convert("RGB").save(buf, format="JPEG")
        if include_product:
            prompt = (
                "Detect every instance of: a person's face, a visible tattoo, a logo or brand mark, "
                "readable text or wording (on clothing, signage, packaging, etc.), and the held/worn "
                "product itself. Return ONLY a JSON array, each entry shaped like "
                '{"label": "face", "box_2d": [ymin, xmin, ymax, xmax]}, where label is one of '
                '"face", "tattoo", "logo", "text", "product", and box_2d is normalized to 0-1000. '
                "No markdown, no other text, just the JSON array (use [] if nothing is found)."
            )
        else:
            prompt = (
                "Detect every instance of: a person's face, a visible tattoo, a logo or brand mark, or "
                "readable text or wording (on clothing, signage, packaging, etc.). Do NOT detect hands, "
                "held items, or products — only these four identity/branding categories. Return ONLY a "
                'JSON array, each entry shaped like {"label": "face", "box_2d": [ymin, xmin, ymax, xmax]}, '
                'where label is one of "face", "tattoo", "logo", "text", and box_2d is normalized to 0-1000. '
                "No markdown, no other text, just the JSON array (use [] if nothing is found)."
            )
        resp = client.models.generate_content(
            model=DEFAULT_GEMINI_MODEL,
            contents=[gtypes.Content(parts=[
                gtypes.Part(inline_data=gtypes.Blob(mime_type="image/jpeg", data=buf.getvalue())),
                gtypes.Part(text=prompt),
            ], role="user")],
            config=gtypes.GenerateContentConfig(response_mime_type="application/json"),
        )
        boxes = json.loads((resp.text or "[]").strip())
        return boxes if isinstance(boxes, list) else []
    except Exception as e:
        print(f"[Prism] Region detection failed ({e}), skipping identity-restore pass")
        return []


def _boxes_to_mask_png(width: int, height: int, boxes: list) -> bytes:
    """Build an OpenAI-compatible RGBA mask: opaque (255) = keep the pose-changed pixels,
    transparent (0) = regenerate. Detected regions get light padding/feathering only —
    just enough to blend the edit seam, since OpenAI's masking is prompt-guided rather
    than a hard pixel constraint, so a larger mask gives the model more room to drift
    the pose/composition beyond the intended region."""
    mask = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(mask)
    for b in boxes:
        box = b.get("box_2d") if isinstance(b, dict) else None
        if not (isinstance(box, list) and len(box) == 4):
            continue
        ymin, xmin, ymax, xmax = box
        x0, y0 = xmin / 1000 * width, ymin / 1000 * height
        x1, y1 = xmax / 1000 * width, ymax / 1000 * height
        pad_x, pad_y = (x1 - x0) * 0.03, (y1 - y0) * 0.03
        draw.rectangle([max(0, x0 - pad_x), max(0, y0 - pad_y), min(width, x1 + pad_x), min(height, y1 + pad_y)], fill=0)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=max(1, int(min(width, height) * 0.004))))
    rgba = Image.new("RGBA", (width, height))
    rgba.putalpha(mask)
    out = io.BytesIO()
    rgba.save(out, format="PNG")
    return out.getvalue()


def _crop_identity_reference(image_bytes: bytes, boxes: list) -> bytes | None:
    """Crop the original reference photo down to just the union of its detected
    face/tattoo/logo/text regions (generously padded), instead of sending the
    whole photo as a second images.edit() reference. A full reference image has its own
    (different) pose/framing/background, and since OpenAI's masking is prompt-guided
    rather than a hard pixel constraint, sending the whole photo risks the model blending
    that entire composition back in — which looked like the pose-changed result reverting
    to the original image. A tight identity-only crop removes that competing context."""
    if not (boxes and HAS_PILLOW):
        return None
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        width, height = img.size
        xs0, ys0, xs1, ys1 = [], [], [], []
        for b in boxes:
            box = b.get("box_2d") if isinstance(b, dict) else None
            if not (isinstance(box, list) and len(box) == 4):
                continue
            ymin, xmin, ymax, xmax = box
            xs0.append(xmin / 1000 * width); ys0.append(ymin / 1000 * height)
            xs1.append(xmax / 1000 * width); ys1.append(ymax / 1000 * height)
        if not xs0:
            return None
        x0, y0, x1, y1 = min(xs0), min(ys0), max(xs1), max(ys1)
        # Modest padding only — a wide crop drags in extra head/neck context (angle, tilt)
        # from the reference photo's own pose, which risks getting copied into the restore.
        pad_x, pad_y = (x1 - x0) * 0.2, (y1 - y0) * 0.2
        crop = img.crop((max(0, x0 - pad_x), max(0, y0 - pad_y), min(width, x1 + pad_x), min(height, y1 + pad_y)))
        buf = io.BytesIO()
        crop.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


def _restore_identity_openai(cfg: dict, base_image_bytes: bytes, boxes: list, original_reference_bytes: bytes | None) -> dict:
    """Second pass: re-render just the masked regions (face/tattoo/logo/text) of an
    already pose-changed image so they match the original reference photo, via OpenAI's
    gpt-image-2 mask-guided edit (images.edit with mask + the original photo as a second
    reference image). Falls back to returning base_image_bytes unchanged on any failure so
    a broken restore pass never loses the pass-1 result."""
    passthrough = {"image_b64": f"data:image/png;base64,{base64.b64encode(base_image_bytes).decode()}"}
    if not (boxes and HAS_PILLOW):
        return passthrough
    api_key = cfg.get("openai_api_key", "")
    if not api_key:
        print("[Prism] Skipping identity-restore pass: no OpenAI API key configured")
        return passthrough
    try:
        from openai import OpenAI
    except ImportError:
        return passthrough
    try:
        base_img = Image.open(io.BytesIO(base_image_bytes)).convert("RGBA")
        width, height = base_img.size
        base_buf = io.BytesIO(); base_img.save(base_buf, format="PNG"); base_buf.seek(0); base_buf.name = "posed.png"
        mask_buf = io.BytesIO(_boxes_to_mask_png(width, height, boxes)); mask_buf.name = "mask.png"
        labels = sorted({b.get("label", "region") for b in boxes if isinstance(b, dict)})
        label_desc = {
            "face": "the same facial identity/likeness (eyes, nose, mouth shape, skin tone, facial "
                    "structure) — but keep the exact head angle, tilt, rotation, and expression from "
                    "the FIRST image; do NOT rotate or re-angle the head to match the reference photo's "
                    "head angle, that would change the pose",
            "tattoo": "same tattoos in the same location and shape",
            "logo": "same logos positioned identically",
            "text": "same readable text spelled and positioned identically",
            "product": "the exact same product — same shape, color, packaging, and every letter of its logo/label text",
        }
        identity_line = "; ".join(label_desc.get(l, l) for l in labels)
        prompt = (
            "ABSOLUTE RULE, HIGHEST PRIORITY: Do NOT change the body pose, posture, limb positions, "
            "head angle/tilt/rotation, camera angle, framing, or crop AT ALL — not even slightly. This "
            "is a tiny detail touch-up on small masked regions only, not a re-pose or re-composition. "
            "The head/face must stay at the SAME angle and orientation it has in the FIRST image — "
            "never rotate it toward the angle shown in the second (reference) image; the reference "
            "image's pose and head angle are irrelevant and must be completely ignored, only its "
            "identity/likeness details matter. "
            "This is a mask-guided touch-up edit, not a new image. The FIRST image is the only "
            "composition that matters — keep its exact pose, camera angle, framing, and background "
            "unchanged pixel-for-pixel in every area outside the masked regions. The SECOND image is "
            "ONLY an identity reference crop for the masked regions (" + ", ".join(labels) + ") — ignore "
            "its framing, pose, head angle, and background entirely, and do not let it influence anything "
            "outside the mask, including nearby pose/limb position or head orientation. "
            "Using it only as an identity reference, restore the masked regions to match: " + identity_line + ". "
            "Do NOT add any object, jewelry, prop, or held item that is not already visible in the first "
            "image's masked region — never invent new content, only restore identity fidelity. Keep every "
            "pixel outside the masked regions exactly as it is in the first image, and keep the exact same "
            "pose, head angle, and framing inside the masked regions too — only the identity details listed "
            "above may change."
        )
        images_arg = [base_buf]
        if original_reference_bytes:
            ref_img = Image.open(io.BytesIO(original_reference_bytes)).convert("RGBA")
            ref_buf = io.BytesIO(); ref_img.save(ref_buf, format="PNG"); ref_buf.seek(0); ref_buf.name = "reference.png"
            images_arg.append(ref_buf)
        cl = OpenAI(api_key=api_key, timeout=OPENAI_IMAGE_TIMEOUT_S)
        # quality="high" (not "medium") — better instruction-following matters more than the extra
        # latency here, since this small touch-up pass is exactly where pose drift was happening.
        resp = cl.images.edit(model="gpt-image-2", image=images_arg, mask=mask_buf, prompt=prompt[:4000], n=1, size="auto", quality="high")
        b64 = resp.data[0].b64_json
        if b64:
            return {"image_b64": f"data:image/png;base64,{b64}"}
    except Exception as e:
        print(f"[Prism] Identity-restore pass failed ({e}), keeping pass-1 result")
    return passthrough


# ---------------------------------------------------------------------------
# Background job tracking for the (slow) identity-restore pass — pass-1 image
# returns to the client immediately; restoration runs after the response via
# FastAPI's BackgroundTasks and is picked up later by polling or push notification.
# In-memory dict is fine since Fly.io runs a single instance (min_machines_running=1).
# ---------------------------------------------------------------------------
_image_jobs_lock = threading.Lock()
_image_jobs: dict[str, dict] = {}
_IMAGE_JOB_TTL_S = 3600  # prune finished jobs after an hour


def _prune_image_jobs() -> None:
    cutoff = time.time() - _IMAGE_JOB_TTL_S
    for jid in [j for j, v in _image_jobs.items() if v.get("created", 0) < cutoff]:
        _image_jobs.pop(jid, None)


def _run_restore_job(job_id: str, cfg: dict, posed_bytes: bytes, reference_bytes: bytes, username: str, content_type: str = "creator") -> None:
    include_product = content_type in ("product", "ugc")
    try:
        boxes = _detect_edit_regions(cfg, posed_bytes, include_product=include_product)
        if boxes:
            # Crop the reference photo to just its own identity regions (its face/tattoo
            # position differs from the posed image since the pose changed) so the restore
            # edit only ever sees a tight identity reference, never the reference's full
            # pose/background — see _crop_identity_reference for why this matters.
            ref_boxes = _detect_edit_regions(cfg, reference_bytes, include_product=include_product)
            reference_for_restore = _crop_identity_reference(reference_bytes, ref_boxes) or reference_bytes
            result = _restore_identity_openai(cfg, posed_bytes, boxes, reference_for_restore)
        else:
            result = {"image_b64": f"data:image/png;base64,{base64.b64encode(posed_bytes).decode()}"}
        with _image_jobs_lock:
            _image_jobs[job_id] = {"status": "done", "image_b64": result["image_b64"], "created": time.time()}
        _send_push(username, "Pose image details restored", "Face/tattoo/logo touch-up is ready — tap to view.", "/")
    except Exception as e:
        print(f"[Prism] Background restore job {job_id} failed: {e}")
        with _image_jobs_lock:
            _image_jobs[job_id] = {"status": "error", "error": str(e), "created": time.time()}

# ---------------------------------------------------------------------------
# Brand research addons — injected into post prompts for product/ugc
# ---------------------------------------------------------------------------

# Gemini: uses Google Search grounding to look up real brand info in the same call
_BRAND_ADDON_GEMINI = (
    "\n\nBRAND RESEARCH REQUIRED: Identify any brand name, product name, or company logo "
    "visible in this image (clothing label, bottle, packaging, hat logo, tag, etc.). "
    "Use Google Search to find real current information about that brand: their official tagline, "
    "target customer, signature products, and brand personality. "
    "Weave this verified brand knowledge naturally into the caption. "
    "Do not guess or make up brand facts."
)

# Ollama: uses the model's training knowledge about the brand
_BRAND_ADDON_LOCAL = (
    "\n\nBRAND AWARENESS: If you can see a brand name, product, or logo in this image, "
    "use your knowledge of that brand (tagline, target customer, what they sell, brand personality) "
    "to write a more specific and authentic caption. "
    "Knowing the brand always beats writing a generic caption."
)


def _call_gemini_grounded(api_key: str, model: str, prompt: str, image_bytes: bytes | None, max_tokens: int = 0, url: str = "") -> str:
    """Gemini call with Google Search grounding + optional URL context for brand websites."""
    try:
        from google import genai as _gai
        from google.genai import types as _gt
    except ImportError:
        return _call_gemini(api_key, model, prompt, image_bytes, max_tokens)
    if not api_key:
        raise HTTPException(400, "Gemini API key not set in Settings")
    try:
        client = _gai.Client(api_key=api_key, http_options=_gt.HttpOptions(timeout=GEMINI_TIMEOUT_MS))
        parts = []
        if image_bytes and HAS_PILLOW:
            buf = io.BytesIO()
            Image.open(io.BytesIO(image_bytes)).convert("RGB").save(buf, format="JPEG")
            parts.append(_gt.Part(inline_data=_gt.Blob(mime_type="image/jpeg", data=buf.getvalue())))
        active_prompt = prompt
        if url.strip():
            active_prompt = f"Visit {url.strip()} to research this brand, then use what you find.\n\n" + prompt
        parts.append(_gt.Part(text=active_prompt))
        tools = [_gt.Tool(google_search=_gt.GoogleSearch())]
        if url.strip():
            tools.append(_gt.Tool(url_context=_gt.UrlContext()))
        cfg_kw: dict = {"tools": tools}
        if max_tokens > 0:
            cfg_kw["max_output_tokens"] = max_tokens
        resp = client.models.generate_content(
            model=model,
            contents=[_gt.Content(parts=parts, role="user")],
            config=_gt.GenerateContentConfig(**cfg_kw),
        )
        return resp.text.strip()
    except Exception as e:
        print(f"[Prism] Gemini grounded call failed ({e}), falling back to standard call")
        return _call_gemini(api_key, model, prompt, image_bytes, max_tokens)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ImageGenRequest(BaseModel):
    prompt: str
    reference_b64: Optional[str] = None
    mode: str = ""  # e.g. 'pose_series' to apply consistency rules
    # Temporarily disabled by default — pass-2's mask-guided restore was still altering the
    # pose/head angle too much, and pass-1 alone is already keeping the face accurate enough.
    restore_details: bool = False  # auto-detect + fix face/tattoos/logos/text/products after a pose change
    content_type: str = "creator"  # "product"/"ugc" locks the product+logo+text in place across poses


class PrefetchRequest(BaseModel):
    image_b64: str


class GenerateRequest(BaseModel):
    image_b64: str
    mode: str
    platform: str = "general"
    hashtags: bool = True
    guidance: str = ""
    language: str = "en"
    variants: bool = False
    style: str = ""
    hashtag_set: bool = False
    content_type: str = "creator"
    search_brand: bool = False  # search/use brand info for product and UGC captions
    brand_url: str = ""  # optional brand website URL for URL context tool
    hub_hashtags: list = []  # required hashtags from selected Distribution & Tags hubs
    cached_pose_series: str = ""  # pose text the frontend already pre-fetched on step 1 -> skip re-generating it


class SettingsUpdate(BaseModel):
    ollama_host: Optional[str] = None
    vision_model: Optional[str] = None
    provider: Optional[str] = None
    api_key: Optional[str] = None
    cloud_model: Optional[str] = None


class UserSettingsUpdate(BaseModel):
    enabled_modes: Optional[list] = None
    gender: Optional[str] = None
    signature: Optional[str] = None   # brand signature appended to captions
    brand_voice: Optional[str] = None  # writing style examples injected into prompt
    notifications_enabled: Optional[bool] = None
    notify_streak_risk: Optional[bool] = None
    notify_scheduled_due: Optional[bool] = None
    notify_limit_reset: Optional[bool] = None
    notify_inactivity: Optional[bool] = None
    notify_streak_milestone: Optional[bool] = None
    notify_weekly_recap: Optional[bool] = None
    notify_personal_best: Optional[bool] = None
    notify_holiday_idea: Optional[bool] = None
    notify_trend_alert: Optional[bool] = None
    niche: Optional[str] = None


class PushSubscribeRequest(BaseModel):
    endpoint: str
    keys: dict


class PushUnsubscribeRequest(BaseModel):
    endpoint: str


class LoginRequest(BaseModel):
    username: str
    password: str


class DeleteAccountRequest(BaseModel):
    password: str


class ExpandRequest(BaseModel):
    keywords: str
    prompt_type: str = "post"
    platform: str = "general"
    hashtags: bool = True


class HubCreate(BaseModel):
    handle: str
    niche: str
    tier: str = "micro"
    platform: str = "instagram"
    bio_snippet: str = ""
    submission_rule: str = ""
    hashtags: list = []


class VaultCreate(BaseModel):
    name: str
    niche: str = ""
    hubs: list = []
    hashtags: list = []


class HubReport(BaseModel):
    reason: str = "inactive"
    note: str = ""


HUB_REPORT_REASONS = {"inactive", "not_accepting", "spam", "other"}
HUB_FLAG_THRESHOLD = 3  # distinct reporters before a hub is auto-flagged for review
HUB_PLATFORMS = {"instagram", "tiktok"}


class CreatorProfile(BaseModel):
    platform: str = "instagram"
    handle: str
    niche: str
    tier: str = "micro"
    pitch: str = ""

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/prefetch")
def prefetch_route(req: PrefetchRequest, request: Request):
    """Pre-compute and cache image description. Call after upload to warm the cache before Generate."""
    token = request.cookies.get("que_session")
    if not _get_session(token):
        return {"ok": False, "reason": "not authenticated"}
    try:
        b64_data = req.image_b64.split(",")[-1]
        image_bytes = _resize_for_ai(base64.b64decode(b64_data))
        cfg = load_config()
        _get_cached_description(image_bytes, cfg)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "reason": str(e)}


@app.post("/api/generate-image")
def generate_image_route(req: ImageGenRequest, request: Request, background_tasks: BackgroundTasks):
    """Generate a preview image from a pose prompt using the configured cloud AI provider."""
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401, "Unauthorized")
    if not req.prompt.strip():
        raise HTTPException(400, "prompt required")
    cfg = load_config()
    # Decode reference image and extract appearance description for better likeness
    reference_bytes: bytes | None = None
    enriched_prompt = req.prompt
    if req.reference_b64:
        try:
            ref_data = req.reference_b64.split(",")[-1]
            reference_bytes = base64.b64decode(ref_data)
            provider_check = cfg.get("provider", "ollama")
            if provider_check == "ollama" and HAS_OLLAMA:
                appearance = _call_provider(cfg, APPEARANCE_EXTRACT_PROMPT, reference_bytes, {"num_ctx": 2048, "num_predict": 150})
                if appearance.strip():
                    enriched_prompt = f"SUBJECT REFERENCE — maintain this exact appearance for the person: {appearance.strip()}\n\n{req.prompt}"
            elif provider_check == "gemini":
                appearance = _call_gemini(cfg.get("gemini_api_key", ""), cfg.get("cloud_model") or DEFAULT_GEMINI_MODEL, APPEARANCE_EXTRACT_PROMPT, reference_bytes)
                if appearance.strip():
                    enriched_prompt = f"SUBJECT REFERENCE — {appearance.strip()}\n\n{req.prompt}"
            elif provider_check == "grok":
                # grok now also gets the raw reference image via /v1/images/edits (see _gen_image_grok),
                # but the text description is still appended as extra reinforcement of face/tattoo details
                appearance = _call_provider(cfg, APPEARANCE_EXTRACT_PROMPT, reference_bytes, {"num_predict": 150})
                if appearance.strip():
                    enriched_prompt = f"SUBJECT REFERENCE — {appearance.strip()}\n\n{req.prompt}"
            elif provider_check == "openai":
                # gpt-image-2 also gets the raw reference image via images.edit() (see _gen_image_openai),
                # but the text description is still appended as extra reinforcement of face/tattoo details
                appearance = _call_provider(cfg, APPEARANCE_EXTRACT_PROMPT, reference_bytes, {"num_predict": 150})
                if appearance.strip():
                    enriched_prompt = f"SUBJECT REFERENCE — {appearance.strip()}\n\n{req.prompt}"
        except Exception as e:
            print(f"[Prism] Reference processing error: {e}")
    # For pose series: append consistency rules to keep background, tattoos, held items unchanged.
    # Product/UGC content additionally locks the product itself + its logo/text in place, since
    # losing or redesigning the featured product across poses defeats the point of that content type.
    if req.mode == "pose_series" and req.reference_b64:
        enriched_prompt = enriched_prompt.rstrip() + POSE_CONSISTENCY_RULES
        if req.content_type in ("product", "ugc"):
            enriched_prompt = enriched_prompt.rstrip() + PRODUCT_LOCK_RULES
    provider = cfg.get("provider", "ollama")
    if provider == "openai":
        result = _gen_image_openai(cfg, enriched_prompt, reference_bytes)
    elif provider == "gemini":
        result = _gen_image_gemini(cfg, enriched_prompt, reference_bytes)
    elif provider == "grok":
        result = _gen_image_grok(cfg, enriched_prompt, reference_bytes)
    else:
        raise HTTPException(400, "Image generation requires a cloud provider. Go to Settings and configure OpenAI or Gemini.")
    # Pass 2 (face/tattoo/logo/text restore) is slow (Gemini detection + up to ~2min
    # OpenAI masked edit), so don't block the response on it — return pass-1's image right away
    # and finish the restore in the background; the client polls /api/generate-image/status/{job_id}
    # (and/or gets a push notification) for the touched-up result.
    result["restore_job_id"] = None
    if req.mode == "pose_series" and reference_bytes and req.restore_details:
        job_id = uuid.uuid4().hex
        with _image_jobs_lock:
            _prune_image_jobs()
            _image_jobs[job_id] = {"status": "pending", "created": time.time()}
        posed_bytes = base64.b64decode(result["image_b64"].split(",")[-1])
        background_tasks.add_task(_run_restore_job, job_id, cfg, posed_bytes, reference_bytes, session["username"], req.content_type)
        result["restore_job_id"] = job_id
    return result


@app.get("/api/generate-image/status/{job_id}")
def generate_image_status(job_id: str, request: Request):
    """Poll for the background identity-restore pass started by /api/generate-image."""
    token = request.cookies.get("que_session")
    if not _get_session(token):
        raise HTTPException(401, "Unauthorized")
    with _image_jobs_lock:
        job = _image_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Unknown or expired job")
    return job


# ---------------------------------------------------------------------------
# Appearance extraction for pose image reference
# ---------------------------------------------------------------------------

APPEARANCE_EXTRACT_PROMPT = (
    "Analyze this image and describe it comprehensively for AI image generation consistency reference.\n"
    "Cover in one paragraph:\n"
    "FACE: face shape, eye color/shape, nose, lips, jawline, distinctive features, approximate age.\n"
    "HAIR: exact color (specific shade), length, texture (straight/wavy/curly), style.\n"
    "SKIN: exact tone descriptor (e.g. 'light olive', 'deep warm brown'). Body type and build.\n"
    "TATTOOS: list EVERY visible tattoo with its EXACT body location "
    "(e.g. 'full sleeve tattoo covering entire right arm', 'rose on inner left wrist', 'script on right collarbone'). "
    "If no tattoos are visible, write NONE.\n"
    "HANDS AND HELD ITEMS: describe everything the person is holding or wearing on their hands. "
    "Specify which hand and how each item is held. If the hands are empty, write EMPTY — do not invent an item.\n"
    "OUTFIT: full clothing description.\n"
    "BACKGROUND: describe the exact background, setting, and environment.\n"
    "Output ONLY the dense description. No other text."
)

POSE_CONSISTENCY_RULES = (
    "\n\nCRITICAL CONSISTENCY RULES — THIS IS AN EDIT OF THE ATTACHED SOURCE PHOTO, NOT A NEW IMAGE. "
    "Reuse the source photo's actual pixels for everything below and ONLY change the body pose:\n"
    "• FACE: The face must be a pixel-perfect, identical match to the source photo — same identity, "
    "same facial structure, same eyes/nose/lips/jawline, same skin tone and texture. Do not regenerate, "
    "beautify, morph, or reinterpret the face.\n"
    "• TATTOOS: ALL tattoos are part of the skin surface, not a separate overlay — they must stay at their "
    "EXACT same body location and warp, foreshorten, and follow the muscle/skin contour naturally as the limb "
    "moves or rotates, exactly like real skin ink would. Do NOT add, remove, flatten, float, misplace, or leave "
    "tattoos looking pasted-on when the pose changes.\n"
    "• HANDS: Render hands with the correct number of fingers, natural anatomy, and nothing extra. Do NOT "
    "invent, add, or place any object, jewelry, phone, prop, or held item in either hand unless that exact item "
    "is clearly visible in the source photo — if the source photo's hands are empty, keep them empty. If the "
    "source photo shows the person holding something, keep that same item in the same hand ONLY when the new "
    "pose naturally still holds it; otherwise let the hand rest empty rather than fabricating a substitute.\n"
    "• BACKGROUND: Keep the EXACT same background, location, and environment\n"
    "• OUTFIT: Keep identical clothing and accessories\n"
    "\nONLY CHANGE: body pose, posture, weight distribution, arm angles, head/face direction, and camera angle/framing."
)

PRODUCT_LOCK_RULES = (
    "\n\nPRODUCT LOCK — this is product/UGC content, so the featured product is the whole point of the shot and "
    "OVERRIDES the general hands rule above: the product from the source photo MUST remain held/worn and clearly "
    "visible in EVERY pose, never removed, hidden, or swapped out. Keep it in the same hand/position whenever the "
    "new pose allows, and if the pose changes which hand is naturally free, move the SAME product to the new hand "
    "rather than dropping it. The product's shape, color, packaging, and proportions must stay identical to the "
    "source photo. Every letter of its logo and any printed/label text must be reproduced exactly as shown in the "
    "source photo — do not redesign, restyle, blur, or invent different branding or wording."
)

# ---------------------------------------------------------------------------
# Audio transcription helpers (faster-whisper local or OpenAI Whisper API)
# ---------------------------------------------------------------------------

def _extract_audio_ffmpeg(video_path: str) -> str | None:
    """Extract audio to a 16kHz mono WAV file using ffmpeg. Returns path or None."""
    wav_path = video_path + "_audio.wav"
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", wav_path],
            capture_output=True, timeout=120,
        )
        if result.returncode == 0 and os.path.exists(wav_path):
            return wav_path
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def _transcribe_audio(audio_path: str, cfg: dict) -> str:
    """Transcribe audio using faster-whisper (local) or OpenAI Whisper API fallback."""
    global _whisper_model
    if HAS_WHISPER:
        try:
            if _whisper_model is None:
                os.makedirs("/data/whisper_cache", exist_ok=True)
                _whisper_model = _WhisperModel("tiny", device="cpu", compute_type="int8", download_root="/data/whisper_cache")
            segments, _ = _whisper_model.transcribe(audio_path, beam_size=5)
            transcript = " ".join(seg.text.strip() for seg in segments).strip()
            if transcript:
                return transcript
        except Exception as e:
            print(f"[Prism] faster-whisper error: {e}")
    # Fall back to OpenAI Whisper API
    api_key = cfg.get("openai_api_key", "")
    if api_key:
        try:
            from openai import OpenAI as _OAI
            cl = _OAI(api_key=api_key)
            with open(audio_path, "rb") as f:
                resp = cl.audio.transcriptions.create(model="whisper-1", file=f)
            return resp.text.strip()
        except Exception as e:
            print(f"[Prism] OpenAI Whisper API error: {e}")
    return ""


# ---------------------------------------------------------------------------
# Video pipeline (Take-5-Skip-10 + Hold-and-Wait batch analysis)
# ---------------------------------------------------------------------------

VIDEO_BATCH_PROMPT = (
    "You are analyzing a sequence of video frames arranged left-to-right, top-to-bottom in chronological order. "
    "Describe concisely what is happening across these frames: "
    "subject(s), actions/movements, environment, any notable changes. "
    "Be factual and specific. 2-3 sentences max. "
    "Output ONLY the description, nothing else."
)

VIDEO_SYNTHESIS_PROMPTS = {
    "post": (
        "You are a social media content creator. "
        "A video was analyzed frame-by-frame. Here is what was seen:\n\n"
        "{scene_descriptions}\n\n"
        "Based on this video, write an engaging first-person {platform} caption. "
        "Capture the energy and story of the video. "
        "SHORT punchy lines. Natural emojis. CTA at the end. "
        "BANNED: captivating, mesmerizing, stunning, breathtaking. "
        "{hashtag_line}"
        "Output ONLY the caption, nothing else."
    ),
    "flux_image": (
        "You are an expert Flux.1 image generation prompt engineer. "
        "A video was analyzed frame-by-frame. Here is what was seen:\n\n"
        "{scene_descriptions}\n\n"
        "Based on this video, write a Flux.1 prompt for the most visually compelling still from this video. "
        "Include: subject, outfit, pose, setting, lighting, camera angle. "
        "End with: photorealistic, highly detailed, 8k, professional photography, sharp focus. "
        "Output ONLY the prompt as one paragraph, nothing else."
    ),
    "wan_video": (
        "You are an expert WAN2.2 video generation prompt engineer. "
        "A video was analyzed frame-by-frame. Here is what was seen:\n\n"
        "{scene_descriptions}\n\n"
        "Based on this video, write a cinematic WAN video prompt for a 3-6 second clip capturing its essence. "
        "Include: scene, subject movement, camera movement, mood. Keep under 90 words. "
        "Output ONLY the prompt as one flowing paragraph, nothing else."
    ),
}

# ---------------------------------------------------------------------------
# Gemini native video prompts (used when Gemini watches the video directly)
# ---------------------------------------------------------------------------

VIDEO_GEMINI_FLUX = (
    "Watch this video carefully. Identify the most visually compelling moment. "
    "Write a Flux.1 image generation prompt that recreates that moment exactly. "
    "Include: subject appearance, outfit, pose, expression, setting, lighting, camera angle. "
    "End with: photorealistic, highly detailed, 8k, professional photography, sharp focus. "
    "Output ONLY the prompt as one paragraph, nothing else."
)

VIDEO_GEMINI_WAN = (
    "Watch this video. Write a WAN2.2 video generation prompt for a 3-6 second clip capturing its essence. "
    "Include: scene description, subject movement, camera movement, mood. Keep under 90 words. "
    "Output ONLY the prompt as one paragraph, nothing else."
)

VIDEO_GEMINI_PREFIX = (
    "Watch this entire video carefully, noting movement, expressions, atmosphere, "
    "and any spoken words or audio. This is a VIDEO — you can reference motion, "
    "sequence of events, and what was said in your output.\n\n"
)

# ---------------------------------------------------------------------------
# JSON schemas for Gemini structured output (eliminates regex parsing bugs)
# ---------------------------------------------------------------------------

_POSE_SCHEMA = {
    "type": "object",
    "properties": {"poses": {"type": "array", "items": {"type": "string"}, "minItems": 6, "maxItems": 6}},
    "required": ["poses"],
}
_THREAD_SCHEMA = {
    "type": "object",
    "properties": {"tweets": {"type": "array", "items": {"type": "string"}, "minItems": 5, "maxItems": 5}},
    "required": ["tweets"],
}
_VARIANTS_SCHEMA = {
    "type": "object",
    "properties": {"captions": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 3}},
    "required": ["captions"],
}
_HASHTAG_SCHEMA = {
    "type": "object",
    "properties": {
        "high_reach":  {"type": "array", "items": {"type": "string"}},
        "engagement":  {"type": "array", "items": {"type": "string"}},
        "niche":       {"type": "array", "items": {"type": "string"}},
    },
    "required": ["high_reach", "engagement", "niche"],
}

def _json_to_numbered(items: list) -> str:
    return "\n".join(f"[{i+1}] {p.strip()}" for i, p in enumerate(items))

def _json_to_variants(items: list) -> str:
    return "\n---\n".join(c.strip() for c in items)

def _json_to_hashtags(data: dict) -> str:
    def fmt(lst):
        return " ".join("#" + t.lstrip("#") for t in lst)
    return (f"HIGH REACH: {fmt(data.get('high_reach', []))}\n"
            f"ENGAGEMENT: {fmt(data.get('engagement', []))}\n"
            f"NICHE: {fmt(data.get('niche', []))}")


def _extract_video_frames(video_path: str, threshold: float = 2.5, max_frames: int = 30) -> list:
    """Take-5-Skip-10 burst pattern with motion detection. Returns list of JPEG bytes."""
    if not HAS_CV2:
        raise HTTPException(503, "Video processing requires opencv. Run: pip install opencv-python-headless")
    cap = _cv2.VideoCapture(video_path)
    frame_count, burst_counter = 0, 0
    is_skipping = False
    prev_gray = None
    saved: list = []
    while cap.isOpened() and len(saved) < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
        frame_480p = _cv2.resize(frame, (854, 480), interpolation=_cv2.INTER_AREA)
        gray = _cv2.GaussianBlur(_cv2.cvtColor(frame_480p, _cv2.COLOR_BGR2GRAY), (21, 21), 0)
        if prev_gray is not None:
            delta = _cv2.absdiff(prev_gray, gray)
            thresh_img = _cv2.threshold(delta, 25, 255, _cv2.THRESH_BINARY)[1]
            motion_score = (_cv2.countNonZero(thresh_img) / float(gray.size)) * 100
            is_static = motion_score < threshold
        else:
            is_static = False
        prev_gray = gray
        if is_static:
            if frame_count % 30 == 0:
                _, buf = _cv2.imencode(".jpg", frame_480p, [_cv2.IMWRITE_JPEG_QUALITY, 82])
                saved.append(bytes(buf))
            continue
        if not is_skipping:
            _, buf = _cv2.imencode(".jpg", frame_480p, [_cv2.IMWRITE_JPEG_QUALITY, 82])
            saved.append(bytes(buf))
            burst_counter += 1
            if burst_counter >= 5:
                is_skipping = True
                burst_counter = 0
        else:
            burst_counter += 1
            if burst_counter >= 10:
                is_skipping = False
                burst_counter = 0
    cap.release()
    return saved


def _make_frame_grid(frames: list) -> bytes:
    """Stitch up to 3 frames side-by-side into a single JPEG for one AI call."""
    if not HAS_PILLOW:
        raise HTTPException(503, "Pillow not installed")
    thumb_w, thumb_h = 400, 225
    imgs = [Image.open(io.BytesIO(f)).resize((thumb_w, thumb_h), Image.LANCZOS) for f in frames[:3]]
    canvas = Image.new("RGB", (thumb_w * len(imgs), thumb_h), (20, 20, 20))
    for i, img in enumerate(imgs):
        canvas.paste(img, (i * thumb_w, 0))
    buf = io.BytesIO()
    canvas.save(buf, format="JPEG", quality=82)
    return buf.getvalue()


def _analyze_video_gemini_sync(cfg: dict, video_path: str, modes_to_run: list,
                                platform: str, hashtags: bool, style: str,
                                language: str, brand_voice: str, guidance: str,
                                signature: str, variants: bool = False) -> dict:
    """Upload video to Gemini Files API and generate results directly — no frame extraction."""
    import time as _t
    try:
        from google import genai as _gai
        from google.genai import types as _gt
    except ImportError:
        raise RuntimeError("google-genai not installed")
    api_key = cfg.get("gemini_api_key") or cfg.get("api_key", "")
    if not api_key:
        raise RuntimeError("Gemini API key not configured")
    client = _gai.Client(api_key=api_key)
    model_name = cfg.get("cloud_model") or DEFAULT_GEMINI_MODEL
    # Upload to Gemini Files API (handles audio + video natively)
    video_file = client.files.upload(file=video_path, config={"mime_type": "video/mp4"})
    # Poll until ACTIVE (usually < 15s for short clips)
    deadline = _t.monotonic() + 120
    while _t.monotonic() < deadline:
        vf = client.files.get(name=video_file.name)
        if vf.state.name == "ACTIVE":
            video_file = vf
            break
        if vf.state.name == "FAILED":
            client.files.delete(name=video_file.name)
            raise RuntimeError("Gemini video processing failed")
        _t.sleep(3)
    else:
        try:
            client.files.delete(name=video_file.name)
        except Exception:
            pass
        raise RuntimeError("Gemini video processing timed out")
    hl = _HASHTAG_ON if hashtags else _HASHTAG_OFF
    results: dict = {}
    try:
        for m in modes_to_run:
            if m == "post":
                base = CAPTION_PROMPTS.get(platform, CAPTION_PROMPTS["general"]).replace("{hashtag_line}", hl)
                if style and style in CAPTION_STYLES:
                    base = base.rstrip() + CAPTION_STYLES[style]
                lang_suffix = LANGUAGES.get(language, "")
                if lang_suffix:
                    base = base.rstrip() + lang_suffix
                if brand_voice.strip():
                    base = f"BRAND VOICE \u2014 match this creator's tone:\n{brand_voice.strip()}\n\n" + base
                examples = _top_performer_examples(platform)
                if examples:
                    base = base.rstrip() + "\n\nTOP-PERFORMING PAST CAPTIONS (style/structure reference, don't copy):\n" + "\n".join(f"- {e}" for e in examples)
                if guidance.strip():
                    base = base.rstrip() + f"\n\nCREATOR CONTEXT: {guidance.strip()}"
                if variants:
                    base = base.rstrip() + VARIANTS_SUFFIX
                prompt = VIDEO_GEMINI_PREFIX + base
            elif m == "flux_image":
                prompt = VIDEO_GEMINI_FLUX
            elif m == "wan_video":
                prompt = VIDEO_GEMINI_WAN
            else:
                continue
            resp = client.models.generate_content(model=model_name, contents=[video_file, prompt])
            text = resp.text.strip()
            if m == "post" and not variants and signature.strip():
                text += "\n\n" + signature.strip()
            results[m] = text
    finally:
        try:
            client.files.delete(name=video_file.name)
        except Exception:
            pass
    return results


def _gemini_structured(cfg: dict, prompt: str, image_bytes: bytes | None, schema: dict) -> dict:
    """Gemini call with JSON structured output — guaranteed valid JSON, no regex parsing."""
    try:
        from google import genai as _gai
        from google.genai import types as _gt
    except ImportError:
        raise RuntimeError("google-genai not installed")
    api_key = cfg.get("gemini_api_key") or cfg.get("api_key", "")
    client = _gai.Client(api_key=api_key, http_options=_gt.HttpOptions(timeout=GEMINI_TIMEOUT_MS))
    model_name = cfg.get("cloud_model") or DEFAULT_GEMINI_MODEL
    parts = []
    if image_bytes and HAS_PILLOW:
        buf = io.BytesIO()
        Image.open(io.BytesIO(image_bytes)).convert("RGB").save(buf, format="JPEG")
        parts.append(_gt.Part(inline_data=_gt.Blob(mime_type="image/jpeg", data=buf.getvalue())))
    parts.append(_gt.Part(text=prompt))
    resp = _gemini_retry(lambda: client.models.generate_content(
        model=model_name,
        contents=[_gt.Content(parts=parts, role="user")],
        config=_gt.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
        ),
    ))
    return json.loads(resp.text)


@app.post("/api/video")
async def process_video_route(
    request: Request,
    file: UploadFile = File(...),
    mode: str = Form("post"),
    platform: str = Form("general"),
    hashtags: bool = Form(True),
    style: str = Form(""),
    content_type: str = Form("creator"),
    guidance: str = Form(""),
    language: str = Form("en"),
    transcribe_audio: bool = Form(True),
    variants: bool = Form(False),
):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401, "Unauthorized")
    content_type_header = file.content_type or ""
    if not (content_type_header.startswith("video/") or file.filename.lower().endswith((".mp4", ".mov", ".webm", ".avi"))):
        raise HTTPException(400, "Please upload a video file (MP4, MOV, WEBM)")
    cfg = load_config()
    provider = cfg.get("provider", "ollama") or "ollama"
    username = session["username"]
    user_settings = _get_user_settings(username)
    signature = user_settings.get("signature", "")
    brand_voice = user_settings.get("brand_voice", "")
    MAX_SIZE = 500 * 1024 * 1024  # 500 MB
    video_bytes = await file.read()
    if len(video_bytes) > MAX_SIZE:
        raise HTTPException(413, "Video file too large (max 500 MB)")
    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(video_bytes)
        del video_bytes  # free memory
        # Gemini native video understanding — watches the full video directly
        if provider == "gemini":
            api_key = cfg.get("gemini_api_key") or cfg.get("api_key", "")
            if api_key:
                try:
                    valid_video_modes = {"post", "flux_image", "wan_video"}
                    if mode == "all":
                        modes_to_run = list(valid_video_modes)
                    elif mode in valid_video_modes:
                        modes_to_run = [mode]
                    else:
                        modes_to_run = ["post"]
                    results = _analyze_video_gemini_sync(
                        cfg, tmp_path, modes_to_run, platform, hashtags,
                        style, language, brand_voice, guidance, signature, variants,
                    )
                    entry_id = str(uuid.uuid4())
                    conn = sqlite3.connect(DB_PATH, timeout=10)
                    conn.execute("INSERT INTO history (id, created_at, thumb, mode, platform, results, style) VALUES (?,?,?,?,?,?,?)",
                                 (entry_id, _utcnow().isoformat(), "",
                                  f"video_{mode}", platform, json.dumps(results), style or None))
                    conn.commit()
                    conn.close()
                    return {"id": entry_id, "results": results,
                            "frame_count": -1, "batch_count": -1,
                            "transcript_available": True, "method": "gemini_native"}
                except Exception as gvid_err:
                    print(f"[Prism] Gemini video failed ({gvid_err}), falling back to frame extraction")
        # Frame extraction fallback (Ollama or Gemini video failure)
        if not HAS_CV2:
            raise HTTPException(503, "Video processing requires opencv-python-headless. Run: pip install opencv-python-headless")
        frames = _extract_video_frames(tmp_path)
        if not frames:
            raise HTTPException(422, "Could not extract frames. Check the file is a valid video.")
        # Hold-and-Wait: batch frames 3 at a time, describe each batch
        opts = {"num_ctx": 4096, "num_predict": 150}
        batches = [frames[i:i + 3] for i in range(0, len(frames), 3)][:10]
        batch_descriptions = []
        for i, batch in enumerate(batches):
            grid_bytes = _make_frame_grid(batch)
            desc = _call_provider(cfg, VIDEO_BATCH_PROMPT, grid_bytes, opts)
            batch_descriptions.append(f"[Segment {i + 1}/{len(batches)}] {desc}")
        scene_text = "\n".join(batch_descriptions)
        # Audio transcription (Hold-and-Wait: audio processed independently, then merged)
        transcript = ""
        if transcribe_audio:
            audio_path = _extract_audio_ffmpeg(tmp_path)
            if audio_path:
                try:
                    transcript = _transcribe_audio(audio_path, cfg)
                finally:
                    try:
                        os.unlink(audio_path)
                    except Exception:
                        pass
        if transcript:
            scene_text = (
                "VISUAL ANALYSIS:\n" + scene_text +
                "\n\nAUDIO TRANSCRIPT (what was said in the video):\n" + transcript
            )
        hl = _HASHTAG_ON if hashtags else _HASHTAG_OFF
        # Determine which modes to run (pose_series/thread not applicable to video)
        valid_video_modes = {"post", "flux_image", "wan_video"}
        if mode == "all":
            modes_to_run = list(valid_video_modes)
        elif mode in valid_video_modes:
            modes_to_run = [mode]
        else:
            modes_to_run = ["post"]
        results: dict = {}
        for m in modes_to_run:
            tpl = VIDEO_SYNTHESIS_PROMPTS.get(m, VIDEO_SYNTHESIS_PROMPTS["post"])
            synthesis_prompt = tpl.format(scene_descriptions=scene_text, platform=platform, hashtag_line=hl)
            if m == "post":
                if style and style in CAPTION_STYLES:
                    synthesis_prompt = synthesis_prompt.rstrip() + CAPTION_STYLES[style]
                lang_suffix = LANGUAGES.get(language, "")
                if lang_suffix:
                    synthesis_prompt = synthesis_prompt.rstrip() + lang_suffix
                if brand_voice.strip():
                    synthesis_prompt = (f"BRAND VOICE — match this creator's tone:\n{brand_voice.strip()}\n\n" + synthesis_prompt)
                examples = _top_performer_examples(platform)
                if examples:
                    synthesis_prompt = synthesis_prompt.rstrip() + "\n\nTOP-PERFORMING PAST CAPTIONS (style/structure reference, don't copy):\n" + "\n".join(f"- {e}" for e in examples)
                if guidance.strip():
                    synthesis_prompt = synthesis_prompt.rstrip() + f"\n\nCREATOR CONTEXT: {guidance.strip()}"
                if variants:
                    synthesis_prompt = synthesis_prompt.rstrip() + VARIANTS_SUFFIX
            result = _call_provider(cfg, synthesis_prompt, None, {"num_ctx": 2048, "num_gpu": 99})
            if m == "post" and not variants and signature.strip():
                result = result + "\n\n" + signature.strip()
            results[m] = result
        entry_id = str(uuid.uuid4())
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.execute("INSERT INTO history (id, created_at, thumb, mode, platform, results, style) VALUES (?,?,?,?,?,?,?)",
                     (entry_id, _utcnow().isoformat(), "", f"video_{mode}", platform, json.dumps(results), style or None))
        conn.commit()
        conn.close()
        return {"id": entry_id, "results": results, "frame_count": len(frames), "batch_count": len(batches), "transcript_available": bool(transcript)}
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


@app.get("/api/settings")
def get_settings():
    cfg = load_config()
    safe = {**cfg}
    for k in ("api_key", "gemini_api_key", "grok_api_key", "openai_api_key"):
        if safe.get(k): safe[k] = "••••••••"
    safe["gemini_key_set"]  = bool(cfg.get("gemini_api_key"))
    safe["grok_key_set"]    = bool(cfg.get("grok_api_key"))
    safe["openai_key_set"]  = bool(cfg.get("openai_api_key"))
    return safe


@app.post("/api/settings")
def update_settings(req: SettingsUpdate, request: Request):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session or not _is_admin(session["username"]):
        raise HTTPException(403, "Admin access required")
    cfg = load_config()
    if req.ollama_host is not None:
        cfg["ollama_host"] = req.ollama_host.rstrip("/")
    if req.vision_model is not None:
        cfg["vision_model"] = req.vision_model.strip()
    if req.provider is not None:
        cfg["provider"] = req.provider
    if req.cloud_model is not None:
        cfg["cloud_model"] = req.cloud_model.strip()
    if req.api_key is not None and req.api_key not in ("••••••••",):
        provider = req.provider or cfg.get("provider", "ollama")
        key_map = {"gemini": "gemini_api_key", "grok": "grok_api_key", "openai": "openai_api_key"}
        field = key_map.get(provider, "api_key")
        cfg[field] = req.api_key
        cfg["api_key"] = req.api_key
    save_config(cfg)
    safe = {**cfg}
    for k in ("api_key", "gemini_api_key", "grok_api_key", "openai_api_key"):
        if safe.get(k): safe[k] = "••••••••"
    safe["gemini_key_set"]  = bool(cfg.get("gemini_api_key"))
    safe["grok_key_set"]    = bool(cfg.get("grok_api_key"))
    safe["openai_key_set"]  = bool(cfg.get("openai_api_key"))
    return safe


@app.get("/api/models")
def list_models():
    cfg = load_config()
    try:
        client = ollama_client.Client(host=cfg["ollama_host"])
        resp = client.list()
        models = []
        for m in resp.models:
            families = []
            try:
                if m.details and m.details.families:
                    families = [f.lower() for f in m.details.families]
            except Exception:
                pass
            models.append({"name": m.model, "has_vision": "clip" in families})
        models.sort(key=lambda x: (0 if x["has_vision"] else 1, x["name"].lower()))
        return {"models": models}
    except Exception as e:
        raise HTTPException(503, f"Ollama unavailable: {e}")


@app.post("/api/generate")
def generate(req: GenerateRequest, request: Request):
    cfg = load_config()
    provider = cfg.get("provider", "ollama") or "ollama"
    token = request.cookies.get("que_session")
    session = _get_session(token)
    username = session["username"] if session else "guest"
    user_settings = _get_user_settings(username)
    gender = user_settings["gender"]
    enabled_modes = user_settings["enabled_modes"]
    signature = user_settings.get("signature", "")
    brand_voice = user_settings.get("brand_voice", "")
    daily_limit = user_settings.get("daily_limit", 0)
    today_str = date.today().isoformat()

    # Check daily limit
    if daily_limit > 0:
        _lc = sqlite3.connect(DB_PATH, timeout=10)
        _lr = _lc.execute("SELECT count FROM usage WHERE username=? AND date=?", (username, today_str)).fetchone()
        _lc.close()
        if _lr and _lr[0] >= daily_limit:
            raise HTTPException(429, f"Daily limit of {daily_limit} generations reached for today")

    if req.mode == "all":
        modes_to_run = ["post"] + [m for m in ["flux_image", "wan_video", "pose_series"] if m in enabled_modes]
    else:
        modes_to_run = [req.mode]

    try:
        b64_data = req.image_b64.split(",")[-1]
        image_bytes = base64.b64decode(b64_data)
    except Exception:
        raise HTTPException(400, "Invalid image data")

    # Resize to 854×480 max — matches video pipeline resolution, reduces vision token count
    image_bytes = _resize_for_ai(image_bytes)

    # Context cache: describe the image once, then reuse the text description for every
    # mode instead of resending/re-processing the raw image bytes N times. Beneficial for
    # Ollama (single-threaded, ~30s per call) and Gemini (each vision call is several
    # seconds — running it once instead of per-mode meaningfully cuts total latency).
    description = ""
    use_cache = False
    if len(modes_to_run) > 1 and provider in ("ollama", "gemini"):
        try:
            description = _get_cached_description(image_bytes, cfg)
            use_cache = True
        except Exception:
            pass  # Fall back to direct image passing

    results: dict = {}
    errors: dict = {}  # mode -> error message, kept separate so failures are never saved/rendered as content
    # num_ctx 2048 is enough for prompt+image+caption; num_gpu:99 forces full GPU offload
    opts = {"num_ctx": 2048, "num_gpu": 99}

    for mode in modes_to_run:
        prompt = _apply_gender(_build_prompt(mode, req.platform, req.hashtags, req.style, req.content_type), mode, gender)
        # Inject brand voice examples into caption prompt
        if mode == "post" and brand_voice.strip():
            prompt = (
                f"BRAND VOICE — match this creator's exact tone and writing style:\n"
                f"{brand_voice.strip()}\n\n"
                + prompt
            )
        if mode == "post":
            examples = _top_performer_examples(req.platform)
            if examples:
                prompt = prompt.rstrip() + "\n\nTOP-PERFORMING PAST CAPTIONS (style/structure reference, don't copy):\n" + "\n".join(f"- {e}" for e in examples)
        # Inject optional creator guidance into caption only
        if mode == "post" and req.guidance.strip():
            prompt = (prompt.rstrip() +
                      f"\n\nCREATOR CONTEXT — naturally weave this into the caption "
                      f"(mention it as part of the post, not as a footnote):\n{req.guidance.strip()}"
                      )
        # Apply language instruction to caption
        if mode == "post":
            lang_suffix = LANGUAGES.get(req.language, "")
            if lang_suffix:
                prompt = prompt.rstrip() + lang_suffix
        # Apply variants request (3 distinct takes)
        if mode == "post" and req.variants:
            prompt = prompt.rstrip() + VARIANTS_SUFFIX
        # Brand research addon for product/ugc
        if req.search_brand and mode == "post" and req.content_type in ("product", "ugc"):
            prompt = prompt.rstrip() + (_BRAND_ADDON_GEMINI if provider == "gemini" else _BRAND_ADDON_LOCAL)
        # JSON structured output for pose/thread/variants on Gemini — eliminates regex/format parsing bugs
        _json_modes = {
            "pose_series": (_POSE_SCHEMA, lambda d: _json_to_numbered(d.get("poses", []))),
            "thread": (_THREAD_SCHEMA, lambda d: _json_to_numbered(d.get("tweets", []))),
        }
        try:
            if (req.search_brand and mode == "post" and
                    req.content_type in ("product", "ugc") and provider == "gemini"):
                api_key = cfg.get("gemini_api_key") or cfg.get("api_key", "")
                result = _call_gemini_grounded(api_key, cfg.get("cloud_model") or DEFAULT_GEMINI_MODEL,
                                               prompt if not use_cache else _inject_description(prompt, description),
                                               None if use_cache else image_bytes)
            elif provider == "gemini" and mode == "post" and req.variants:
                try:
                    v_prompt = prompt if not use_cache else _inject_description(prompt, description)
                    data = _gemini_structured(cfg, v_prompt, None if use_cache else image_bytes, _VARIANTS_SCHEMA)
                    result = _json_to_variants(data.get("captions", []))
                except Exception as je:
                    print(f"[Prism] JSON variants failed ({je}), using text fallback")
                    result = _call_provider(cfg, prompt, image_bytes, opts)
            elif provider == "gemini" and mode in _json_modes:
                schema, converter = _json_modes[mode]
                try:
                    m_prompt = prompt if not use_cache else _inject_description(prompt, description)
                    data = _gemini_structured(cfg, m_prompt, None if use_cache else image_bytes, schema)
                    result = converter(data)
                except Exception as je:
                    print(f"[Prism] JSON mode failed for {mode} ({je}), using text fallback")
                    result = _call_provider(cfg, prompt, image_bytes, opts)
            elif use_cache:
                result = _call_provider(cfg, _inject_description(prompt, description), None, opts)
            else:
                result = _call_provider(cfg, prompt, image_bytes, opts)
            # Append Distribution & Tags hub hashtags, then brand voice signature (skip when variants active)
            if mode == "post" and not req.variants:
                result = result + _hub_hashtag_suffix(req.hub_hashtags)
                if signature.strip():
                    result = result + "\n\n" + signature.strip()
            results[mode] = result
        except Exception as e:
            errors[mode] = str(e)

    # Generate hashtag set if requested (separate from caption hashtags)
    if req.hashtag_set:
        try:
            if use_cache:
                results["hashtag_set"] = _call_provider(cfg, _inject_description(HASHTAG_PROMPT, description), None, {"num_ctx": 4096, "num_predict": 220})
            else:
                results["hashtag_set"] = _call_provider(cfg, HASHTAG_PROMPT, image_bytes, {"num_ctx": 4096, "num_predict": 220})
        except Exception as e:
            errors["hashtag_set"] = str(e)

    # Every requested mode failed — don't charge usage or pollute history with error text
    if not results:
        raise HTTPException(502, detail="Generation failed: " + ("; ".join(errors.values()) if errors else "unknown error"))

    # Track usage (only counted when at least one mode actually succeeded)
    _uc = sqlite3.connect(DB_PATH, timeout=10)
    _uc.execute(
        "INSERT INTO usage (username, date, count) VALUES (?,?,1) "
        "ON CONFLICT(username, date) DO UPDATE SET count=count+1",
        (username, today_str)
    )
    _uc.commit()
    _uc.close()

    thumb = make_thumb(image_bytes)
    entry_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("INSERT INTO history (id, created_at, thumb, mode, platform, results, style) VALUES (?,?,?,?,?,?,?)",
                 (entry_id, _utcnow().isoformat(), thumb, req.mode, req.platform, json.dumps(results), req.style or None))
    conn.commit()
    conn.close()
    return {"id": entry_id, "results": results, "errors": errors or None}


# ---------------------------------------------------------------------------
# Streaming generate — tokens appear as the model writes them
# ---------------------------------------------------------------------------

@app.post("/api/generate-stream")
def generate_stream_route(req: GenerateRequest, request: Request):
    """SSE streaming version of /api/generate. Text appears token by token."""
    from fastapi.responses import StreamingResponse as _SR
    cfg = load_config()
    token_cookie = request.cookies.get("que_session")
    session = _get_session(token_cookie)
    username = session["username"] if session else "guest"
    user_settings = _get_user_settings(username)
    gender = user_settings["gender"]
    enabled_modes = user_settings["enabled_modes"]
    signature = user_settings.get("signature", "")
    brand_voice = user_settings.get("brand_voice", "")

    if req.mode == "all":
        modes_to_run = ["post"] + [m for m in ["flux_image", "wan_video", "pose_series"] if m in enabled_modes]
    else:
        modes_to_run = [req.mode]

    # Frontend may have already pre-generated pose_series text as soon as content type was
    # confirmed on step 1 (via the auto-pose toggle) — reuse it instead of paying for a
    # second AI call for the same result.
    cached_pose_text = req.cached_pose_series.strip()
    if cached_pose_text and "pose_series" in modes_to_run:
        modes_to_run = [m for m in modes_to_run if m != "pose_series"]

    try:
        b64_data = req.image_b64.split(",")[-1]
        image_bytes = _resize_for_ai(base64.b64decode(b64_data))
    except Exception:
        def _err():
            yield 'data: {"type":"error","message":"Invalid image data"}\n\n'
        return _SR(_err(), media_type="text/event-stream")

    # Description cache: describe the image once, then reuse the text description for every
    # mode instead of resending the raw image bytes to N separate parallel Gemini calls.
    provider = cfg.get("provider", "ollama") or "ollama"
    description = ""
    use_cache = False
    if len(modes_to_run) > 1 and provider in ("ollama", "gemini"):
        try:
            description = _get_cached_description(image_bytes, cfg)
            use_cache = True
        except Exception:
            pass

    thumb = make_thumb(image_bytes)
    full_results: dict = {}

    def _sse(obj: dict) -> str:
        return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

    def _build_mode_prompt(mode: str) -> str:
        """Build final prompt for a mode, applying all user preferences."""
        p = _apply_gender(
            _build_prompt(mode, req.platform, req.hashtags, req.style, req.content_type),
            mode, gender,
        )
        if mode == "post" and brand_voice.strip():
            p = f"BRAND VOICE — match this creator's exact tone:\n{brand_voice.strip()}\n\n" + p
        if mode == "post":
            examples = _top_performer_examples(req.platform)
            if examples:
                p = p.rstrip() + "\n\nTOP-PERFORMING PAST CAPTIONS (style/structure reference, don't copy):\n" + "\n".join(f"- {e}" for e in examples)
        if req.guidance.strip():
            p = p.rstrip() + f"\n\nUSER CONTEXT (incorporate this context into your generation):\n{req.guidance.strip()}"
        if mode == "post":
            lang_suffix = LANGUAGES.get(req.language, "")
            if lang_suffix:
                p = p.rstrip() + lang_suffix
        if mode == "post" and req.variants:
            p = p.rstrip() + VARIANTS_SUFFIX
        # Brand research for product/ugc captions
        if req.search_brand and mode == "post" and req.content_type in ("product", "ugc"):
            p = p.rstrip() + (_BRAND_ADDON_GEMINI if provider == "gemini" else _BRAND_ADDON_LOCAL)
        if use_cache:
            p = _inject_description(p, description)
        return p

    def stream_gen():
        import queue as _queue

        if cached_pose_text:
            full_results["pose_series"] = cached_pose_text
            yield _sse({"type": "mode_start", "mode": "pose_series"})
            yield _sse({"type": "token", "mode": "pose_series", "text": cached_pose_text})
            yield _sse({"type": "mode_done", "mode": "pose_series"})

        if provider == "ollama" and HAS_OLLAMA:
            # Ollama: sequential streaming — tokens appear as they generate
            ol_client = ollama_client.Client(host=cfg["ollama_host"])
            for mode in modes_to_run:
                final_prompt = _build_mode_prompt(mode)
                final_image = None if use_cache else image_bytes
                yield _sse({"type": "mode_start", "mode": mode})
                mode_text = ""
                try:
                    msgs: list = [{"role": "user", "content": final_prompt}]
                    if final_image:
                        msgs[0]["images"] = [final_image]
                    for chunk in ol_client.chat(
                        model=cfg["vision_model"],
                        messages=msgs,
                        options={"num_ctx": 2048, "num_gpu": 99},
                        stream=True,
                    ):
                        piece = chunk.message.content or ""
                        if piece:
                            mode_text += piece
                            yield _sse({"type": "token", "mode": mode, "text": piece})
                except Exception as exc:
                    yield _sse({"type": "mode_error", "mode": mode, "message": str(exc)})
                    continue
                if mode == "post" and not req.variants:
                    hh = _hub_hashtag_suffix(req.hub_hashtags)
                    if hh:
                        mode_text += hh
                        yield _sse({"type": "token", "mode": mode, "text": hh})
                    if signature.strip():
                        sig = "\n\n" + signature.strip()
                        mode_text += sig
                        yield _sse({"type": "token", "mode": mode, "text": sig})
                full_results[mode] = mode_text
                yield _sse({"type": "mode_done", "mode": mode})
        else:
            # Cloud providers: ALL modes fire in parallel
            # Gemini: true token-by-token streaming (text appears word by word from <1s)
            # Other cloud (OpenAI/Grok): batch result delivered as single chunk
            token_q: _queue.Queue = _queue.Queue()

            def _cloud_worker(m: str):
                prompt = _build_mode_prompt(m)
                # prompt already has the description injected (see _build_mode_prompt) when
                # use_cache is active — drop the raw image bytes so it isn't sent twice.
                final_image = None if use_cache else image_bytes
                use_grounding = (req.search_brand and m == "post" and
                                 req.content_type in ("product", "ugc") and provider == "gemini")
                if use_grounding:
                    # Grounding doesn't support streaming — batch
                    try:
                        ak = cfg.get("gemini_api_key") or cfg.get("api_key", "")
                        mn = cfg.get("cloud_model") or DEFAULT_GEMINI_MODEL
                        text = _call_gemini_grounded(ak, mn, prompt, final_image, url=req.brand_url)
                    except Exception as exc:
                        token_q.put(("error", m, str(exc)))
                        return
                    if m == "post" and not req.variants:
                        text += _hub_hashtag_suffix(req.hub_hashtags)
                        if signature.strip():
                            text += "\n\n" + signature.strip()
                    token_q.put(("batch", m, text))
                    return
                if provider == "gemini":
                    # Use JSON structured output for pose/thread/hashtag/variants — eliminates regex/format parsing bugs
                    if m == "post" and req.variants:
                        try:
                            data = _gemini_structured(cfg, prompt, final_image, _VARIANTS_SCHEMA)
                            text = _json_to_variants(data.get("captions", []))
                        except Exception as je:
                            print(f"[Prism] JSON variants failed ({je}), using text fallback")
                            try:
                                text = _call_provider(cfg, prompt, final_image, {})
                            except Exception as exc:
                                token_q.put(("error", m, str(exc)))
                                return
                        token_q.put(("batch", m, text))
                        return
                    _json_modes = {
                        "pose_series": (_POSE_SCHEMA,   lambda d: _json_to_numbered(d.get("poses", []))),
                        "thread":      (_THREAD_SCHEMA,  lambda d: _json_to_numbered(d.get("tweets", []))),
                        "hashtag_set": (_HASHTAG_SCHEMA, _json_to_hashtags),
                    }
                    if m in _json_modes:
                        schema, converter = _json_modes[m]
                        try:
                            data = _gemini_structured(cfg, prompt, final_image, schema)
                            text = converter(data)
                        except Exception as je:
                            print(f"[Prism] JSON mode failed for {m} ({je}), using text fallback")
                            try:
                                text = _call_provider(cfg, prompt, final_image, {})
                            except Exception as exc:
                                token_q.put(("error", m, str(exc)))
                                return
                        token_q.put(("batch", m, text))
                        return
                    # True token-by-token Gemini streaming
                    try:
                        from google import genai as _gai
                        from google.genai import types as _gt
                        ak = cfg.get("gemini_api_key") or cfg.get("api_key", "")
                        mn = cfg.get("cloud_model") or DEFAULT_GEMINI_MODEL
                        client = _gai.Client(api_key=ak, http_options=_gt.HttpOptions(timeout=GEMINI_TIMEOUT_MS))
                        parts = []
                        if final_image and HAS_PILLOW:
                            buf = io.BytesIO()
                            Image.open(io.BytesIO(final_image)).convert("RGB").save(buf, format="JPEG")
                            parts.append(_gt.Part(inline_data=_gt.Blob(mime_type="image/jpeg", data=buf.getvalue())))
                        parts.append(_gt.Part(text=prompt))
                        # Retry the whole stream from scratch on a transient 503 —
                        # but only before any token has been emitted, to avoid duplicating output.
                        stream_started = False
                        delay = 1.0
                        max_attempts = 3
                        for attempt in range(max_attempts):
                            try:
                                for chunk in client.models.generate_content_stream(
                                    model=mn,
                                    contents=[_gt.Content(parts=parts, role="user")],
                                ):
                                    piece = chunk.text or ""
                                    if piece:
                                        stream_started = True
                                        token_q.put(("chunk", m, piece))
                                break
                            except Exception as e:
                                if stream_started or attempt == max_attempts - 1 or not _is_gemini_overloaded(e):
                                    raise
                                print(f"[Prism] Gemini stream overloaded, retrying ({attempt + 1}/{max_attempts - 1}) in {delay}s")
                                time.sleep(delay)
                                delay *= 2
                        if m == "post" and not req.variants:
                            hh = _hub_hashtag_suffix(req.hub_hashtags)
                            if hh:
                                token_q.put(("chunk", m, hh))
                            if signature.strip():
                                token_q.put(("chunk", m, "\n\n" + signature.strip()))
                        token_q.put(("done", m, None))
                        return
                    except Exception as e:
                        print(f"[Prism] Gemini stream failed ({e}), using batch fallback")
                # Fallback: batch for non-Gemini or Gemini stream failure
                try:
                    text = _call_provider(cfg, prompt, final_image, {})
                except Exception as exc:
                    token_q.put(("error", m, str(exc)))
                    return
                if m == "post" and not req.variants:
                    text += _hub_hashtag_suffix(req.hub_hashtags)
                    if signature.strip():
                        text += "\n\n" + signature.strip()
                token_q.put(("batch", m, text))

            # Show all loading cards immediately
            for mode in modes_to_run:
                yield _sse({"type": "mode_start", "mode": mode})

            # Launch all modes concurrently in threads
            for m in modes_to_run:
                threading.Thread(target=_cloud_worker, args=(m,), daemon=True).start()

            # Drain the token queue — yields chunks as they arrive across all modes
            remaining = set(modes_to_run)
            while remaining:
                try:
                    evt, mode, text = token_q.get(timeout=120)
                except _queue.Empty:
                    yield _sse({"type": "error", "message": "Request timed out"})
                    break
                if evt == "chunk":
                    full_results[mode] = full_results.get(mode, "") + text
                    yield _sse({"type": "token", "mode": mode, "text": text})
                elif evt == "batch":
                    full_results[mode] = text
                    yield _sse({"type": "token", "mode": mode, "text": text})
                    yield _sse({"type": "mode_done", "mode": mode})
                    remaining.discard(mode)
                elif evt == "done":
                    # All chunks already sent; finalize
                    yield _sse({"type": "mode_done", "mode": mode})
                    remaining.discard(mode)
                elif evt == "error":
                    yield _sse({"type": "mode_error", "mode": mode, "message": text})
                    remaining.discard(mode)

        # Hashtag set (always sequential — runs after main modes)
        if req.hashtag_set:
            yield _sse({"type": "mode_start", "mode": "hashtag_set"})
            try:
                hs_img = None if use_cache else image_bytes
                hs_prompt = _inject_description(HASHTAG_PROMPT, description) if use_cache else HASHTAG_PROMPT
                hs_text = _call_provider(cfg, hs_prompt, hs_img, {"num_predict": 220})
            except Exception as exc:
                yield _sse({"type": "mode_error", "mode": "hashtag_set", "message": str(exc)})
            else:
                full_results["hashtag_set"] = hs_text
                yield _sse({"type": "token", "mode": "hashtag_set", "text": hs_text})
                yield _sse({"type": "mode_done", "mode": "hashtag_set"})

        # Every requested mode failed — don't charge usage or save error text as history
        if not full_results:
            yield _sse({"type": "error", "message": "Generation failed for all requested content types. Nothing was saved and your daily usage was not charged."})
            return

        # Save to history
        try:
            entry_id = str(uuid.uuid4())
            conn = sqlite3.connect(DB_PATH, timeout=10)
            conn.execute("INSERT INTO history (id, created_at, thumb, mode, platform, results, style) VALUES (?,?,?,?,?,?,?)",
                         (entry_id, _utcnow().isoformat(), thumb,
                          req.mode, req.platform, json.dumps(full_results), req.style or None))
            today_str = date.today().isoformat()
            conn.execute(
                "INSERT INTO usage (username, date, count) VALUES (?,?,1) "
                "ON CONFLICT(username, date) DO UPDATE SET count=count+1",
                (username, today_str),
            )
            conn.commit()
            conn.close()
        except Exception:
            entry_id = str(uuid.uuid4())

        yield _sse({"type": "done", "id": entry_id})

    return _SR(
        stream_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # prevent nginx from buffering
            "Connection": "keep-alive",
        },
    )


@app.get("/api/history")
def get_history():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    rows = conn.execute(
        "SELECT id, created_at, thumb, mode, platform, results, posted, rating FROM history ORDER BY created_at DESC LIMIT 50"
    ).fetchall()
    conn.close()
    return [{"id": r[0], "created_at": r[1], "thumb": r[2], "mode": r[3],
             "platform": r[4], "results": json.loads(r[5]), "posted": bool(r[6]), "rating": r[7]} for r in rows]


class HistoryFeedback(BaseModel):
    posted: bool = True
    rating: int = 0  # 0 = unrated, 1-5 stars


@app.post("/api/history/{item_id}/feedback")
def set_history_feedback(item_id: str, req: HistoryFeedback):
    if req.rating < 0 or req.rating > 5:
        raise HTTPException(400, "rating must be between 0 and 5")
    conn = sqlite3.connect(DB_PATH, timeout=10)
    row = conn.execute("SELECT id FROM history WHERE id=?", (item_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "History item not found")
    conn.execute(
        "UPDATE history SET posted=?, rating=? WHERE id=?",
        (1 if req.posted else 0, req.rating, item_id),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


@app.delete("/api/history/{item_id}")
def delete_history(item_id: str):
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("DELETE FROM history WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


def _on_this_day_pick(conn) -> Optional[dict]:
    """Resurface a top-rated past post — prefers one created on this day in a
    previous year (a true 'on this day' anniversary), falling back to the
    single highest-rated posted item overall so the feature still has
    something useful to show early on."""
    today = date.today()
    rows = conn.execute(
        "SELECT id, mode, platform, created_at, rating, results, thumb FROM history "
        "WHERE posted=1 AND rating>=4 ORDER BY created_at DESC"
    ).fetchall()
    if not rows:
        return None
    same_day = []
    for r in rows:
        try:
            d = datetime.fromisoformat(r[3]).date()
        except ValueError:
            continue
        if d.month == today.month and d.day == today.day and d.year != today.year:
            same_day.append(r)
    pick = same_day[0] if same_day else max(rows, key=lambda r: r[4])
    id_, mode, platform, created_at, rating, results, thumb = pick
    try:
        results_obj = json.loads(results) if results else {}
    except (json.JSONDecodeError, TypeError):
        results_obj = {}
    return {
        "id": id_, "mode": mode, "platform": platform, "created_at": created_at,
        "rating": rating, "results": results_obj, "thumb": thumb,
        "is_anniversary": bool(same_day),
    }


@app.get("/api/suggestions")
def get_suggestions():
    today = date.today()
    month = today.month
    upcoming = []
    for h in HOLIDAY_IDEAS:
        d = days_until(h["month"], h["day"], today)
        if d <= h["window_days"]:
            upcoming.append({**h, "days_until": d})
    upcoming.sort(key=lambda x: x["days_until"])
    current_season = None
    for name, data in SEASON_IDEAS.items():
        if month in data["months"]:
            current_season = {"name": name, **data}
            break
    conn = sqlite3.connect(DB_PATH, timeout=10)
    on_this_day = _on_this_day_pick(conn)
    conn.close()
    return {"upcoming": upcoming[:3], "season": current_season, "evergreen": EVERGREEN_IDEAS, "on_this_day": on_this_day}


@app.post("/api/expand-idea")
def expand_idea(req: ExpandRequest):
    if not req.keywords.strip():
        raise HTTPException(400, "keywords required")
    cfg = load_config()
    hl = _HASHTAG_ON if req.hashtags else _HASHTAG_OFF
    kw = req.keywords.strip()

    if req.prompt_type == "post":
        tpl = EXPAND_CAPTIONS.get(req.platform, EXPAND_CAPTIONS["general"])
        prompt_text = tpl.replace("{hashtag_line}", hl).replace("{keywords}", kw)
    elif req.prompt_type == "flux_image":
        prompt_text = EXPAND_PROMPTS_FLUX.format(keywords=kw)
    elif req.prompt_type == "wan_video":
        prompt_text = EXPAND_PROMPTS_WAN.format(keywords=kw)
    else:
        raise HTTPException(400, f"unknown prompt_type: {req.prompt_type}")

    opts2 = {"num_ctx": 4096, "num_gpu": 99}
    try:
        result = _call_provider(cfg, prompt_text, None, opts2)
    except Exception as e:
        raise HTTPException(503, f"AI provider error: {e}")
    return {"result": result}


@app.get("/api/whoami")
def whoami(request: Request):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401, "Not authenticated")
    u = session["username"]
    return {"username": u, "is_admin": _is_admin(u), "settings": _get_user_settings(u)}


@app.get("/api/user-settings")
def get_user_settings_route(request: Request):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401)
    return _get_user_settings(session["username"])


@app.post("/api/user-settings")
def update_user_settings_route(req: UserSettingsUpdate, request: Request):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401)
    username = session["username"]
    data = _load_users()
    settings = data["users"].get(username, {}).get("settings", {})
    if req.enabled_modes is not None:
        valid = {"flux_image", "wan_video", "pose_series"}
        settings["enabled_modes"] = [m for m in req.enabled_modes if m in valid]
    if req.gender is not None and req.gender in ("neutral", "male", "female"):
        settings["gender"] = req.gender
    if req.signature is not None:
        settings["signature"] = req.signature[:300]
    if req.brand_voice is not None:
        settings["brand_voice"] = req.brand_voice[:600]
    if req.notifications_enabled is not None:
        settings["notifications_enabled"] = bool(req.notifications_enabled)
    if req.notify_streak_risk is not None:
        settings["notify_streak_risk"] = bool(req.notify_streak_risk)
    if req.notify_scheduled_due is not None:
        settings["notify_scheduled_due"] = bool(req.notify_scheduled_due)
    if req.notify_limit_reset is not None:
        settings["notify_limit_reset"] = bool(req.notify_limit_reset)
    if req.notify_inactivity is not None:
        settings["notify_inactivity"] = bool(req.notify_inactivity)
    if req.notify_streak_milestone is not None:
        settings["notify_streak_milestone"] = bool(req.notify_streak_milestone)
    if req.notify_weekly_recap is not None:
        settings["notify_weekly_recap"] = bool(req.notify_weekly_recap)
    if req.notify_personal_best is not None:
        settings["notify_personal_best"] = bool(req.notify_personal_best)
    if req.notify_holiday_idea is not None:
        settings["notify_holiday_idea"] = bool(req.notify_holiday_idea)
    if req.notify_trend_alert is not None:
        settings["notify_trend_alert"] = bool(req.notify_trend_alert)
    if req.niche is not None:
        settings["niche"] = req.niche.strip()[:120]
    data["users"][username]["settings"] = settings
    _save_users(data)
    return _get_user_settings(username)


@app.post("/api/delete-account")
def delete_account_route(req: DeleteAccountRequest, request: Request):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401)
    username = session["username"]
    data = _load_users()
    user = data.get("users", {}).get(username)
    if not user or not _verify_pw(req.password, user):
        raise HTTPException(401, "Incorrect password")
    enabled_count = sum(1 for u in data["users"].values() if u.get("enabled", True))
    if enabled_count <= 1:
        raise HTTPException(400, "Can't delete the only remaining account — create another account first.")
    del data["users"][username]
    _save_users(data)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("DELETE FROM sessions WHERE username=?", (username,))
    conn.execute("DELETE FROM usage WHERE username=?", (username,))
    conn.execute("DELETE FROM creators WHERE owner=?", (username,))
    conn.execute("DELETE FROM scheduled_posts WHERE owner=?", (username,))
    conn.execute("DELETE FROM push_subscriptions WHERE owner=?", (username,))
    conn.execute("DELETE FROM notification_log WHERE owner=?", (username,))
    conn.execute("DELETE FROM vaults WHERE owner=?", (username,))
    conn.commit()
    conn.close()
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("que_session")
    return resp


@app.get("/api/push/public-key")
def get_push_public_key(request: Request):
    token = request.cookies.get("que_session")
    if not _get_session(token):
        raise HTTPException(401)
    if not HAS_WEBPUSH:
        raise HTTPException(503, "Push notifications not available on this server")
    return {"public_key": _ensure_vapid_keys()}


@app.post("/api/push/subscribe")
def push_subscribe(req: PushSubscribeRequest, request: Request):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute(
        "INSERT OR REPLACE INTO push_subscriptions (id, owner, endpoint, p256dh, auth, created_at) VALUES (?,?,?,?,?,?)",
        (hashlib.sha256(req.endpoint.encode()).hexdigest()[:24], session["username"], req.endpoint,
         req.keys.get("p256dh", ""), req.keys.get("auth", ""), _utcnow().isoformat()),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


@app.post("/api/push/unsubscribe")
def push_unsubscribe(req: PushUnsubscribeRequest, request: Request):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("DELETE FROM push_subscriptions WHERE endpoint=? AND owner=?", (req.endpoint, session["username"]))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.post("/api/push/test")
def push_test(request: Request):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401)
    _send_push(session["username"], "Prism notifications are on 🔔", "You'll get helpful reminders like this to help you post consistently.", "/")
    return {"ok": True}


@app.get("/login")
def login_page():
    return FileResponse(str(BASE_DIR / "login.html"))


@app.get("/")
def root_page(request: Request):
    token = request.cookies.get("que_session")
    if token and _get_session(token):
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        html = html.replace('href="/enhancements.css"', f'href="/enhancements.css?v={ASSET_VERSION}"')
        html = html.replace('src="app.js"', f'src="app.js?v={ASSET_VERSION}"')
        return HTMLResponse(html, headers={"Cache-Control": "no-cache"})
    return FileResponse(str(STATIC_DIR / "landing.html"))


@app.post("/api/login")
def api_login(req: LoginRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    rl_key = f"{client_ip}:{req.username}"
    if _login_rate_limited(rl_key):
        raise HTTPException(429, "Too many failed login attempts. Try again in a few minutes.")
    data = _load_users()
    user = data.get("users", {}).get(req.username)
    if not user or not user.get("enabled", True) or not _verify_pw(req.password, user):
        _record_login_failure(rl_key)
        raise HTTPException(401, "Invalid username or password")
    _clear_login_attempts(rl_key)
    hours = int(data.get("session_hours", 24))
    token = _create_session(req.username, hours)
    resp = JSONResponse({"ok": True, "username": req.username})
    resp.set_cookie("que_session", token, httponly=True, samesite="lax", secure=IS_PRODUCTION, max_age=hours * 3600)
    return resp


@app.post("/api/logout")
def api_logout(request: Request):
    token = request.cookies.get("que_session")
    if token:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.execute("DELETE FROM sessions WHERE token=?", (token,))
        conn.commit()
        conn.close()
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("que_session", samesite="lax", secure=IS_PRODUCTION)
    return resp


# ---------------------------------------------------------------------------
# Usage & export endpoints
# ---------------------------------------------------------------------------


@app.get("/api/usage")
def get_usage(request: Request):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401)
    username = session["username"]
    today_str = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH, timeout=10)
    row = conn.execute("SELECT count FROM usage WHERE username=? AND date=?", (username, today_str)).fetchone()
    conn.close()
    user_settings = _get_user_settings(username)
    return {"count": row[0] if row else 0, "limit": user_settings.get("daily_limit", 0), "date": today_str}


@app.get("/api/streak")
def get_streak(request: Request):
    """Posting Consistency Streak — consecutive days the user has generated at
    least one caption/idea, based on the existing per-day `usage` counters."""
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401)
    return _compute_streak(session["username"])


def _compute_streak(username: str) -> dict:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    rows = conn.execute("SELECT date FROM usage WHERE username=? AND count>0", (username,)).fetchall()
    conn.close()
    active_dates = set()
    for (d_str,) in rows:
        try:
            active_dates.add(date.fromisoformat(d_str))
        except (ValueError, TypeError):
            continue
    today = date.today()
    current = 0
    cursor = today if today in active_dates else today - timedelta(days=1)
    while cursor in active_dates:
        current += 1
        cursor -= timedelta(days=1)
    longest = 0
    run = 0
    prev = None
    for d in sorted(active_dates):
        run = run + 1 if prev is not None and (d - prev).days == 1 else 1
        longest = max(longest, run)
        prev = d
    return {"current_streak": current, "longest_streak": longest, "active_today": today in active_dates}


# ---------------------------------------------------------------------------
# Scheduling / Publishing Queue (internal — no external auto-publish yet)
# ---------------------------------------------------------------------------


# Self-enforced posting cap: Meta's Instagram Content Publishing API confirms
# a hard limit of 100 API-published posts per rolling 24-hour period per
# account (carousels count as one post). TikTok/X/Facebook don't publish an
# exact equivalent number, so the same conservative cap is applied to every
# platform here — Prism checks and blocks BEFORE any real publish call is
# ever made, so we never risk tripping a platform's own rate limiter once
# live auto-publish is wired in.
PLATFORM_DAILY_POST_LIMIT = 100


class ScheduleCreate(BaseModel):
    content: str
    platform: str = "general"
    mode: str = "post"
    scheduled_for: str  # ISO datetime string
    history_id: Optional[str] = None
    thumb: Optional[str] = None
    notes: str = ""


class ScheduleUpdate(BaseModel):
    status: Optional[str] = None  # 'pending' | 'posted' | 'skipped'
    scheduled_for: Optional[str] = None
    notes: Optional[str] = None


@app.post("/api/schedule")
def create_scheduled_post(req: ScheduleCreate, request: Request):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401, "Unauthorized")
    content = req.content.strip()
    if not content:
        raise HTTPException(400, "content is required")
    try:
        datetime.fromisoformat(req.scheduled_for)
    except ValueError:
        raise HTTPException(400, "scheduled_for must be a valid ISO datetime")
    post_id = str(uuid.uuid4())
    now = _utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute(
        "INSERT INTO scheduled_posts (id, owner, history_id, platform, mode, content, thumb, scheduled_for, status, notes, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (post_id, session["username"], req.history_id, req.platform, req.mode, content,
         req.thumb, req.scheduled_for, "pending", req.notes.strip()[:500], now, now),
    )
    conn.commit()
    conn.close()
    return {"id": post_id, "ok": True}


@app.get("/api/schedule")
def list_scheduled_posts(request: Request):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401, "Unauthorized")
    conn = sqlite3.connect(DB_PATH, timeout=10)
    rows = conn.execute(
        "SELECT id, history_id, platform, mode, content, thumb, scheduled_for, status, notes, created_at "
        "FROM scheduled_posts WHERE owner=? ORDER BY scheduled_for ASC",
        (session["username"],),
    ).fetchall()
    conn.close()
    return [{"id": r[0], "history_id": r[1], "platform": r[2], "mode": r[3], "content": r[4],
              "thumb": r[5], "scheduled_for": r[6], "status": r[7], "notes": r[8], "created_at": r[9]} for r in rows]


@app.patch("/api/schedule/{post_id}")
def update_scheduled_post(post_id: str, req: ScheduleUpdate, request: Request):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401, "Unauthorized")
    conn = sqlite3.connect(DB_PATH, timeout=10)
    row = conn.execute(
        "SELECT owner, history_id, content, thumb, mode, platform FROM scheduled_posts WHERE id=?", (post_id,)
    ).fetchone()
    if not row or row[0] != session["username"]:
        conn.close()
        raise HTTPException(404, "Scheduled post not found")
    updates, params = [], []
    if req.status is not None:
        if req.status not in ("pending", "posted", "skipped"):
            conn.close()
            raise HTTPException(400, "status must be pending, posted, or skipped")
        updates.append("status=?")
        params.append(req.status)
    if req.scheduled_for is not None:
        try:
            datetime.fromisoformat(req.scheduled_for)
        except ValueError:
            conn.close()
            raise HTTPException(400, "scheduled_for must be a valid ISO datetime")
        updates.append("scheduled_for=?")
        params.append(req.scheduled_for)
    if req.notes is not None:
        updates.append("notes=?")
        params.append(req.notes.strip()[:500])
    if updates:
        updates.append("updated_at=?")
        params.append(_utcnow().isoformat())
        params.append(post_id)
        # Marking a scheduled post "posted" feeds it into the existing History /
        # What-Worked Feedback Loop + Streak system, linking back if it came from a generation.
        if req.status == "posted":
            _, history_id, content, thumb, mode, platform = row
            platform_check = platform or "general"
            since = (_utcnow() - timedelta(hours=24)).isoformat()
            recent_count = conn.execute(
                "SELECT COUNT(*) FROM history WHERE platform=? AND posted=1 AND posted_at>=?",
                (platform_check, since),
            ).fetchone()[0]
            if recent_count >= PLATFORM_DAILY_POST_LIMIT:
                conn.close()
                raise HTTPException(
                    429,
                    f"Self-enforced daily posting cap reached for {platform_check} "
                    f"({PLATFORM_DAILY_POST_LIMIT} posts / 24h). This guards against "
                    f"violating platform API rate limits once live publishing is connected — try again later.",
                )
            posted_at = _utcnow().isoformat()
            if history_id:
                conn.execute("UPDATE history SET posted=1, posted_at=? WHERE id=?", (posted_at, history_id))
            else:
                new_id = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO history (id, created_at, thumb, mode, platform, results, posted, rating, posted_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (new_id, _utcnow().isoformat(), thumb or "", mode, platform,
                     json.dumps({mode: content}), 1, 0, posted_at),
                )
        conn.execute(f"UPDATE scheduled_posts SET {', '.join(updates)} WHERE id=?", params)
        conn.commit()
    conn.close()
    return {"ok": True}


@app.delete("/api/schedule/{post_id}")
def delete_scheduled_post(post_id: str, request: Request):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401, "Unauthorized")
    conn = sqlite3.connect(DB_PATH, timeout=10)
    row = conn.execute("SELECT owner FROM scheduled_posts WHERE id=?", (post_id,)).fetchone()
    if not row or row[0] != session["username"]:
        conn.close()
        raise HTTPException(404, "Scheduled post not found")
    conn.execute("DELETE FROM scheduled_posts WHERE id=?", (post_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Analytics Dashboard (built from data Prism already has, plus optional
# manually-logged engagement numbers — no external platform API access yet)
# ---------------------------------------------------------------------------


class MetricsUpdate(BaseModel):
    likes: int = 0
    views: int = 0
    comments: int = 0
    shares: int = 0


@app.post("/api/history/{item_id}/metrics")
def set_history_metrics(item_id: str, req: MetricsUpdate, request: Request):
    """Manually log real engagement numbers for a history entry (e.g. copied from
    Instagram/TikTok insights) until live platform API integration is wired up."""
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401, "Unauthorized")
    for name, val in (("likes", req.likes), ("views", req.views), ("comments", req.comments), ("shares", req.shares)):
        if val < 0:
            raise HTTPException(400, f"{name} cannot be negative")
    conn = sqlite3.connect(DB_PATH, timeout=10)
    row = conn.execute("SELECT id FROM history WHERE id=?", (item_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "History item not found")
    now = _utcnow().isoformat()
    prior_best = conn.execute(
        "SELECT MAX(likes), MAX(views), MAX(comments), MAX(shares) FROM post_metrics WHERE history_id != ?",
        (item_id,),
    ).fetchone()
    conn.execute(
        "INSERT INTO post_metrics (history_id, likes, views, comments, shares, updated_at) VALUES (?,?,?,?,?,?) "
        "ON CONFLICT(history_id) DO UPDATE SET likes=excluded.likes, views=excluded.views, "
        "comments=excluded.comments, shares=excluded.shares, updated_at=excluded.updated_at",
        (item_id, req.likes, req.views, req.comments, req.shares, now),
    )
    conn.commit()
    conn.close()

    if HAS_WEBPUSH:
        username = session["username"]
        settings = _get_user_settings(username)
        if settings.get("notifications_enabled") and settings.get("notify_personal_best", True):
            max_likes, max_views, max_comments, max_shares = [v or 0 for v in prior_best]
            bests = []
            if req.likes > 0 and req.likes > max_likes:
                bests.append(f"{req.likes} likes")
            if req.views > 0 and req.views > max_views:
                bests.append(f"{req.views} views")
            if req.comments > 0 and req.comments > max_comments:
                bests.append(f"{req.comments} comments")
            if req.shares > 0 and req.shares > max_shares:
                bests.append(f"{req.shares} shares")
            if bests:
                _send_push(username, "New personal best! 🏆", "Your post just hit a new high: " + ", ".join(bests) + ".", "/")

    return {"ok": True}


def _best_time_insight(conn) -> Optional[dict]:
    """Find which day-of-week / time-of-day bucket has the highest average rating
    among posted items, requiring at least 2 posts in a bucket to avoid noise
    from a single one-off data point."""
    rows = conn.execute(
        "SELECT posted_at, rating FROM history WHERE posted=1 AND posted_at IS NOT NULL AND rating > 0"
    ).fetchall()
    if len(rows) < 3:
        return None
    HOUR_BUCKETS = [
        ("Early morning", 5, 8), ("Morning", 8, 12), ("Midday", 12, 14),
        ("Afternoon", 14, 17), ("Evening", 17, 21), ("Night", 21, 24), ("Late night", 0, 5),
    ]

    def hour_label(h: int) -> str:
        for label, start, end in HOUR_BUCKETS:
            if start <= h < end:
                return label
        return "Late night"

    DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    buckets: dict = {}
    for posted_at, rating in rows:
        try:
            dt = datetime.fromisoformat(posted_at)
        except ValueError:
            continue
        key = (DAY_NAMES[dt.weekday()], hour_label(dt.hour))
        buckets.setdefault(key, []).append(rating)
    scored = [(key, sum(v) / len(v), len(v)) for key, v in buckets.items() if len(v) >= 2]
    if not scored:
        return None
    scored.sort(key=lambda x: (-x[1], -x[2]))
    (best_day, best_hour), avg, sample = scored[0]
    return {"day": best_day, "time_of_day": best_hour, "avg_rating": round(avg, 2), "sample_size": sample}


@app.get("/api/analytics")
def get_analytics(request: Request):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401, "Unauthorized")
    username = session["username"]
    conn = sqlite3.connect(DB_PATH, timeout=10)

    total_row = conn.execute(
        "SELECT COUNT(*), SUM(posted), AVG(NULLIF(rating,0)) FROM history"
    ).fetchone()
    total_generations = total_row[0] or 0
    total_posted = total_row[1] or 0
    avg_rating = round(total_row[2], 2) if total_row[2] is not None else None

    platform_rows = conn.execute(
        "SELECT platform, COUNT(*), AVG(NULLIF(rating,0)) FROM history GROUP BY platform ORDER BY COUNT(*) DESC"
    ).fetchall()
    by_platform = [{"platform": r[0] or "general", "count": r[1],
                     "avg_rating": round(r[2], 2) if r[2] is not None else None} for r in platform_rows]

    mode_rows = conn.execute("SELECT mode, COUNT(*) FROM history GROUP BY mode ORDER BY COUNT(*) DESC").fetchall()
    by_mode = [{"mode": r[0], "count": r[1]} for r in mode_rows]

    style_rows = conn.execute(
        "SELECT style, COUNT(*), AVG(NULLIF(rating,0)) FROM history "
        "WHERE style IS NOT NULL AND style != '' GROUP BY style ORDER BY COUNT(*) DESC"
    ).fetchall()
    by_style = [{"style": r[0], "label": CAPTION_STYLE_LABELS.get(r[0], r[0]), "count": r[1],
                 "avg_rating": round(r[2], 2) if r[2] is not None else None} for r in style_rows]

    since = (date.today() - timedelta(days=29)).isoformat()
    daily_rows = conn.execute(
        "SELECT date, count FROM usage WHERE username=? AND date>=? ORDER BY date ASC", (username, since)
    ).fetchall()
    daily_map = {r[0]: r[1] for r in daily_rows}
    daily_activity = []
    for i in range(30):
        d = (date.today() - timedelta(days=29 - i)).isoformat()
        daily_activity.append({"date": d, "count": daily_map.get(d, 0)})

    metrics_row = conn.execute(
        "SELECT SUM(likes), SUM(views), SUM(comments), SUM(shares), COUNT(*) FROM post_metrics"
    ).fetchone()
    engagement_totals = {
        "likes": metrics_row[0] or 0, "views": metrics_row[1] or 0,
        "comments": metrics_row[2] or 0, "shares": metrics_row[3] or 0,
        "logged_posts": metrics_row[4] or 0,
    }
    best_row = conn.execute(
        "SELECT h.id, h.mode, h.platform, h.created_at, m.likes, m.views FROM post_metrics m "
        "JOIN history h ON h.id = m.history_id ORDER BY m.likes DESC LIMIT 1"
    ).fetchone()
    best_post = None
    if best_row:
        best_post = {"id": best_row[0], "mode": best_row[1], "platform": best_row[2],
                      "created_at": best_row[3], "likes": best_row[4], "views": best_row[5]}
    best_time_insight = _best_time_insight(conn)

    conn.close()
    return {
        "total_generations": total_generations,
        "total_posted": total_posted,
        "avg_rating": avg_rating,
        "by_platform": by_platform,
        "by_mode": by_mode,
        "by_style": by_style,
        "daily_activity": daily_activity,
        "streak": _compute_streak(username),
        "engagement_totals": engagement_totals,
        "best_post": best_post,
        "best_time_insight": best_time_insight,
    }


class HookScoreRequest(BaseModel):
    text: str


@app.post("/api/hook-score")
def score_hook(req: HookScoreRequest, request: Request):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401, "Unauthorized")
    text = req.text.strip()
    if not text:
        raise HTTPException(400, "text is required")
    hook = text.split("\n")[0].strip()[:200]
    if not hook:
        raise HTTPException(400, "Could not find an opening line to score")
    cfg = load_config()
    prompt = HOOK_SCORE_PROMPT.format(hook=hook.replace('"', "'"))
    try:
        raw = _call_provider(cfg, prompt, None, {"num_ctx": 1024, "num_gpu": 99, "num_predict": 1500})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Scoring failed: {e}")
    return _parse_hook_score(raw)


class TrendRequest(BaseModel):
    niche: str
    platform: str = "general"


@app.post("/api/trends")
def get_trends(req: TrendRequest, request: Request):
    """Trend-Aware Grounding — uses Gemini's Google Search grounding to surface
    what's currently trending in a niche, plus suggested caption angles."""
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401, "Unauthorized")
    niche = req.niche.strip()
    if not niche:
        raise HTTPException(400, "niche is required")
    cfg = load_config()
    provider = cfg.get("provider", "ollama") or "ollama"
    if provider != "gemini":
        raise HTTPException(400, "Trend-aware grounding requires the Gemini provider (Google Search grounding) \u2014 switch providers in Settings to use this.")
    api_key = cfg.get("gemini_api_key") or cfg.get("api_key", "")
    model = cfg.get("cloud_model") or DEFAULT_GEMINI_MODEL
    prompt = TREND_PROMPT.format(niche=niche.replace('"', "'")[:60], platform=(req.platform or "general").replace('"', "'"))
    try:
        raw = _call_gemini_grounded(api_key, model, prompt, None, max_tokens=1500)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Trend lookup failed: {e}")
    return _parse_trends(raw)


ALT_TEXT_PROMPT = (
    "Write a concise, descriptive ALT TEXT for this image for screen-reader accessibility. "
    "Describe the concrete visual content (subject, setting, action, notable colors/text) in "
    "one plain sentence, under 125 characters. Do not start with \"Image of\" or \"Photo of\". "
    "Respond with ONLY the alt text sentence, nothing else \u2014 no quotes, no markdown."
)


class AltTextRequest(BaseModel):
    image_b64: str


@app.post("/api/alt-text")
def generate_alt_text(req: AltTextRequest, request: Request):
    """Alt-Text Generator — reuses the vision pipeline to produce a short, screen-reader
    friendly alt text description for the same image used for caption generation."""
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401, "Unauthorized")
    b64 = req.image_b64.strip()
    if not b64:
        raise HTTPException(400, "image_b64 is required")
    try:
        image_bytes = base64.b64decode(b64.split(",")[-1])
    except Exception:
        raise HTTPException(400, "Invalid image_b64")
    cfg = load_config()
    try:
        raw = _call_provider(cfg, ALT_TEXT_PROMPT, image_bytes, {"num_ctx": 1024, "num_gpu": 99, "num_predict": 200})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Alt text generation failed: {e}")
    alt = raw.strip().strip('"').strip()
    if len(alt) > 300:
        alt = alt[:300].rsplit(" ", 1)[0] + "\u2026"
    return {"alt_text": alt}



@app.get("/api/history/export")
def export_history(request: Request):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    rows = conn.execute(
        "SELECT created_at, mode, platform, results FROM history ORDER BY created_at DESC LIMIT 200"
    ).fetchall()
    conn.close()
    lines = []
    for r in rows:
        results_data = json.loads(r[3])
        lines.append("=" * 60)
        lines.append(f"Date: {r[0][:19]}  |  Mode: {r[1]}  |  Platform: {r[2]}")
        lines.append("")
        for mode, text in results_data.items():
            lines.append(f"[ {mode.upper().replace('_', ' ')} ]")
            lines.append(text)
            lines.append("")
    return Response(
        content="\n".join(lines),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=que_history.txt"},
    )


# ---------------------------------------------------------------------------
# Feature Page Discovery & Targeting Engine — Instagram hub management +
# Reddit research panel. Hub data is entirely user/admin-submitted after they
# find accounts themselves (search engine or in-app search) — Prism never
# scrapes Instagram/TikTok directly, so this stays ToS-compliant.
# ---------------------------------------------------------------------------

@app.get("/api/hubs")
def list_hubs(request: Request, niche: str = "", tier: str = "", platform: str = "instagram"):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401, "Unauthorized")
    conn = sqlite3.connect(DB_PATH, timeout=10)
    rows = conn.execute(
        "SELECT id, handle, niche, tier, bio_snippet, submission_rule, hashtags, added_by, created_at, status, platform "
        "FROM hubs WHERE status IN ('active','flagged') ORDER BY created_at DESC"
    ).fetchall()
    flag_counts = dict(conn.execute(
        "SELECT hub_id, COUNT(DISTINCT reported_by) FROM hub_reports GROUP BY hub_id"
    ).fetchall())
    reported_by_me = {r[0] for r in conn.execute(
        "SELECT hub_id FROM hub_reports WHERE reported_by=?", (session["username"],)
    ).fetchall()}
    conn.close()
    n = niche.strip().lower()
    out = []
    for r in rows:
        row_niche = (r[2] or "").lower()
        row_platform = r[10] or "instagram"
        if platform and row_platform != platform:
            continue
        if n and n not in row_niche and row_niche not in n:
            continue
        if tier and r[3] != tier:
            continue
        out.append({
            "id": r[0], "handle": r[1], "niche": r[2], "tier": r[3],
            "bio_snippet": r[4], "submission_rule": r[5],
            "hashtags": json.loads(r[6]) if r[6] else [],
            "added_by": r[7], "created_at": r[8], "status": r[9],
            "platform": row_platform,
            "flag_count": flag_counts.get(r[0], 0),
            "reported_by_me": r[0] in reported_by_me,
        })
    return {"hubs": out, "tiers": HUB_TIERS}


@app.post("/api/hubs")
def create_hub(req: HubCreate, request: Request):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401, "Unauthorized")
    handle = req.handle.strip().lstrip("@")
    if not handle:
        raise HTTPException(400, "Handle required")
    if not req.niche.strip():
        raise HTTPException(400, "Niche required")
    if req.tier not in HUB_TIERS:
        raise HTTPException(400, f"tier must be one of {list(HUB_TIERS)}")
    platform = req.platform if req.platform in HUB_PLATFORMS else "instagram"
    hub_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute(
        "INSERT INTO hubs (id, platform, handle, niche, tier, bio_snippet, submission_rule, hashtags, status, added_by, created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (hub_id, platform, handle, req.niche.strip()[:60], req.tier,
         req.bio_snippet.strip()[:500], req.submission_rule.strip()[:300],
         json.dumps([h.lstrip("#").strip() for h in req.hashtags if h.strip()][:15]),
         "active", session["username"], _utcnow().isoformat()),
    )
    conn.commit()
    conn.close()
    return {"id": hub_id, "ok": True}


@app.delete("/api/hubs/{hub_id}")
def delete_hub(hub_id: str, request: Request):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session or not _is_admin(session["username"]):
        raise HTTPException(403, "Admin access required")
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("DELETE FROM hubs WHERE id=?", (hub_id,))
    conn.execute("DELETE FROM hub_reports WHERE hub_id=?", (hub_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.post("/api/hubs/{hub_id}/report")
def report_hub(hub_id: str, req: HubReport, request: Request):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401, "Unauthorized")
    reason = req.reason if req.reason in HUB_REPORT_REASONS else "other"
    conn = sqlite3.connect(DB_PATH, timeout=10)
    exists = conn.execute("SELECT 1 FROM hubs WHERE id=?", (hub_id,)).fetchone()
    if not exists:
        conn.close()
        raise HTTPException(404, "Hub not found")
    already = conn.execute(
        "SELECT 1 FROM hub_reports WHERE hub_id=? AND reported_by=?", (hub_id, session["username"])
    ).fetchone()
    if already:
        conn.close()
        raise HTTPException(400, "You already reported this hub")
    conn.execute(
        "INSERT INTO hub_reports (id, hub_id, reason, note, reported_by, created_at) VALUES (?,?,?,?,?,?)",
        (str(uuid.uuid4()), hub_id, reason, req.note.strip()[:300], session["username"], _utcnow().isoformat()),
    )
    flag_count = conn.execute(
        "SELECT COUNT(DISTINCT reported_by) FROM hub_reports WHERE hub_id=?", (hub_id,)
    ).fetchone()[0]
    flagged = flag_count >= HUB_FLAG_THRESHOLD
    if flagged:
        conn.execute("UPDATE hubs SET status='flagged' WHERE id=? AND status='active'", (hub_id,))
    conn.commit()
    conn.close()
    return {"ok": True, "flag_count": flag_count, "flagged": flagged}


@app.get("/api/reddit-panel")
def reddit_panel(request: Request, niche: str = ""):
    token = request.cookies.get("que_session")
    if not _get_session(token):
        raise HTTPException(401, "Unauthorized")
    return {"niche": niche, "subreddits": _match_reddit_niche(niche)}


# Targeting Vault — named, reusable snapshots of a hub + hashtag selection so
# users can save a niche/campaign's targeting set and reload it later instead
# of re-picking hubs each time. Snapshots store the hub data at save time
# (not just ids) so a vault still displays correctly even if a hub is later
# edited or removed from the shared hubs list.

@app.get("/api/vaults")
def list_vaults(request: Request):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401, "Unauthorized")
    conn = sqlite3.connect(DB_PATH, timeout=10)
    rows = conn.execute(
        "SELECT id, name, niche, hubs, hashtags, created_at FROM vaults WHERE owner=? ORDER BY created_at DESC",
        (session["username"],),
    ).fetchall()
    conn.close()
    out = [{
        "id": r[0], "name": r[1], "niche": r[2],
        "hubs": json.loads(r[3]) if r[3] else [],
        "hashtags": json.loads(r[4]) if r[4] else [],
        "created_at": r[5],
    } for r in rows]
    return {"vaults": out}


@app.post("/api/vaults")
def create_vault(req: VaultCreate, request: Request):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401, "Unauthorized")
    name = req.name.strip()
    if not name:
        raise HTTPException(400, "Vault name required")
    if not req.hubs and not req.hashtags:
        raise HTTPException(400, "Select at least one hub or hashtag before saving")
    vault_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute(
        "INSERT INTO vaults (id, name, niche, hubs, hashtags, owner, created_at) VALUES (?,?,?,?,?,?,?)",
        (vault_id, name[:60], req.niche.strip()[:60], json.dumps(req.hubs), json.dumps(req.hashtags),
         session["username"], _utcnow().isoformat()),
    )
    conn.commit()
    conn.close()
    return {"id": vault_id, "ok": True}


@app.delete("/api/vaults/{vault_id}")
def delete_vault(vault_id: str, request: Request):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401, "Unauthorized")
    conn = sqlite3.connect(DB_PATH, timeout=10)
    row = conn.execute("SELECT owner FROM vaults WHERE id=?", (vault_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Vault not found")
    if row[0] != session["username"] and not _is_admin(session["username"]):
        conn.close()
        raise HTTPException(403, "You can only delete your own vaults")
    conn.execute("DELETE FROM vaults WHERE id=?", (vault_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


# Peer Shoutout Matching — opt-in directory where users list their own
# account so other Prism users looking for reciprocal shoutout swaps
# (similar follower tier, same niche) can find and contact them directly.
# One listing per user (upsert), fully opt-in/opt-out.

@app.get("/api/creators")
def list_creators(request: Request, niche: str = "", tier: str = "", platform: str = ""):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401, "Unauthorized")
    conn = sqlite3.connect(DB_PATH, timeout=10)
    rows = conn.execute(
        "SELECT owner, platform, handle, niche, tier, pitch, created_at FROM creators "
        "WHERE owner != ? ORDER BY created_at DESC",
        (session["username"],),
    ).fetchall()
    conn.close()
    n = niche.strip().lower()
    out = []
    for r in rows:
        row_niche = (r[3] or "").lower()
        if platform and r[1] != platform:
            continue
        if tier and r[4] != tier:
            continue
        if n and n not in row_niche and row_niche not in n:
            continue
        out.append({
            "owner": r[0], "platform": r[1], "handle": r[2], "niche": r[3],
            "tier": r[4], "pitch": r[5], "created_at": r[6],
        })
    return {"creators": out}


@app.get("/api/creators/me")
def get_my_creator_profile(request: Request):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401, "Unauthorized")
    conn = sqlite3.connect(DB_PATH, timeout=10)
    row = conn.execute(
        "SELECT platform, handle, niche, tier, pitch FROM creators WHERE owner=?",
        (session["username"],),
    ).fetchone()
    conn.close()
    if not row:
        return {"profile": None}
    return {"profile": {"platform": row[0], "handle": row[1], "niche": row[2], "tier": row[3], "pitch": row[4]}}


@app.post("/api/creators")
def upsert_creator_profile(req: CreatorProfile, request: Request):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401, "Unauthorized")
    handle = req.handle.strip().lstrip("@")
    if not handle:
        raise HTTPException(400, "Handle required")
    if not req.niche.strip():
        raise HTTPException(400, "Niche required")
    if req.tier not in HUB_TIERS:
        raise HTTPException(400, f"tier must be one of {list(HUB_TIERS)}")
    platform = req.platform if req.platform in HUB_PLATFORMS else "instagram"
    now = _utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH, timeout=10)
    existing = conn.execute("SELECT owner FROM creators WHERE owner=?", (session["username"],)).fetchone()
    if existing:
        conn.execute(
            "UPDATE creators SET platform=?, handle=?, niche=?, tier=?, pitch=?, updated_at=? WHERE owner=?",
            (platform, handle, req.niche.strip()[:60], req.tier, req.pitch.strip()[:300], now, session["username"]),
        )
    else:
        conn.execute(
            "INSERT INTO creators (owner, platform, handle, niche, tier, pitch, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (session["username"], platform, handle, req.niche.strip()[:60], req.tier, req.pitch.strip()[:300], now, now),
        )
    conn.commit()
    conn.close()
    return {"ok": True}


@app.delete("/api/creators/me")
def delete_my_creator_profile(request: Request):
    token = request.cookies.get("que_session")
    session = _get_session(token)
    if not session:
        raise HTTPException(401, "Unauthorized")
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("DELETE FROM creators WHERE owner=?", (session["username"],))
    conn.commit()
    conn.close()
    return {"ok": True}


app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    cfg = load_config()
    port = int(os.environ.get("PORT", cfg.get("server_port", 7861)))
    print()
    print("  ⚡  Prism — AI Social Media Content Studio")
    print(f"     URL:      http://0.0.0.0:{port}")
    print(f"     Provider: {cfg.get('provider', 'ollama')}")
    print(f"     Model:    {cfg.get('vision_model', 'not set')}")
    print()
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
