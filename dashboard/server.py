import os
import sys

# CUDA Dual RTX 3060 (Ampere sm_86) Optimization Flags
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
os.environ["CUDA_MODULE_LOADING"] = "LAZY"
os.environ["TORCH_CUDA_ARCH_LIST"] = "8.6"

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import asyncio
import time
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

BASE_DIR = Path("F:/WORKHORSE")
sys.path.insert(0, str(BASE_DIR))

from shared.system_monitor import get_system_stats, get_ollama_models
from shared.ai_providers import AIProviderService
from shared.auth import verify_password, hash_password, make_session_token, verify_session_token, get_session_id
from shared.vram_manager import vram_manager, VramManager
from pipeline.orchestrator import WorkhorseOrchestrator
from pipeline.stages.photo_retoucher import PhotoRetoucher
from pipeline.stages.inspiration_scanner import InspirationScanner
from pipeline.stages.cam_template_generator import CamTemplateGenerator
from pipeline.stages.etsy_digital_store import EtsyDigitalStore
from pipeline.stages.fiverr_service_bot import FiverrServiceBot
from pipeline.stages.trend_researcher import TrendResearchAgent
from pipeline.stages.order_radar import OrderRadar
from pipeline.stages.omni_marketer import OmniMarketer
from pipeline.stages.newsletter_manager import NewsletterManager
from pipeline.stages.twitter_poster import TwitterPoster
from pipeline.stages.pinterest_poster import PinterestPoster
from pipeline.stages.ai_operator import ai_operator, CLIENT_INBOX_DIR, CLIENT_OUTPUTS_DIR
from pipeline.stages.herald_scheduler import herald_scheduler

main_loop = None
connected_websockets: List[WebSocket] = []

CONFIG_FILE = BASE_DIR / "config.json"
orchestrator = WorkhorseOrchestrator(str(CONFIG_FILE))
ai_service = AIProviderService(str(CONFIG_FILE))
photo_retoucher = PhotoRetoucher()
inspiration_scanner = InspirationScanner()
cam_generator = CamTemplateGenerator()
etsy_store = EtsyDigitalStore()
fiverr_bot = FiverrServiceBot()
trend_agent = TrendResearchAgent()
order_radar = OrderRadar()
omni_marketer = OmniMarketer()
newsletter_mgr = NewsletterManager()
twitter_poster = TwitterPoster(str(CONFIG_FILE))
pinterest_poster = PinterestPoster(str(CONFIG_FILE))
# vram_manager imported as global singleton from shared.vram_manager

def is_any_orchestrator_job_active() -> bool:
    for j in orchestrator.jobs.values():
        if j.status in ("running", "processing", "queued"):
            return True
    return False

vram_manager.register_active_jobs_checker(is_any_orchestrator_job_active)


def ws_event_dispatcher(job_data: Dict[str, Any]):
    payload = json.dumps({"type": "job_update", "job": job_data})
    for ws in list(connected_websockets):
        try:
            if main_loop and main_loop.is_running():
                asyncio.run_coroutine_threadsafe(ws.send_text(payload), main_loop)
        except Exception:
            pass

orchestrator.subscribe(ws_event_dispatcher)

# Cached ComfyUI (RTX 5070 Ti Main PC) health status, refreshed by a background
# monitor task so the telemetry websocket can report online/offline state
# cheaply (without blocking on a network call every 3s). This is the fix for
# "ComfyUI going offline with no alerting anywhere in the dashboard" - the
# only prior check was the on-demand /api/comfy/status route, which nobody
# polled periodically.
comfy_health_cache: Dict[str, Any] = {"online": None, "last_checked": None, "error": None}

async def comfy_health_monitor_loop():
    from pipeline.stages.comfyui_bridge import comfy_bridge
    loop = asyncio.get_event_loop()
    was_online = None
    while True:
        try:
            status = await loop.run_in_executor(None, comfy_bridge.check_connection)
            comfy_health_cache["online"] = status.get("online", False)
            comfy_health_cache["host"] = status.get("host")
            comfy_health_cache["error"] = status.get("error")
            comfy_health_cache["last_checked"] = time.strftime("%Y-%m-%d %H:%M:%S")
            # Log transitions (not every poll) so the incident log stays readable
            if was_online is True and comfy_health_cache["online"] is False:
                ai_operator.log_incident("comfy_ui", f"ComfyUI (RTX 5070 Ti) went offline: {comfy_health_cache['error']}", "Cannot remotely restart Main PC service - flagged for Commander attention.", status="needs_attention")
            elif was_online is False and comfy_health_cache["online"] is True:
                ai_operator.log_incident("comfy_ui", "ComfyUI (RTX 5070 Ti) came back online", "No action needed - connection self-recovered.", status="resolved")
            was_online = comfy_health_cache["online"]
        except Exception as e:
            comfy_health_cache["online"] = False
            comfy_health_cache["error"] = str(e)
            comfy_health_cache["last_checked"] = time.strftime("%Y-%m-%d %H:%M:%S")
        await asyncio.sleep(45)

async def auto_remediation_loop():
    """Periodic self-healing sweep (every 10 min): proactively runs diagnostics and
    attempts known fixes instead of waiting for someone to ask Synapse to check."""
    loop = asyncio.get_event_loop()
    while True:
        try:
            await asyncio.sleep(600)
            await loop.run_in_executor(None, ai_operator.auto_remediate)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[AUTO-REMEDIATION] Error in loop: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global main_loop
    main_loop = asyncio.get_running_loop()
    print("[WORKHORSE] Command Center Server running on http://0.0.0.0:8800 (Tailscale: http://100.66.45.48:8800 or http://secondary-pc:8800)")
    watchdog_task = asyncio.create_task(vram_manager.run_watchdog_loop())
    herald_task = asyncio.create_task(herald_scheduler.run_loop())
    comfy_health_task = asyncio.create_task(comfy_health_monitor_loop())
    remediation_task = asyncio.create_task(auto_remediation_loop())
    # Logs today's health snapshot immediately on startup instead of waiting for the
    # first 10-minute auto-remediation cycle (run_daily_health_check is a no-op if
    # today's entry already exists, so this is safe to call on every restart).
    main_loop.run_in_executor(None, ai_operator.run_daily_health_check)
    try:
        yield
    finally:
        watchdog_task.cancel()
        herald_task.cancel()
        comfy_health_task.cancel()
        remediation_task.cancel()

app = FastAPI(title="WORKHORSE AI Command Center", version="1.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # wildcard origin + credentials would let any site ride the session cookie
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRETS_FILE = BASE_DIR / "secrets.json"
SESSION_COOKIE = "workhorse_session"
# Routes reachable without login: the newsletter signup portal is meant for external subscribers.
# The Stripe/Gumroad webhooks and order-download link are also unauthenticated since they're
# called by external services/buyers who have no WORKHORSE login - protected instead by
# Stripe signature verification, Gumroad seller_id matching, and an unguessable download token.
PUBLIC_PATHS = {"/login", "/api/login", "/setup", "/api/setup", "/favicon.ico", "/subscribe", "/api/newsletter/subscribe", "/api/newsletter/unsubscribe", "/api/radar/webhook/stripe", "/api/radar/webhook/gumroad"}
PUBLIC_PREFIXES = ("/static/", "/api/download/order/")


def _load_secrets() -> Dict[str, Any]:
    if not SECRETS_FILE.exists():
        return {}
    try:
        with open(SECRETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _get_session_secret() -> str:
    data = _load_secrets()
    auth = data.setdefault("dashboard_auth", {})
    secret = auth.get("session_secret")
    if not secret:
        secret = os.urandom(32).hex()
        auth["session_secret"] = secret
        with open(SECRETS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    return secret


def _is_authenticated(request) -> bool:
    token = request.cookies.get(SESSION_COOKIE)
    return bool(token) and verify_session_token(token, _get_session_secret())


def _get_request_session_id(request) -> Optional[str]:
    """Extracts the unique per-login session id from the request's auth cookie, used to
    keep each browser session's SYNAPSE chat memory separate from every other session."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    return get_session_id(token, _get_session_secret())


@app.middleware("http")
async def auth_gate_middleware(request, call_next):
    path = request.url.path
    if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
        return await call_next(request)
    if not _is_authenticated(request):
        if path.startswith("/api/"):
            return JSONResponse({"status": "error", "detail": "Not authenticated"}, status_code=401)
        return RedirectResponse(url="/login")
    return await call_next(request)


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return """<!doctype html><html><head><title>WORKHORSE Login</title>
<style>
body{background:#0b0e14;color:#e6e6e6;font-family:system-ui,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
.box{background:#131722;padding:32px 40px;border-radius:10px;border:1px solid #232a3b;min-width:300px}
h1{font-size:18px;margin:0 0 18px}
input{width:100%;box-sizing:border-box;padding:10px;margin:8px 0;border-radius:6px;border:1px solid #2b3245;background:#0b0e14;color:#e6e6e6}
button{width:100%;padding:10px;margin-top:10px;border-radius:6px;border:none;background:#4f7cff;color:#fff;font-weight:600;cursor:pointer}
#err{color:#ff6b6b;font-size:13px;min-height:16px;margin-top:6px}
</style></head><body>
<form class="box" id="f">
<h1>WORKHORSE Command Center</h1>
<input id="pw" type="password" placeholder="Password" autofocus required>
<button type="submit">Sign in</button>
<div id="err"></div>
</form>
<script>
document.getElementById('f').addEventListener('submit', async (e) => {
  e.preventDefault();
  const pw = document.getElementById('pw').value;
  const r = await fetch('/api/login', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({password: pw})});
  if (r.ok) { window.location.href = '/'; }
  else { document.getElementById('err').textContent = 'Invalid password.'; }
});
</script></body></html>"""


@app.post("/api/login")
async def login(payload: Dict[str, Any]):
    data = _load_secrets()
    auth = data.get("dashboard_auth", {})
    pw_hash = auth.get("password_hash")
    salt = auth.get("salt")
    if not pw_hash or not salt:
        raise HTTPException(status_code=503, detail="No dashboard password set. Run set_dashboard_password.py first.")
    if not verify_password(payload.get("password", ""), salt, pw_hash):
        raise HTTPException(status_code=401, detail="Invalid password")
    resp = JSONResponse({"status": "ok"})
    resp.set_cookie(SESSION_COOKIE, make_session_token(_get_session_secret()), httponly=True, samesite="lax", max_age=7 * 24 * 3600)
    return resp


@app.post("/api/logout")
async def logout():
    resp = JSONResponse({"status": "ok"})
    resp.delete_cookie(SESSION_COOKIE)
    return resp


@app.get("/setup", response_class=HTMLResponse)
async def setup_page():
    data = _load_secrets()
    if data.get("dashboard_auth", {}).get("password_hash"):
        return RedirectResponse(url="/login")
    return """<!doctype html><html><head><title>WORKHORSE Setup</title>
<style>
body{background:#0b0e14;color:#e6e6e6;font-family:system-ui,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
.box{background:#131722;padding:32px 40px;border-radius:10px;border:1px solid #232a3b;min-width:320px}
h1{font-size:18px;margin:0 0 18px}
input{width:100%;box-sizing:border-box;padding:10px;margin:8px 0;border-radius:6px;border:1px solid #2b3245;background:#0b0e14;color:#e6e6e6}
button{width:100%;padding:10px;margin-top:10px;border-radius:6px;border:none;background:#4f7cff;color:#fff;font-weight:600;cursor:pointer}
#err{color:#ff6b6b;font-size:13px;min-height:16px;margin-top:6px}
</style></head><body>
<form class="box" id="f">
<h1>Set WORKHORSE dashboard password</h1>
<input id="pw" type="password" placeholder="New password (min 8 chars)" autofocus required>
<input id="pw2" type="password" placeholder="Confirm password" required>
<button type="submit">Set password</button>
<div id="err"></div>
</form>
<script>
document.getElementById('f').addEventListener('submit', async (e) => {
  e.preventDefault();
  const pw = document.getElementById('pw').value;
  const pw2 = document.getElementById('pw2').value;
  if (pw !== pw2) { document.getElementById('err').textContent = 'Passwords do not match.'; return; }
  if (pw.length < 8) { document.getElementById('err').textContent = 'Password must be at least 8 characters.'; return; }
  const r = await fetch('/api/setup', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({password: pw})});
  if (r.ok) { window.location.href = '/login'; }
  else { const body = await r.json().catch(() => ({})); document.getElementById('err').textContent = body.detail || 'Setup failed.'; }
});
</script></body></html>"""


@app.post("/api/setup")
async def setup(payload: Dict[str, Any]):
    data = _load_secrets()
    auth = data.setdefault("dashboard_auth", {})
    if auth.get("password_hash"):
        raise HTTPException(status_code=403, detail="Password already configured. Use /login.")
    password = payload.get("password", "")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    creds = hash_password(password)
    auth["salt"] = creds["salt"]
    auth["password_hash"] = creds["hash"]
    if not auth.get("session_secret"):
        auth["session_secret"] = os.urandom(32).hex()
    with open(SECRETS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return JSONResponse({"status": "ok"})


@app.middleware("http")
async def activity_tracker_middleware(request, call_next):
    path = request.url.path
    if not (path.startswith("/static") or path in ("/api/system/stats", "/api/radar/status", "/api/vram/status", "/ws/telemetry", "/favicon.ico")):
        vram_manager.record_activity(source=path)
    response = await call_next(request)
    return response

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "dashboard" / "static")), name="static")

@app.get("/favicon.ico")
async def favicon():
    fav_file = BASE_DIR / "dashboard" / "static" / "favicon.ico"
    if fav_file.exists():
        return FileResponse(fav_file)
    return JSONResponse({"status": "none"})

@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def serve_dashboard():
    index_file = BASE_DIR / "dashboard" / "static" / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Dashboard UI not found")
    with open(index_file, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/subscribe", response_class=HTMLResponse)
async def serve_subscribe_portal():
    subscribe_file = BASE_DIR / "dashboard" / "static" / "subscribe.html"
    if not subscribe_file.exists():
        raise HTTPException(status_code=404, detail="Subscribe portal UI not found")
    with open(subscribe_file, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/system/stats")
async def get_telemetry():
    stats = get_system_stats()
    stats["ollama"] = get_ollama_models()
    stats["vram_watchdog"] = vram_manager.get_status()
    stats["comfy_health"] = comfy_health_cache
    return stats

@app.get("/api/system/models")
async def get_models():
    return get_ollama_models()

@app.get("/api/agents/{agent_key}/config")
async def get_agent_config(agent_key: str):
    if not CONFIG_FILE.exists():
        raise HTTPException(status_code=404, detail="Config not found")
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    agent_cfg = cfg.get("agents", {}).get(agent_key, {})
    return {"status": "ok", "agent": agent_key, "config": agent_cfg}

@app.post("/api/agents/{agent_key}/config")
async def update_agent_config(agent_key: str, payload: Dict[str, Any]):
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if "agents" not in cfg:
            cfg["agents"] = {}
        if agent_key not in cfg["agents"]:
            cfg["agents"][agent_key] = {}
        cfg["agents"][agent_key].update(payload)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        return {"status": "ok", "message": f"Updated config for agent {agent_key}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/open-folder")
async def open_output_folder(payload: Optional[Dict[str, Any]] = None):
    folder_path = BASE_DIR / "workspace" / "output"
    if payload and payload.get("path"):
        cand = Path(payload["path"])
        if cand.exists():
            folder_path = cand
    folder_path.mkdir(parents=True, exist_ok=True)
    try:
        if sys.platform == "win32":
            os.startfile(str(folder_path))
        else:
            subprocess.Popen(["xdg-open", str(folder_path)])
        return {"status": "ok", "opened": str(folder_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to open Explorer: {e}")

# =========================================================================
# PHOTO SHOOT & RETOUCHING BAY APIS
# =========================================================================
@app.get("/api/photos/list-input")
async def list_input_photos():
    photos_dir = BASE_DIR / "workspace" / "photos_input"
    photos_dir.mkdir(parents=True, exist_ok=True)
    image_exts = {".jpg", ".jpeg", ".png", ".webp"}
    files = [f.name for f in photos_dir.iterdir() if f.is_file() and f.suffix.lower() in image_exts]
    return {"status": "ok", "photos": files, "count": len(files)}

@app.post("/api/photos/upload")
async def upload_photos(files: List[UploadFile] = File(...)):
    photos_dir = BASE_DIR / "workspace" / "photos_input"
    photos_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for file in files:
        safe_name = Path(file.filename or "upload").name  # strip any path components from the client-supplied filename
        dest = photos_dir / safe_name
        with open(dest, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved.append(str(dest))
    return {"status": "ok", "count": len(saved), "files": saved}

@app.post("/api/photos/retouch")
async def retouch_photo_shoot(payload: Dict[str, Any]):
    shoot_name = payload.get("shoot_name", "glamour_shoot")
    preset = payload.get("preset", "moody_boudoir")
    strength = float(payload.get("smooth_strength", 0.5))
    watermark = payload.get("watermark_text", "@ExclusiveDrop")

    photos_dir = BASE_DIR / "workspace" / "photos_input"
    image_exts = {".jpg", ".jpeg", ".png", ".webp"}
    files = [f for f in photos_dir.iterdir() if f.is_file() and f.suffix.lower() in image_exts]

    if not files:
        raise HTTPException(status_code=400, detail="No photos found in workspace/photos_input/")

    res = photo_retoucher.process_photo_batch(
        image_paths=files,
        shoot_name=shoot_name,
        preset=preset,
        smooth_strength=strength,
        watermark_text=watermark
    )
    return res

# =========================================================================
# INSPIRATION & SHOOT IDEAS BAY APIS
# =========================================================================
@app.get("/api/inspiration/files")
async def list_inspiration_files():
    insp_dir = BASE_DIR / "workspace" / "inspiration"
    insp_dir.mkdir(parents=True, exist_ok=True)
    image_exts = {".jpg", ".jpeg", ".png", ".webp"}
    files = [f.name for f in insp_dir.iterdir() if f.is_file() and f.suffix.lower() in image_exts]
    return {"files": files, "count": len(files)}

@app.post("/api/inspiration/upload")
async def upload_inspiration(files: List[UploadFile] = File(...)):
    insp_dir = BASE_DIR / "workspace" / "inspiration"
    insp_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for file in files:
        safe_name = Path(file.filename or "upload").name  # strip any path components from the client-supplied filename
        dest = insp_dir / safe_name
        with open(dest, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved.append(safe_name)
    return {"status": "ok", "uploaded": saved}

@app.get("/api/inspiration/analyze")
def analyze_inspiration(image: Optional[str] = None):
    return inspiration_scanner.scan_and_analyze(image_filename=image)

@app.get("/api/inspiration/comfyui-prompts")
def get_inspiration_comfyui_prompts(image: Optional[str] = None):
    return inspiration_scanner.generate_comfyui_prompts(image_filename=image)

# =========================================================================
# LIVE CAM & CREATOR STORE TEMPLATE APIS (CHATURBATE & MFC)
# =========================================================================
@app.post("/api/templates/generate-cam")
async def generate_cam_template(payload: Dict[str, Any]):
    model_name = payload.get("model_name", "GoddessAura")
    theme = payload.get("theme", "neon_cyber")
    tip_menu = payload.get("tip_menu")
    bundle_name = payload.get("bundle_name", f"{model_name}_{theme.upper()}_BIO_KIT")

    res = cam_generator.bundle_digital_product(bundle_name=bundle_name, theme=theme, tip_menu=tip_menu)
    cb_html = cam_generator.generate_chaturbate_profile(model_name=model_name, theme=theme, tip_menu=tip_menu)
    mfc_html = cam_generator.generate_mfc_bio(model_name=model_name, theme=theme, tip_menu=tip_menu)

    res["chaturbate_html"] = cb_html
    res["mfc_html"] = mfc_html
    return res

@app.post("/api/templates/tip-menu/generate")
async def generate_tip_menu_endpoint(payload: Dict[str, Any]):
    title = payload.get("title", "✨ Goddess Aura's Interactive Tip Menu ✨")
    subtitle = payload.get("subtitle", "⚡ Lovense Lush & Domi Active · High Vibration ⚡")
    theme = payload.get("theme", "neon_cyber")
    layout_style = payload.get("layout_style", "table")
    items = payload.get("items", [])
    goal_text = payload.get("goal_text", "Tonight's Goal: 1500 / 3000 Tokens — Hot Oil & Dance Show")
    avatar_url = payload.get("avatar_url")
    banner_url = payload.get("banner_url")
    top_tipper = payload.get("top_tipper")
    schedule = payload.get("schedule")

    # Surface which fields are still demo placeholders so the operator doesn't
    # accidentally ship stock photos/fake data to a real client.
    warnings = cam_generator.validate_tip_menu_inputs(
        avatar_url=avatar_url, banner_url=banner_url, top_tipper=top_tipper,
        schedule=schedule, items=items
    )

    rendered_html = cam_generator.generate_tip_menu_standalone(
        title=title,
        subtitle=subtitle,
        theme=theme,
        layout_style=layout_style,
        items=items,
        goal_text=goal_text,
        avatar_url=avatar_url,
        banner_url=banner_url,
        top_tipper=top_tipper,
        schedule=schedule
    )

    chatbot_text = cam_generator.generate_chatbot_text(title, items)
    bundle_name = f"TIP_MENU_{theme.upper()}_PACK"
    bundle_res = cam_generator.bundle_tip_menu_product(bundle_name=bundle_name, theme=theme, items=items)

    return {
        "status": "ok",
        "rendered_html": rendered_html,
        "chatbot_text": chatbot_text,
        "bundle": bundle_res,
        "warnings": warnings
    }


# =========================================================================
# HERALD AUTONOMOUS SCHEDULER & MULTI-TWEET/NEWSLETTER ENDPOINTS
# =========================================================================
@app.get("/api/herald/schedule-status")
async def get_herald_schedule_status():
    return {
        "status": "ok",
        "schedule": herald_scheduler.get_status()
    }

@app.post("/api/herald/dispatch-daily")
async def dispatch_herald_daily():
    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(None, herald_scheduler.dispatch_today_all_now)
    return {
        "status": "ok",
        "message": "Herald daily drop executed immediately (newsletters + pending slots).",
        "results": res
    }

@app.post("/api/herald/dispatch-slot")
async def dispatch_herald_slot(payload: Dict[str, Any]):
    slot_id = payload.get("slot_id", "slot_1_morning")
    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(None, lambda: herald_scheduler.dispatch_slot(slot_id))
    return {
        "status": "ok",
        "slot_id": slot_id,
        "results": res
    }

# =========================================================================
# ETSY DIGITAL STORE APIS (THE MULTI-THOUSAND DOLLAR WORKAROUND)
# =========================================================================
@app.get("/api/etsy/products")
async def get_etsy_products():
    return {
        "status": "ok",
        "products": [
            {
                "id": "presets",
                "title": 'Lightroom Presets (.xmp): "Boudoir & Glamour 1-Click Mobile & Desktop Presets"',
                "description": "5 Studio Presets: Moody Boudoir, Golden Hour Glow, Cyber Neon, Monochrome Noir, 35mm Film",
                "price_rec": "$12.99"
            },
            {
                "id": "contracts",
                "title": "Model Release & Photo Shoot Contract Templates (Legal Pack)",
                "description": "Adult Model Release, 18 U.S.C. 2257 Compliance Checklist, Location Shoot Release",
                "price_rec": "$19.99"
            },
            {
                "id": "posing",
                "title": "50 Boudoir Posing Guide Cards (Printable & Mobile PDF)",
                "description": "50 Elite Poses with director cues, spine arch angles, hand placement, and lighting diagrams",
                "price_rec": "$14.99"
            },
            {
                "id": "templates",
                "title": "Canva / Social Media Promo Templates for Content Creators",
                "description": "OnlyFans/Fansly announcement banners, tip menu flyers, and VIP schedules",
                "price_rec": "$14.99"
            },
            {
                "id": "all",
                "title": "Complete Creator Studio Digital Empire Bundle (All 4 Products)",
                "description": "Full master bundle with all presets, legal releases, 50 posing cards, and promo graphics",
                "price_rec": "$49.99"
            }
        ]
    }

@app.post("/api/etsy/bundle")
async def bundle_etsy_product_endpoint(payload: Dict[str, Any]):
    product_type = payload.get("product_type", "all")
    return etsy_store.bundle_etsy_product(product_type=product_type)

@app.get("/api/download/etsy/{bundle_name}")
async def download_etsy_bundle(bundle_name: str):
    zip_path = BASE_DIR / "workspace" / "etsy_bundles" / f"{bundle_name}.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Etsy bundle zip not found")
    return FileResponse(zip_path, filename=zip_path.name, media_type="application/zip")

# =========================================================================
# FIVERR DELIVERY PACKAGER APIS
# NOTE: This does NOT automate Fiverr itself (no Fiverr API / browser login).
# It only (1) serves a static local gig catalog, (2) bundles already-generated
# assets + a review-request note into a ZIP, and (3) serves that ZIP for
# manual upload to the real Fiverr order page. Posting gigs, detecting new
# orders, and messaging buyers on Fiverr are all still manual/human steps
# (new orders ARE detected separately via email in order_radar.py, which
# polls IMAP - it does not call the Fiverr API either).
# =========================================================================
@app.get("/api/fiverr/gigs")
async def get_fiverr_gigs():
    return {"status": "ok", "gigs": fiverr_bot.get_all_gigs()}

@app.post("/api/fiverr/fulfill")
async def fulfill_fiverr_order(payload: Dict[str, Any]):
    gig_id = payload.get("gig_id", "gig_retouch")
    client_name = payload.get("client_name", "Valued Client")
    order_number = payload.get("order_number", "FO_1001")
    notes = payload.get("notes", "")

    # Collect any relevant files to include in delivery
    assets = []
    if gig_id == "gig_retouch":
        photos_dir = BASE_DIR / "workspace" / "photos_output"
        zips = list(photos_dir.glob("*.zip"))
        if zips:
            assets.append(str(zips[-1]))
    elif gig_id == "gig_teaser":
        output_dir = BASE_DIR / "workspace" / "output"
        zips = list(output_dir.glob("*.zip"))
        if zips:
            assets.append(str(zips[-1]))
    elif gig_id in ("gig_copy", "gig_banner"):
        cam_dir = BASE_DIR / "workspace" / "cam_templates"
        zips = list(cam_dir.glob("*.zip"))
        if zips:
            assets.append(str(zips[-1]))

    res = fiverr_bot.fulfill_order(
        gig_id=gig_id,
        order_number=order_number,
        client_name=client_name,
        assets=assets,
        notes=notes
    )
    return res

@app.get("/api/download/fiverr/{order_number}")
async def download_fiverr_delivery(order_number: str):
    zip_path = BASE_DIR / "workspace" / "fiverr_deliveries" / f"{order_number}_DELIVERY_PACKAGE.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Fiverr delivery zip not found")
    return FileResponse(zip_path, filename=zip_path.name, media_type="application/zip")

# =========================================================================
# CIPHER TREND RESEARCH & MARKET INTELLIGENCE APIS
# =========================================================================
@app.get("/api/research/trends")
async def get_market_trends():
    return {"status": "ok", "trends": trend_agent.get_static_trend_matrix()}

@app.post("/api/research/briefing")
async def generate_research_briefing(payload: Optional[Dict[str, Any]] = None):
    focus = payload.get("focus_area", "all") if payload else "all"
    briefing = trend_agent.generate_intelligence_briefing(focus_area=focus)
    return {"status": "ok", "focus_area": focus, "briefing": briefing}

# =========================================================================
# PIPE 1 - WEBHOOK AUTO-FULFILLMENT (Stripe / Gumroad)
# Public, unauthenticated endpoints called directly by Stripe/Gumroad servers.
# Stripe calls are verified via HMAC signature; Gumroad via seller_id match.
# =========================================================================
@app.post("/api/radar/webhook/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(None, lambda: order_radar.handle_stripe_webhook(payload, sig_header))
    status_code = 200 if res.get("success") else 400
    return JSONResponse(res, status_code=status_code)

@app.post("/api/radar/webhook/gumroad")
async def gumroad_webhook(request: Request):
    form = await request.form()
    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(None, lambda: order_radar.handle_gumroad_webhook(dict(form)))
    status_code = 200 if res.get("success") else 400
    return JSONResponse(res, status_code=status_code)

@app.post("/api/radar/webhook/config")
async def update_webhook_config(payload: Dict[str, Any]):
    cfg = order_radar.update_config(
        stripe_webhook_secret=payload.get("stripe_webhook_secret"),
        gumroad_seller_id=payload.get("gumroad_seller_id"),
        webhook_product_map=payload.get("webhook_product_map")
    )
    return {"status": "ok", "config": {k: v for k, v in cfg.items() if k != "app_password"}}

@app.get("/api/download/order/{token}")
async def download_order_by_token(token: str):
    zip_path = order_radar.get_delivery_by_token(token)
    if not zip_path:
        raise HTTPException(status_code=404, detail="Invalid or expired download link")
    return FileResponse(zip_path, filename=zip_path.name, media_type="application/zip")

# =========================================================================
# PIPE 3 - AUTONOMOUS AI MODEL CONTENT ENGINE (Cipher -> RTX 5070 Ti -> Forge -> Scribe)
# =========================================================================
@app.get("/api/content-engine/status")
async def get_content_engine_status():
    from pipeline.stages.content_engine import content_engine
    return {"status": "ok", "last_result": content_engine.get_last_result(), "schedule": herald_scheduler.get_status()}

@app.post("/api/content-engine/run-now")
async def run_content_engine_now():
    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(None, herald_scheduler.dispatch_content_engine)
    return {"status": "ok", "result": res}

# =========================================================================
# MASTER PIPELINE APIS
# =========================================================================
@app.post("/api/upload")
async def upload_media(file: UploadFile = File(...)):
    try:
        input_dir = BASE_DIR / "workspace" / "input"
        input_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(file.filename or "upload").name  # strip any path components from the client-supplied filename
        dest_file = input_dir / safe_name
        with open(dest_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {
            "status": "ok",
            "filename": safe_name,
            "saved_path": str(dest_file),
            "size_mb": round(dest_file.stat().st_size / (1024**2), 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

@app.post("/api/pipeline/start")
async def start_pipeline_job(payload: Dict[str, Any]):
    video_path_str = payload.get("video_path")
    preset = payload.get("preset", "Adult Creator Shoot")
    if not video_path_str:
        raise HTTPException(status_code=400, detail="video_path is required")
    video_path = Path(video_path_str)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Target video file does not exist")
    job = orchestrator.create_job(video_path, preset)
    orchestrator.run_job_async(job.job_id)
    return {"status": "started", "job_id": job.job_id}

@app.get("/api/pipeline/jobs/{job_id}")
async def get_job(job_id: str):
    job = orchestrator.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()

@app.get("/api/media/{file_path:path}")
async def serve_media(file_path: str):
    search_dirs = [
        BASE_DIR / "workspace" / "output",
        BASE_DIR / "workspace" / "photos_output",
        BASE_DIR / "workspace" / "photos_input",
        BASE_DIR / "workspace" / "inspiration",
        BASE_DIR / "workspace" / "cam_templates",
        BASE_DIR / "workspace" / "temp",
    ]
    for base_dir in search_dirs:
        base_resolved = base_dir.resolve()
        candidate = (base_dir / file_path).resolve()
        # reject any traversal ("..") that escapes the intended base directory
        if candidate.is_relative_to(base_resolved) and candidate.exists():
            return FileResponse(candidate)
    raise HTTPException(status_code=404, detail="Media file not found")

@app.get("/api/download/photos-zip/{shoot_name}")
async def download_photos_bundle(shoot_name: str):
    zip_path = BASE_DIR / "workspace" / "photos_output" / f"{shoot_name}_PHOTO_PACKAGE.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Photo bundle zip not found")
    return FileResponse(zip_path, filename=zip_path.name, media_type="application/zip")

@app.get("/api/download/zip/{job_id}")
async def download_bundle_zip(job_id: str):
    job = orchestrator.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    zip_path_str = job.results.get("bundle", {}).get("zip_file")
    if not zip_path_str or not Path(zip_path_str).exists():
        raise HTTPException(status_code=404, detail="Zip bundle not found or not yet generated")
    return FileResponse(
        Path(zip_path_str),
        filename=Path(zip_path_str).name,
        media_type="application/zip"
    )

@app.get("/api/download/cam-template/{bundle_name}")
async def download_cam_bundle(bundle_name: str):
    zip_path = BASE_DIR / "workspace" / "cam_templates" / f"{bundle_name}.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Template zip not found")
    return FileResponse(zip_path, filename=zip_path.name, media_type="application/zip")

prism_process = None

@app.post("/api/prism/launch")
async def launch_local_prism():
    global prism_process
    prism_dir = BASE_DIR / "prism_local"
    if not prism_dir.exists():
        raise HTTPException(status_code=404, detail="Local Prism copy not found")
    try:
        if prism_process is None or prism_process.poll() is not None:
            cmd = [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "7862"]
            prism_process = subprocess.Popen(
                cmd,
                cwd=str(prism_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
            )
        return {
            "status": "launched",
            "url": "http://127.0.0.1:7862",
            "message": "Local Prism copy running on port 7862 (isolated from F:/QUE)"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start local Prism: {e}")


# =============================================================================
# ORDER RADAR (GMAIL & NOTIFICATIONS)
# =============================================================================
@app.post("/api/open-brand-folder")
async def open_brand_folder():
    folder = BASE_DIR / "workspace" / "brand_assets"
    folder.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        os.startfile(str(folder))
    return {"status": "ok", "path": str(folder)}

@app.get("/api/radar/status")
async def get_radar_status():
    return {
        "status": "ok",
        "config": {
            "email": order_radar.config.get("email", "digitalcreatorassets@gmail.com"),
            "has_password": bool(order_radar.config.get("app_password")),
            "imap_server": order_radar.config.get("imap_server", "imap.gmail.com"),
            "auto_check": order_radar.config.get("auto_check", False),
            "last_checked": order_radar.config.get("last_checked")
        },
        "active_orders": order_radar.orders
    }

@app.post("/api/radar/config")
async def update_radar_config(payload: Dict[str, Any]):
    app_pw = payload.get("app_password")
    auto_check = payload.get("auto_check")
    cfg = order_radar.update_config(app_password=app_pw, auto_check=auto_check)
    return {"status": "ok", "config": cfg}

@app.post("/api/radar/check")
async def check_radar_inbox():
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, order_radar.check_inbox)

@app.post("/api/radar/simulate")
async def simulate_radar_order(payload: Dict[str, Any] = None):
    platform = "fiverr"
    if payload and "platform" in payload:
        platform = payload["platform"]
    return order_radar.simulate_order(platform=platform)

@app.post("/api/radar/fulfill/{order_id}")
async def fulfill_radar_order(order_id: str):
    success = order_radar.mark_fulfilled(order_id)
    if not success:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"status": "ok", "order_id": order_id, "state": "fulfilled"}

# =========================================================================
# VRAM MEMORY WATCHDOG (5-MIN IDLE RECOVERY)
# =========================================================================
@app.get("/api/vram/status")
async def get_vram_status():
    return {"status": "ok", "vram": vram_manager.get_status()}

@app.post("/api/vram/purge")
async def purge_vram_endpoint():
    report = vram_manager.purge_vram(reason="manual_request")
    return {"status": "ok", "report": report, "vram": vram_manager.get_status()}

@app.post("/api/vram/config")
async def update_vram_config(payload: Dict[str, Any]):
    timeout = payload.get("idle_timeout_seconds")
    if timeout and isinstance(timeout, (int, float)) and timeout >= 30:
        vram_manager.idle_timeout = int(timeout)
        return {"status": "ok", "idle_timeout_seconds": vram_manager.idle_timeout}
    raise HTTPException(status_code=400, detail="Invalid idle_timeout_seconds (minimum 30 seconds)")

@app.post("/api/vram/swap")
async def block_swap_endpoint(payload: Dict[str, Any] = {}):
    target = payload.get("target_model") or payload.get("model")
    if not target:
        target = ai_service.get_text_model()
    res = vram_manager.prepare_for_model(target)
    return {"status": "ok", "swap": res, "vram": vram_manager.get_status()}

@app.get("/api/system/gpu-partition")
async def get_gpu_partition_endpoint():
    return {"status": "ok", "partition": vram_manager.get_dual_gpu_partition(), "vram": vram_manager.get_status()}


# =========================================================================
# OMNI-MARKETING ENGINE (AGENT: MERCURY [80 Hg])
# =========================================================================
@app.post("/api/marketing/generate")
async def generate_marketing_campaign(payload: Dict[str, Any]):
    channel = payload.get("channel", "fiverr")
    target_name = payload.get("target_name", "")
    target_url = payload.get("target_url", "")
    goal = payload.get("goal", "conversions")
    custom_notes = payload.get("custom_notes", "")
    
    result = omni_marketer.generate_campaign(
        channel=channel,
        target_name=target_name,
        target_url=target_url,
        goal=goal,
        custom_notes=custom_notes
    )
    return {"status": "ok", "campaign": result}

@app.get("/api/marketing/history")
async def get_marketing_history():
    history = omni_marketer.get_campaign_history()
    return {"status": "ok", "campaigns": history}

# =========================================================================
# NEWSLETTER & BLOG DISPATCHER (AGENT: HERALD [33 As])
# =========================================================================
@app.get("/api/newsletter/subscribers")
async def get_newsletter_subscribers():
    summary = newsletter_mgr.get_subscribers_summary()
    return {"status": "ok", "data": summary}

@app.post("/api/newsletter/subscribe")
async def subscribe_to_newsletters(payload: Dict[str, Any]):
    email = payload.get("email", "")
    publications = payload.get("publications", [])
    name = payload.get("name", "")
    source = payload.get("source", "web_portal")
    send_welcome = payload.get("send_welcome", True)

    res = newsletter_mgr.subscribe_multi(
        email=email,
        publications=publications,
        name=name,
        source=source,
        send_welcome=send_welcome
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to subscribe"))
    return {"status": "ok", "result": res}

@app.post("/api/newsletter/unsubscribe")
async def unsubscribe_from_newsletter(payload: Dict[str, Any]):
    email = payload.get("email", "")
    pub = payload.get("publication")
    res = newsletter_mgr.unsubscribe(email=email, publication=pub)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to unsubscribe"))
    return {"status": "ok", "message": res.get("message")}
@app.get("/api/newsletter/config")
async def get_newsletter_config():
    cfg = newsletter_mgr.load_config()
    status = newsletter_mgr.get_run_status()
    return {"status": "ok", "config": cfg, "execution": status}

@app.post("/api/newsletter/subscribers/add")
async def add_newsletter_subscriber(payload: Dict[str, Any]):
    email = payload.get("email", "")
    res = newsletter_mgr.add_subscriber(email)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to add email"))
    return res

@app.post("/api/newsletter/subscribers/remove")
async def remove_newsletter_subscriber(payload: Dict[str, Any]):
    email = payload.get("email", "")
    res = newsletter_mgr.remove_subscriber(email)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to remove email"))
    return res

@app.post("/api/newsletter/elements/update")
async def update_newsletter_elements(payload: Dict[str, Any]):
    elements = payload.get("elements", {})
    categories = payload.get("categories")
    min_discount = payload.get("min_discount_pct")
    res = newsletter_mgr.update_elements(elements, categories=categories, min_discount=min_discount)
    return {"status": "ok", "result": res}

@app.post("/api/newsletter/run")
async def trigger_newsletter_run():
    res = newsletter_mgr.trigger_dispatch()
    return {"status": "ok", "result": res}

@app.get("/api/newsletter/logs")
async def get_newsletter_logs():
    return newsletter_mgr.get_run_status()

@app.get("/api/newsletter/publications")
async def get_newsletter_publications():
    pubs = newsletter_mgr.get_publications()
    return {"status": "ok", "publications": pubs}

@app.get("/api/newsletter/preview", response_class=HTMLResponse)
async def get_newsletter_preview(pub: str = "creator_pulse"):
    html_content = newsletter_mgr.get_html_preview(pub_id=pub)
    return HTMLResponse(content=html_content)

@app.get("/api/newsletter/blog-post")
async def get_newsletter_blog_post(pub: str = "creator_pulse"):
    md = newsletter_mgr.get_blog_post_markdown(pub_id=pub)
    return {"status": "ok", "markdown": md, "pub": pub}

@app.get("/api/newsletter/thread")
async def get_newsletter_thread(pub: str = "creator_pulse"):
    info = newsletter_mgr.get_twitter_thread_with_media(pub_id=pub)
    return {
        "status": "ok",
        "thread": info["thread"],
        "pub": pub,
        "media_path": info.get("media_path"),
        "media_filename": info.get("media_filename")
    }


@app.post("/api/newsletter/send-test")
async def send_newsletter_test(payload: Dict[str, Any]):
    pub = payload.get("pub", "creator_pulse")
    recipient = payload.get("recipient", "careypmediagroup@gmail.com")
    res = newsletter_mgr.send_test_email(pub_id=pub, recipient=recipient)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to send test email"))
    return res



@app.get("/api/twitter/status")
async def get_twitter_status(handle: str = "creatorpulselab"):
    return twitter_poster.verify_credentials(handle)

@app.post("/api/twitter/publish")
async def publish_twitter_thread(payload: Dict[str, Any]):
    handle = payload.get("handle", "creatorpulselab")
    tweets = payload.get("thread", [])
    media_path = payload.get("media_path")
    if not media_path:
        latest_vis = newsletter_mgr.get_latest_comfy_visual()
        if latest_vis and latest_vis.exists():
            media_path = str(latest_vis)
    media_list = [media_path] if media_path else None
    res = twitter_poster.post_thread(handle, tweets, media_paths=media_list)
    return res

@app.get("/api/pinterest/status")
async def get_pinterest_status():
    return pinterest_poster.verify_credentials()

@app.get("/api/pinterest/boards")
async def get_pinterest_boards():
    return pinterest_poster.list_boards()

@app.post("/api/pinterest/post-now")
async def publish_pinterest_pin():
    """Manually triggers today's scheduled Pinterest pin immediately (for testing the
    integration end-to-end), instead of waiting for Herald's daily_slot_time window."""
    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(None, herald_scheduler.dispatch_pinterest_daily)
    return res

@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    token = websocket.cookies.get(SESSION_COOKIE)
    if not token or not verify_session_token(token, _get_session_secret()):
        await websocket.close(code=4401)
        return
    await websocket.accept()
    connected_websockets.append(websocket)
    try:
        while True:
            stats = get_system_stats()
            stats["ollama"] = get_ollama_models()
            stats["vram_watchdog"] = vram_manager.get_status()
            stats["comfy_health"] = comfy_health_cache
            await websocket.send_text(json.dumps({"type": "telemetry", "stats": stats}))
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)
    except Exception:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)


# ==============================================================================
# WORKHORSE MASTER AI OPERATOR ENDPOINTS
# ==============================================================================
@app.get("/api/system/health-check")
async def get_system_health():
    report = ai_operator.run_system_diagnostics()
    return report

@app.get("/api/system/incidents")
async def get_incident_log(limit: int = 20):
    return {"status": "ok", "incidents": ai_operator.get_recent_incidents(limit=limit)}

@app.get("/api/system/daily-health-log")
async def get_daily_health_log(limit: int = 30):
    """Returns the persisted daily system-health snapshot history (one entry per
    calendar day) so health trends are reviewable over time, not just right now."""
    return {"status": "ok", "daily_checks": ai_operator.get_daily_health_log(limit=limit)}

@app.get("/api/system/error-log")
async def get_error_log(limit: int = 20):
    """Returns the persistent raw error log - tool failures, Ollama timeouts/connection
    errors, etc. - independent from the self-healing incident log."""
    return {"status": "ok", "errors": ai_operator.get_recent_errors(limit=limit)}

@app.post("/api/system/self-heal")
async def trigger_self_heal(payload: Dict[str, Any] = {}):
    action = payload.get("action", "all")
    results = {}
    if action in ("all", "vram"):
        results["vram"] = ai_operator.fix_vram_overflow()
    if action in ("all", "subscribers"):
        results["subscribers"] = ai_operator.repair_subscribers_db()
    results["diagnostics"] = ai_operator.run_system_diagnostics()
    return {"status": "ok", "results": results}

@app.get("/api/operator/models")
async def get_operator_models():
    models = ai_operator.get_available_models()
    return {"status": "ok", "models": models}

@app.get("/api/operator/history")
async def get_operator_history(request: Request):
    """Returns the persisted SYNAPSE conversation for THIS browser session only, so the
    UI can restore it after a page reload, tab switch, or a dropped connection without
    pulling in any other session's chat."""
    session_id = _get_request_session_id(request)
    return {"status": "ok", "history": ai_operator.get_history(session_id)}

@app.post("/api/operator/chat")
async def operator_chat_endpoint(
    request: Request,
    message: str = Form(...),
    model: str = Form("huihui_ai/qwen3-abliterated:14b"),
    web_search: bool = Form(False),
    files: List[UploadFile] = File(default=[])
):
    saved_paths = []
    if files:
        for f in files:
            if f.filename:
                safe_name = Path(f.filename).name  # strip any path components from the client-supplied filename
                dest = CLIENT_INBOX_DIR / safe_name
                content = await f.read()
                with open(dest, "wb") as out:
                    out.write(content)
                saved_paths.append(str(dest))

    session_id = _get_request_session_id(request)
    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(
        None,
        lambda: ai_operator.chat(
            message=message,
            model=model,
            web_search=web_search,
            attached_files=saved_paths,
            session_id=session_id
        )
    )
    return res

@app.post("/api/operator/clear")
async def operator_clear_endpoint(request: Request):
    session_id = _get_request_session_id(request)
    ai_operator.clear_history(session_id)
    return {"status": "ok", "message": "Operator history cleared"}

@app.get("/api/operator/client-files")
async def get_client_inbox_files():
    files = []
    if CLIENT_INBOX_DIR.exists():
        for f in CLIENT_INBOX_DIR.iterdir():
            if f.is_file():
                files.append({
                    "name": f.name,
                    "size": f.stat().st_size,
                    "suffix": f.suffix.lower()
                })
    return {"status": "ok", "files": files}

# ==============================================================================
# REAL-TIME MARKET RADAR & LINK INGESTION ENDPOINTS (CIPHER & SYNAPSE)
# ==============================================================================
@app.get("/api/trends/vault")
async def get_trends_vault():
    vault = trend_agent.load_vault()
    return {"status": "ok", "vault": vault}

@app.post("/api/trends/sweep")
async def trigger_trend_sweep():
    loop = asyncio.get_event_loop()
    vault = await loop.run_in_executor(None, trend_agent.run_daily_radar_sweep)
    return {"status": "ok", "vault": vault}

@app.post("/api/trends/ingest-link")
async def ingest_trend_link(payload: Dict[str, Any]):
    url = payload.get("url", "").strip()
    notes = payload.get("notes", "")
    if not url:
        raise HTTPException(status_code=400, detail="Missing required 'url' parameter")
    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(None, lambda: trend_agent.ingest_user_link(url=url, user_notes=notes))
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("message", "Failed to ingest link"))
    return {"status": "ok", "result": res}

# ==============================================================================
# COMFYUI 5070 Ti DIFFUSION & IRIS [77 Ir] AUTO-QC ENDPOINTS
# ==============================================================================
@app.get("/api/comfy/status")
async def get_comfy_status():
    from pipeline.stages.comfyui_bridge import comfy_bridge
    loop = asyncio.get_event_loop()
    status = await loop.run_in_executor(None, comfy_bridge.check_connection)
    return {"status": "ok", "comfy": status}

@app.post("/api/comfy/generate")
async def trigger_comfy_generation(payload: Dict[str, Any]):
    from pipeline.stages.comfyui_bridge import comfy_bridge
    prompt = payload.get("prompt", "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Missing required 'prompt' field")
    negative_prompt = payload.get("negative_prompt", "")
    width = payload.get("width", 1024)
    height = payload.get("height", 1024)
    style = payload.get("style", "photorealism")
    checkpoint = payload.get("checkpoint")
    loras = payload.get("loras")
    lora_name = payload.get("lora_name")
    lora_strength = payload.get("lora_strength", 0.8)
    steps = payload.get("steps", 25)
    cfg = payload.get("cfg", 7.0)
    auto_qc = payload.get("auto_qc", True)

    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(
        None,
        lambda: comfy_bridge.generate_and_audit(
            positive_prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            style_preset=style,
            checkpoint=checkpoint,
            loras=loras,
            lora_name=lora_name,
            lora_strength=lora_strength,
            steps=steps,
            cfg=cfg,
            auto_qc=auto_qc
        )
    )
    return res

@app.post("/api/comfy/qc-audit")
async def trigger_iris_qc_audit(payload: Dict[str, Any]):
    from pipeline.stages.comfyui_bridge import comfy_bridge
    filename = payload.get("filename", "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="Missing 'filename'")
    img_path = Path(filename)
    if not img_path.is_absolute():
        img_path = Path("F:/WORKHORSE/workspace/brand_assets/comfy_renders") / filename
        if not img_path.exists():
            img_path = Path("F:/WORKHORSE/workspace/client_inbox") / filename

    if not img_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found")

    loop = asyncio.get_event_loop()
    audit = await loop.run_in_executor(
        None,
        lambda: comfy_bridge.run_iris_qc_audit(img_path, original_prompt=payload.get("prompt", ""))
    )
    return {"status": "ok", "audit": audit}

@app.get("/api/comfy/audit-log")
async def get_comfy_audit_log():
    audit_file = Path("F:/WORKHORSE/workspace/comfy_qc_audit.json")
    if audit_file.exists():
        try:
            with open(audit_file, "r", encoding="utf-8") as f:
                return {"status": "ok", "records": json.load(f)}
        except Exception:
            pass
    return {"status": "ok", "records": []}

@app.get("/api/comfy/gallery")
async def get_comfy_gallery():
    gallery_dir = Path("F:/WORKHORSE/workspace/brand_assets/comfy_renders")
    images = []
    if gallery_dir.exists():
        for f in sorted(gallery_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                images.append({
                    "filename": f.name,
                    "url": f"/static/brand_assets/comfy_renders/{f.name}",
                    "size_kb": round(f.stat().st_size / 1024, 1),
                    "created": f.stat().st_mtime
                })
    return {"status": "ok", "images": images[:30]}



@app.post("/api/comfy/generate-glb")
async def generate_glb_endpoint(payload: Dict[str, Any]):
    """Generates an interactive 3D GLB character model on the Main PC (5070 Ti)."""
    from pipeline.stages.comfyui_bridge import comfy_bridge
    agent = payload.get("agent", "synapse")
    prompt = payload.get("prompt")
    res = comfy_bridge.generate_glb_character(agent_name=agent, prompt=prompt)
    return res

@app.post("/api/comfy/purge-vram")
async def comfy_remote_purge():
    """Remotely purges RTX 5070 Ti VRAM on Main PC."""
    from pipeline.stages.comfyui_bridge import comfy_bridge
    res = comfy_bridge.remote_purge_vram()
    return res

@app.post("/api/comfy/prewarm")
async def comfy_prewarm_endpoint(checkpoint: Optional[str] = None):
    """Sends a 1-step warmup ping to RTX 5070 Ti on Main PC."""
    from pipeline.stages.comfyui_bridge import comfy_bridge
    res = comfy_bridge.prewarm_model(checkpoint=checkpoint)
    return res

@app.post("/api/system/prune-staging")
async def prune_staging_endpoint(hours: int = 48):
    """Manually triggers pruning of old staging and temp renders."""
    from shared.vram_manager import vram_manager
    res = vram_manager.prune_old_staging_files(max_age_hours=hours)
    return res

if __name__ == "__main__":

    uvicorn.run("dashboard.server:app", host="0.0.0.0", port=8800, reload=False)
