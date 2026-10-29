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
import urllib.parse
import tempfile
import zipfile
from pathlib import Path, PurePath
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool
import uvicorn

BASE_DIR = Path("F:/WORKHORSE")
sys.path.insert(0, str(BASE_DIR))

from shared.system_monitor import get_system_stats, get_ollama_models
from shared.atomic_writer import atomic_write_json, safe_read_json
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
from pipeline.stages.ai_operator import ai_operator, CLIENT_INBOX_DIR, CLIENT_OUTPUTS_DIR, create_client_batch, register_batch_files
from pipeline.stages.herald_scheduler import herald_scheduler

main_loop = None
connected_websockets: List[WebSocket] = []
connected_stackchan_websockets: Dict[str, List[WebSocket]] = {"synapse": [], "muse": []}

def broadcast_stackchan(robot_name: str, packet: Dict[str, Any]):
    """Broadcasts a telemetry packet or speech command to connected M5Stack-chan robot."""
    robot_key = robot_name.lower().strip()
    sockets = connected_stackchan_websockets.get(robot_key, [])
    payload = json.dumps(packet)
    for ws in list(sockets):
        try:
            if main_loop and main_loop.is_running():
                asyncio.run_coroutine_threadsafe(ws.send_text(payload), main_loop)
        except Exception:
            pass

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
    try:
        from pipeline.stages.ai_operator import active_task_tracker
        if active_task_tracker.get_all_active_tasks():
            return True
    except Exception:
        pass
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

async def dropzone_watcher_loop():
    """Polls F:\\WORKHORSE\\dropzone every 3s for dropped client photo batches and
    auto-fulfills them (pipeline.stages.dropzone_fulfiller.DropzoneFulfiller). This was
    previously only a standalone script (dropzone_watcher.py) that nothing ever
    actually launched - "hands-off fulfillment" wasn't running at all. Runs as a
    background task here instead, so it's active for as long as WORKHORSE itself is."""
    from pipeline.stages.dropzone_fulfiller import DropzoneFulfiller
    fulfiller = DropzoneFulfiller()
    loop = asyncio.get_event_loop()
    print("[DROPZONE WATCHER] Active and monitoring F:\\WORKHORSE\\dropzone...")
    from pipeline.stages.ai_operator import active_task_tracker
    while True:
        try:
            await asyncio.sleep(3)
            drop_path = BASE_DIR / "dropzone"
            has_drops = drop_path.exists() and any(p.is_dir() for p in drop_path.iterdir())
            if has_drops:
                active_task_tracker.start_task(
                    agent="aura",
                    sub_agent="apex",
                    task_desc="Aura [79 Au] & Apex [78 Pt]: Auto-retouching & packaging client batch from Dropzone...",
                    task_id="dropzone_active",
                    progress=30
                )
            try:
                results = await loop.run_in_executor(None, fulfiller.process_dropzone)
            finally:
                if has_drops:
                    active_task_tracker.finish_task("dropzone_active")
            for r in results:
                if r.get("status") == "completed":
                    print(f"[DROPZONE WATCHER] Completed order: {r.get('order_name')} ({r.get('photos_processed')} photos)")
                elif r.get("status") == "failed":
                    print(f"[DROPZONE WATCHER] FAILED order: {r.get('order_name')}: {r.get('error')}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[DROPZONE WATCHER ERROR] {e}")

async def cam_show_watcher_loop():
    """Polls F:\\WORKHORSE\\cam_shows\\inbox for dropped raw adult cam shows, tracks real-time progress
    across Vanguard, Iris, Echo, Aura, Forge, and Apex, and auto-packages them sequentially."""
    from pipeline.stages.cam_show_packager import INBOX_DIR, PROCESSING_DIR, ARCHIVE_DIR, package_cam_show
    from pipeline.stages.ai_operator import active_task_tracker
    loop = asyncio.get_event_loop()
    print("[CAM SHOW WATCHER] Active and monitoring F:\\WORKHORSE\\cam_shows\\inbox...")
    seen_sizes = {}
    while True:
        try:
            await asyncio.sleep(4)
            if not INBOX_DIR.exists():
                continue
            raw_files = [f for f in INBOX_DIR.iterdir() if f.suffix.lower() in [".mp4", ".mkv", ".mov"] and not f.name.startswith(".")]
            if raw_files and not active_task_tracker.get_all_active_tasks():
                active_task_tracker.start_task(
                    agent="synapse",
                    sub_agent="vanguard",
                    task_desc=f"Synapse [100 Fm]: Cam Show Queue — {len(raw_files)} shows waiting in inbox ({raw_files[0].name})...",
                    task_id="cam_show_queue",
                    progress=5
                )

            for item in raw_files:
                current_size = item.stat().st_size
                if item.name in seen_sizes and seen_sizes[item.name] == current_size:
                    print(f"[CAM SHOW WATCHER] Processing stable file: {item.name} ({round(current_size/(1024**3), 2)} GB)")
                    target_proc = PROCESSING_DIR / item.name
                    shutil.move(item, target_proc)
                    seen_sizes.pop(item.name, None)
                    active_task_tracker.finish_task("cam_show_queue")

                    try:
                        await loop.run_in_executor(None, package_cam_show, target_proc)
                        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
                        dest_arch = ARCHIVE_DIR / item.name
                        if target_proc.exists():
                            shutil.move(target_proc, dest_arch)
                            print(f"[CAM SHOW WATCHER] Archived raw stream to: {dest_arch.name}")
                    except Exception as e:
                        print(f"[CAM SHOW WATCHER ERROR] {item.name}: {e}")
                    break
                else:
                    seen_sizes[item.name] = current_size
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[CAM SHOW WATCHER ERROR] {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global main_loop
    main_loop = asyncio.get_running_loop()
    print("[WORKHORSE] Command Center Server running on http://0.0.0.0:8800 (Tailscale: http://100.66.45.48:8800 or http://secondary-pc:8800)")
    watchdog_task = asyncio.create_task(vram_manager.run_watchdog_loop())
    herald_task = asyncio.create_task(herald_scheduler.run_loop())
    comfy_health_task = asyncio.create_task(comfy_health_monitor_loop())
    remediation_task = asyncio.create_task(auto_remediation_loop())
    dropzone_task = asyncio.create_task(dropzone_watcher_loop())
    cam_show_task = asyncio.create_task(cam_show_watcher_loop())
    try:
        from pipeline.stages.creator_community_hub import get_community_daemon
        get_community_daemon().start()
    except Exception as _ce:
        print(f"[WORKHORSE] Community daemon init note: {_ce}")
    main_loop.run_in_executor(None, ai_operator.run_daily_health_check)
    try:
        yield
    finally:
        watchdog_task.cancel()
        herald_task.cancel()
        comfy_health_task.cancel()
        remediation_task.cancel()
        dropzone_task.cancel()
        cam_show_task.cancel()

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
PUBLIC_PATHS = {"/login", "/api/login", "/setup", "/api/setup", "/favicon.ico", "/subscribe", "/api/newsletter/subscribe", "/api/newsletter/unsubscribe", "/api/radar/webhook/stripe", "/api/radar/webhook/gumroad", "/api/radar/webhook/whop", "/api/monitor/agents-active", "/api/cam-shows/queue"}
PUBLIC_PREFIXES = ("/static/", "/api/download/order/", "/api/vault/stream/", "/craftymyia", "/creatormediastudio", "/charlettewebb", "/ws/stackchan/", "/api/stackchan/")


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


def _is_loopback(host: Optional[str]) -> bool:
    return host in ("127.0.0.1", "::1", "localhost")


def _is_authenticated(request) -> bool:
    token = request.cookies.get(SESSION_COOKIE)
    if bool(token) and verify_session_token(token, _get_session_secret()):
        return True
    client_host = getattr(request.client, "host", "") if request.client else ""
    if _is_loopback(client_host):
        return True
    return False


def _get_request_session_id(request) -> Optional[str]:
    """Extracts the unique per-login session id from the request's auth cookie, used to
    keep each browser session's SYNAPSE chat memory separate from every other session."""
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        sid = get_session_id(token, _get_session_secret())
        if sid:
            return sid
    client_host = getattr(request.client, "host", "") if request.client else ""
    if _is_loopback(client_host):
        return "local_commander_session"
    return None


@app.middleware("http")
async def auth_gate_middleware(request, call_next):
    path = request.url.path
    if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
        return await call_next(request)
    if not _is_authenticated(request):
        if path.startswith("/api/"):
            return JSONResponse({"status": "error", "detail": "Not authenticated"}, status_code=401)
        return RedirectResponse(url="/login")
    response = await call_next(request)
    client_host = getattr(request.client, "host", "") if request.client else ""
    if _is_loopback(client_host) and not request.cookies.get(SESSION_COOKIE):
        try:
            token = make_session_token(_get_session_secret())
            response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", max_age=7 * 24 * 3600)
        except Exception:
            pass
    return response


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


_PASSIVE_POLL_PATHS = {
    "/api/system/stats",
    "/api/system/health-check",
    "/api/radar/status",
    "/api/vram/status",
    "/api/monitor/agents-active",
    "/api/fiverr/orders",
    "/api/etsy/orders",
    "/api/herald/schedule-status",
    "/api/outputs/gallery",
    "/api/outputs/categories",
    "/ws/telemetry",
    "/favicon.ico",
}

@app.middleware("http")
async def activity_tracker_middleware(request, call_next):
    path = request.url.path
    if not (path.startswith("/static") or path in _PASSIVE_POLL_PATHS):
        vram_manager.record_activity(source=path)
    response = await call_next(request)
    return response

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "dashboard" / "static")), name="static")

brand_assets_dir = BASE_DIR / "workspace" / "brand_assets"
brand_assets_dir.mkdir(parents=True, exist_ok=True)
app.mount("/brand_assets", StaticFiles(directory=str(brand_assets_dir)), name="brand_assets")
app.mount("/craftymyia", StaticFiles(directory=str(BASE_DIR / "workspace" / "craftymyia_site"), html=True), name="craftymyia")
app.mount("/creatormediastudio", StaticFiles(directory=str(BASE_DIR / "workspace" / "creatormediastudio_site"), html=True), name="creatormediastudio")
app.mount("/charlettewebb", StaticFiles(directory=str(BASE_DIR / "workspace" / "charlettewebb_site"), html=True), name="charlettewebb")

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
    stats = await asyncio.to_thread(get_system_stats)
    stats["ollama"] = await asyncio.to_thread(get_ollama_models)
    stats["vram_watchdog"] = vram_manager.get_status()
    stats["comfy_health"] = comfy_health_cache
    return stats

@app.get("/api/system/models")
async def get_models():
    return await asyncio.to_thread(get_ollama_models)

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
        cfg = safe_read_json(CONFIG_FILE, default={})
        if "agents" not in cfg:
            cfg["agents"] = {}
        if agent_key not in cfg["agents"]:
            cfg["agents"][agent_key] = {}
        cfg["agents"][agent_key].update(payload)
        atomic_write_json(CONFIG_FILE, cfg)
        return {"status": "ok", "message": f"Updated config for agent {agent_key}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/open-folder")
async def open_output_folder(payload: Optional[Dict[str, Any]] = None):
    folder_path = BASE_DIR / "workspace" / "output"
    if payload and payload.get("path"):
        cand = Path(str(payload["path"]).strip())
        if not cand.is_absolute():
            cand = BASE_DIR / cand
        cand.mkdir(parents=True, exist_ok=True)
        folder_path = cand
    else:
        folder_path.mkdir(parents=True, exist_ok=True)

    opened_ok = False
    try:
        if sys.platform == "win32":
            os.startfile(str(folder_path))
            opened_ok = True
        else:
            subprocess.Popen(["xdg-open", str(folder_path)])
            opened_ok = True
    except Exception as e:
        print(f"[OPEN-FOLDER] Host OS explorer note: {e}")
        opened_ok = False

    files = []
    total_size = 0
    try:
        if folder_path.exists():
            for p in sorted(folder_path.iterdir(), key=lambda x: x.stat().st_mtime if x.is_file() else 0, reverse=True):
                if p.is_file():
                    size = p.stat().st_size
                    total_size += size
                    files.append({
                        "name": p.name,
                        "size_bytes": size,
                        "size_formatted": f"{size / (1024*1024):.1f} MB" if size >= 1024*1024 else f"{size / 1024:.1f} KB",
                        "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.stat().st_mtime)),
                        "url": f"/api/media/{p.name}"
                    })
    except Exception as e:
        print(f"[OPEN-FOLDER] File scan note: {e}")

    return {
        "status": "ok",
        "opened": str(folder_path),
        "folder_name": folder_path.name,
        "path": str(folder_path).replace("\\", "/"),
        "files": files[:200],
        "total_files": len(files),
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "opened_in_os": opened_ok
    }

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
    preset = payload.get("preset", "pro_natural")
    strength = float(payload.get("smooth_strength", 0.5))
    watermark = payload.get("watermark_text", "@ExclusiveDrop")
    edit_style = payload.get("edit_style")  # "glamour"|"natural"|"concert_stage"|"family_event"

    photos_dir = BASE_DIR / "workspace" / "photos_input"
    image_exts = {".jpg", ".jpeg", ".png", ".webp"}
    files = [f for f in photos_dir.iterdir() if f.is_file() and f.suffix.lower() in image_exts]

    if not files:
        raise HTTPException(status_code=400, detail="No photos found in workspace/photos_input/")

    print_master = bool(payload.get("print_master", False))
    from pipeline.stages.ai_operator import active_task_tracker
    active_task_tracker.start_task(
        agent="aura",
        task_desc=f"Aura [79 Au]: Retouching {len(files)} photos for '{shoot_name}' ({preset})...",
        task_id=f"aura_retouch_{shoot_name}",
        progress=35
    )
    try:
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(
            None,
            lambda: photo_retoucher.process_photo_batch(
                image_paths=files,
                shoot_name=shoot_name,
                preset=preset,
                smooth_strength=strength,
                watermark_text=watermark,
                edit_style=edit_style,
                print_master=print_master
            )
        )
        return res
    finally:
        active_task_tracker.finish_task(f"aura_retouch_{shoot_name}")

@app.get("/api/photos/packages")
async def list_photo_packages():
    """Lists all available retouched photo packages on disk."""
    out_dir = BASE_DIR / "workspace" / "photos_output"
    if not out_dir.exists():
        return {"packages": []}
    packages = []
    for p in out_dir.iterdir():
        if p.is_dir() and p.name.endswith("_RETOUCHED_PACKAGE"):
            manifest_file = p / "manifest.json"
            created_at = None
            total_photos = 0
            if manifest_file.exists():
                try:
                    with open(manifest_file, "r", encoding="utf-8") as mf:
                        m_data = json.load(mf)
                        created_at = m_data.get("created_at")
                        total_photos = len(m_data.get("source_filenames", []))
                except Exception:
                    pass
            if not total_photos:
                master_dir = p / "01_master_fullres"
                if master_dir.exists():
                    total_photos = len([f for f in master_dir.iterdir() if f.is_file()])

            shoot_stem = p.name.replace("_RETOUCHED_PACKAGE", "")
            client_zip = out_dir / f"{shoot_stem}_CLIENT_PACKAGE.zip"
            photo_zip = out_dir / f"{shoot_stem}_PHOTO_PACKAGE.zip"
            zip_file = client_zip if client_zip.exists() else (photo_zip if photo_zip.exists() else None)
            zip_size_mb = round(zip_file.stat().st_size / (1024**2), 1) if zip_file else 0

            packages.append({
                "package_name": p.name,
                "shoot_name": shoot_stem,
                "total_photos": total_photos,
                "created_at": created_at,
                "zip_name": zip_file.name if zip_file else None,
                "zip_size_mb": zip_size_mb,
                "mtime": p.stat().st_mtime
            })
    packages.sort(key=lambda x: x.get("mtime", 0), reverse=True)
    return {"packages": packages}


@app.get("/api/photos/latest-retouched")
async def get_latest_retouched_package(package_name: Optional[str] = None):
    """Loads a retouched package from disk so the UI gallery displays all retouched images."""
    out_dir = BASE_DIR / "workspace" / "photos_output"
    if not out_dir.exists():
        return {"status": "none", "photos": []}

    target_pkg = None
    if package_name:
        candidate = out_dir / package_name
        if candidate.exists() and candidate.is_dir():
            target_pkg = candidate

    if not target_pkg:
        dirs = [p for p in out_dir.iterdir() if p.is_dir() and p.name.endswith("_RETOUCHED_PACKAGE")]
        if not dirs:
            return {"status": "none", "photos": []}
        dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        target_pkg = dirs[0]

    shoot_name = target_pkg.name.replace("_RETOUCHED_PACKAGE", "")
    master_dir = target_pkg / "01_master_fullres"
    teasers_dir = target_pkg / "02_social_teasers"
    crops_4x5_dir = target_pkg / "03_instagram_4x5"
    crops_9x16_dir = target_pkg / "04_stories_9x16"

    photos = []
    if master_dir.exists():
        image_exts = {".jpg", ".jpeg", ".png", ".webp"}
        master_files = sorted([f for f in master_dir.iterdir() if f.is_file() and f.suffix.lower() in image_exts])
        for mf in master_files:
            stem = mf.stem.replace("_retouched", "")
            orig_name = f"{stem}.jpg"
            teaser_file = teasers_dir / f"{stem}_teaser_preview.jpg" if teasers_dir.exists() else None
            c45_file = crops_4x5_dir / f"{stem}_4x5.jpg" if crops_4x5_dir.exists() else None
            c916_file = crops_9x16_dir / f"{stem}_9x16.jpg" if crops_9x16_dir.exists() else None

            photos.append({
                "original": orig_name,
                "master": str(mf.relative_to(out_dir)).replace("\\", "/"),
                "teaser": str(teaser_file.relative_to(out_dir)).replace("\\", "/") if (teaser_file and teaser_file.exists()) else str(mf.relative_to(out_dir)).replace("\\", "/"),
                "crop_4x5": str(c45_file.relative_to(out_dir)).replace("\\", "/") if (c45_file and c45_file.exists()) else str(mf.relative_to(out_dir)).replace("\\", "/"),
                "crop_9x16": str(c916_file.relative_to(out_dir)).replace("\\", "/") if (c916_file and c916_file.exists()) else str(mf.relative_to(out_dir)).replace("\\", "/"),
            })

    client_zip = out_dir / f"{shoot_name}_CLIENT_PACKAGE.zip"
    photo_zip = out_dir / f"{shoot_name}_PHOTO_PACKAGE.zip"
    zip_file = client_zip if client_zip.exists() else (photo_zip if photo_zip.exists() else None)
    zip_size_mb = round(zip_file.stat().st_size / (1024**2), 1) if zip_file else 0

    return {
        "status": "completed",
        "shoot_name": shoot_name,
        "package_name": target_pkg.name,
        "zip_name": zip_file.name if zip_file else None,
        "zip_size_mb": zip_size_mb,
        "total_processed": len(photos),
        "photos": photos
    }

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
    from pipeline.stages.ai_operator import active_task_tracker
    active_task_tracker.start_task(
        agent="cipher",
        task_desc="Cipher [36 Cp]: Analyzing visual aesthetic and lighting trends in inspiration vault...",
        task_id="cipher_analyze",
        progress=40
    )
    try:
        return inspiration_scanner.scan_and_analyze(image_filename=image)
    finally:
        active_task_tracker.finish_task("cipher_analyze")

@app.get("/api/inspiration/comfyui-prompts")
def get_inspiration_comfyui_prompts(image: Optional[str] = None):
    from pipeline.stages.ai_operator import active_task_tracker
    active_task_tracker.start_task(
        agent="muse",
        sub_agent="cipher",
        task_desc="Muse [34 Se] & Cipher [36 Cp]: Crafting ComfyUI diffusion prompts from inspiration...",
        task_id="muse_prompts",
        progress=45
    )
    try:
        return inspiration_scanner.generate_comfyui_prompts(image_filename=image)
    finally:
        active_task_tracker.finish_task("muse_prompts")

# =========================================================================
# LIVE CAM & CREATOR STORE TEMPLATE APIS (CHATURBATE & MFC)
# =========================================================================
@app.post("/api/templates/generate-cam")
async def generate_cam_template(payload: Dict[str, Any]):
    model_name = payload.get("model_name", "GoddessAura")
    theme = payload.get("theme", "neon_cyber")
    tip_menu = payload.get("tip_menu")
    bundle_name = payload.get("bundle_name", f"{model_name}_{theme.upper()}_BIO_KIT")

    from pipeline.stages.ai_operator import active_task_tracker
    active_task_tracker.start_task(
        agent="muse",
        task_desc=f"Muse [34 Se]: Generating Cam model templates & bio kit for '{model_name}' ({theme})...",
        task_id=f"muse_cam_{model_name}",
        progress=35
    )
    try:
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(
            None,
            lambda: cam_generator.bundle_digital_product(bundle_name=bundle_name, theme=theme, tip_menu=tip_menu)
        )
        cb_html = await loop.run_in_executor(
            None,
            lambda: cam_generator.generate_chaturbate_profile(model_name=model_name, theme=theme, tip_menu=tip_menu)
        )
        mfc_html = await loop.run_in_executor(
            None,
            lambda: cam_generator.generate_mfc_bio(model_name=model_name, theme=theme, tip_menu=tip_menu)
        )

        res["chaturbate_html"] = cb_html
        res["mfc_html"] = mfc_html
        return res
    finally:
        active_task_tracker.finish_task(f"muse_cam_{model_name}")

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
                "id": "luts",
                "title": "Cinematic 3D LUT Video Pack (.CUBE for Premiere / DaVinci / CapCut / OBS)",
                "description": "7 Cinematic LUTs: Kodak Portra 400, Cinestill 800T, Teal & Orange, Provia 100F, Golden Hour, Noir, Cyber Neon",
                "price_rec": "$14.99"
            },
            {
                "id": "prompts",
                "title": "FLUX.1 & Midjourney Photorealistic Prompt Engineering Bible (Lookbook & Cheat Sheet)",
                "description": "150+ Categorized Master Prompts with dark-mode interactive HTML lookbook, lens formulas & studio lighting diagrams",
                "price_rec": "$17.99"
            },
            {
                "id": "all",
                "title": "Complete Creator Studio Digital Empire Bundle (All 6 Products)",
                "description": "Full master bundle with all presets, legal releases, 50 posing cards, promo graphics, 3D LUTs, and AI Prompt Bible",
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

@app.get("/api/etsy/orders")
async def get_etsy_orders(shop: Optional[str] = None):
    all_etsy = [o for o in order_radar.orders if o.get("platform") == "etsy"]
    crafty_count = sum(1 for o in all_etsy if o.get("shop") == "CraftyMyia")
    creator_count = sum(1 for o in all_etsy if (o.get("shop") or "CreatorMediaLab") == "CreatorMediaLab")
    
    filtered_orders = all_etsy
    if shop and shop.lower() != "all":
        filtered_orders = [o for o in all_etsy if (o.get("shop") or "CreatorMediaLab").lower() == shop.lower()]
        
    return {
        "status": "ok",
        "orders": filtered_orders,
        "total": len(filtered_orders),
        "pending": sum(1 for o in filtered_orders if o.get("status") in ("pending", "unfulfilled")),
        "by_shop": {
            "CraftyMyia": crafty_count,
            "CreatorMediaLab": creator_count
        }
    }

@app.post("/api/etsy/fulfill-order/{order_id}")
async def fulfill_etsy_order_endpoint(order_id: str):
    target_order = None
    for o in order_radar.orders:
        if o.get("id") == order_id:
            target_order = o
            break
            
    if not target_order:
        raise HTTPException(status_code=404, detail=f"Etsy order '{order_id}' not found")
        
    title_lower = (target_order.get("title") or "").lower()
    gig_id = target_order.get("gig_id") or ""
    order_shop = target_order.get("shop")

    # Check if this order is for CraftyMyia (or matches any folder in workspace/etsy_listings)
    etsy_listings_dir = BASE_DIR / "workspace" / "etsy_listings"
    matched_listing_folder = None

    if gig_id and (etsy_listings_dir / gig_id).is_dir():
        matched_listing_folder = gig_id
    elif etsy_listings_dir.exists():
        for folder in etsy_listings_dir.iterdir():
            if folder.is_dir():
                clean_name = folder.name.replace("_", " ").lower()
                folder_words = [w for w in folder.name.split("_") if len(w) > 3 and w not in ("bundle", "files", "quotes")]
                if folder.name.lower() in title_lower or any(w in title_lower for w in folder_words):
                    matched_listing_folder = folder.name
                    break

    if matched_listing_folder:
        pkg_dir = etsy_listings_dir / matched_listing_folder
        upload_dir = pkg_dir / "etsy_upload"
        upload_files = [f.name for f in upload_dir.glob("*")] if upload_dir.exists() else []
        order_radar.mark_fulfilled(order_id)
        target_order["fulfilled_bundle"] = matched_listing_folder
        target_order["shop"] = "CraftyMyia"
        order_radar.save_orders()
        primary_file = upload_files[0] if upload_files else ""
        bundle_res = {
            "bundle_name": matched_listing_folder,
            "shop": "CraftyMyia",
            "upload_files": upload_files,
            "download_url": f"/api/download/craftymyia/{matched_listing_folder}/{primary_file}" if primary_file else ""
        }
        return {
            "status": "ok",
            "order_id": order_id,
            "shop": "CraftyMyia",
            "bundle": bundle_res,
            "message": f"CraftyMyia Order {order_id} fulfilled with {matched_listing_folder}"
        }

    product_type = "all"
    if "preset" in title_lower:
        product_type = "presets"
    elif "contract" in title_lower or "legal" in title_lower or "release" in title_lower or "2257" in title_lower:
        product_type = "contracts"
    elif "pos" in title_lower or "card" in title_lower:
        product_type = "posing"
    elif "template" in title_lower or "banner" in title_lower or "flyer" in title_lower or "menu" in title_lower:
        product_type = "templates"
    elif "lut" in title_lower or "cube" in title_lower or "davinci" in title_lower or "premiere" in title_lower or "color grade" in title_lower:
        product_type = "luts"
    elif "prompt" in title_lower or "bible" in title_lower or "midjourney" in title_lower or "flux" in title_lower or "cheat sheet" in title_lower:
        product_type = "prompts"
        
    bundle_res = etsy_store.bundle_etsy_product(product_type=product_type)
    order_radar.mark_fulfilled(order_id)
    target_order["fulfilled_bundle"] = bundle_res.get("bundle_name")
    target_order["shop"] = target_order.get("shop") or "CreatorMediaLab"
    order_radar.save_orders()
    
    return {
        "status": "ok",
        "order_id": order_id,
        "shop": "CreatorMediaLab",
        "bundle": bundle_res,
        "message": f"Order {order_id} fulfilled with {bundle_res.get('bundle_name', 'bundle')}"
    }

@app.get("/api/download/craftymyia/{package_name}/{file_name}")
async def download_craftymyia_file(package_name: str, file_name: str):
    file_path = BASE_DIR / "workspace" / "etsy_listings" / package_name / "etsy_upload" / file_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="CraftyMyia deliverable file not found")
    return FileResponse(file_path, filename=file_path.name, media_type="application/octet-stream")

@app.get("/api/etsy/craftymyia/catalog")
async def get_craftymyia_catalog():
    etsy_listings_dir = BASE_DIR / "workspace" / "etsy_listings"
    packages = []
    if etsy_listings_dir.exists():
        for d in sorted(etsy_listings_dir.iterdir()):
            if d.is_dir():
                lj = d / "listing.json"
                if lj.exists():
                    try:
                        data = safe_read_json(lj, default={})
                        packages.append({
                            "folder": d.name,
                            "title": data.get("title", d.name),
                            "price_usd": data.get("price_usd", 4.99),
                            "sale_hint": data.get("sale_hint", ""),
                            "tags": data.get("tags", []),
                            "category": data.get("category", "Digital"),
                            "materials": data.get("materials", "Digital files"),
                            "description": data.get("description", ""),
                            "upload_files": data.get("upload_files", []),
                            "images_count": len(data.get("images_in_upload_order", []))
                        })
                    except Exception:
                        pass
    return {"status": "ok", "shop": "CraftyMyia", "count": len(packages), "packages": packages}

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
    # Optional explicit filename (no path components - resolved within the gig's own
    # asset directory only) so the Commander/Synapse can bind delivery to a SPECIFIC
    # file instead of relying on an auto-guess. Strongly recommended whenever more than
    # one client's package could be sitting in the same shared folder.
    requested_asset = payload.get("asset_filename")

    gig_dirs = {
        "gig_photo_to_3d": BASE_DIR / "workspace" / "fiverr_deliveries",
        "gig_photo_to_video": BASE_DIR / "workspace" / "brand_assets" / "comfy_video_renders",
        "gig_relight": BASE_DIR / "workspace" / "photos_output",
        "gig_retouch": BASE_DIR / "workspace" / "photos_output",
        "gig_teaser": BASE_DIR / "workspace" / "output",
        "gig_copy": BASE_DIR / "workspace" / "cam_templates",
        "gig_banner": BASE_DIR / "workspace" / "cam_templates",
    }
    asset_dir = gig_dirs.get(gig_id)


    assets = []
    warning = None
    if asset_dir and asset_dir.exists():
        if requested_asset:
            candidate = asset_dir / Path(requested_asset).name
            if candidate.exists() and candidate.is_file():
                assets.append(str(candidate))
            else:
                return {"status": "error", "error": f"Requested asset '{Path(requested_asset).name}' was not found in {asset_dir}"}
        else:
            zips = [f for f in asset_dir.glob("*.zip") if f.is_file()]
            if zips:
                # Previously picked list(glob())[-1] - alphabetical/directory order, NOT
                # recency, and with zero binding to this client/order. That let a
                # completely different client's package get delivered here. Now: true
                # newest-by-modification-time, and if more than one candidate exists,
                # the response says so explicitly instead of silently guessing.
                newest = max(zips, key=lambda f: f.stat().st_mtime)
                assets.append(str(newest))
                if len(zips) > 1:
                    warning = (
                        f"No asset_filename was specified and {len(zips)} ZIP files exist in "
                        f"{asset_dir.name}/ - auto-selected the newest ('{newest.name}'). "
                        f"Verify this is really {client_name}'s file before sending, or re-run "
                        f"with an explicit asset_filename."
                    )

    res = fiverr_bot.fulfill_order(
        gig_id=gig_id,
        order_number=order_number,
        client_name=client_name,
        assets=assets,
        notes=notes
    )
    if warning:
        res["warning"] = warning
    return res

@app.get("/api/download/fiverr/{order_number}")
async def download_fiverr_delivery(order_number: str):
    zip_path = BASE_DIR / "workspace" / "fiverr_deliveries" / f"{order_number}_DELIVERY_PACKAGE.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Fiverr delivery zip not found")
    return FileResponse(zip_path, filename=zip_path.name, media_type="application/zip")

@app.get("/api/fiverr/orders")
async def get_fiverr_orders():
    fiverr_orders = [o for o in order_radar.orders if o.get("platform") == "fiverr"]
    return {
        "status": "ok",
        "orders": fiverr_orders,
        "total": len(fiverr_orders),
        "pending": sum(1 for o in fiverr_orders if o.get("status") in ("pending", "unfulfilled"))
    }

@app.post("/api/fiverr/fulfill-order/{order_id}")
async def fulfill_fiverr_order_endpoint(order_id: str):
    target_order = None
    for o in order_radar.orders:
        if o.get("id") == order_id:
            target_order = o
            break
            
    if not target_order:
        raise HTTPException(status_code=404, detail=f"Fiverr order '{order_id}' not found")
        
    gig_id = target_order.get("gig_id") or "gig_retouch"
    client_name = target_order.get("buyer") or "Valued Client"
    
    gig_dirs = {
        "gig_photo_to_3d": BASE_DIR / "workspace" / "fiverr_deliveries",
        "gig_photo_to_video": BASE_DIR / "workspace" / "brand_assets" / "comfy_video_renders",
        "gig_relight": BASE_DIR / "workspace" / "photos_output",
        "gig_retouch": BASE_DIR / "workspace" / "photos_output",
        "gig_teaser": BASE_DIR / "workspace" / "output",
        "gig_copy": BASE_DIR / "workspace" / "cam_templates",
        "gig_banner": BASE_DIR / "workspace" / "cam_templates",
    }
    asset_dir = gig_dirs.get(gig_id, BASE_DIR / "workspace" / "fiverr_deliveries")
    assets = []
    if asset_dir.exists():
        for f in sorted(asset_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if f.is_file() and not f.name.startswith(".") and not f.name.endswith("_DELIVERY_PACKAGE.zip"):
                # Safety: skip multi-gigabyte raw shoot master archives (e.g. >100MB) in quick auto-fulfillment
                if f.stat().st_size < 100 * 1024 * 1024:
                    assets.append(str(f))
                    if len(assets) >= 3:
                        break

                    
    bundle_res = fiverr_bot.fulfill_order(
        gig_id=gig_id,
        order_number=order_id,
        client_name=client_name,
        assets=assets
    )
    order_radar.mark_fulfilled(order_id)
    target_order["fulfilled_delivery"] = bundle_res.get("delivery_zip_name")
    
    return {
        "status": "ok",
        "order_id": order_id,
        "delivery": bundle_res,
        "message": f"Order {order_id} fulfilled with {bundle_res.get('delivery_zip_name')}"
    }

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
        webhook_product_map=payload.get("webhook_product_map"),
        public_download_base_url=payload.get("public_download_base_url")
    )
    # update_config() already returns a redacted view (secrets reduced to booleans) -
    # no additional filtering needed here.
    return {"status": "ok", "config": cfg}

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

@app.post("/api/pipeline/jobs/{job_id}/cancel")
async def cancel_job_endpoint(job_id: str):
    success = orchestrator.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Job not found or already completed/cancelled")
    return {"status": "ok", "job_id": job_id, "message": "Job cancellation initiated"}

@app.get("/api/pipeline/jobs-active")
async def get_active_jobs_endpoint():
    return {"status": "ok", "active_jobs": orchestrator.get_active_jobs()}

@app.get("/api/cam-shows/queue")
async def get_cam_shows_queue():
    from pipeline.stages.cam_show_packager import get_cam_show_queue_status
    return get_cam_show_queue_status()

_comfy_queue_cache = {"busy": False, "expires": 0.0}

@app.get("/api/monitor/agents-active")
async def get_active_agents_monitor():
    from shared.agent_roster import AGENT_ROSTER
    from pipeline.stages.ai_operator import active_task_tracker
    active_jobs = list(orchestrator.get_active_jobs())
    active_tasks = active_task_tracker.get_all_active_tasks()
    
    comfy_busy = False
    now_ts = time.time()
    if now_ts < _comfy_queue_cache["expires"]:
        comfy_busy = _comfy_queue_cache["busy"]
    else:
        try:
            from pipeline.stages.comfyui_bridge import comfy_bridge
            q = await asyncio.to_thread(comfy_bridge.get_queue_status)
            if q.get("executing") or q.get("pending_count", 0) > 0:
                comfy_busy = True
        except Exception:
            pass
        _comfy_queue_cache["busy"] = comfy_busy
        _comfy_queue_cache["expires"] = now_ts + 2.5

    if not comfy_busy and active_tasks:
        for t in active_tasks:
            td = (t.get("task") or "").lower()
            if any(w in td for w in ["comfy", "rendering", "rtx 5070 ti", "video"]):
                comfy_busy = True
                break

    herald_active = False
    try:
        h_status = herald_scheduler.get_status()
        if h_status.get("running"):
            herald_active = True
    except Exception:
        pass

    agents_state = []
    stalled_alerts = []
    active_agents_set = set()

    # Track all active tasks from active_task_tracker across any of the 14 agents
    task_by_agent = {}
    for task in active_tasks:
        a_id = (task.get("agent") or "").lower()
        s_id = (task.get("sub_agent") or "").lower()
        if a_id:
            active_agents_set.add(a_id)
            task_by_agent[a_id] = task
        if s_id:
            active_agents_set.add(s_id)
            task_by_agent[s_id] = task

        display_agent = s_id or a_id or "synapse"
        task_job = {
            "job_id": task.get("task_id", f"{display_agent}_task"),
            "active_agent": display_agent,
            "agent_message": task.get("task", "Executing task..."),
            "current_stage": 1,
            "total_stages": 1,
            "progress": task.get("progress", 50),
            "stage_elapsed_sec": int(task.get("elapsed_sec", 0)),
            "is_stalled": task.get("is_stalled", False)
        }
        active_jobs.insert(0, task_job)
        if task.get("is_stalled"):
            stalled_alerts.append({
                "job_id": task.get("task_id", f"{display_agent}_task"),
                "agent": display_agent,
                "elapsed_sec": task.get("elapsed_sec", 0),
                "message": f"Task '{task.get('task')}' has been running for {int(task.get('elapsed_sec', 0))}s without completing."
            })

    job_by_agent = {}
    for job in active_jobs:
        agent_id = (job.get("active_agent") or "").lower()
        if agent_id:
            job_by_agent[agent_id] = job
            active_agents_set.add(agent_id)
            if job.get("is_stalled") and not job.get("job_id", "").endswith("_task") and job.get("job_id") != "synapse_chat_op":
                stalled_alerts.append({
                    "job_id": job.get("job_id"),
                    "agent": agent_id,
                    "filename": job.get("filename"),
                    "stage": job.get("current_stage"),
                    "elapsed_sec": job.get("stage_elapsed_sec"),
                    "message": f"Stage {job.get('current_stage')}/8 on {agent_id.upper()} has been running for {job.get('stage_elapsed_sec')}s without progression."
                })

    if comfy_busy:
        active_agents_set.add("forge")
        if "forge" not in job_by_agent:
            forge_job = {
                "job_id": "synapse_chat_op",
                "active_agent": "forge",
                "agent_message": "Forge [74 W]: Rendering ComfyUI workflow on RTX 5070 Ti...",
                "current_stage": 1,
                "total_stages": 1,
                "progress": 60,
                "stage_elapsed_sec": 0,
                "is_stalled": False
            }
            active_jobs.append(forge_job)
            job_by_agent["forge"] = forge_job

    if herald_active:
        active_agents_set.add("herald")

    for agent_key, meta in AGENT_ROSTER.items():
        job = job_by_agent.get(agent_key)
        agent_task = task_by_agent.get(agent_key)
        if job:
            state = "stalled" if job.get("is_stalled") else "active"
            current_task = job.get("agent_message", "Executing pipeline task")
            elapsed = job.get("stage_elapsed_sec", 0)
            progress = job.get("progress", 0)
        elif agent_task:
            state = "stalled" if agent_task.get("is_stalled") else "active"
            current_task = agent_task.get("task", f"{meta.get('name')} executing task")
            elapsed = agent_task.get("elapsed_sec", 0)
            progress = agent_task.get("progress", 45)
        elif agent_key == "forge" and comfy_busy:
            state = "active"
            current_task = "Forge: Rendering ComfyUI workflow on RTX 5070 Ti..."
            elapsed = None
            progress = 50
        elif agent_key == "herald" and herald_active:
            state = "active"
            current_task = "Herald: Dispatching scheduled publication drops..."
            elapsed = None
            progress = 50
        else:
            state = "idle"
            current_task = f"Standing by on {meta.get('hardware', 'Local Dual RTX 3060')}"
            elapsed = 0
            progress = 0

        agents_state.append({
            "id": agent_key,
            "name": meta.get("name", agent_key.capitalize()),
            "symbol": meta.get("symbol", ""),
            "title": meta.get("title", ""),
            "hardware": meta.get("hardware", ""),
            "state": state,
            "current_task": current_task,
            "elapsed_sec": elapsed,
            "progress": progress,
            "is_stalled": state == "stalled"
        })

    return {
        "status": "ok",
        "version": "20261015_v17",
        "has_active": bool(active_jobs or comfy_busy or herald_active or active_tasks),
        "active_jobs": active_jobs,
        "agents": agents_state,
        "active_count": len(active_agents_set),
        "stalled_count": len(stalled_alerts),
        "stalled_alerts": stalled_alerts,
        "comfy_online": comfy_health_cache.get("online"),
        "timestamp": time.time()
    }

@app.post("/api/monitor/stop-process")
async def stop_process_endpoint(payload: Optional[Dict[str, Any]] = None):
    payload = payload or {}
    job_id = payload.get("job_id")
    target = payload.get("target", "job" if job_id else "all")
    
    actions_taken = []
    
    # 1. Stop active chat operator task if target is all or specific chat op
    if not job_id or job_id == "synapse_chat_op" or target in ("all", "all_jobs", "emergency_stop"):
        try:
            from pipeline.stages.ai_operator import active_task_tracker
            if active_task_tracker.cancel_current_task():
                actions_taken.append("Halted active Synapse operator task")
        except Exception:
            pass

    # 2. Stop pipeline batch job
    if job_id and job_id != "synapse_chat_op":
        if orchestrator.cancel_job(job_id):
            actions_taken.append(f"Cancelled pipeline job {job_id}")
    elif target in ("all", "all_jobs", "emergency_stop"):
        cancelled_count = orchestrator.cancel_all_jobs()
        if cancelled_count:
            actions_taken.append(f"Cancelled {cancelled_count} active pipeline job(s)")
            
    # 3. Interrupt ComfyUI GPU execution & clear queue
    if target in ("all", "comfy", "emergency_stop") or job_id == "synapse_chat_op":
        try:
            from pipeline.stages.comfyui_bridge import comfy_bridge
            comfy_bridge.interrupt()
            comfy_bridge.clear_queue()
            comfy_bridge.remote_purge_vram()
            actions_taken.append("Sent interrupt and queue-clear to ComfyUI (RTX 5070 Ti)")
        except Exception:
            pass

    # 4. Purge local VRAM
    if target in ("all", "vram", "emergency_stop") or job_id == "synapse_chat_op":
        try:
            vram_report = vram_manager.purge_vram(reason="emergency_stop")
            actions_taken.append(f"Purged local GPU VRAM ({len(vram_report.get('unloaded_models', []))} models unloaded)")
        except Exception:
            pass
            
    return {
        "status": "ok",
        "target": target,
        "actions": actions_taken,
        "message": "; ".join(actions_taken) if actions_taken else "No active jobs or processes to stop"
    }

@app.get("/api/media/{file_path:path}")
async def serve_media(file_path: str):
    search_dirs = [
        BASE_DIR / "workspace" / "output",
        BASE_DIR / "workspace" / "photos_output",
        BASE_DIR / "workspace" / "photos_input",
        BASE_DIR / "workspace" / "inspiration",
        BASE_DIR / "workspace" / "cam_templates",
        BASE_DIR / "workspace" / "temp",
        BASE_DIR / "workspace" / "etsy_bundles",
        BASE_DIR / "workspace" / "fiverr_deliveries",
        BASE_DIR / "workspace" / "brand_assets",
        BASE_DIR / "dropzone",
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
    out_dir = BASE_DIR / "workspace" / "photos_output"
    client_zip = out_dir / f"{shoot_name}_CLIENT_PACKAGE.zip"
    if client_zip.exists():
        return FileResponse(client_zip, filename=client_zip.name, media_type="application/zip")
    zip_path = out_dir / f"{shoot_name}_PHOTO_PACKAGE.zip"
    if zip_path.exists():
        return FileResponse(zip_path, filename=zip_path.name, media_type="application/zip")
    raise HTTPException(status_code=404, detail="Photo bundle zip not found")

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
    return await open_output_folder({"path": str(BASE_DIR / "workspace" / "brand_assets")})

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
    from pipeline.stages.ai_operator import active_task_tracker
    active_task_tracker.start_task(
        agent="radar",
        task_desc="Radar [47 Ag]: Scanning Gmail for incoming Fiverr & Etsy orders...",
        task_id="radar_check_inbox",
        progress=35
    )
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, order_radar.check_inbox)
    finally:
        active_task_tracker.finish_task("radar_check_inbox")

@app.post("/api/radar/simulate")
async def simulate_radar_order(payload: Dict[str, Any] = None):
    platform = "fiverr"
    shop = "auto"
    if payload:
        if "platform" in payload:
            platform = payload["platform"]
        if "shop" in payload:
            shop = payload["shop"]
    return order_radar.simulate_order(platform=platform, shop=shop)

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
# AUTONOMOUS MARKET & REVENUE SCOUT (AGENTS: CIPHER [36 Cp] & MERCURY [80 Hg])
# =========================================================================
@app.get("/api/market/opportunities")
async def get_market_opportunities(refresh: bool = False):
    try:
        data = trend_agent.scout_market_and_revenue_ideas(force_refresh=refresh)
        return {"status": "ok", "vault": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/market/scout-now")
async def trigger_market_scout():
    try:
        data = trend_agent.scout_market_and_revenue_ideas(force_refresh=True)
        return {"status": "ok", "vault": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/market/deploy-opportunity")
async def deploy_market_opportunity(payload: Dict[str, Any]):
    opp = payload.get("opportunity")
    opp_id = payload.get("opportunity_id")
    if not opp and opp_id:
        vault = trend_agent.scout_market_and_revenue_ideas(force_refresh=False)
        for item in vault.get("opportunities", []):
            if item.get("id") == opp_id:
                opp = item
                break
    if not opp:
        raise HTTPException(status_code=400, detail="Opportunity data or valid ID required")

    campaign = omni_marketer.deploy_opportunity_kit(opp)
    return {"status": "ok", "campaign": campaign}


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
async def get_newsletter_preview(pub: str = "creator_pulse", refresh: bool = False):
    html_content = await asyncio.to_thread(newsletter_mgr.get_html_preview, pub, refresh, False, refresh)
    return HTMLResponse(content=html_content)

@app.post("/api/newsletter/regenerate-visual")
async def regenerate_newsletter_visual(payload: Dict[str, Any] = None):
    pub = (payload or {}).get("pub", "creator_pulse")
    loop = asyncio.get_event_loop()
    fresh_path = await loop.run_in_executor(None, lambda: newsletter_mgr.ensure_fresh_daily_newsletter_visual(pub, force=True))
    if fresh_path and fresh_path.exists():
        return {"status": "ok", "filename": fresh_path.name, "path": str(fresh_path)}
    return {"status": "error", "message": "Visual generation failed or ComfyUI offline"}

@app.post("/api/newsletter/regenerate")
async def regenerate_newsletter(payload: Dict[str, Any] = None):
    pub = (payload or {}).get("pub", "creator_pulse")
    from pipeline.stages.ai_operator import active_task_tracker
    active_task_tracker.start_task(
        agent="scribe",
        task_desc=f"Scribe [6 C]: Synthesizing fresh daily editorial copy for '{pub}' on Qwen 14B...",
        task_id=f"scribe_regen_{pub}",
        progress=40
    )
    try:
        loop = asyncio.get_event_loop()
        if pub == "all":
            results = {}
            for p in ["creator_pulse", "studio_wire", "creator_blueprint"]:
                res = await loop.run_in_executor(None, lambda target=p: newsletter_mgr._get_daily_scribe_content(target, force_refresh=True))
                results[p] = bool(res and res.get("success"))
            return {"status": "ok", "message": "All publications regenerated fresh", "results": results}
        else:
            res = await loop.run_in_executor(None, lambda: newsletter_mgr._get_daily_scribe_content(pub, force_refresh=True))
            return {"status": "ok", "message": f"Fresh content synthesized for {pub}", "success": bool(res and res.get("success"))}
    finally:
        active_task_tracker.finish_task(f"scribe_regen_{pub}")

@app.get("/api/newsletter/blog-post")
async def get_newsletter_blog_post(pub: str = "creator_pulse"):
    if hasattr(newsletter_mgr, "get_blog_post_markdown"):
        md = newsletter_mgr.get_blog_post_markdown(pub_id=pub)
    else:
        md = newsletter_mgr.get_markdown_article(pub_id=pub)
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
    client_host = getattr(websocket.client, "host", "") if websocket.client else ""
    if not _is_loopback(client_host) and (not token or not verify_session_token(token, _get_session_secret())):
        await websocket.close(code=4401)
        return
    await websocket.accept()
    connected_websockets.append(websocket)
    try:
        while True:
            stats = await asyncio.to_thread(get_system_stats)
            stats["ollama"] = await asyncio.to_thread(get_ollama_models)
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


@app.websocket("/ws/stackchan/{robot_id}")
async def websocket_stackchan(websocket: WebSocket, robot_id: str):
    robot_key = robot_id.lower().strip()
    if robot_key not in connected_stackchan_websockets:
        connected_stackchan_websockets[robot_key] = []
    await websocket.accept()
    connected_stackchan_websockets[robot_key].append(websocket)
    print(f"[STACKCHAN] Robot connected via WebSocket: {robot_key.upper()}")
    try:
        welcome_pkt = {
            "type": "handshake",
            "robot": robot_key,
            "status": "connected",
            "system": "WORKHORSE AI Command Center",
            "message": f"Welcome online, {robot_key.capitalize()}!"
        }
        await websocket.send_text(json.dumps(welcome_pkt))
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                print(f"[STACKCHAN:{robot_key}] Received: {msg}")
            except Exception:
                pass
    except WebSocketDisconnect:
        if websocket in connected_stackchan_websockets[robot_key]:
            connected_stackchan_websockets[robot_key].remove(websocket)
    except Exception:
        if websocket in connected_stackchan_websockets[robot_key]:
            connected_stackchan_websockets[robot_key].remove(websocket)

@app.post("/api/stackchan/test-alert")
async def test_stackchan_alert(payload: Dict[str, Any]):
    robot = payload.get("robot", "synapse").lower().strip()
    alert_type = payload.get("type", "ping")
    text = payload.get("text", "Test alert from WORKHORSE command center.")
    expression = payload.get("expression", "happy")
    pkt = {
        "type": "event",
        "name": alert_type,
        "expression": expression,
        "text": text,
        "sound": payload.get("sound", "ding"),
        "theme_color": "#00f2fe" if robot == "synapse" else "#ff007f"
    }
    broadcast_stackchan(robot, pkt)
    return {"status": "dispatched", "robot": robot, "packet": pkt}


# ==============================================================================
# WORKHORSE MASTER AI OPERATOR ENDPOINTS
# ==============================================================================
_health_cache = {"data": None, "expires": 0.0}

@app.get("/api/system/health-check")
async def get_system_health():
    now = time.time()
    if _health_cache["data"] is not None and now < _health_cache["expires"]:
        return _health_cache["data"]
    report = await asyncio.to_thread(ai_operator.run_system_diagnostics)
    _health_cache["data"] = report
    _health_cache["expires"] = now + 10.0
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
    models = await asyncio.to_thread(ai_operator.get_available_models)
    return {"status": "ok", "models": models}

@app.get("/api/operator/history")
async def get_operator_history(request: Request):
    """Returns the persisted SYNAPSE conversation for THIS browser session only, so the
    UI can restore it after a page reload, tab switch, or a dropped connection without
    pulling in any other session's chat."""
    session_id = _get_request_session_id(request)
    return {"status": "ok", "history": ai_operator.get_history(session_id)}

def _extract_zip_uploads_into_batch(batch_dir: Path, zip_path: Path) -> List[str]:
    """If a client-uploaded file is itself a ZIP archive (e.g. a full photo-shoot
    export), extracts its image contents directly into the same upload batch so
    aura_retouch/apex_package can see the real photos instead of silently treating
    the opaque .zip as zero matching images (PhotoRetoucher's cv2.imread() returns
    None for a .zip and just skips it with no error - this is what let an entire
    client job go through as a no-op). The original zip is left in place untouched;
    this only adds sibling image files. Returns the newly extracted filenames."""
    extracted: List[str] = []
    try:
        with zipfile.ZipFile(zip_path) as archive:
            for info in archive.infolist():
                if not safe_archive_member(info):
                    continue
                fmt = preview_format(info.filename)
                if not fmt or fmt[0] != "image":
                    continue
                safe_name = PurePath(info.filename.replace("\\", "/")).name
                if not safe_name:
                    continue
                dest = batch_dir / safe_name
                counter = 1
                while dest.exists():
                    stem_path = PurePath(safe_name)
                    dest = batch_dir / f"{stem_path.stem}_{counter}{stem_path.suffix}"
                    counter += 1
                with archive.open(info) as source, open(dest, "wb") as out:
                    shutil.copyfileobj(source, out)
                extracted.append(dest.name)
    except zipfile.BadZipFile:
        print(f"[WORKHORSE] Uploaded file '{zip_path.name}' has a .zip extension but is not a valid archive - left as-is.")
    except Exception as e:
        print(f"[WORKHORSE] Failed to extract images from uploaded zip '{zip_path.name}': {e}")
    return extracted


@app.post("/api/operator/chat")
async def operator_chat_endpoint(
    request: Request,
    message: str = Form(...),
    model: str = Form("huihui_ai/qwen3-abliterated:14b"),
    web_search: bool = Form(False),
    adult_mode: bool = Form(False),
    files: List[UploadFile] = File(default=[])
):
    saved_paths = []
    session_id = _get_request_session_id(request)
    if files:
        # Every file-drop event gets its own isolated client_inbox/batch_.../ subfolder
        # instead of landing directly in the flat shared root - so this client's/session's
        # files can never be mixed with a different client's or an older/newer drop when
        # Synapse's tools later default to "whatever was just uploaded".
        batch_dir = create_client_batch(session_id=session_id)
        batch_filenames = []
        for f in files:
            if f.filename:
                safe_name = Path(f.filename).name  # strip any path components from the client-supplied filename
                dest = batch_dir / safe_name
                content = await f.read()
                with open(dest, "wb") as out:
                    out.write(content)
                saved_paths.append(str(dest))
                batch_filenames.append(safe_name)
                if dest.suffix.lower() == ".zip":
                    extracted_names = _extract_zip_uploads_into_batch(batch_dir, dest)
                    for name in extracted_names:
                        saved_paths.append(str(batch_dir / name))
                    batch_filenames.extend(extracted_names)
        if batch_filenames:
            register_batch_files(batch_dir, batch_filenames)

    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(
        None,
        lambda: ai_operator.chat(
            message=message,
            model=model,
            web_search=web_search,
            attached_files=saved_paths,
            session_id=session_id,
            adult_mode=adult_mode
        )
    )
    return res

@app.post("/api/operator/clear")
async def operator_clear_endpoint(request: Request):
    session_id = _get_request_session_id(request)
    ai_operator.clear_history(session_id)
    return {"status": "ok", "message": "Operator history cleared"}

@app.get("/api/operator/client-files")
async def get_client_inbox_files(request: Request):
    """Lists files in THIS session's most recent upload batch (falling back to any
    legacy files sitting directly in the flat client_inbox/ root), rather than every
    file across every client's batches."""
    from pipeline.stages.ai_operator import get_latest_client_batch_dir
    files = []
    session_id = _get_request_session_id(request)
    batch_dir = get_latest_client_batch_dir(session_id)
    scan_dir = batch_dir if batch_dir and batch_dir.exists() else CLIENT_INBOX_DIR
    if scan_dir.exists():
        for f in scan_dir.iterdir():
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
            candidate = Path("F:/WORKHORSE/workspace/client_inbox") / filename
            if candidate.exists():
                img_path = candidate
            else:
                # Files now live in per-upload batch_.../ subfolders rather than the flat
                # inbox root - fall back to searching those for a same-name match.
                matches = list(Path("F:/WORKHORSE/workspace/client_inbox").glob(f"batch_*/{filename}"))
                img_path = matches[0] if matches else candidate

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

# ==============================================================================
# UNIFIED OUTPUT GALLERY & AUTHENTICATED FILE DOWNLOADS
# ==============================================================================
# Registry lives in shared/output_categories.py (single source of truth, also
# used by ai_operator.py to tag each tool result with a media entry) so the
# "Completed Work" gallery and in-chat media rendering can never drift out of
# sync. Deliberately NOT served via the public /static/ mount (which has zero
# auth) - this content can include adult-brand material and client-specific
# deliverables, so every file read goes through this authenticated endpoint
# instead, matching the rest of the dashboard's auth model.
from shared.output_categories import OUTPUT_CATEGORIES, DEFAULT_MEDIA_EXTENSIONS, GROUP_LABELS
from shared.output_preview import (
    MAX_PREVIEW_BYTES, MAX_ARCHIVE_ENTRIES, preview_format, safe_archive_member,
)


def _resolve_output_file(category: str, rel_path: str) -> Path:
    """Resolves a category+relative-path pair to an absolute file path, rejecting
    anything that isn't actually inside that category's registered directory (path
    traversal protection) - the only way callers can reach a file through this
    system is via a path this server itself already listed in the gallery."""
    cat = OUTPUT_CATEGORIES.get(category)
    if not cat:
        raise HTTPException(status_code=404, detail=f"Unknown output category: {category}")
    base_dir = cat["dir"].resolve()
    candidate = (base_dir / rel_path).resolve()
    if base_dir not in candidate.parents and candidate != base_dir:
        raise HTTPException(status_code=403, detail="Invalid path")
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return candidate


@app.get("/api/outputs/file")
async def download_output_file(category: str, path: str, member: Optional[str] = None):
    """Explicit authenticated download; viewing uses /api/outputs/preview."""
    file_path = _resolve_output_file(category, path)
    if member is not None:
        return await run_in_threadpool(_archive_member_response, file_path, member, download=True)
    return FileResponse(file_path, filename=file_path.name)

@app.delete("/api/outputs/file")
@app.post("/api/outputs/delete")
async def delete_output_file(
    category: Optional[str] = None,
    path: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None
):
    target_category = category or (payload.get("category") if payload else None)
    target_path = path or (payload.get("path") if payload else None)
    
    if not target_category or not target_path:
        raise HTTPException(status_code=400, detail="Missing required 'category' and 'path' parameters")
        
    file_path = _resolve_output_file(target_category, target_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
        
    try:
        filename = file_path.name
        file_path.unlink()
        
        sidecar_json = file_path.with_suffix(".json")
        if sidecar_json.exists() and sidecar_json.is_file():
            try:
                sidecar_json.unlink()
            except Exception:
                pass
                
        return {
            "status": "ok",
            "message": f"Successfully deleted {filename}",
            "filename": filename,
            "category": target_category
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {e}")

@app.delete("/api/photos/packages/{package_name}")
@app.post("/api/photos/packages/{package_name}/delete")
async def delete_photo_package_endpoint(package_name: str):
    if not package_name or ".." in package_name or "/" in package_name or "\\" in package_name:
        raise HTTPException(status_code=400, detail="Invalid package name")
    
    out_dir = (BASE_DIR / "workspace" / "photos_output").resolve()
    target_dir = (out_dir / package_name).resolve()
    
    deleted_items = []
    if out_dir in target_dir.parents and target_dir.exists() and target_dir.is_dir():
        shutil.rmtree(target_dir, ignore_errors=True)
        deleted_items.append(f"Directory: {package_name}")
        
    for zip_name in [f"{package_name}_PHOTO_PACKAGE.zip", f"{package_name}_CLIENT_PACKAGE.zip"]:
        candidate = (out_dir / zip_name).resolve()
        if out_dir in candidate.parents and candidate.exists() and candidate.is_file():
            candidate.unlink()
            deleted_items.append(f"ZIP: {zip_name}")
            
    if not deleted_items:
        raise HTTPException(status_code=404, detail=f"Photo package '{package_name}' not found")
        
    return {"status": "ok", "deleted_items": deleted_items}


def _archive_member_response(file_path: Path, member: str, download: bool = False):
    if file_path.suffix.lower() != ".zip":
        raise HTTPException(status_code=400, detail="This output is not a ZIP package")
    temp_dir = tempfile.TemporaryDirectory(prefix="workhorse-preview-")
    try:
        with zipfile.ZipFile(file_path) as archive:
            try:
                info = archive.getinfo(member)
            except KeyError:
                raise HTTPException(status_code=404, detail="Package file not found")
            if not safe_archive_member(info):
                raise HTTPException(status_code=400, detail="Package file is unsafe or encrypted")
            if info.file_size > MAX_PREVIEW_BYTES:
                raise HTTPException(status_code=413, detail="Package file exceeds the 256 MiB viewing limit; download the original ZIP instead")
            fmt = preview_format(info.filename)
            if not download and not fmt:
                raise HTTPException(status_code=415, detail="This file format cannot be viewed in WORKHORSE")
            target = Path(temp_dir.name) / "member"
            with archive.open(info) as source, target.open("wb") as dest:
                remaining = MAX_PREVIEW_BYTES
                while chunk := source.read(min(1024 * 1024, remaining + 1)):
                    remaining -= len(chunk)
                    if remaining < 0:
                        raise HTTPException(status_code=413, detail="Package file exceeds the 256 MiB viewing limit")
                    dest.write(chunk)
        headers = {} if download else _preview_headers()
        return FileResponse(
            target, filename=PurePath(member.replace("\\", "/")).name,
            media_type=fmt[1] if fmt else "application/octet-stream",
            content_disposition_type="attachment" if download else "inline",
            headers=headers, background=BackgroundTask(temp_dir.cleanup),
        )
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        temp_dir.cleanup()
        raise HTTPException(status_code=422, detail="ZIP package is damaged or uses unsupported compression") from exc
    except BaseException:
        temp_dir.cleanup()
        raise


def _preview_headers():
    # HTML deliverables must not execute scripts or access the dashboard session.
    return {
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:; media-src data:",
    }


@app.get("/api/outputs/preview")
def preview_output_file(category: str, path: str, member: Optional[str] = None):
    """Authenticated inline viewing, separate from the explicit download action."""
    file_path = _resolve_output_file(category, path)
    if member is not None:
        return _archive_member_response(file_path, member)
    fmt = preview_format(file_path.name)
    if not fmt:
        raise HTTPException(status_code=415, detail="This file format cannot be viewed in WORKHORSE")
    return FileResponse(
        file_path, filename=file_path.name, media_type=fmt[1],
        content_disposition_type="inline", headers=_preview_headers(),
    )


@app.get("/api/outputs/archive")
def list_output_archive(category: str, path: str):
    """Lists package contents without downloading or extracting the entire ZIP."""
    file_path = _resolve_output_file(category, path)
    if file_path.suffix.lower() != ".zip":
        raise HTTPException(status_code=400, detail="This output is not a ZIP package")
    try:
        with zipfile.ZipFile(file_path) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_ARCHIVE_ENTRIES:
                raise HTTPException(status_code=413, detail="Package contains more than 2000 entries; download the ZIP to inspect it")
            items = []
            for info in entries:
                if not safe_archive_member(info):
                    continue
                fmt = preview_format(info.filename)
                query = urllib.parse.urlencode({"category": category, "path": path, "member": info.filename})
                viewable = bool(fmt) and info.file_size <= MAX_PREVIEW_BYTES
                items.append({
                    "filename": info.filename, "size_kb": round(info.file_size / 1024, 1),
                    "preview_type": fmt[0] if viewable else None,
                    "preview_url": f"/api/outputs/preview?{query}" if viewable else None,
                    "download_url": f"/api/outputs/file?{query}" if info.file_size <= MAX_PREVIEW_BYTES else None,
                })
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=422, detail="ZIP package is damaged") from exc
    return {"status": "ok", "items": items}


@app.get("/api/outputs/categories")
async def get_outputs_categories():
    """Lightweight registry listing for the 'Completed Work' gallery UI - lets the
    frontend build its per-business-line (Fiverr/Etsy/Social Media/Synapse) category
    filter buttons dynamically from shared/output_categories.py, instead of a
    hardcoded list that could drift out of sync with the real registry."""
    return {
        "status": "ok",
        "groups": GROUP_LABELS,
        "categories": [
            {"category": key, "label": cat["label"], "group": cat["group"], "group_label": GROUP_LABELS.get(cat["group"], cat["group"])}
            for key, cat in OUTPUT_CATEGORIES.items()
        ]
    }


@app.get("/api/outputs/gallery")
async def get_outputs_gallery(category: Optional[str] = None, group: Optional[str] = None, limit: int = 120):
    """Unified 'Completed Work' gallery across every output category - images,
    videos, 3D models, banners, client character test renders, and client
    packages - each clearly tagged by category/type so client deliverables are
    never visually confused with postable marketing content. Addresses the
    Commander's 'I need a folder where all completed work goes that I can get to
    from in WORKHORSE' request directly.

    Results are also tagged/filterable by 'group' - one of the Commander's 4 real
    business lines (fiverr / etsy / social / synapse, see shared/output_categories.py)
    - so the gallery can present them as fully separate sections rather than one
    mixed pile."""
    items = []
    categories_to_scan = [category] if category else list(OUTPUT_CATEGORIES.keys())
    if group and group != "all":
        categories_to_scan = [k for k in categories_to_scan if OUTPUT_CATEGORIES.get(k, {}).get("group") == group]

    for cat_key in categories_to_scan:
        cat = OUTPUT_CATEGORIES.get(cat_key)
        if not cat or not cat["dir"].exists():
            continue
        extensions = cat.get("extensions", DEFAULT_MEDIA_EXTENSIONS.get(cat["media_type"], ()))
        exclude_prefixes = tuple(cat.get("exclude_prefixes", ()))
        file_iter = cat["dir"].rglob("*") if cat.get("recursive") else cat["dir"].iterdir()
        for f in file_iter:
            if not f.is_file() or f.suffix.lower() not in extensions:
                continue
            if exclude_prefixes and f.name.startswith(exclude_prefixes):
                continue
            rel_path = str(f.relative_to(cat["dir"]))
            items.append({
                "category": cat_key,
                "label": cat["label"],
                "group": cat["group"],
                "group_label": GROUP_LABELS.get(cat["group"], cat["group"]),
                "media_type": cat["media_type"],
                "filename": f.name,
                "rel_path": rel_path,
                "download_url": f"/api/outputs/file?category={urllib.parse.quote(cat_key)}&path={urllib.parse.quote(rel_path)}",
                "preview_url": f"/api/outputs/preview?category={urllib.parse.quote(cat_key)}&path={urllib.parse.quote(rel_path)}",
                "preview_type": "archive" if f.suffix.lower() == ".zip" else (preview_format(f.name) or (None, None))[0],
                "size_kb": round(f.stat().st_size / 1024, 1),
                "created": f.stat().st_mtime
            })

    items.sort(key=lambda x: x["created"], reverse=True)
    return {"status": "ok", "items": items[:limit], "total_found": len(items)}




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
    bounded_hours = max(1, int(hours)) if hours is not None else 48
    res = await asyncio.to_thread(vram_manager.prune_old_staging_files, max_age_hours=bounded_hours)
    return res


# ─── Creator Discord + Telegram Community Hub & Fiverr Template Engine ───
@app.get("/api/community/profiles")
async def api_get_community_profiles():
    from pipeline.stages.creator_community_hub import load_community_profiles
    return {"status": "ok", "profiles": load_community_profiles()}


@app.post("/api/community/build-discord")
async def api_build_creator_discord(payload: Dict[str, Any]):
    from pipeline.stages.creator_community_hub import build_creator_discord_server
    client_id = payload.get("client_id", "charlette_webb")
    bot_token = payload.get("bot_token")
    guild_id = payload.get("guild_id")
    wipe_existing = bool(payload.get("wipe_existing", True))
    return await build_creator_discord_server(
        client_id=client_id,
        bot_token=bot_token,
        guild_id=guild_id,
        wipe_existing=wipe_existing,
    )


@app.post("/api/community/setup-telegram")
async def api_setup_creator_telegram(payload: Dict[str, Any]):
    from pipeline.stages.creator_community_hub import setup_creator_telegram_channel
    client_id = payload.get("client_id", "charlette_webb")
    telegram_bot_token = payload.get("telegram_bot_token")
    channel_id = payload.get("channel_id")
    discord_invite_url = payload.get("discord_invite_url")
    return await setup_creator_telegram_channel(
        client_id=client_id,
        telegram_bot_token=telegram_bot_token,
        channel_id=channel_id,
        discord_invite_url=discord_invite_url,
    )


@app.post("/api/community/go-live")
async def api_community_go_live(payload: Dict[str, Any]):
    from pipeline.stages.creator_community_hub import blast_live_on_cam_alert
    client_id = payload.get("client_id", "charlette_webb")
    custom_message = payload.get(
        "custom_message",
        "I'm LIVE right now across all cam sites (8PM–3AM EST)! Come hang out, vibe, and control my toys 💕💦",
    )
    res = await blast_live_on_cam_alert(client_id=client_id, custom_message=custom_message)
    return {"status": "ok", "results": res}


@app.post("/api/community/post-poll")
async def api_community_post_poll(payload: Dict[str, Any]):
    from pipeline.stages.creator_community_hub import post_outfit_poll
    client_id = payload.get("client_id", "charlette_webb")
    return await post_outfit_poll(client_id=client_id)


@app.post("/api/community/configure-whop")
async def api_community_configure_whop(payload: Dict[str, Any]):
    from pipeline.stages.creator_community_hub import configure_whop_store
    return await configure_whop_store(
        client_id=payload.get("client_id", "charlette_webb"),
        whop_store_url=payload.get("whop_store_url", "https://whop.com/charlette-webb-vip/"),
        whop_api_key=payload.get("whop_api_key", ""),
    )


@app.post("/api/radar/webhook/whop")
async def api_whop_webhook(payload: Dict[str, Any]):
    from pipeline.stages.creator_community_hub import handle_whop_webhook
    client_id = payload.get("client_id", "charlette_webb")
    return await handle_whop_webhook(payload=payload, client_id=client_id)


@app.get("/api/vault/stream/{client_id}")
async def api_anti_scrape_vault_stream(client_id: str, file: str = "", expires: int = 0, sig: str = ""):
    from pipeline.stages.creator_community_hub import verify_signed_vault_token
    if not verify_signed_vault_token(client_id, file, expires, sig):
        raise HTTPException(status_code=403, detail="Expired or invalid HMAC Anti-Scrape Vault signature.")
    vault_dir = BASE_DIR / "workspace" / "media_vault" / client_id
    cand = vault_dir / Path(file).name
    if not cand.exists():
        raise HTTPException(status_code=404, detail="Vault item not found.")
    return FileResponse(
        cand,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.post("/api/community/telegram-stars-ppv")
async def api_telegram_stars_ppv(payload: Dict[str, Any]):
    from pipeline.stages.creator_community_hub import send_telegram_stars_ppv
    return await send_telegram_stars_ppv(
        client_id=payload.get("client_id", "charlette_webb"),
        star_count=int(payload.get("star_count", 250)),
        caption=payload.get("caption", "🔥 Exclusive Uncensored PPV Drop — Tap below to unlock with Telegram Stars!"),
        photo_path=payload.get("photo_path"),
    )


if __name__ == "__main__":
    # Pass the already-constructed `app` object directly rather than the string
    # reference "dashboard.server:app". The string form forces uvicorn to import this
    # entire module a SECOND time under a different module name ("dashboard.server"
    # vs this process's "__main__"), which silently re-ran every singleton
    # constructor (order_radar, herald_scheduler, ai_operator, comfy_bridge, etc.) and
    # their real file I/O twice on every `python dashboard/server.py` launch - the
    # first copy was just wasted work, not even the one serving requests. Only valid
    # because reload=False; uvicorn's reload mode requires the string form.
    uvicorn.run(app, host="0.0.0.0", port=8800, reload=False)
