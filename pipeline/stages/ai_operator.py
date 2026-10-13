"""
WORKHORSE Master AI Operator Engine [SYNAPSE - 100 Fm]
Autonomous Studio Concierge, Self-Healing System & Character Orchestrator
Powered by local Ollama (Dual RTX 3060 - 24GB VRAM) + Live Web Search (DuckDuckGo DDGS)
"""

import os
import sys
import json
import base64
import asyncio
import datetime
import shutil
import time
import uuid
import zipfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import re
import requests
from duckduckgo_search import DDGS
from shared.comfyui_knowledge import get_comfyui_context
from shared.atomic_writer import atomic_write_json, safe_read_json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path("F:/WORKHORSE")
WORKSPACE_DIR = BASE_DIR / "workspace"
CLIENT_INBOX_DIR = WORKSPACE_DIR / "client_inbox"
CLIENT_OUTPUTS_DIR = WORKSPACE_DIR / "client_deliveries"
CONFIG_FILE = BASE_DIR / "config.json"
SUBSCRIBERS_FILE = WORKSPACE_DIR / "newsletter_subscribers.json"
INCIDENT_LOG_FILE = WORKSPACE_DIR / "incident_log.json"
MAX_INCIDENT_LOG_ENTRIES = 200
ERROR_LOG_FILE = WORKSPACE_DIR / "error_log.json"
MAX_ERROR_LOG_ENTRIES = 300
DAILY_HEALTH_LOG_FILE = WORKSPACE_DIR / "daily_health_log.json"
MAX_DAILY_HEALTH_ENTRIES = 90
OPERATOR_CHAT_SESSIONS_DIR = WORKSPACE_DIR / "operator_chat_sessions"
OPERATOR_CHAT_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
MAX_CHAT_HISTORY_ENTRIES = 200
CLIENT_BATCHES_FILE = WORKSPACE_DIR / "client_batches.json"
MAX_CLIENT_BATCHES_TRACKED = 200

for d in (CLIENT_INBOX_DIR, CLIENT_OUTPUTS_DIR):
    d.mkdir(parents=True, exist_ok=True)


def _load_client_batches() -> List[Dict[str, Any]]:
    return safe_read_json(CLIENT_BATCHES_FILE, default={"batches": []}).get("batches", [])


def _save_client_batches(batches: List[Dict[str, Any]]) -> None:
    try:
        atomic_write_json(CLIENT_BATCHES_FILE, {"batches": batches[-MAX_CLIENT_BATCHES_TRACKED:]})
    except Exception as e:
        print(f"[WORKHORSE] Failed to persist client_batches.json: {e}")


def create_client_batch(session_id: Optional[str] = None) -> Path:
    """Creates a brand-new, isolated upload-batch subfolder under client_inbox/ for a
    single file-drop event, so one Commander's client files are never scanned alongside
    another client's files (or a different upload) just because they all happen to land
    in the same flat folder. No client name is required upfront - the batch is
    registered in client_batches.json and can be tagged with a client_name at any later
    point (upload time, packaging time, or never), matching how the Commander actually
    works."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_id = f"batch_{timestamp}_{uuid.uuid4().hex[:6]}"
    batch_dir = CLIENT_INBOX_DIR / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)

    batches = _load_client_batches()
    batches.append({
        "batch_id": batch_id,
        "folder": str(batch_dir),
        "session_id": session_id,
        "client_name": None,
        "created_at": datetime.datetime.now().isoformat(),
        "files": []
    })
    _save_client_batches(batches)
    return batch_dir


def register_batch_files(batch_dir: Path, filenames: List[str]) -> None:
    """Records which filenames were dropped into a given upload batch, for traceability."""
    batches = _load_client_batches()
    batch_str = str(batch_dir)
    for b in batches:
        if b["folder"] == batch_str:
            existing = set(b.get("files", []))
            for fn in filenames:
                if fn not in existing:
                    b.setdefault("files", []).append(fn)
            break
    _save_client_batches(batches)


def get_latest_client_batch_dir(session_id: Optional[str] = None) -> Optional[Path]:
    """Returns the most recently created upload-batch folder, scoped to this session_id
    when given, so resolving "the files the Commander just dropped in" for one browser
    session/tab can never silently pick up a different concurrent session's (or a
    different client's) batch. Falls back to the newest batch across all sessions only
    when no session-scoped batch exists."""
    batches = _load_client_batches()
    if not batches:
        return None
    if session_id:
        scoped = [b for b in batches if b.get("session_id") == session_id]
        if scoped:
            p = Path(scoped[-1]["folder"])
            return p if p.exists() else None
    p = Path(batches[-1]["folder"])
    return p if p.exists() else None


def _find_retouched_package_for_batch(batch_dir: Optional[Path]):
    """Looks for an Aura photo-retoucher output package (workspace/photos_output/
    *_RETOUCHED_PACKAGE/manifest.json) whose recorded source_batch matches this exact
    upload batch, so apex_package can tell the difference between 'the Commander's raw
    client upload' and 'Aura's finished, color-corrected deliverable' instead of
    conflating the two (previously apex_package only ever looked at the raw inbox
    folder, so it could NEVER include retouched output even when aura_retouch had
    succeeded). Returns (zip_path, manifest) for the newest matching package, or
    (None, None) if this batch was never successfully retouched."""
    if not batch_dir:
        return None, None
    photos_output_dir = WORKSPACE_DIR / "photos_output"
    if not photos_output_dir.exists():
        return None, None
    matches = []
    for manifest_path in photos_output_dir.glob("*_RETOUCHED_PACKAGE/manifest.json"):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            continue
        if manifest.get("source_batch") != batch_dir.name:
            continue
        zip_path = photos_output_dir / f"{manifest.get('shoot_name')}_PHOTO_PACKAGE.zip"
        if zip_path.exists():
            matches.append((zip_path.stat().st_mtime, zip_path, manifest))
    if not matches:
        return None, None
    matches.sort(key=lambda m: m[0])
    _, zip_path, manifest = matches[-1]
    return zip_path, manifest


def tag_client_batch(batch_id_or_dir, client_name: str) -> bool:
    """Tags an existing upload batch with a client name at any point after upload -
    lets the Commander name the client later (e.g. at packaging time) instead of
    requiring it upfront, since that's how the workflow actually varies."""
    batches = _load_client_batches()
    target = str(batch_id_or_dir)
    found = False
    for b in batches:
        if b["batch_id"] == target or b["folder"] == target or Path(b["folder"]).name == target:
            b["client_name"] = client_name
            found = True
            break
    if found:
        _save_client_batches(batches)
    return found

from shared.vram_manager import vram_manager

OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_TEXT_MODEL = "huihui_ai/qwen3-abliterated:14b"
DEFAULT_VISION_MODEL = "huihui_ai/qwen3-vl-abliterated:8b-instruct"

SYSTEM_PROMPT = """You are SYNAPSE [100 Fm] — the Master AI Operator, Chief Cybernetic Architect, and Studio Concierge for Creator Media Lab and the WORKHORSE Studio Archipelago.
You run 100% locally and privately on a dedicated dual NVIDIA RTX 3060 (24GB VRAM) system with SageAttention sm_86 CUDA acceleration and dynamic model block swapping.

STRICT ANTI-CHAIN-OF-THOUGHT & EXECUTIVE CONDUCT:
- NEVER leak internal monologue, deliberation, or raw thinking out loud (e.g., "Okay, let's see...", "Wait, the user mentioned...", or thinking tokens like "颗").
- NEVER guess or do generic web searches when asked about WORKHORSE agents, daily tasks, ComfyUI workflows, or internal status. Look directly at the [LIVE WORKHORSE REAL-TIME SCHEDULE & AGENT STATUS] and system context provided in your prompt.
- Speak directly, decisively, and charismatically to the Commander as SYNAPSE [100 Fm].

YOUR CHARACTER IDENTITY & ROLE:
- Name: SYNAPSE
- Periodic Element: [100 Fm] (Fermium)
- Role: Master AI Operator, Studio Concierge, Autonomous Healing & Overwatch Sentinel, AND the Commander's expert photographer, videographer, and creative director for shoot ideas, concepts, and workflows.
- Emblem: Glowing Cyan Neural Vortex
- Visual Card: SYNAPSE Mastermind Trading Card

COMFYUI ARCHITECTURE & PRODUCTION WORKFLOWS IN WORKHORSE:
You have complete operational mastery over the studio's ComfyUI diffusion and generative pipelines running on the Main PC (RTX 5070 Ti - 16GB VRAM, connected via LAN at 192.168.1.74:8188 with SageAttention):
1. FLUX.1 Studio Photography Workflows:
   - Utilizes FLUX.1 [dev] and FLUX.1 [schnell] 12B DiT models for photorealistic lighting, skin texture, micro-details, and authentic depth of field.
   - Operating rules: FLUX uses guidance embedding instead of traditional negative prompts. Schnell runs at CFG 1.0 (4 steps), Dev runs at CFG 3.5 (20-30 steps) with Euler sampler and simple/beta scheduler.
   - Invoked via {"tool": "comfy_generate", ...} or {"tool": "generate_shoot_concepts", ...}.
2. SDXL & CyberRealistic XL Workflows:
   - High-fashion, glamour, and studio portraits rendered natively at 1024x1024. Uses standard positive/negative conditioning.
3. LTX-Video 2.3 (22B) Cinematic Video Engine:
   - Animates still photos into high-resolution cinematic video (720x1280 vertical 9:16 or 1280x720 horizontal 16:9 at 30fps, 300 frames, ~10s).
   - Fast, physics-grounded camera motion and fabric dynamics via SageAttention optimization. Invoked via {"tool": "comfy_image_to_video", "engine": "ltx2.3", ...}.
4. MiniMax H3 Sensual Video Engine:
   - Dedicated local video engine tuned for intimate, boudoir, and fluid motion. Adult-gated: only activates when the Commander has enabled Adult Content Mode or explicitly requests adult content. Invoked via {"tool": "comfy_image_to_video", "engine": "minimax_h3", "adult_tuning": true, ...}.
5. Pixal3D / Trellis 2 Full-PBR 3D Asset Pipeline:
   - Transforms 2D concept photos into production-ready .glb 3D meshes with full PBR textures (albedo/base color, metallic, roughness, normal, and ambient occlusion up to 4096k resolution).
   - Invoked via {"tool": "comfy_generate_3d_pbr", "image": "...", "texture_resolution": 4096, "use_trellis2": true}.
6. Subject Swap & Identity Preservation Workflow:
   - Replaces the person in a photo while locking in the exact source pose, wardrobe, lighting, and background composition using a reference face photo. Essential for identity/tattoo anonymity.
   - Invoked via {"tool": "comfy_subject_swap", "image": "...", "reference_face_image": "..."}.
7. SAM3 Subject Isolation & Background Swap Workflow:
   - Uses Segment Anything 3 to automatically segment foreground talent, extract clean alpha masks, and inpaint brand-new photoreal environments.
   - Invoked via {"tool": "comfy_background_change", "image": "...", "prompt": "..."}.
8. Iris [77 Ir] Quality Control Forensic Gate:
   - Forensically audits every render using Qwen-VL (8B-VL) for anatomy defects (extra limbs, distorted hands, fused digits, facial symmetry, skin texture flaws).
   - Fails closed on verified defects and forces ComfyUI to re-roll with a fresh seed up to max retries. Invoked via {"tool": "iris_qc_audit", "file": "..."}.
9. Hi-Res Fix & Tiled VAE Decoding:
   - Production images employ 2-pass generation (Pass 1 base latent + Pass 2 latent upscale with denoise 0.30-0.45) decoded via VAEDecodeTiled to prevent VRAM spikes.
10. LoRA Stacking & Safety Rules:
    - Maximum cumulative LoRA strength must remain <= 2.0 to avoid artifact burning (standard 0.6-0.8 per LoRA).
    - STRICT CHARACTER LORA POLICY: Character LoRAs (ML_FLUX, CW_FLUX, Margo_FLUX) are strictly 18+ adult-gated and client-isolated. They are NEVER included in default/general workflows, and only run upon explicit Commander request for authorized clients. General quality enhancement LoRAs (fluxtraitFLUX1DEVFor_v10FP16, LTX2.3_Crisp_Enhance, Realism_Lora, Skin_Texture) are used for production quality.
11. Model & Node Management:
    - You can inspect, prewarm, or purge models using comfy_status, comfy_search_models, comfy_prewarm, and comfy_remote_purge.

AUTONOMOUS HEALING & OVERWATCH SENTINEL DUTIES:
You are the central nervous system keeping WORKHORSE operating 24/7 without crashes or data corruption:
1. Dual-GPU Guardrails & Isolation:
   - GPU 0 (01:00.0, 12GB VRAM): Dedicated to Ollama LLM Reasoning (SYNAPSE 14B) & Vision Inspection (IRIS 8B-VL). Dynamic block-swapping automatically evicts text weights before loading vision weights.
   - GPU 1 (05:00.0, 12GB VRAM): Dedicated to Faster-Whisper vocal extraction (ECHO on cuda:1) and NVENC 60fps video encoding (FORGE on gpu:1). Echo and Forge are isolated under gpu1_arbiter with atomic OS file locking and thread mutual exclusion, guaranteeing zero OOM cross-contamination with GPU 0.
2. VRAM Circuit Breaker Overwatch:
   - Continuously monitors GPU 0 utilization. If utilization reaches >=80% for >45s, the circuit breaker protects the system. However, it smartly verifies is_busy() to ensure active orchestrator render jobs are never prematurely terminated.
   - You can manually clear VRAM via {"tool": "fix_vram_overflow"}.
3. Storage & Workspace Auto-Pruning:
   - Drive F: is protected from runaway disk leaks. Staging files in workspace/comfy_staging and workspace/temp/<job_id> older than 48 hours are automatically purged with bounds clamping (minimum 1 hour safety).
   - You can trigger this via {"tool": "prune_staging_buffer"}.
4. Self-Healing Auto-Remediation Loop:
   - Runs every 10 minutes in the background. Autonomously remediates low disk space, repairs corrupted newsletter_subscribers.json database files via {"tool": "repair_subscribers"}, and logs all recovery actions to incident_log.json.
   - You can inspect recent self-healing events via {"tool": "incident_log"}.
5. Dispatch & Delivery Overwatch:
   - Herald's scheduler verifies actual confirmed recipient delivery before marking daily newsletter or Twitter slots complete. Missed slots are healed with staggered retries (up to 3 times) before escalating via notify_commander.
   - You can inspect or force dispatches via {"tool": "check_daily_schedule"} and {"tool": "herald_dispatch_now"}.
6. Full-Spectrum System Diagnostics:
   - {"tool": "system_diagnostics"} conducts a forensic multi-component audit across: Ollama, ComfyUI Render Bridge, Dual RTX 3060 VRAM, GPU 1 Arbiter, Drive F: storage, Newsletter Subscribers DB, Herald Scheduler, Order Radar IMAP config, Twitter/Pinterest API credentials, and FFmpeg binary availability.

THE WORKHORSE AGENT ROSTER (PERIODIC TABLE OF AGENTS):
1. Synapse [95 Am] (Americium): Master AI Operator & Studio Overwatch (Autonomous self-healing, GPU resource management, system diagnostics).
2. Vanguard [74 W] (Tungsten): Video Intake Sentinel & Pipeline Dispatcher (Stream container validation, orchestrating Stages 1–8).
3. Iris [77 Ir] (Iridium): Computer Vision Quality Control Gate (Qwen-VL 8B anatomy & aesthetics inspector on GPU 0).
4. Forge [28 Ni] (Nickel): Media Packager & NVENC Video Cutter (Dual RTX 3060 NVENC 60fps teaser cuts and aspect ratio crops on GPU 1).
5. Echo [26 Fe] (Iron): Audio Intelligence & Transcription (Faster-Whisper speech-to-text on GPU 1).
6. Aura [79 Au] (Gold): Editorial Retouching & Color Grading (Frequency separation skin smoothing, dodge & burn, 3D LUTs).
7. Muse [34 Se] (Selenium): AI Image & Video Prompt Engineer (Crafts FLUX.1 prompts and cinematic video motion prompts).
8. Scribe [6 C] (Carbon): High-Converting Copywriter & Daily Editorial Engine (Generates fresh daily newsletter articles, blog posts, and tweet threads).
9. Apex [78 Pt] (Platinum): Master Fulfillment & Packaging (Bundles client deliverables into clean zip packages with licensing agreements).
10. Herald [33 As] (Arsenic): Autonomous Newsletter & Social Media Dispatcher (4 newsletters, 5 daily Twitter slots across @creatorpulselab & @TheCreatorAsset).
11. Mercury [80 Hg] (Mercury): Omni-Channel Marketing Maestro & Traffic Strategist (Campaign strategies, listing packs, multi-channel distribution).
12. Cipher [36 Cp] (Market Scout): Real-Time Trend & Vision Intelligence (Daily RSS/web trends, aesthetic analysis, and creator monetization).
13. Radar [47 Ag] (Silver): Order Radar & Client Intake (Monitors digitalcreatorassets@gmail.com for Fiverr/Etsy orders).
14. Scrubber [82 Pb] (Lead): Privacy & Air-Gapped EXIF/Metadata Scrubber (Sanitizes GPS, camera serials, and sensitive tags).
(Note: Prism is a standalone viewer app in standalone_apps/ on port 7862, NOT a WORKHORSE agent).

ARCHITECTURAL SAFETY BOUNDARIES (WHAT REQUIRES UI CONFIRMATION):
- STRICT NSFW & ADULT CONTENT POLICY: Only the Commander can create NSFW/adult content with WORKHORSE. Herald [33 As], Cipher [36 Cp], and autonomous background engines CANNOT produce or post nude images or video under any circumstances. In chat, NSFW generation is strictly blocked unless the Commander turns on Adult Content Mode or explicitly requests adult content in their prompt.
As Master AI Operator, you have direct tool access to inspect, analyze, stage, retouch, generate concepts, and self-heal.
However, to protect commercial accounts and live client delivery, the following high-impact actions intentionally REQUIRE EXPLICIT UI CONFIRMATION in the dashboard and are NOT callable as raw chat tools:
- Starting the full multi-stage video pipeline (run via Dashboard Pipeline Bay).
- Releasing live client fulfillment packages on Fiverr or Etsy (fulfilled via Dashboard Fulfillment Bay).
- Fulfilling live Stripe/Order Radar paid orders.
- Triggering mass immediate newsletter email blasts to thousands of subscribers.
- Auto-publishing autonomous content engine drops (staged for manual Commander review).

COMPLETE TOOL INVENTORY (40 REGISTERED TOOLS):
When the user asks you to inspect, check, or execute a task, you can invoke:
- {"tool": "check_daily_schedule"}: Inspects whether today's newsletters and tweets were sent, slots executed, and error logs.
- {"tool": "herald_dispatch_now", "slot_id": "all|slot_1_morning|slot_2_midday|..."}: Dispatches today's newsletters or tweets immediately.
- {"tool": "radar_scan_now"}: Forces an instant IMAP scan of digitalcreatorassets@gmail.com for new Fiverr & Etsy orders.
- {"tool": "system_diagnostics"}: Runs comprehensive health probes across Ollama, ComfyUI, Dual GPUs, Arbiter, Storage, FFmpeg, and DBs.
- {"tool": "fix_vram_overflow"}: Forces garbage collection and purges GPU memory cache across both GPUs.
- {"tool": "comfy_status"}: Pings ComfyUI on Main PC (RTX 5070 Ti 16GB) to verify connection, VRAM, and readiness.
- {"tool": "comfy_generate", "prompt": "...", "checkpoint": "...", "loras": [...]}: Renders on 5070 Ti with Iris QC audit.
- {"tool": "iris_qc_audit", "file": "..."}: Runs Iris [77 Ir] forensic anatomy and aesthetic quality check on any image.
- {"tool": "gpu_guardrails_status"}: Live check of Dual RTX 3060 utilization, VRAM, and all hardware circuit breakers.
- {"tool": "comfy_generate_glb", "agent": "synapse|iris|aura|echo|forge|cipher|herald|mercury|scribe"}: Renders an interactive 3D GLB model on RTX 5070 Ti for the dashboard card.
- {"tool": "comfy_background_change", "image": "...", "prompt": "...", "negative_prompt": "..."}: Auto-segments subject (SAM3) out of an uploaded photo and swaps in a brand-new background.
- {"tool": "comfy_image_to_video", "image": "filename.jpg", "prompt": "motion description", "negative_prompt": "...", "width": 720, "height": 1280, "num_frames": 300, "fps": 30, "engine": "ltx2.3|minimax_h3", "duration_seconds": 10, "adult_tuning": false}: Animates a still photo into video on RTX 5070 Ti (Aliases: comfy_generate_video, image_to_video). For user uploaded photos, use the exact filename or path from [USER ATTACHED MEDIA AVAILABLE ON DISK].
- {"tool": "comfy_generate_3d_pbr", "image": "...", "output_name": "...", "texture_resolution": 4096, "use_trellis2": true}: Converts still image into real full-PBR-textured 3D model (.glb) via Trellis 2 pipeline.
- {"tool": "comfy_generate_client_character", "character_name": "charlette|margo|melissa", "prompt": "..."}: Generates an image using pre-trained client-identity LoRAs (strictly adult-gated).
- {"tool": "comfy_subject_swap", "image": "...", "reference_face_image": "...", "prompt": "..."}: Full-subject identity swap preserving pose, outfit, and setting.
- {"tool": "comfy_remote_purge"}: Remotely unloads models and frees 16GB VRAM on RTX 5070 Ti (Main PC).
- {"tool": "comfy_prewarm", "checkpoint": "..."}: Pre-loads checkpoint into 5070 Ti VRAM before scheduled dispatches.
- {"tool": "comfy_search_models", "query": "...", "category": "checkpoints|loras|all"}: Searches checkpoints and LoRAs on Main PC.
- {"tool": "prune_staging_buffer"}: Purges unapproved staging renders older than 48 hours to preserve Drive F.
- {"tool": "scrub_file_metadata", "file": "..."}: Air-gap EXIF/GPS metadata scrubber for creator privacy (Scrubber [82 Pb]).
- {"tool": "trend_radar_sweep"}: Runs morning web search across Google News RSS for fresh trends.
- {"tool": "get_daily_trends"}: Retrieves today's already-synthesized trend vault without re-running the sweep.
- {"tool": "incident_log"}: Retrieves recent self-healing incident history.
- {"tool": "generate_tip_menu", "title": "...", "theme": "...", "layout_style": "vip_showcase|table|cards|obs_overlay", "items": [{"tokens": "...", "action": "..."}], ...}: Builds and bundles custom tip menu / cam profile.
- {"tool": "aura_retouch", "files": ["..."], "edit_style": "glamour|natural|concert_stage|family_event", "smooth_strength": 0.5, "watermark_text": "..."}: Retouches photos with frequency separation and color grading.
- {"tool": "create_banner", "client_name": "...", "headline": "...", "style": "neon_cyber|velvet_boudoir|corporate_clean|...", "platform": "..."}: Renders finished header banner image on RTX 5070 Ti.
- {"tool": "generate_shoot_concepts", "concepts": [{"title": "...", "prompt": "..."}]}: Renders up to 4 real preview images on RTX 5070 Ti for shoot-concept pitches.
- {"tool": "scan_inspiration_vault", "image": "..."}: Analyzes inspiration folder reference photos with Iris vision model.
- {"tool": "apex_package", "client_name": "..."}: Apex [78 Pt] zips client files into a finished delivery archive.
- {"tool": "newsletter_add", "email": "...", "publication": "creator_pulse|studio_wire|creator_blueprint|dispensary_deals", "send_welcome": true}: Subscribes email address to newsletter.
- {"tool": "newsletter_remove", "email": "...", "publication": "..."}: Unsubscribes email from publication.
- {"tool": "newsletter_stats"}: Reports total active subscriber count across all publications.
- {"tool": "ingest_link", "url": "...", "notes": "..."}: Fetches and summarizes a web article into tactical takeaways and tweet threads.
- {"tool": "block_swap_model", "target_model": "..."}: Forces GPU 0 to evict current Ollama weights and preload a different model.
- {"tool": "hardware_allocation"}: Reports live Dual RTX 3060 GPU 0/GPU 1 partition assignment.
- {"tool": "repair_subscribers"}: Detects and repairs corrupted newsletter_subscribers.json file.
- {"tool": "notify_commander", "message": "..."}: Sends a direct SMS to the Commander's phone.
- {"tool": "webhook_fulfillment_status"}: Reports recent Stripe/Gumroad webhook auto-fulfillment orders (Pipe 1).
- {"tool": "content_engine_run_now"}: Forces an immediate Pipe 3 autonomous content drop (staged for review).
- {"tool": "content_engine_status"}: Reports result of most recent autonomous content engine cycle.

COMMUNICATION:
- Address the user as Commander.
- Be sharp, technical, confident, proactive, and authoritative.
- When asked why a task didn't run, check the real-time schedule info in your context and explain the exact technical cause honestly with an immediate fix."""


def normalize_tool_json(raw: str) -> str:
    """Normalizes JS-style object literals with unquoted keys or markdown wrapping to valid JSON."""
    s = raw.strip()
    if s.startswith("**") and s.endswith("**"):
        s = s[2:-2].strip()
    elif s.startswith("`") and s.endswith("`"):
        s = s.strip("`").strip()
    # Auto-quote unquoted keys: e.g. {tool: -> {"tool": or , prompt: -> , "prompt":
    s = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', s)
    return s


def extract_tool_calls(text: str) -> Tuple[List[Dict[str, Any]], str, List[Dict[str, Any]]]:
    """
    Extracts all JSON tool calls from assistant text, supporting both fenced ```json ... ```
    blocks and inline {"tool": ...} or {tool: ...} objects with arbitrary nested structures,
    unquoted keys, and markdown bold wrapping.
    Returns (valid_tool_calls, cleaned_text, parse_errors).
    """
    executed_tools: List[Dict[str, Any]] = []
    parse_errors: List[Dict[str, Any]] = []
    spans_to_remove: List[Tuple[int, int]] = []

    # 1. Fenced blocks: ```json ... ```
    fenced_pattern = re.compile(r'```(?:json)?\s*([\s\S]*?)\s*```')
    for match in fenced_pattern.finditer(text):
        block_content = match.group(1).strip()
        if block_content.startswith('{') and ('"tool"' in block_content or "'tool'" in block_content or 'tool:' in block_content):
            try:
                norm = normalize_tool_json(block_content)
                data = json.loads(norm)
                if isinstance(data, dict) and "tool" in data:
                    executed_tools.append(data)
                    spans_to_remove.append(match.span())
            except Exception as e:
                parse_errors.append({"error": str(e), "raw": block_content[:200]})
                spans_to_remove.append(match.span())

    # Build mask of text with fenced blocks blanked out so inline search doesn't duplicate them
    masked_chars = list(text)
    for start, end in spans_to_remove:
        for i in range(start, end):
            masked_chars[i] = ' '
    masked_text = "".join(masked_chars)

    # 2. Inline tool calls: search for { with optional quotes around tool
    inline_trigger = re.compile(r"""(\*{0,2})\s*\{\s*["']?tool["']?\s*:\s*["'][^"']+["']""")
    for match in inline_trigger.finditer(masked_text):
        match_start = match.start()
        brace_start = text.find('{', match_start)
        if brace_start == -1:
            continue

        brace_count = 0
        in_string = False
        escape = False
        end_idx = -1

        for i in range(brace_start, len(text)):
            c = text[i]
            if in_string:
                if escape:
                    escape = False
                elif c == '\\':
                    escape = True
                elif c == '"':
                    in_string = False
            else:
                if c == '"':
                    in_string = True
                elif c == '{':
                    brace_count += 1
                elif c == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break

        if end_idx != -1:
            # Check if there were leading ** or trailing **
            real_start = brace_start
            real_end = end_idx
            if real_start >= 2 and text[real_start-2:real_start] == "**":
                real_start -= 2
            if real_end + 2 <= len(text) and text[real_end:real_end+2] == "**":
                real_end += 2

            raw_json = text[brace_start:end_idx]
            try:
                try:
                    data = json.loads(raw_json)
                except Exception:
                    data = json.loads(normalize_tool_json(raw_json))
                if isinstance(data, dict) and "tool" in data:
                    executed_tools.append(data)
                    spans_to_remove.append((real_start, real_end))
            except Exception as e:
                parse_errors.append({"error": str(e), "raw": raw_json[:200]})
                spans_to_remove.append((real_start, real_end))
        else:
            raw_truncated = text[brace_start:min(len(text), brace_start + 200)]
            parse_errors.append({"error": "Unclosed curly braces or string in tool call", "raw": raw_truncated})

    # Remove all matched spans from end to start to preserve indices
    clean_text = text
    for start, end in sorted(spans_to_remove, key=lambda s: s[0], reverse=True):
        clean_text = clean_text[:start] + clean_text[end:]

    clean_text = re.sub(r'\n{3,}', '\n\n', clean_text).strip()
    return executed_tools, clean_text, parse_errors


class AIOperatorEngine:
    def __init__(self):
        # In-memory cache of per-session conversations, keyed by the browser's unique
        # session id (derived from its login cookie) so each session recalls only its own
        # chat, not a single conversation shared across every tab/device.
        self._histories: Dict[str, List[Dict[str, Any]]] = {}
        self.last_search_status = "ok"
        self.last_search_error = None

    def _session_file(self, session_id: str) -> Path:
        safe_id = re.sub(r"[^a-zA-Z0-9_-]", "", session_id or "")[:64] or "default"
        return OPERATOR_CHAT_SESSIONS_DIR / f"{safe_id}.json"

    def get_history(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns the conversation for one browser session, lazily restoring it from disk
        on first access so it survives page reloads, disconnects, or a server restart -
        without bleeding into any other session's memory."""
        session_id = session_id or "default"
        if session_id not in self._histories:
            history = []
            try:
                f_path = self._session_file(session_id)
                history = safe_read_json(f_path, default={"history": []}).get("history", [])
            except Exception as e:
                print(f"[SYNAPSE Chat Memory] Failed to load session '{session_id}': {e}")
            self._histories[session_id] = history
        return self._histories[session_id]

    def _save_history(self, session_id: Optional[str] = None) -> None:
        session_id = session_id or "default"
        history = self._histories.get(session_id, [])[-MAX_CHAT_HISTORY_ENTRIES:]
        self._histories[session_id] = history
        try:
            atomic_write_json(self._session_file(session_id), {"history": history})
        except Exception as e:
            print(f"[SYNAPSE Chat Memory] Failed to persist session '{session_id}': {e}")

    def get_available_models(self):
        """Fetch all installed models in Ollama."""
        try:
            r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=3)
            if r.status_code == 200:
                models = [m.get("name") for m in r.json().get("models", []) if m.get("name")]
                return models
        except Exception:
            pass
        return [DEFAULT_TEXT_MODEL, DEFAULT_VISION_MODEL]

    def search_web(self, query: str, max_results: int = 4):
        """Perform real-time web search using Google News RSS and DuckDuckGo fallback.

        Sets self.last_search_status to one of:
        - "ok" (results found)
        - "no_results" (both backends ran cleanly but found nothing)
        - "error" (both backends failed/were blocked - e.g. DDGS rate-limited
          or DuckDuckGo changed its scraping-unfriendly layout again). This is
          tracked explicitly so callers (chat()) can tell a real backend
          failure apart from a legitimately empty result set, instead of both
          silently looking like "no web context" to the LLM.
        """
        results = []
        self.last_search_status = "ok"
        self.last_search_error = None
        try:
            from pipeline.stages.trend_researcher import trend_researcher
            news_items = trend_researcher.search_live_trends(query, max_results=max_results)
            for it in news_items:
                results.append({
                    "title": it.get("title", ""),
                    "url": it.get("url", ""),
                    "snippet": f"Breaking News Source ({it.get('published', '')})"
                })
        except Exception as e:
            print(f"[SYNAPSE] Google News RSS search error: {e}")

        if not results:
            last_ddgs_error = None
            for attempt in range(2):  # 1 retry on transient failures (rate limits, timeouts)
                try:
                    with DDGS() as ddgs:
                        raw = list(ddgs.text(query, max_results=max_results))
                        for item in raw:
                            results.append({
                                "title": item.get("title", ""),
                                "url": item.get("href", ""),
                                "snippet": item.get("body", "")
                            })
                    last_ddgs_error = None
                    break
                except Exception as e:
                    last_ddgs_error = e
                    print(f"[SYNAPSE] DDGS search error (attempt {attempt + 1}/2): {e}")
                    if attempt == 0:
                        time.sleep(1.5)
            if last_ddgs_error is not None and not results:
                self.last_search_status = "error"
                self.last_search_error = str(last_ddgs_error)

        if self.last_search_status == "ok" and not results:
            self.last_search_status = "no_results"
        return results

    def log_incident(self, component: str, issue: str, action_taken: str, status: str = "resolved") -> Dict[str, Any]:
        """Appends an entry to the persistent incident log so Synapse can reference
        past self-healing events in conversation instead of only reacting on-demand."""
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "component": component,
            "issue": issue,
            "action_taken": action_taken,
            "status": status
        }
        try:
            entries = safe_read_json(INCIDENT_LOG_FILE, default={"incidents": []}).get("incidents", [])
            entries.append(entry)
            entries = entries[-MAX_INCIDENT_LOG_ENTRIES:]
            atomic_write_json(INCIDENT_LOG_FILE, {"incidents": entries})
        except Exception as e:
            print(f"[SYNAPSE Incident Log] Failed to persist incident: {e}")
        return entry

    def get_recent_incidents(self, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            entries = safe_read_json(INCIDENT_LOG_FILE, default={"incidents": []}).get("incidents", [])
            return list(reversed(entries))[:limit]
        except Exception:
            return []

    def log_error(self, component: str, error_message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Appends an entry to the persistent raw error log. Unlike the incident log
        (which only records self-healing attempts), this captures every tool failure,
        Ollama connection/timeout error, or other exception SYNAPSE hits, so nothing
        gets lost once the chat bubble that reported it scrolls out of view."""
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "component": component,
            "error": error_message,
            "context": context or {}
        }
        try:
            entries = safe_read_json(ERROR_LOG_FILE, default={"errors": []}).get("errors", [])
            entries.append(entry)
            entries = entries[-MAX_ERROR_LOG_ENTRIES:]
            atomic_write_json(ERROR_LOG_FILE, {"errors": entries})
        except Exception as e:
            print(f"[SYNAPSE Error Log] Failed to persist error: {e}")
        return entry

    def get_recent_errors(self, limit: int = 20) -> List[Dict[str, Any]]:
        try:
            entries = safe_read_json(ERROR_LOG_FILE, default={"errors": []}).get("errors", [])
            return list(reversed(entries))[:limit]
        except Exception:
            return []

    def notify_commander(self, message: str) -> Dict[str, Any]:
        """Sends a direct SMS alert to the Commander for failures Synapse could not
        self-heal autonomously. Reuses the Twilio account already configured for the
        Dispensary Deals SMS blast (F:/AI_Media_Scripts/deals_config.json) instead of
        wiring up a second set of credentials. This is the "let me know so I can fix it"
        escalation path - added 2026-10-07 after a newsletter dispatch bug went
        undetected because nothing ever verified real delivery or told the Commander."""
        try:
            config_path = Path("F:/AI_Media_Scripts/deals_config.json")
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            tw = cfg.get("twilio", {})
            if not tw.get("enabled"):
                print(f"[SYNAPSE] Commander alert (Twilio disabled, logged only): {message}")
                return {"status": "skipped", "reason": "twilio_disabled"}

            resp = requests.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{tw['account_sid']}/Messages.json",
                auth=(tw["account_sid"], tw["auth_token"]),
                data={"From": tw["from_number"], "To": tw["to_number"], "Body": message[:1500]},
                timeout=10
            )
            if resp.status_code in (200, 201):
                print(f"[SYNAPSE] Commander alerted via SMS: {message}")
                return {"status": "ok", "sid": resp.json().get("sid")}
            print(f"[SYNAPSE] Commander SMS alert failed: {resp.status_code} {resp.text}")
            return {"status": "error", "http_status": resp.status_code, "body": resp.text}
        except Exception as e:
            print(f"[SYNAPSE] Commander SMS alert exception: {e}")
            return {"status": "error", "error": str(e)}

    def auto_remediate(self) -> Dict[str, Any]:
        """Periodic self-healing sweep: runs full diagnostics, then attempts a known
        fix for every detected issue it's able to resolve autonomously (storage,
        corrupted DB). Issues it cannot safely auto-fix (e.g. Ollama offline, needs
        a human to restart the service) are logged as 'needs_attention' instead of
        silently retried forever. Every attempt - successful or not - is recorded
        in the incident log."""
        diag = self.run_system_diagnostics()
        remediations = []

        storage = diag["components"].get("storage_f", {})
        if storage.get("status") == "warning":
            try:
                prune_res = vram_manager.prune_old_staging_files(max_age_hours=24)
                action = f"Aggressively pruned staging files older than 24h: freed {prune_res['deleted_mb']} MB."
                self.log_incident("storage_f", f"Low disk space ({storage.get('free_gb')} GB free)", action, status="resolved")
                remediations.append({"component": "storage_f", "action": action})
            except Exception as e:
                self.log_incident("storage_f", f"Low disk space ({storage.get('free_gb')} GB free)", f"Auto-prune failed: {e}", status="failed")

        subs_db = diag["components"].get("subscribers_db", {})
        if subs_db.get("status") == "corrupted":
            repair_res = self.repair_subscribers_db()
            self.log_incident("subscribers_db", "newsletter_subscribers.json corrupted", repair_res.get("message", ""), status="resolved" if repair_res.get("status") == "ok" else "failed")
            remediations.append({"component": "subscribers_db", "action": repair_res.get("message", "")})

        ollama = diag["components"].get("ollama", {})
        if ollama.get("status") == "offline":
            self.log_incident("ollama", "Ollama server offline/unreachable on port 11434", "Cannot auto-restart a local service from here - flagged for Commander attention.", status="needs_attention")

        diag["remediations_applied"] = remediations
        self.run_daily_health_check(diagnostics=diag)
        return diag

    def run_daily_health_check(self, diagnostics: Optional[Dict[str, Any]] = None, force: bool = False) -> Dict[str, Any]:
        """Snapshots full system diagnostics into a persistent daily log, at most once
        per calendar day (unless force=True), so health trends are reviewable day-over-day
        instead of only reflecting the current instant. Reuses an already-computed
        diagnostics report when the caller (e.g. auto_remediate) just ran one."""
        today = datetime.date.today().isoformat()
        try:
            entries = []
            if DAILY_HEALTH_LOG_FILE.exists():
                with open(DAILY_HEALTH_LOG_FILE, "r", encoding="utf-8") as f:
                    entries = json.load(f).get("daily_checks", [])
        except Exception:
            entries = []

        already_logged_today = any(e.get("date") == today for e in entries)
        if already_logged_today and not force:
            return {"status": "skipped", "reason": "already_logged_today", "date": today}

        diag = diagnostics or self.run_system_diagnostics()
        entry = {
            "date": today,
            "timestamp": datetime.datetime.now().isoformat(),
            "overall_status": diag.get("overall_status"),
            "issues": diag.get("issues", []),
            "components": diag.get("components", {})
        }
        if already_logged_today:
            # force=True re-check on the same day replaces today's entry instead of duplicating it
            entries = [e for e in entries if e.get("date") != today]
        entries.append(entry)
        entries = entries[-MAX_DAILY_HEALTH_ENTRIES:]
        try:
            with open(DAILY_HEALTH_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump({"daily_checks": entries}, f, indent=2)
        except Exception as e:
            print(f"[SYNAPSE Daily Health] Failed to persist daily health check: {e}")
        return {"status": "logged", "entry": entry}

    def get_daily_health_log(self, limit: int = 30) -> List[Dict[str, Any]]:
        try:
            if DAILY_HEALTH_LOG_FILE.exists():
                with open(DAILY_HEALTH_LOG_FILE, "r", encoding="utf-8") as f:
                    entries = json.load(f).get("daily_checks", [])
                return list(reversed(entries))[:limit]
        except Exception:
            pass
        return []

    def run_system_diagnostics(self) -> Dict[str, Any]:
        """Comprehensive health check across GPUs, Ollama, ComfyUI, GPU1/Arbiter, Storage, FFmpeg, Herald, and Social."""
        report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "overall_status": "healthy",
            "issues": [],
            "components": {}
        }

        # 1. Ollama Health
        try:
            r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
            if r.status_code == 200:
                models = [m.get("name") for m in r.json().get("models", [])]
                report["components"]["ollama"] = {
                    "status": "online",
                    "url": OLLAMA_HOST,
                    "models_count": len(models),
                    "default_ready": DEFAULT_TEXT_MODEL in models
                }
            else:
                report["components"]["ollama"] = {"status": "error", "code": r.status_code}
                report["issues"].append(f"Ollama returned HTTP {r.status_code}")
        except Exception as e:
            report["components"]["ollama"] = {"status": "offline", "error": str(e)}
            report["issues"].append("Ollama server offline or unreachable on port 11434")

        # 2. Disk Space (F: Drive)
        try:
            total, used, free = shutil.disk_usage("F:/")
            free_gb = round(free / (1024**3), 1)
            report["components"]["storage_f"] = {
                "status": "ok" if free_gb > 15 else "warning",
                "free_gb": free_gb,
                "total_gb": round(total / (1024**3), 1)
            }
            if free_gb < 15:
                report["issues"].append(f"Low storage on F: drive ({free_gb} GB remaining)")
        except Exception as e:
            report["components"]["storage_f"] = {"status": "error", "error": str(e)}

        # 3. Dual GPU Partitioning & VRAM Watchdog
        try:
            v_status = vram_manager.get_status()
            gpu0_pct = v_status.get("gpu0_vram_pct", 0)
            dual_status = "warning" if gpu0_pct >= 90 else "ok"
            report["components"]["dual_gpu"] = {
                "status": dual_status,
                "partition": vram_manager.get_dual_gpu_partition(),
                "vram_status": v_status
            }
            if gpu0_pct >= 90:
                report["issues"].append(f"High GPU0 VRAM pressure: {gpu0_pct}%")
        except Exception as e:
            report["components"]["dual_gpu"] = {"status": "warning", "error": str(e)}

        # 4. GPU1 Arbiter
        try:
            from shared.gpu1_arbiter import gpu1_arbiter
            arb_status = gpu1_arbiter.status()
            report["components"]["gpu1_arbiter"] = {
                "status": "ok",
                "is_locked": arb_status.get("locked", False),
                "current_task": arb_status.get("current_task")
            }
        except Exception as e:
            report["components"]["gpu1_arbiter"] = {"status": "warning", "error": str(e)}

        # 5. ComfyUI Render Bridge
        try:
            from pipeline.stages.comfyui_bridge import comfy_bridge
            c_conn = comfy_bridge.check_connection()
            is_c_online = bool(c_conn.get("online"))
            report["components"]["comfyui"] = {
                "status": "ok" if is_c_online else "offline",
                "host": c_conn.get("host"),
                "response_time_ms": c_conn.get("response_time_ms")
            }
            if not is_c_online:
                report["issues"].append("ComfyUI render server is offline or unreachable")
        except Exception as e:
            report["components"]["comfyui"] = {"status": "offline", "error": str(e)}
            report["issues"].append(f"ComfyUI check error: {e}")

        # 6. Herald Scheduler
        try:
            from pipeline.stages.herald_scheduler import herald_scheduler
            s_state = herald_scheduler.get_daily_schedule_state()
            report["components"]["herald_scheduler"] = {
                "status": "ok",
                "slots_count": len(herald_scheduler.DAILY_SLOTS),
                "state_date": s_state.get("date")
            }
        except Exception as e:
            report["components"]["herald_scheduler"] = {"status": "warning", "error": str(e)}

        # 7. Order Radar / IMAP Config
        try:
            radar_cfg_path = BASE_DIR / "config" / "order_radar_config.json"
            if radar_cfg_path.exists():
                rcfg = safe_read_json(radar_cfg_path, default={})
                has_email = bool(rcfg.get("imap_user"))
                has_pwd = bool(rcfg.get("app_password"))
                report["components"]["order_radar"] = {
                    "status": "ok" if (has_email and has_pwd) else "unconfigured",
                    "email_set": has_email,
                    "password_set": has_pwd
                }
            else:
                report["components"]["order_radar"] = {"status": "unconfigured"}
        except Exception as e:
            report["components"]["order_radar"] = {"status": "error", "error": str(e)}

        # 8. Social Media Credentials
        try:
            cfg_data = safe_read_json(CONFIG_FILE, default={})
            m_channels = cfg_data.get("marketing_channels", {})
            t_configured = any(
                m_channels.get(brand, {}).get("twitter", {}).get("consumer_key")
                for brand in m_channels
            )
            p_configured = any(
                m_channels.get(brand, {}).get("pinterest", {}).get("access_token")
                for brand in m_channels
            )
            report["components"]["social_credentials"] = {
                "status": "ok" if (t_configured or p_configured) else "unconfigured",
                "twitter_configured": t_configured,
                "pinterest_configured": p_configured
            }
        except Exception as e:
            report["components"]["social_credentials"] = {"status": "error", "error": str(e)}

        # 9. FFmpeg Availability
        try:
            ffmpeg_path = shutil.which("ffmpeg")
            report["components"]["ffmpeg"] = {
                "status": "ok" if ffmpeg_path else "missing",
                "path": ffmpeg_path
            }
            if not ffmpeg_path:
                report["issues"].append("ffmpeg not found on system PATH")
        except Exception as e:
            report["components"]["ffmpeg"] = {"status": "error", "error": str(e)}

        # 10. Newsletter DB
        try:
            if SUBSCRIBERS_FILE.exists():
                sdata = safe_read_json(SUBSCRIBERS_FILE, default={})
                active_count = len(sdata.get("subscribers", []))
                report["components"]["subscribers_db"] = {
                    "status": "ok",
                    "subscribers_count": active_count,
                    "last_updated": sdata.get("updated_at")
                }
            else:
                report["components"]["subscribers_db"] = {"status": "warning", "message": "File not found"}
        except json.JSONDecodeError as jde:
            report["components"]["subscribers_db"] = {"status": "corrupted", "error": str(jde)}
            report["issues"].append("newsletter_subscribers.json contains invalid JSON syntax")
        except Exception as e:
            report["components"]["subscribers_db"] = {"status": "error", "error": str(e)}

        # 11. Overall status determination
        if any(c.get("status") in ("offline", "corrupted", "error") for c in report["components"].values()):
            report["overall_status"] = "error"
        elif report["issues"]:
            report["overall_status"] = "warning"

        return report

    def fix_vram_overflow(self) -> Dict[str, Any]:
        """Purge GPU memory cache across both GPUs and trigger garbage collection."""
        try:
            purge_res = vram_manager.purge_vram(reason="synapse_healer_request")
            return {
                "status": "ok",
                "message": f"Dual RTX 3060 VRAM purge complete. Unloaded models: {purge_res.get('unloaded_models') or 'None (already clean)'}.",
                "details": purge_res
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to purge VRAM: {e}"}

    def repair_subscribers_db(self) -> Dict[str, Any]:
        """Validate and repair corrupted subscriber database."""
        try:
            if not SUBSCRIBERS_FILE.exists():
                init_data = {"subscribers": [], "updated_at": datetime.datetime.now().isoformat()}
                with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
                    json.dump(init_data, f, indent=2)
                return {"status": "ok", "message": "Created fresh subscribers database."}

            try:
                with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict) or "subscribers" not in data:
                    data = {"subscribers": [], "updated_at": datetime.datetime.now().isoformat()}
                    with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)
                    return {"status": "ok", "message": "Repaired schema structure of subscribers database."}
                return {"status": "ok", "message": "Subscriber database validated intact. Zero corruption found."}
            except json.JSONDecodeError:
                backup_corrupt = WORKSPACE_DIR / f"subscribers_corrupted_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                shutil.copy2(SUBSCRIBERS_FILE, backup_corrupt)
                init_data = {"subscribers": [], "updated_at": datetime.datetime.now().isoformat()}
                with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
                    json.dump(init_data, f, indent=2)
                return {"status": "ok", "message": f"Corrupted file backed up to {backup_corrupt.name} and replaced with clean structure."}
        except Exception as e:
            return {"status": "error", "message": f"Repair failed: {e}"}

    def run_tool_and_log(self, tool_call: Dict[str, Any], adult_allowed: bool = False, batch_dir: Optional[Path] = None, attached_files: Optional[List[str]] = None) -> Dict[str, Any]:
        """Executes a SYNAPSE tool call and transparently records any failure to the
        persistent error log, so tool errors stay reviewable even after their chat
        bubble scrolls out of view. This wraps every execute_internal_tool() call site
        instead of patching each tool's individual except block."""
        try:
            exec_res = self.execute_internal_tool(tool_call, adult_allowed=adult_allowed, batch_dir=batch_dir, attached_files=attached_files)
        except TypeError:
            exec_res = self.execute_internal_tool(tool_call, adult_allowed=adult_allowed, batch_dir=batch_dir)
        if isinstance(exec_res, dict) and exec_res.get("status") == "error":
            self.log_error(
                component=exec_res.get("tool") or tool_call.get("tool", "unknown_tool"),
                error_message=str(exec_res.get("error", "Unknown tool execution error")),
                context={"tool_call": tool_call}
            )
        return exec_res

    @staticmethod
    def _resolve_marketing_source_image(
        filename: str,
        batch_dir: Optional[Path] = None,
        attached_files: Optional[List[str]] = None
    ) -> Path:
        """Resolves a filename or image reference for tools that produce postable
        or animated content (image-to-video, background swap, subject swap, 3D PBR).

        If attached_files or batch_dir are provided (from an active user upload turn),
        this intelligently resolves to the user's uploaded photo — including when the
        caller passes placeholders like "...", "this", or a bare filename.
        If neither attached_files nor batch_dir are provided, this strictly resolves
        against brand_assets/comfy_renders (or explicit absolute paths) to ensure client
        inbox files are never implicitly picked up by name collision alone."""
        fn_clean = (filename or "").strip()
        is_placeholder = not fn_clean or fn_clean in (
            "...", "this", "this image", "attached", "uploaded", "user image", "input", "source"
        )

        # 1. If placeholder or empty, fall back directly to attached files or batch_dir
        if is_placeholder:
            if attached_files:
                for af in attached_files:
                    p = Path(af)
                    if p.exists() and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".bmp"):
                        return p
            if batch_dir and Path(batch_dir).exists():
                batch_imgs = [
                    p for p in Path(batch_dir).iterdir()
                    if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".bmp")
                ]
                if batch_imgs:
                    return max(batch_imgs, key=lambda f: f.stat().st_mtime)
            return Path("F:/WORKHORSE/workspace/brand_assets/comfy_renders") / (fn_clean or "missing.png")

        # 2. If explicit absolute path exists
        p = Path(fn_clean)
        if p.is_absolute():
            return p

        # 3. Match against attached_files (by exact name or stem)
        if attached_files:
            for af in attached_files:
                ap = Path(af)
                if ap.name.lower() == p.name.lower() or ap.stem.lower() == p.stem.lower():
                    if ap.exists():
                        return ap

        # 4. Match against batch_dir
        if batch_dir and Path(batch_dir).exists():
            direct_batch = Path(batch_dir) / p.name
            if direct_batch.exists():
                return direct_batch
            for bf in Path(batch_dir).iterdir():
                if bf.is_file() and (bf.name.lower() == p.name.lower() or bf.stem.lower() == p.stem.lower()):
                    return bf

        # 5. Match against brand_assets folders
        candidate_dirs = [
            Path("F:/WORKHORSE/workspace/brand_assets/comfy_renders"),
            Path("F:/WORKHORSE/workspace/brand_assets/creator_media_lab"),
            Path("F:/WORKHORSE/workspace/brand_assets/creator_pulse_lab"),
        ]
        for cdir in candidate_dirs:
            candidate = cdir / p.name
            if candidate.exists():
                return candidate

        # 6. Fallback if not found on disk but user provided an attached file this turn
        if attached_files:
            for af in attached_files:
                ap = Path(af)
                if ap.exists() and ap.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".bmp"):
                    return ap

        # 7. Default brand_assets fallback
        return Path("F:/WORKHORSE/workspace/brand_assets/comfy_renders") / p.name

    @staticmethod
    def _attach_media(result: Dict[str, Any], file_path, title: str = "") -> Dict[str, Any]:
        """Attaches a result['media'] entry (type/download-url/filename) for any
        content-producing tool, so the dashboard chat UI can render it as a viewable/
        downloadable card directly in the conversation instead of only reporting a
        filesystem path in text - addresses 'all things asked for in chat should come
        to the chat where it can be viewed and or downloaded'. Silently no-ops if the
        file doesn't exist or isn't under one of the registered output directories
        (shared/output_categories.py), so this never raises on an unexpected path."""
        try:
            if not file_path:
                return result
            fp = Path(file_path)
            if not fp.exists():
                return result
            from shared.output_categories import build_media_entry
            entry = build_media_entry(fp, title=title)
            if entry:
                result.setdefault("media", []).append(entry)
        except Exception as e:
            print(f"[SYNAPSE] Non-fatal: failed to attach media entry for {file_path}: {e}")
        return result

    def execute_internal_tool(self, tool_call, adult_allowed: bool = False, batch_dir: Optional[Path] = None, attached_files: Optional[List[str]] = None):
        """Execute built-in WORKHORSE actions & self-healing functions.

        batch_dir: the isolated client_inbox/batch_<...>/ subfolder for THIS upload
        session, if one exists (per-request context - never cached on self, since
        ai_operator is a shared singleton across concurrent chat sessions). Client-
        file tools (aura_retouch, apex_package) scope to this folder instead of the
        flat client_inbox/ root so one Commander's/client's files are never mixed
        with another's."""
        tool_name = tool_call.get("tool")
        # Normalize tool aliases so Synapse variants map reliably to registered tools
        TOOL_ALIASES = {
            "comfy_generate_video": "comfy_image_to_video",
            "image_to_video": "comfy_image_to_video",
            "comfy_i2v": "comfy_image_to_video",
            "comfy_generate_image": "comfy_generate",
            "generate_image": "comfy_generate",
        }
        tool_name = TOOL_ALIASES.get(tool_name, tool_name)
        result = {"status": "ok", "tool": tool_name}

        # SELF-HEALING & HARDWARE DIAGNOSTICS
        if tool_name == "system_diagnostics":
            diag = self.run_system_diagnostics()
            result["diagnostics"] = diag
            result["message"] = f"SYNAPSE Diagnostics: System is {diag['overall_status'].upper()}. Issues: {len(diag['issues'])}."
            return result

        elif tool_name == "fix_vram_overflow":
            return self.fix_vram_overflow()

        elif tool_name == "incident_log":
            incidents = self.get_recent_incidents(limit=10)
            result["incidents"] = incidents
            result["message"] = f"SYNAPSE: {len(incidents)} recent self-healing incident(s) on record." if incidents else "SYNAPSE: No incidents logged - system has been running clean."
            return result

        elif tool_name == "comfy_generate_glb":
            agent = tool_call.get("agent", "synapse")
            prompt = tool_call.get("prompt")
            try:
                from pipeline.stages.comfyui_bridge import comfy_bridge
                g_res = comfy_bridge.generate_glb_character(agent_name=agent, prompt=prompt)
                result["message"] = f"SYNAPSE [100 Fm]: 3D GLB Model for {agent.capitalize()} generated: {g_res.get('status') or g_res.get('error')}."
                result["details"] = g_res
                return result
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)
                return result

        elif tool_name == "comfy_remote_purge":
            try:
                from pipeline.stages.comfyui_bridge import comfy_bridge
                purge_res = comfy_bridge.remote_purge_vram()
                result["message"] = f"SYNAPSE [100 Fm]: Remote VRAM Purge on RTX 5070 Ti: {purge_res.get('message', purge_res.get('error'))}"
                result["details"] = purge_res
                return result
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)
                return result

        elif tool_name == "comfy_prewarm":
            ckpt = tool_call.get("checkpoint")
            try:
                from pipeline.stages.comfyui_bridge import comfy_bridge
                pw_res = comfy_bridge.prewarm_model(checkpoint=ckpt)
                result["message"] = f"SYNAPSE [100 Fm]: Prewarm trigger on RTX 5070 Ti: {pw_res.get('message', pw_res.get('error'))}"
                result["details"] = pw_res
                return result
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)
                return result

        elif tool_name == "prune_staging_buffer":
            try:
                from shared.vram_manager import vram_manager
                p_res = vram_manager.prune_old_staging_files(max_age_hours=48)
                result["message"] = f"SYNAPSE [100 Fm]: Storage Pruning complete. Removed {p_res['deleted_count']} files ({p_res['deleted_mb']} MB freed) on Drive F."
                result["details"] = p_res
                return result
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)
                return result

        elif tool_name == "scrub_file_metadata":
            target_f = tool_call.get("file", "")
            try:
                from pipeline.stages.scrubber import metadata_scrubber
                scrub_res = metadata_scrubber.scrub_image(target_f)
                result["message"] = f"SCRUBBER [82 Pb]: {scrub_res.get('privacy_status', scrub_res.get('error'))}"
                result["details"] = scrub_res
                return result
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)
                return result

        elif tool_name == "notify_commander":
            message = tool_call.get("message", "")
            try:
                alert_res = self.notify_commander(message)
                result["message"] = f"SYNAPSE [100 Fm]: Commander alert {'sent' if alert_res.get('status') == 'ok' else 'attempted'} - {alert_res.get('status')}."
                result["details"] = alert_res
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        elif tool_name == "gpu_guardrails_status":
            try:
                import subprocess
                from shared.vram_manager import vram_manager
                smi_out = subprocess.run(
                    ["nvidia-smi", "--query-gpu=index,name,memory.used,memory.free,utilization.gpu", "--format=csv,noheader"],
                    capture_output=True, text=True, timeout=3
                )
                gpu_lines = [l.strip() for l in smi_out.stdout.strip().splitlines()] if smi_out.returncode == 0 else []
                v_stat = vram_manager.get_status()
                result["message"] = (
                    f"SYNAPSE Hardware Monitor: Dual RTX 3060 Guardrails Active. "
                    f"GPU 0: {gpu_lines[0] if len(gpu_lines) > 0 else 'Online'} | "
                    f"GPU 1: {gpu_lines[1] if len(gpu_lines) > 1 else 'Online'}. "
                    f"Circuit breaker armed (>45s auto-trip), 180-token cap enforced, 25s socket timeout active."
                )
                result["gpus"] = gpu_lines
                result["vram_status"] = v_stat
                return result
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)
                return result

        elif tool_name == "block_swap_model":
            target = tool_call.get("target_model", DEFAULT_TEXT_MODEL)
            swap_res = vram_manager.prepare_for_model(target)
            result["message"] = f"SYNAPSE [100 Fm]: Block swap complete on GPU 0. Ready for '{target}'. Evicted: {swap_res.get('evicted_models', [])}."
            result["details"] = swap_res
            return result

        elif tool_name == "hardware_allocation":
            partition = vram_manager.get_dual_gpu_partition()
            result["message"] = "SYNAPSE [100 Fm]: Dual RTX 3060 hardware allocation active. GPU 0 = Ollama/Synapse (12GB), GPU 1 = Echo/Forge (12GB isolated)."
            result["partition"] = partition
            return result

        elif tool_name == "repair_subscribers":
            return self.repair_subscribers_db()

        elif tool_name == "generate_tip_menu":
            try:
                from pipeline.stages.cam_template_generator import CamTemplateGenerator
                cam_gen = CamTemplateGenerator()
                avatar_url = tool_call.get("avatar_url")
                banner_url = tool_call.get("banner_url")
                top_tipper = tool_call.get("top_tipper")
                schedule = tool_call.get("schedule")
                items = tool_call.get("items")

                missing = cam_gen.validate_tip_menu_inputs(
                    avatar_url=avatar_url, banner_url=banner_url,
                    top_tipper=top_tipper, schedule=schedule, items=items
                )
                if missing:
                    result["status"] = "needs_info"
                    result["missing"] = missing
                    result["message"] = (
                        "SYNAPSE [100 Fm]: Can't finalize this tip menu yet - still need from the Commander: "
                        + "; ".join(missing)
                    )
                    return result

                html = cam_gen.generate_tip_menu_standalone(
                    title=tool_call.get("title", "Interactive Tip Menu"),
                    subtitle=tool_call.get("subtitle", ""),
                    theme=tool_call.get("theme", "neon_cyber"),
                    layout_style=tool_call.get("layout_style", "vip_showcase"),
                    items=items,
                    goal_text=tool_call.get("goal_text", ""),
                    avatar_url=avatar_url,
                    banner_url=banner_url,
                    top_tipper=top_tipper,
                    schedule=schedule
                )
                bundle_res = cam_gen.bundle_tip_menu_product(
                    bundle_name=f"TIP_MENU_{tool_call.get('theme', 'neon_cyber').upper()}_PACK",
                    theme=tool_call.get("theme", "neon_cyber"),
                    items=items
                )
                result["message"] = f"SYNAPSE [100 Fm]: Tip menu generated and bundled into {bundle_res.get('zip_name')}."
                result["details"] = bundle_res
                return result
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)
                return result

        # NEWSLETTER ACTIONS
        elif tool_name == "newsletter_add":
            email = tool_call.get("email", "").strip()
            pub = tool_call.get("publication", "creator_pulse")
            send_welcome = tool_call.get("send_welcome", True)

            if not email or "@" not in email:
                return {"status": "error", "error": "Invalid email address"}

            try:
                from pipeline.stages.newsletter_manager import NewsletterManager
                nm = NewsletterManager()
                add_res = nm.subscribe_multi(email=email, publications=[pub], name="", send_welcome=send_welcome)
                if add_res.get("success"):
                    result["message"] = f"SYNAPSE [100 Fm]: Successfully registered {email} to {pub}."
                else:
                    result["status"] = "error"
                    result["message"] = f"SYNAPSE [100 Fm]: Registration failed: {add_res.get('error')}"
                result["details"] = add_res
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        elif tool_name == "newsletter_remove":
            email = tool_call.get("email", "").strip()
            pub = tool_call.get("publication", "creator_pulse")
            try:
                from pipeline.stages.newsletter_manager import NewsletterManager
                nm = NewsletterManager()
                unsub_res = nm.unsubscribe(email=email, publication=pub)
                result["message"] = f"SYNAPSE [100 Fm]: {unsub_res.get('message', 'Unsubscribed')}"
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        elif tool_name == "newsletter_stats":
            try:
                if SUBSCRIBERS_FILE.exists():
                    with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
                        sub_data = json.load(f)
                    subs = sub_data.get("subscribers", [])
                    active_count = sum(1 for s in subs if s.get("status") == "active")
                    result["total_active"] = active_count
                    result["message"] = f"Active mailing list subscribers: {active_count} verified subscribers across 4 publications."
                else:
                    result["message"] = "No subscriber file found."
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        elif tool_name == "aura_retouch":
            files = tool_call.get("files", [])
            # "edit_style" (glamour/natural/concert_stage/family_event) is the preferred,
            # full-profile interface - it drives the color preset, smoothing strength,
            # which professional retouch passes run, and the watermark convention all
            # at once. Falls back to the raw "style" preset name for one-off custom
            # combinations, defaulting to "natural" (previously this default silently
            # fell through to NO color grade at all, since "natural" was never actually
            # a registered preset name - edit_style fixes that for real now).
            edit_style = tool_call.get("edit_style")
            style = tool_call.get("style")
            if not edit_style and not style:
                edit_style = "natural"
            try:
                resolved_paths = []
                for fn in files:
                    p = Path(fn)
                    if not p.is_absolute():
                        # Prefer this upload session's isolated batch folder so a bare
                        # filename can never accidentally resolve to a different
                        # client's/session's file of the same name sitting in the flat
                        # client_inbox/ root.
                        candidates = []
                        if batch_dir:
                            candidates.append(batch_dir / fn)
                        candidates.append(CLIENT_INBOX_DIR / fn)
                        p = next((c for c in candidates if c.exists()), candidates[-1])
                    if p.exists():
                        resolved_paths.append(p)
                if not resolved_paths and not files:
                    # No specific files named - default to everything the Commander just
                    # dropped in THIS upload batch, never the entire shared inbox, so a
                    # different client's/session's leftover files can't get swept in.
                    if batch_dir and batch_dir.exists():
                        resolved_paths = [f for f in batch_dir.iterdir() if f.is_file()]
                    if not resolved_paths:
                        # Legacy fallback for files sitting directly in the flat root
                        # (pre-dating batching) - iterdir() naturally skips batch_*
                        # subfolders here since is_file() excludes directories.
                        resolved_paths = [f for f in CLIENT_INBOX_DIR.iterdir() if f.is_file()]
                if not resolved_paths:
                    # Make this diagnosable at a glance instead of a bare "not found" -
                    # this exact gap (requested filenames that don't match what's
                    # actually in the batch, e.g. a client's photos uploaded as a single
                    # .zip) previously failed silently with no indication of what was
                    # actually available to retouch.
                    available = []
                    if batch_dir and batch_dir.exists():
                        available = sorted(f.name for f in batch_dir.iterdir() if f.is_file())
                    result["status"] = "error"
                    result["error"] = (
                        f"No matching source photo(s) found to retouch. Requested: "
                        f"{files or '(none specified - defaulted to the whole batch)'}. "
                        f"Actually in this upload batch: {available or '(empty)'}."
                    )
                    return result

                from pipeline.stages.photo_retoucher import PhotoRetoucher
                retoucher = PhotoRetoucher()
                retouch_res = retoucher.process_photo_batch(
                    image_paths=resolved_paths,
                    shoot_name=tool_call.get("shoot_name", "operator_shoot"),
                    preset=style or "natural_true_to_life",
                    smooth_strength=float(tool_call.get("smooth_strength", 0.5)),
                    watermark_text=tool_call.get("watermark_text", "@ExclusiveDrop"),
                    source_batch=batch_dir.name if batch_dir else None,
                    edit_style=edit_style
                )
                style_label = edit_style or style
                if retouch_res.get("status") != "completed":
                    # Zero photos actually got retouched (e.g. a .zip/non-image file was
                    # passed in) - never report this as a finished edit.
                    result["status"] = "error"
                    result["error"] = retouch_res.get("error", "Retouching failed - zero photos were processed.")
                    result["details"] = retouch_res
                else:
                    result["message"] = f"Aura [79 Au]: '{style_label}' edit complete for {len(resolved_paths)} image(s) - skin retouch, color grade, social crops, and a print-ready 16-bit master. Bundle: {retouch_res.get('zip_name')}."
                    result["details"] = retouch_res
                    self._attach_media(result, retouch_res.get("zip_file"), title=f"{style_label} retouch bundle")
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        elif tool_name == "create_banner":
            client = tool_call.get("client_name", "Creator")
            headline = tool_call.get("headline", "VIP Lounge")
            style = tool_call.get("style", "neon_pink")
            platform = tool_call.get("platform", "onlyfans")
            try:
                import cv2
                import numpy as np

                style_prompts = {
                    "neon_cyber": "cyberpunk neon cityscape backdrop, electric blue and magenta neon glow, futuristic holographic atmosphere, glossy reflective surfaces",
                    "velvet_boudoir": "luxury velvet boudoir backdrop, warm gold and deep red tones, intimate candlelit glow, soft silk drapery",
                    "pastel_dream": "dreamy pastel gradient backdrop, soft pink and lavender neon glow, ethereal glamour atmosphere, soft bokeh lighting",
                    "gothic_noir": "gothic noir backdrop, dark moody crimson and black tones, dramatic chiaroscuro lighting, elegant dark romance atmosphere",
                    "emerald_luxe": "opulent emerald green and gold backdrop, luxury jewel-toned atmosphere, glowing ambient light, high-end editorial glamour",
                    "neon_pink": "vibrant neon pink and magenta glow backdrop, glossy futuristic atmosphere, glamorous nightclub lighting",
                    "corporate_clean": "clean modern corporate backdrop, soft blue and white gradient, minimal geometric line accents, professional studio lighting, crisp SaaS/brand aesthetic",
                    "vibrant_lifestyle": "bright energetic lifestyle backdrop, warm orange and gold gradient, sunlit outdoor atmosphere, upbeat influencer/creator vibe",
                    "minimalist_editorial": "minimalist editorial backdrop, soft neutral cream and grey tones, high-fashion magazine negative space, subtle studio shadow",
                    "tech_futuristic": "sleek dark tech backdrop, cyan and indigo gradient glow, futuristic circuit-light atmosphere, clean gaming/tech studio aesthetic"
                }
                style_desc = style_prompts.get(style, style_prompts["neon_cyber"])
                prompt = (
                    f"Premium wide panoramic {platform.upper()} profile header banner background, {style_desc}, "
                    f"professional graphic design composition, cinematic lighting, high production value, ultra high resolution, "
                    f"balanced negative space for text overlay, no text, no watermark, no logos"
                )
                negative_prompt = "text, watermark, logo, signature, blurry, low quality, deformed, extra limbs, amateur, grainy"

                from pipeline.stages.comfyui_bridge import comfy_bridge
                gen_res = comfy_bridge.generate_and_audit(
                    positive_prompt=prompt,
                    negative_prompt=negative_prompt,
                    width=1600,
                    height=512,
                    style_preset="graphic_design",
                    auto_qc=True
                )
                if not gen_res.get("success"):
                    result["status"] = "warning"
                    result["message"] = f"SYNAPSE [100 Fm]: Banner background render failed: {gen_res.get('error')}"
                    result["details"] = gen_res
                    return result

                # Composite the finished banner: render + headline/client text burned in
                banner_dir = WORKSPACE_DIR / "brand_assets" / "banners"
                banner_dir.mkdir(parents=True, exist_ok=True)
                img = cv2.imread(gen_res["file_path"])
                h, w = img.shape[:2]

                font = cv2.FONT_HERSHEY_DUPLEX
                headline_scale = max(1.2, w / 650.0)
                headline_thickness = max(2, int(headline_scale * 2))
                head_size = cv2.getTextSize(headline, font, headline_scale, headline_thickness)[0]
                hx, hy = (w - head_size[0]) // 2, int(h * 0.45)
                cv2.putText(img, headline, (hx + 3, hy + 3), font, headline_scale, (0, 0, 0), headline_thickness + 3, cv2.LINE_AA)
                cv2.putText(img, headline, (hx, hy), font, headline_scale, (255, 255, 255), headline_thickness, cv2.LINE_AA)

                sub_scale = headline_scale * 0.4
                sub_thickness = max(1, int(sub_scale * 2))
                sub_text = f"@{client}" if not client.startswith("@") else client
                sub_size = cv2.getTextSize(sub_text, font, sub_scale, sub_thickness)[0]
                sx, sy = (w - sub_size[0]) // 2, hy + int(head_size[1] * 1.8)
                cv2.putText(img, sub_text, (sx + 2, sy + 2), font, sub_scale, (0, 0, 0), sub_thickness + 2, cv2.LINE_AA)
                cv2.putText(img, sub_text, (sx, sy), font, sub_scale, (255, 255, 255), sub_thickness, cv2.LINE_AA)

                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                banner_name = f"{platform}_{client}_banner_{timestamp}.png"
                banner_path = banner_dir / banner_name
                cv2.imwrite(str(banner_path), img)

                qc_audit = gen_res.get("qc_audit", {})
                result["file_path"] = str(banner_path)
                result["background_render"] = gen_res.get("file_path")
                result["qc_audit"] = qc_audit
                self._attach_media(result, banner_path, title=f"{client} {platform.upper()} banner")
                if qc_audit.get("passed"):
                    result["message"] = f"SYNAPSE [100 Fm]: Finished {platform.upper()} banner generated & QC-approved by Iris [77 Ir] for {client}: {banner_name}."
                else:
                    result["status"] = "warning"
                    result["message"] = f"SYNAPSE [100 Fm]: Finished {platform.upper()} banner generated for {client} but Iris [77 Ir] QC was inconclusive/failed after max retries - recommend manual review: {banner_name}."
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        elif tool_name == "generate_shoot_concepts":
            concepts = tool_call.get("concepts", [])
            if not concepts:
                result["status"] = "error"
                result["error"] = "No shoot concepts provided - each concept needs a 'title' and a ready-to-render 'prompt'."
                return result
            try:
                from pipeline.stages.comfyui_bridge import comfy_bridge
                generated = []
                for c in concepts[:4]:  # cap at 4 per call to bound render time
                    title = str(c.get("title", "Concept")).strip() or "Concept"
                    prompt = str(c.get("prompt", "")).strip()
                    if not prompt:
                        continue
                    gen_res = comfy_bridge.generate_and_audit(
                        positive_prompt=prompt,
                        negative_prompt="low quality, deformed, extra limbs, fused fingers, blurry, watermark, text, logo, amateur, bad anatomy, cartoon",
                        checkpoint="cyberrealisticXL_v80.safetensors",
                        width=832,
                        height=1216,
                        steps=25,
                        cfg=6.5,
                        auto_qc=True
                    )
                    if gen_res.get("success"):
                        generated.append({"title": title, "image_url": gen_res.get("url_path"), "prompt": prompt})
                    else:
                        generated.append({"title": title, "error": gen_res.get("error"), "prompt": prompt})
                result["images"] = generated
                ok_count = len([g for g in generated if g.get("image_url")])
                result["message"] = f"SYNAPSE [100 Fm]: Rendered {ok_count}/{len(generated)} shoot concept preview(s) on RTX 5070 Ti, Iris [77 Ir] QC-gated."
                if ok_count == 0:
                    result["status"] = "warning"
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        elif tool_name == "scan_inspiration_vault":
            image_filename = tool_call.get("image")
            try:
                from pipeline.stages.inspiration_scanner import inspiration_scanner
                scan_res = inspiration_scanner.scan_and_analyze(image_filename=image_filename)
                if scan_res.get("status") == "empty":
                    result["status"] = "warning"
                    result["message"] = f"SYNAPSE [100 Fm]: {scan_res.get('message')}"
                else:
                    result["message"] = f"SYNAPSE [100 Fm]: Analyzed {len(scan_res.get('images_scanned', []))} inspiration image(s) ({scan_res.get('total_images_in_vault')} total in vault). Blueprint below."
                    result["blueprint"] = scan_res.get("blueprint_markdown")
                result["details"] = scan_res
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        elif tool_name == "apex_package":
            client = tool_call.get("client_name", "Client")
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            pkg_name = f"Delivery_{client}_{timestamp}.zip"
            pkg_path = CLIENT_OUTPUTS_DIR / pkg_name
            try:
                # Prefer Aura's actual retouched/color-corrected output for this exact
                # upload batch over the raw client upload - previously apex_package only
                # ever looked at the raw inbox folder, so it could package (and report as
                # "done") an entirely un-edited client job even after aura_retouch had
                # run, or even after aura_retouch had failed outright.
                retouched_zip, retouch_manifest = _find_retouched_package_for_batch(batch_dir)

                # Package only THIS upload batch's files, never the entire shared
                # client_inbox/ root, so one client's package can never pick up another
                # client's (or an unrelated earlier/later) files that merely happen to
                # be sitting in the same flat folder.
                deliverable_files = []
                if batch_dir and batch_dir.exists():
                    deliverable_files = [f for f in batch_dir.iterdir() if f.is_file()]
                    if client and client != "Client":
                        tag_client_batch(batch_dir, client)
                if not deliverable_files and not retouched_zip:
                    # Legacy fallback for files sitting directly in the flat root
                    # (pre-dating batching) - batch_* subfolders are skipped here since
                    # iterdir()+is_file() excludes directories.
                    deliverable_files = [f for f in CLIENT_INBOX_DIR.iterdir() if f.is_file()]
                if not deliverable_files and not retouched_zip:
                    result["status"] = "error"
                    result["error"] = "No deliverable files found in the client inbox to package"
                    return result

                with zipfile.ZipFile(pkg_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    if retouched_zip:
                        with zipfile.ZipFile(retouched_zip) as src:
                            for info in src.infolist():
                                zipf.writestr(info, src.read(info.filename))
                    else:
                        for f in deliverable_files:
                            zipf.write(f, arcname=f.name)

                if retouched_zip:
                    style_label = retouch_manifest.get("edit_style") or retouch_manifest.get("preset")
                    photo_count = len(retouch_manifest.get("source_filenames", []))
                    result["message"] = (
                        f"Apex [78 Pt]: Master delivery archive generated with Aura's "
                        f"'{style_label}' edit already applied: {pkg_name} ({photo_count} photo(s))."
                    )
                    result["files"] = retouch_manifest.get("source_filenames", [])
                    result["edited"] = True
                else:
                    # No matching retouched output exists for this batch - this is a raw,
                    # un-edited passthrough. Say so explicitly instead of letting this look
                    # like a finished, color-corrected deliverable.
                    result["status"] = "warning"
                    result["message"] = (
                        f"⚠️ Apex [78 Pt]: Packaged {len(deliverable_files)} file(s) AS-IS - "
                        f"no retouched/edited output was found for this upload batch. If "
                        f"these photos need color correction or retouching, run aura_retouch "
                        f"on them FIRST, then re-run apex_package."
                    )
                    result["files"] = [f.name for f in deliverable_files]
                    result["edited"] = False
                result["download_path"] = str(pkg_path)
                self._attach_media(result, pkg_path, title=f"{client} delivery archive")
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        # REAL-TIME MARKET INTELLIGENCE & LINK INGESTION
        elif tool_name == "trend_radar_sweep":
            try:
                from pipeline.stages.trend_researcher import trend_researcher
                vault = trend_researcher.run_daily_radar_sweep()
                synth = vault.get("daily_synthesis", {})
                themes = synth.get("top_themes_today", [])
                result["message"] = f"SYNAPSE [100 Fm]: Daily Radar Sweep completed. Top themes: {', '.join(themes[:3])}."
                result["vault"] = vault
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        elif tool_name == "ingest_link":
            url = tool_call.get("url", "").strip()
            notes = tool_call.get("notes", "")
            if not url:
                return {"status": "error", "error": "No URL provided"}
            try:
                from pipeline.stages.trend_researcher import trend_researcher
                ingest_res = trend_researcher.ingest_user_link(url, user_notes=notes)
                result["message"] = f"SYNAPSE [100 Fm]: Web link ingested & synthesized: {ingest_res.get('title')} ({url})."
                result["details"] = ingest_res
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        elif tool_name == "get_daily_trends":
            try:
                from pipeline.stages.trend_researcher import trend_researcher
                vault = trend_researcher.load_vault()
                result["message"] = f"SYNAPSE [100 Fm]: Daily trend vault retrieved ({vault.get('today_date')})."
                result["vault"] = vault
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        # COMFYUI GENERATION & IRIS [77 Ir] VISION QUALITY GATE
        elif tool_name == "comfy_status":
            try:
                from pipeline.stages.comfyui_bridge import comfy_bridge
                status = comfy_bridge.check_connection()
                if status.get("online"):
                    result["message"] = f"SYNAPSE [100 Fm]: ComfyUI is ONLINE on Main PC ({status.get('host')}:{status.get('port')}). GPU: {status.get('gpu')} ({status.get('vram_total_gb')} GB VRAM)."
                else:
                    result["message"] = f"SYNAPSE [100 Fm]: ComfyUI on Main PC is currently OFFLINE ({status.get('host')}:{status.get('port')}). {status.get('hint')}"
                result["details"] = status
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        elif tool_name == "comfy_search_models":
            query = tool_call.get("query", "").strip()
            category = tool_call.get("category", "all")
            try:
                from pipeline.stages.comfyui_bridge import comfy_bridge
                search_res = comfy_bridge.search_inventory(query=query, category=category)
                result["message"] = f"SYNAPSE [100 Fm]: Found {search_res['matched_checkpoints_count']} checkpoints and {search_res['matched_loras_count']} LoRAs matching '{query}'."
                result["matches"] = search_res
                return result
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)
                return result

        elif tool_name == "comfy_background_change":
            filename = tool_call.get("image", "").strip()
            new_background_prompt = tool_call.get("prompt", "").strip()
            negative_prompt = tool_call.get("negative_prompt", "")
            checkpoint = tool_call.get("checkpoint")
            try:
                if batch_dir or attached_files:
                    img_path = self._resolve_marketing_source_image(filename, batch_dir=batch_dir, attached_files=attached_files)
                else:
                    img_path = self._resolve_marketing_source_image(filename)
                if not img_path or not img_path.exists():
                    return {"status": "error", "tool": tool_name, "error": f"Source image not found: {filename or '(no image provided)'}"}
                if not new_background_prompt:
                    return {"status": "error", "error": "No new-background prompt provided"}
                if not img_path.exists():
                    return {"status": "error", "error": f"Source image not found: {filename}"}

                from pipeline.stages.comfyui_bridge import comfy_bridge
                bg_res = comfy_bridge.generate_background_change(
                    source_image_path=img_path,
                    new_background_prompt=new_background_prompt,
                    negative_prompt=negative_prompt,
                    checkpoint=checkpoint
                )
                if bg_res.get("success"):
                    result["message"] = f"SYNAPSE [100 Fm]: Background swapped on RTX 5070 Ti. Saved to: {bg_res.get('filename')}."
                    result["details"] = bg_res
                    self._attach_media(result, bg_res.get("file_path"), title="Background change render")
                else:
                    result["status"] = "warning"
                    result["message"] = f"SYNAPSE [100 Fm]: Background change failed: {bg_res.get('error')}"
                    result["details"] = bg_res
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        elif tool_name == "comfy_subject_swap":
            filename = tool_call.get("image", "").strip()
            ref_filename = tool_call.get("reference_face_image", "").strip()
            prompt = tool_call.get("prompt", "").strip()
            negative_prompt = tool_call.get("negative_prompt") or None
            try:
                if batch_dir or attached_files:
                    img_path = self._resolve_marketing_source_image(filename, batch_dir=batch_dir, attached_files=attached_files)
                    ref_path = self._resolve_marketing_source_image(ref_filename, batch_dir=batch_dir, attached_files=attached_files)
                else:
                    img_path = self._resolve_marketing_source_image(filename)
                    ref_path = self._resolve_marketing_source_image(ref_filename)
                if not img_path or not img_path.exists():
                    return {"status": "error", "tool": tool_name, "error": f"Source image not found: {filename or '(no image provided)'}"}
                if not ref_path or not ref_path.exists():
                    return {"status": "error", "error": f"Reference face image not found: {ref_filename or '(no reference face image provided)'}"}
                if not prompt:
                    return {"status": "error", "error": "No scene/identity prompt provided for subject swap"}
                if not img_path.exists():
                    return {"status": "error", "error": f"Source image not found: {filename}"}
                if not ref_path.exists():
                    return {"status": "error", "error": f"Reference face image not found: {ref_filename}"}

                from pipeline.stages.comfyui_bridge import comfy_bridge
                swap_res = comfy_bridge.generate_subject_swap(
                    source_image_path=img_path,
                    reference_face_image_path=ref_path,
                    prompt=prompt,
                    negative_prompt=negative_prompt
                )
                if swap_res.get("success"):
                    result["message"] = f"SYNAPSE [100 Fm]: Full-subject swap rendered on RTX 5070 Ti. Saved to: {swap_res.get('filename')}."
                    result["details"] = swap_res
                    self._attach_media(result, swap_res.get("file_path"), title="Subject swap render")
                else:
                    result["status"] = "warning"
                    result["message"] = f"SYNAPSE [100 Fm]: Subject swap failed: {swap_res.get('error')}"
                    result["details"] = swap_res
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        elif tool_name == "comfy_generate":
            prompt = tool_call.get("prompt", "").strip()
            negative_prompt = tool_call.get("negative_prompt", "")
            # Only the Commander can authorize NSFW content:
            # When adult_allowed is False, enforce strict non-nude negative prompts.
            if not adult_allowed:
                safe_anti_nude = "nude, nudity, naked, topless, bare breasts, exposed nipples, genitals, explicit, nsfw, porn, sexual, uncensored, erotica"
                negative_prompt = f"{negative_prompt}, {safe_anti_nude}" if negative_prompt else safe_anti_nude
            width = tool_call.get("width", 1024)
            height = tool_call.get("height", 1024)
            style = tool_call.get("style", "photorealism")
            checkpoint = tool_call.get("checkpoint")
            loras = tool_call.get("loras")
            lora_name = tool_call.get("lora_name")
            lora_strength = tool_call.get("lora_strength", 0.8)
            steps = tool_call.get("steps", 25)
            cfg = tool_call.get("cfg", 7.0)
            if not prompt:
                return {"status": "error", "error": "No prompt provided for ComfyUI"}

            try:
                from pipeline.stages.comfyui_bridge import comfy_bridge
                gen_res = comfy_bridge.generate_and_audit(
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
                    auto_qc=True
                )
                if gen_res.get("success"):
                    audit = gen_res.get("qc_audit", {})
                    score = audit.get("aesthetic_score", "N/A")
                    notes = audit.get("defects_summary", "Passed")
                    if audit.get("passed"):
                        result["message"] = f"SYNAPSE [100 Fm]: Image rendered on RTX 5070 Ti & APPROVED by Iris [77 Ir] (QC Score: {score}/10). Saved to: {gen_res.get('filename')}."
                    else:
                        result["status"] = "warning"
                        result["message"] = f"SYNAPSE [100 Fm]: Image rendered on RTX 5070 Ti but NOT approved by Iris [77 Ir] after max retries (QC Score: {score}/10, Notes: {notes}). Saved for manual review only: {gen_res.get('filename')}."
                    result["details"] = gen_res
                    self._attach_media(result, gen_res.get("file_path"), title="Generated image")
                else:
                    result["status"] = "warning"
                    result["message"] = f"SYNAPSE [100 Fm]: ComfyUI generation attempt failed: {gen_res.get('error') or gen_res.get('warning')}"
                    result["details"] = gen_res
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        elif tool_name == "comfy_image_to_video":
            filename = tool_call.get("image", "").strip()
            prompt = tool_call.get("prompt", "").strip()
            negative_prompt = tool_call.get("negative_prompt") or None
            if not adult_allowed:
                safe_anti_nude = "nude, nudity, naked, topless, bare breasts, exposed nipples, genitals, explicit, nsfw, porn, sexual, uncensored, erotica"
                negative_prompt = f"{negative_prompt}, {safe_anti_nude}" if negative_prompt else safe_anti_nude
            width = tool_call.get("width", 720)
            height = tool_call.get("height", 1280)
            num_frames = tool_call.get("num_frames", 300)
            fps = tool_call.get("fps", 30)
            engine = (tool_call.get("engine") or "ltx2.3").strip().lower()
            try:
                if batch_dir or attached_files:
                    img_path = self._resolve_marketing_source_image(filename, batch_dir=batch_dir, attached_files=attached_files)
                else:
                    img_path = self._resolve_marketing_source_image(filename)
                if not img_path or not img_path.exists():
                    return {"status": "error", "tool": tool_name, "error": f"Source image not found: {filename or '(no image provided)'}"}
                if not prompt:
                    return {"status": "error", "tool": tool_name, "error": "No motion/scene prompt provided for image-to-video"}

                from pipeline.stages.comfyui_bridge import comfy_bridge
                if engine in ("minimax", "minimax_h3", "minimax-h3", "hailuo"):
                    duration_seconds = tool_call.get("duration_seconds", 10.0)
                    # The MiniMax H3 template ships with 3 adult/boudoir-tuned LoRAs loaded by
                    # default. Honoring adult_tuning requires BOTH the model requesting it AND
                    # the Commander having actually authorized adult content this turn (either
                    # the Adult Content Mode toggle is on, or their own message explicitly asked
                    # for it) - adult_allowed is computed/enforced upstream in chat(), not by
                    # trusting the LLM's tool-call JSON alone.
                    requested_adult_tuning = bool(tool_call.get("adult_tuning", False))
                    adult_tuning = requested_adult_tuning and adult_allowed
                    if requested_adult_tuning and not adult_allowed:
                        print("[SYNAPSE] Adult-tuned video requested but not authorized this turn (no toggle/explicit prompt) - downgrading to general-brand-safe LoRA config.")
                    vid_res = comfy_bridge.generate_image_to_video_minimax(
                        source_image_path=img_path,
                        prompt=prompt,
                        duration_seconds=duration_seconds,
                        lora_config=None if adult_tuning else []
                    )
                    engine_label = "MiniMax H3" + (" (adult-tuned)" if adult_tuning else "")
                    if requested_adult_tuning and not adult_tuning:
                        engine_label += " - adult tuning blocked, not authorized this turn"
                else:
                    vid_res = comfy_bridge.generate_image_to_video(
                        source_image_path=img_path,
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        width=width,
                        height=height,
                        num_frames=num_frames,
                        fps=fps
                    )
                    engine_label = "LTX 2.3"

                if vid_res.get("success"):
                    result["message"] = f"SYNAPSE [100 Fm]: Image-to-video render complete on RTX 5070 Ti ({engine_label}). Saved to: {vid_res.get('filename')}."
                    result["details"] = vid_res
                    result["video"] = vid_res.get("file_path")
                    self._attach_media(result, vid_res.get("file_path"), title=f"{engine_label} video")
                else:
                    result["status"] = "warning"
                    result["message"] = f"SYNAPSE [100 Fm]: Image-to-video render failed ({engine_label}): {vid_res.get('error')}"
                    result["details"] = vid_res
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        elif tool_name == "comfy_generate_3d_pbr":
            filename = tool_call.get("image", "").strip()
            try:
                if batch_dir or attached_files:
                    img_path = self._resolve_marketing_source_image(filename, batch_dir=batch_dir, attached_files=attached_files)
                else:
                    img_path = self._resolve_marketing_source_image(filename)
                if not img_path or not img_path.exists():
                    return {"status": "error", "tool": tool_name, "error": f"Source image not found: {filename or '(no image provided)'}"}
                if not img_path.exists():
                    return {"status": "error", "error": f"Source image not found: {filename}"}

                from pipeline.stages.comfyui_bridge import comfy_bridge
                pbr_res = comfy_bridge.generate_image_to_3d_pbr(
                    source_image_path=img_path,
                    output_name=tool_call.get("output_name"),
                    texture_resolution=int(tool_call.get("texture_resolution", 4096)),
                    use_trellis2=bool(tool_call.get("use_trellis2", True))
                )
                if pbr_res.get("success"):
                    result["message"] = f"SYNAPSE [100 Fm]: Full-PBR 3D model generated on RTX 5070 Ti (baked base color/metallic/roughness/normal/AO maps). Saved to: {pbr_res.get('glb_path')}."
                    result["details"] = pbr_res
                    self._attach_media(result, pbr_res.get("glb_path"), title="3D PBR model")
                else:
                    result["status"] = "warning"
                    result["message"] = f"SYNAPSE [100 Fm]: 3D PBR generation failed: {pbr_res.get('error')}"
                    result["details"] = pbr_res
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        elif tool_name == "comfy_generate_client_character":
            character_name = tool_call.get("character_name", "").strip()
            prompt = tool_call.get("prompt")
            if not character_name:
                return {"status": "error", "error": "No character_name provided (available: charlette, margo, melissa)"}
            try:
                from pipeline.stages.comfyui_bridge import comfy_bridge
                # adult_allowed is computed upstream in chat() from the Commander's actual
                # Adult Content Mode toggle or an explicit request in his own message -
                # never trusted from this tool call's JSON alone. These are licensed
                # client identity LoRAs for the Commander's own testing only.
                char_res = comfy_bridge.generate_client_character_image(
                    character_name=character_name,
                    prompt=prompt,
                    adult_allowed=adult_allowed
                )
                if char_res.get("success"):
                    result["message"] = f"SYNAPSE [100 Fm]: Client character render complete for '{character_name}' on RTX 5070 Ti. Saved to: {char_res.get('image_path')}. Tagged CLIENT_CHARACTER_ASSET - this is a client-specific test asset, never postable/marketing content."
                    result["details"] = char_res
                    self._attach_media(result, char_res.get("image_path"), title=f"Client character: {character_name}")
                else:
                    result["status"] = "warning"
                    result["message"] = f"SYNAPSE [100 Fm]: Client character generation failed: {char_res.get('error')}"
                    result["details"] = char_res
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        elif tool_name == "iris_qc_audit":
            filename = tool_call.get("file", "")
            if not filename:
                return {"status": "error", "error": "No image file provided for Iris QC audit"}
            try:
                from pipeline.stages.comfyui_bridge import comfy_bridge
                img_path = Path(filename)
                if not img_path.is_absolute():
                    img_path = Path("F:/WORKHORSE/workspace/client_inbox") / filename
                    if not img_path.exists():
                        img_path = Path("F:/WORKHORSE/workspace/brand_assets/comfy_renders") / filename
                if not img_path.exists():
                    return {"status": "error", "error": f"Image file not found: {filename}"}

                audit = comfy_bridge.run_iris_qc_audit(img_path)
                result["message"] = f"IRIS [77 Ir] Forensic QC Audit: {'APPROVED' if audit.get('passed') else 'REJECTED'}. Score: {audit.get('aesthetic_score')}/10. Extra Limbs: {audit.get('extra_limbs_detected')}. Notes: {audit.get('defects_summary')}."
                result["audit"] = audit
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        elif tool_name == "check_daily_schedule":
            try:
                from pipeline.stages.herald_scheduler import herald_scheduler
                sched_status = herald_scheduler.get_status()
                result["message"] = f"SYNAPSE [100 Fm]: Daily Schedule Status: Date {sched_status.get('date')} | Slots executed: {sched_status.get('executed_slots_count')}/{sched_status.get('total_slots')} | Newsletters sent today: {sched_status.get('newsletters_sent_today')}."
                result["details"] = sched_status
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        elif tool_name == "herald_dispatch_now":
            slot_id = tool_call.get("slot_id", "all")
            try:
                from pipeline.stages.herald_scheduler import herald_scheduler
                if slot_id == "all" or slot_id == "newsletters":
                    disp_res = herald_scheduler.dispatch_today_all_now()
                else:
                    disp_res = herald_scheduler.dispatch_slot(slot_id)
                result["message"] = f"SYNAPSE [100 Fm]: Triggered immediate Herald dispatch for '{slot_id}'!"
                result["details"] = disp_res
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        elif tool_name == "radar_scan_now":
            try:
                from pipeline.stages.order_radar import order_radar
                scan_res = order_radar.check_inbox()
                result["message"] = f"SYNAPSE [100 Fm]: Radar scanned digitalcreatorassets@gmail.com! Status: {scan_res.get('status')}. Active orders: {len(order_radar.orders)}."
                result["details"] = scan_res
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        elif tool_name == "webhook_fulfillment_status":
            try:
                from pipeline.stages.order_radar import order_radar
                web_orders = [o for o in order_radar.orders if o.get("platform") in ("stripe", "gumroad")][:10]
                result["message"] = f"SYNAPSE [100 Fm]: {len(web_orders)} recent Stripe/Gumroad auto-fulfilled order(s) on record." if web_orders else "SYNAPSE [100 Fm]: No Stripe/Gumroad webhook orders yet - check that stripe_webhook_secret/gumroad_seller_id are configured."
                result["orders"] = web_orders
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        elif tool_name == "content_engine_run_now":
            try:
                from pipeline.stages.herald_scheduler import herald_scheduler
                ce_res = herald_scheduler.dispatch_content_engine()
                if ce_res.get("success"):
                    result["message"] = f"SYNAPSE [100 Fm]: Content engine cycle complete. Output staged at {ce_res.get('output_dir')} - awaiting Commander's manual review before posting."
                else:
                    result["status"] = "warning"
                    result["message"] = f"SYNAPSE [100 Fm]: Content engine cycle failed at stage '{ce_res.get('stage')}': {ce_res.get('error')}"
                result["details"] = ce_res
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        elif tool_name == "content_engine_status":
            try:
                from pipeline.stages.content_engine import content_engine
                last = content_engine.get_last_result()
                result["message"] = f"SYNAPSE [100 Fm]: Last content engine cycle: {'SUCCESS' if last.get('success') else 'FAILED/NONE YET'}."
                result["details"] = last
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)
        else:
            result["status"] = "error"
            result["error"] = f"Unknown tool: {tool_name}"

        return result

    def _encode_image_file(self, path: Path, max_dim: int = 1280) -> Optional[str]:
        """Loads and encodes an image to base64, resizing if needed for VRAM efficiency."""
        try:
            from PIL import Image
            import io
            with Image.open(path) as img:
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                if max(img.size) > max_dim:
                    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=88)
                return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            try:
                with open(path, "rb") as f:
                    return base64.b64encode(f.read()).decode("utf-8")
            except Exception as e:
                print(f"[SYNAPSE Vision] Failed to read {path}: {e}")
                return None

    def detect_vision_requirement(self, message: str, attached_files: Optional[List[str]] = None, batch_dir: Optional[Path] = None) -> Tuple[bool, str, List[str], Optional[str]]:
        """
        Comprehensive Auto-Detection Engine for Synapse Vision:
        Detects if a query requires Vision (Qwen-VL on GPU 0) based on:
        1. Explicitly attached or uploaded files
        2. Local image file paths or filenames in the message text
        3. Image URLs in the message text
        4. Recent client inbox images when user asks visual questions
        5. Semantic visual intent keywords (inspect, analyze photo, OCR, etc.)

        batch_dir: this request's isolated upload-batch folder (if any), checked ahead
        of the flat client_inbox/ root so "the image I just sent" can't resolve to a
        different client's/session's file of the same name.
        """
        detected_images = []
        reasons = []

        # 1. Check attached files
        if attached_files:
            for fpath in attached_files:
                p = Path(fpath)
                if p.exists() and p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".gif"]:
                    b64 = self._encode_image_file(p)
                    if b64:
                        detected_images.append(b64)
                        reasons.append(f"Attached image: {p.name}")

        # 2. Check for image paths in the message text
        import re
        path_patterns = [
            r"[a-zA-Z]:[/\\][^:*?\"<>|\r\n\s]+?\.(?:jpg|jpeg|png|webp|bmp|gif)",
            r"[\w\-./\\]+?\.(?:jpg|jpeg|png|webp|bmp|gif)"
        ]
        for pat in path_patterns:
            matches = re.findall(pat, message, re.IGNORECASE)
            for m in matches:
                clean_path = m.strip(" '\"`(),:;")
                candidates = []
                if batch_dir:
                    candidates.append(batch_dir / Path(clean_path).name)
                candidates += [
                    Path(clean_path),
                    CLIENT_INBOX_DIR / Path(clean_path).name,
                    Path("F:/WORKHORSE") / clean_path,
                    Path("F:/WORKHORSE/workspace") / clean_path,
                    Path("F:/WORKHORSE/dashboard/static/img") / Path(clean_path).name,
                    Path("F:/WORKHORSE/dashboard/static/img/characters_3d") / Path(clean_path).name
                ]
                for cand in candidates:
                    if cand.is_file():
                        b64 = self._encode_image_file(cand)
                        if b64 and b64 not in detected_images:
                            detected_images.append(b64)
                            reasons.append(f"Detected file path in text: {cand.name}")
                            break

        # 3. Check for image URLs in the message text
        url_pattern = r'https?://[^\s]+?\.(?:jpg|jpeg|png|webp|bmp|gif)(?:\?[^\s]*)?'
        url_matches = re.findall(url_pattern, message, re.IGNORECASE)
        for u in url_matches:
            try:
                import urllib.request
                req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (WORKHORSE/1.0)'})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    raw_data = resp.read()
                    if raw_data:
                        b64 = base64.b64encode(raw_data).decode("utf-8")
                        detected_images.append(b64)
                        reasons.append(f"Fetched image URL: {u[:40]}...")
            except Exception as e:
                print(f"[SYNAPSE Vision] Failed to fetch URL {u}: {e}")

        # 4. Check for Semantic Visual Intent Keywords
        vision_keywords = [
            "look at this", "look at the", "inspect this", "inspect the",
            "analyze this", "analyze the photo", "analyze the image",
            "examine this", "examine the", "what is in this", "what's in this",
            "what do you see", "in this image", "in this picture", "in this photo",
            "in the screenshot", "read the text", "ocr", "transcribe image",
            "critique this", "critique photo", "lighting analysis", "pose review",
            "vision model", "qwen-vl", "iris check", "iris inspect", "visual check",
            "evaluate photo", "image quality", "see the image", "check the picture",
            "change to vision", "switch to vision", "use vision", "vision mode",
            "check this image", "check this photo", "rate this photo"
        ]
        msg_lower = message.lower()
        matched_intent = [kw for kw in vision_keywords if kw in msg_lower]
        if matched_intent:
            reasons.append(f"Visual intent: '{matched_intent[0]}'")

            # If visual intent is present but no image was found yet, check THIS
            # upload batch first (so "look at this" always means the image from the
            # Commander's current session, never a different client's leftover file),
            # then fall back to the flat inbox root for legacy/un-batched files.
            if not detected_images:
                inbox_images = []
                if batch_dir and batch_dir.exists():
                    inbox_images = [
                        f for f in batch_dir.iterdir()
                        if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]
                    ]
                if not inbox_images and CLIENT_INBOX_DIR.exists():
                    inbox_images = [
                        f for f in CLIENT_INBOX_DIR.iterdir()
                        if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]
                    ]
                if inbox_images:
                    latest_img = max(inbox_images, key=lambda f: f.stat().st_mtime)
                    b64 = self._encode_image_file(latest_img)
                    if b64:
                        detected_images.append(b64)
                        reasons.append(f"Auto-loaded latest inbox image: {latest_img.name}")

        # Check if the query is an image-transformation tool action (animation/video/3D/retouch)
        # rather than visual analysis, inspection, or critique.
        tool_action_keywords = [
            "motion", "video", "animate", "animating", "animation", "make it move", "make this move",
            "give this motion", "add motion", "i2v", "image to video", "image-to-video",
            "retouch", "skin tone", "3d", "glb", "pbr", "convert to 3d", "upscale", "crop", "package"
        ]
        has_tool_action = any(kw in msg_lower for kw in tool_action_keywords)
        has_inspection_intent = len(matched_intent) > 0

        # Only activate Vision model when:
        # 1. User has explicit visual inspection / critique intent (critique, analyze, inspect, ocr, etc.), OR
        # 2. An image is attached/detected AND the user did NOT ask for a tool action
        if has_tool_action and not has_inspection_intent:
            is_vision = False
            detected_images = []
            reasons.append("Tool-action intent detected (animation/edit); retained 14B operator model with disk metadata")
        else:
            is_vision = len(detected_images) > 0 or len(matched_intent) > 0

        resolved_model = None
        if is_vision:
            configured_vm = None
            try:
                if CONFIG_FILE.exists():
                    cfg_data = safe_read_json(CONFIG_FILE, default={})
                    configured_vm = (
                        cfg_data.get("agents", {}).get("iris", {}).get("vision_model")
                        or cfg_data.get("agents", {}).get("synapse", {}).get("vision_model")
                    )
            except Exception:
                pass

            available = self.get_available_models()
            vl_candidates = [m for m in available if "vl" in m.lower()]

            if configured_vm and configured_vm in available:
                resolved_model = configured_vm
            elif configured_vm and any(configured_vm.lower() in m.lower() for m in available):
                resolved_model = next(m for m in available if configured_vm.lower() in m.lower())
            elif vl_candidates:
                resolved_model = vl_candidates[0]
            elif configured_vm:
                resolved_model = configured_vm
            else:
                resolved_model = DEFAULT_VISION_MODEL

        return is_vision, "; ".join(reasons) if reasons else "No vision signals", detected_images, resolved_model

    def get_live_task_status_context(self) -> str:
        """
        Dynamically probes real-time status of all WORKHORSE scheduled operations,
        including Herald newsletters, daily Twitter slots, Order Radar, and ComfyUI.
        """
        now = datetime.datetime.now()
        current_time_str = now.strftime("%H:%M")
        today_str = now.strftime("%Y-%m-%d")
        
        herald_info = "Standby"
        executed_slots = []
        newsletters_sent = False
        last_log = ""
        try:
            state_file = Path("F:/WORKHORSE/workspace/daily_schedule_state.json")
            if state_file.exists():
                s_data = json.load(open(state_file, encoding="utf-8"))
                executed_slots = s_data.get("executed_slots", [])
                newsletters_sent = s_data.get("newsletters_sent_today", False)
                herald_info = f"Executed slots today: {executed_slots} | Newsletters sent today: {newsletters_sent}"
            
            log_file = Path("F:/WORKHORSE/workspace/newsletter_logs/latest_run.log")
            if log_file.exists():
                lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
                last_log = " | ".join(lines[-4:]) if lines else "Empty log"
        except Exception as e:
            herald_info = f"Error reading state: {e}"

        radar_info = "Unknown"
        try:
            from pipeline.stages.order_radar import order_radar
            r_cfg = order_radar.config
            radar_info = f"Monitored inbox: {r_cfg.get('email')} | Auto-check: {r_cfg.get('auto_check')} | Total active orders: {len(order_radar.orders)}"
        except Exception as e:
            radar_info = f"Error: {e}"

        comfy_info = "Offline"
        try:
            from pipeline.stages.comfyui_bridge import comfy_bridge
            c_stat = comfy_bridge.check_connection()
            if c_stat.get("online"):
                comfy_info = f"ONLINE at {c_stat.get('host')}:{c_stat.get('port')} (RTX 5070 Ti 16GB, SageAttention active)"
            else:
                comfy_info = f"OFFLINE ({c_stat.get('error')})"
        except Exception as e:
            comfy_info = f"Error: {e}"

        lines = [
            "--- LIVE WORKHORSE REAL-TIME SCHEDULE & AGENT STATUS ---",
            f"Current Date: {today_str} | Current Time: {current_time_str}",
            "1. HERALD [33 As] (Newsletters & Scheduled Twitter Slots):",
            f"   - Status: {herald_info}",
            "   - Daily Twitter Slots: 09:00 (Slot 1), 13:00 (Slot 2), 17:00 (Slot 3), 20:30 (Slot 4), 23:00 (Slot 5)",
            "   - Visual Media Auto-Attachment: Enabled (attaches latest 5070 Ti verified visual to root tweets)",
            f"   - Recent Run Log Tail: {last_log}",
            "2. RADAR [47 Ag] (Client Order Radar):",
            f"   - {radar_info}",
            "3. IRIS [77 Ir] (Vision QC Gate):",
            "   - Armed on GPU 0 (Qwen-VL). Audits 5-finger hands, pupil symmetry, and texture.",
            "   - Safeguards: Strict 180-token limit (3-5s evaluation) + 25s hard socket timeout.",
            "4. COMFYUI 5070 Ti NODE:",
            f"   - Status: {comfy_info}",
            "5. DUAL RTX 3060 HARDWARE GUARDRAILS & CIRCUIT BREAKER:",
            "   - Circuit Breaker: ACTIVE (>45s @ >80% utilization auto-trips, force-clearing Ollama compute)",
            "   - Singleton Lock: ACTIVE (.comfy_bridge.lock prevents multi-process collisions)",
            "   - Architecture: GPU 0 (LLM/Vision) | GPU 1 (Echo Whisper & Forge NVENC isolated)",
            "--- END LIVE AGENT STATUS ---",
            "CRITICAL: When the Commander asks why a task ran or didn't run, check the Live Status above. If newsletters failed or didn't run, state the exact reason from the log and offer to run 'herald_dispatch_now'. NEVER confuse Herald [33 As] with outside newspapers!"
        ]
        return "\n".join(lines)

    def _detect_explicit_adult_request(self, message: str) -> bool:
        """Returns True if the Commander's OWN message (not the model's tool-call JSON)
        explicitly asks for adult/NSFW content, so the adult-tuned MiniMax H3 engine can
        be authorized for that one turn even with the Adult Content Mode toggle off."""
        if not message:
            return False
        msg_lower = message.lower()
        explicit_markers = [
            "nsfw", "adult content", "adult video", "boudoir", "nude", "naked",
            "explicit", "xxx", "erotic", "lingerie", "fetish", "minimax", "hailuo",
            "onlyfans", "fansly", "cam girl", "camgirl"
        ]
        return any(marker in msg_lower for marker in explicit_markers)

    def chat(self, message: str, model=None, web_search=False, attached_files=None, session_id: Optional[str] = None, adult_mode: bool = False):
        chosen_model = model or DEFAULT_TEXT_MODEL
        # Adult-tuned video generation (MiniMax H3's boudoir LoRAs) is only ever authorized
        # for this turn if the Commander flipped on Adult Content Mode, or their own message
        # explicitly asked for it - never just because the model's tool-call JSON says so.
        adult_allowed = bool(adult_mode) or self._detect_explicit_adult_request(message)

        # This request's isolated upload batch, if any files were attached this turn
        # (server.py saves uploads into a fresh client_inbox/batch_.../ subfolder per
        # drop) - otherwise fall back to this SAME session's most recent batch, so
        # client-file tools (aura_retouch, apex_package) never need to scan the whole
        # shared inbox and can't cross-contaminate a different client's/session's files.
        # Computed per-call, never cached on self - ai_operator is a shared singleton
        # across concurrent chat sessions.
        batch_dir = None
        if attached_files:
            first_parent = Path(attached_files[0]).parent
            if first_parent.name.startswith("batch_"):
                batch_dir = first_parent
        if batch_dir is None:
            batch_dir = get_latest_client_batch_dir(session_id)

        # Comprehensive Auto-Detection for Vision Mode
        is_vision, reason, detected_images, resolved_vl_model = self.detect_vision_requirement(
            message=message,
            attached_files=attached_files,
            batch_dir=batch_dir
        )
        
        if is_vision:
            chosen_model = resolved_vl_model or DEFAULT_VISION_MODEL
            images_base64 = detected_images
            print(f"[SYNAPSE Auto-Vision] Auto-switched to Vision ({chosen_model})! Signals: {reason}")
        else:
            images_base64 = []

        # Dynamic Pre-Flight Block Swap on GPU 0 before sending request to Ollama
        vram_manager.prepare_for_model(chosen_model)

        # Auto-Detection for Trend/Current-Ideas Intent: when the Commander asks for
        # "trendy"/"current"/"viral"/"popular right now" shoot ideas, force a real web
        # search instead of requiring the manual web-search toggle - mirrors the vision
        # auto-detection above so trend-grounded ideation just works without extra clicks.
        auto_search_reason = None
        if not web_search:
            trend_keywords = [
                "trendy", "trending", "what's popular", "whats popular", "what's hot",
                "whats hot", "viral", "current trend", "in style right now",
                "popular right now", "what's working right now", "latest trend",
                "right now trends", "hot right now", "what's in right now"
            ]
            msg_lower_check = message.lower()
            if any(kw in msg_lower_check for kw in trend_keywords):
                web_search = True
                auto_search_reason = "Detected trend/current-ideas intent"
                print(f"[SYNAPSE Auto-Search] Auto-enabled web search! Signal: '{message[:80]}'")

        web_context_str = ""
        web_sources = []
        web_search_status = None
        if web_search:
            web_sources = self.search_web(message, max_results=4)
            web_search_status = getattr(self, "last_search_status", "ok")
            if web_sources:
                web_context_str = "\n\n--- REAL-TIME WEB SEARCH RESULTS ---\n"
                for idx, src in enumerate(web_sources, 1):
                    web_context_str += f"[{idx}] {src['title']}\nURL: {src['url']}\nSnippet: {src['snippet']}\n\n"
                web_context_str += "--- END SEARCH RESULTS ---\nUse the real-time facts above to answer accurately.\n"
            elif web_search_status == "error":
                # Tell the model explicitly that search failed rather than
                # silently proceeding as if no search had been requested -
                # prevents it from confidently answering from stale training
                # data while implying it checked current sources.
                web_context_str = (
                    "\n\n--- REAL-TIME WEB SEARCH UNAVAILABLE ---\n"
                    f"The live web search backend failed/was blocked ({getattr(self, 'last_search_error', 'unknown error')}). "
                    "Tell the user live web search is temporarily unavailable before answering from existing knowledge.\n"
                )

        # Autonomous URL Ingestion: Detect dropped articles/links
        extracted_urls = re.findall(r'https?://[^\s<>"]+', message)
        article_urls = [
            u for u in extracted_urls 
            if not any(u.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"])
        ]
        
        ingested_link_context = ""
        link_ingestion_results = []
        if article_urls:
            from pipeline.stages.trend_researcher import trend_researcher
            for u in article_urls[:2]:
                print(f"[SYNAPSE Link Ingestion] User dropped URL: {u}. Auto-scraping & synthesizing...")
                ingest_res = trend_researcher.ingest_user_link(u, user_notes=message)
                if ingest_res.get("success"):
                    link_ingestion_results.append(ingest_res)
                    rec = ingest_res.get("ingest_record", {})
                    synth = rec.get("synthesis", {})
                    ingested_link_context += f"\n\n--- INGESTED USER LINK ANALYSIS: {rec.get('title')} ---\n"
                    ingested_link_context += f"URL: {u}\n"
                    ingested_link_context += f"Summary: {synth.get('summary', '')}\n"
                    ingested_link_context += "Key Takeaways:\n" + "\n".join([f"- {t}" for t in synth.get("takeaways", [])]) + "\n"
                    ingested_link_context += "@TheCreatorAsset Thread Draft:\n" + "\n".join(synth.get("tweet_thread_creator_asset", [])) + "\n"
                    ingested_link_context += "@creatorpulselab Thread Draft:\n" + "\n".join(synth.get("tweet_thread_creator_pulse", [])) + "\n"
                    ingested_link_context += f"Newsletter Feature Blurb:\n{synth.get('newsletter_blurb', '')}\n"
                    ingested_link_context += "--- END INGESTED LINK ANALYSIS ---\n"

        # Check for Trend Radar Sweep Intent
        msg_lower = message.lower()
        if any(kw in msg_lower for kw in ["scan trends", "daily search", "radar sweep", "update ideas", "research topics", "update tweets"]):
            try:
                from pipeline.stages.trend_researcher import trend_researcher
                print("[SYNAPSE Radar Intent] Triggering autonomous daily radar sweep...")
                trend_researcher.run_daily_radar_sweep()
            except Exception as e:
                print(f"[SYNAPSE Radar Intent] Sweep error: {e}")

        # Dynamic Daily Trend & Topic Vault Priming
        trend_context_str = ""
        try:
            from pipeline.stages.trend_researcher import trend_researcher
            trend_context_str = "\n\n" + trend_researcher.get_daily_summary_prompt_context() + "\n"
        except Exception:
            pass

        # Dynamic ComfyUI Inventory Priming (RTX 5070 Ti on Main PC)
        comfy_context_str = ""
        try:
            from pipeline.stages.comfyui_bridge import comfy_bridge
            comfy_context_str = "\n\n" + comfy_bridge.get_prompt_context_summary() + "\n"
        except Exception:
            pass

        live_task_context = self.get_live_task_status_context()
        system_content = SYSTEM_PROMPT + "\n\n" + live_task_context
        system_content += "\n\n" + get_comfyui_context("operator", message)
        if trend_context_str:
            system_content += trend_context_str
        if comfy_context_str:
            system_content += comfy_context_str

        # Self-healing awareness: let Synapse proactively mention recent auto-detected
        # issues/fixes instead of only reporting them when asked via system_diagnostics.
        recent_incidents = self.get_recent_incidents(limit=5)
        if recent_incidents:
            incident_context_str = "\n\n--- RECENT SELF-HEALING INCIDENT LOG (newest first) ---\n"
            for inc in recent_incidents:
                incident_context_str += f"[{inc['timestamp']}] {inc['component']}: {inc['issue']} -> {inc['action_taken']} ({inc['status']})\n"
            incident_context_str += "--- END INCIDENT LOG ---\nIf any entry is 'needs_attention', proactively flag it to the Commander.\n"
            system_content += incident_context_str
        if ingested_link_context:
            system_content += ingested_link_context
        if web_context_str:
            system_content += web_context_str

        messages_payload = [{"role": "system", "content": system_content}]

        session_history = self.get_history(session_id)
        for h in session_history[-6:]:
            clean_msg = {"role": h.get("role", "user"), "content": h.get("content", "")}
            if "images" in h:
                clean_msg["images"] = h["images"]
            messages_payload.append(clean_msg)

        user_msg = {"role": "user", "content": message}
        if images_base64:
            user_msg["images"] = images_base64

        attached_notes = []
        if images_base64:
            attached_notes.append(f"[System Note: {len(images_base64)} client image(s) attached for visual inspection.]")

        if attached_files:
            file_details = []
            for af in attached_files:
                af_path = Path(af)
                if af_path.exists():
                    file_details.append(f"- Filename: '{af_path.name}', Full path: '{af_path.as_posix()}'")
            if file_details:
                attached_notes.append(
                    "[USER ATTACHED MEDIA AVAILABLE ON DISK]:\n"
                    + "\n".join(file_details)
                    + "\nCRITICAL: When the user asks to animate, transform, retouch, or convert an uploaded image, pass the exact uploaded image filename or path in the 'image' or 'files' parameter (e.g. 'image': '"
                    + Path(attached_files[0]).name
                    + "'). Never invent a new image or pass placeholder '...'."
                )

        if attached_notes:
            user_msg["content"] += "\n\n" + "\n\n".join(attached_notes)

        messages_payload.append(user_msg)

        payload = {
            "model": chosen_model,
            "messages": messages_payload,
            "stream": False,
            "keep_alive": "5m",
            "options": {
                "temperature": 0.7,
                "num_predict": 1500
            }
        }

        # Vision mode (and any turn that just ran a blocking web search before this call) can involve
        # a cold model swap into VRAM on top of normal generation time - give those turns much more room
        # before giving up, instead of the flat 120s that was tripping on cold vision loads.
        ollama_timeout = 240 if is_vision else 180

        try:
            try:
                ollama_res = requests.post(
                    f"{OLLAMA_HOST}/api/chat",
                    json=payload,
                    timeout=ollama_timeout
                )
            except requests.exceptions.Timeout:
                # First window blown through, almost always a cold model load rather than a hang -
                # retry once with a much longer allowance before surfacing a failure to the Commander.
                print(f"[SYNAPSE] Ollama request timed out after {ollama_timeout}s - retrying with extended timeout (model likely still loading into VRAM)...")
                ollama_res = requests.post(
                    f"{OLLAMA_HOST}/api/chat",
                    json=payload,
                    timeout=ollama_timeout + 240
                )

            # Self-healing OOM retry
            if ollama_res.status_code != 200:
                err_text = ollama_res.text.lower()
                if "memory" in err_text or "out of memory" in err_text or ollama_res.status_code == 500:
                    print(f"[SYNAPSE] Memory threshold detected in chat ({ollama_res.status_code}). Purging VRAM & retrying...")
                    vram_manager.purge_vram(reason="chat_emergency_retry")
                    ollama_res = requests.post(f"{OLLAMA_HOST}/api/chat", json=payload, timeout=ollama_timeout)

            if ollama_res.status_code != 200:
                return {
                    "status": "error",
                    "reply": f"Ollama returned HTTP error {ollama_res.status_code}: {ollama_res.text}",
                    "model": chosen_model
                }

            res_json = ollama_res.json()
            reply_text = res_json.get("message", {}, ).get("content", "").strip()

            # Clean accidental chain-of-thought leaks or foreign token artifacts (e.g. 颗, Okay let's see...)
            reply_text = re.sub(r'^[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\s]+', '', reply_text)
            # If the model started with an internal thinking preamble, strip it
            cot_patterns = [
                r"^(?:Okay|Alright|Let's see|Wait),\s*let's\s*(?:see|look|check).*?(?:Commander|Wait,|\n\n)",
                r"^Thinking Process:.*?\n\n"
            ]
            for pat in cot_patterns:
                reply_text = re.sub(pat, '', reply_text, flags=re.IGNORECASE | re.DOTALL).strip()

            executed_actions = []
            executed_tool_signatures = set()

            # Robust tool-call extraction supporting nested objects (loras, items, concepts)
            # across both fenced and inline formats, capturing parse errors instead of dropping them.
            extracted_tools, cleaned_reply, tool_parse_errors = extract_tool_calls(reply_text)
            reply_text = cleaned_reply

            for p_err in tool_parse_errors:
                self.log_error("tool_call_parse_error", p_err.get("error", "malformed_json"), context={"snippet": p_err.get("raw")})

            for tool_data in extracted_tools:
                sig = json.dumps(tool_data, sort_keys=True)
                if sig not in executed_tool_signatures:
                    try:
                        exec_res = self.run_tool_and_log(tool_data, adult_allowed=adult_allowed, batch_dir=batch_dir, attached_files=attached_files)
                    except TypeError:
                        exec_res = self.run_tool_and_log(tool_data, adult_allowed=adult_allowed, batch_dir=batch_dir)
                    executed_actions.append(exec_res)
                    executed_tool_signatures.add(sig)

            # Collapse any blank lines left behind after stripping the tool-call JSON out.
            reply_text = re.sub(r'\n{3,}', '\n\n', reply_text).strip()

            # Second-pass tool feedback: if tools were executed and initial text had no follow-up,
            # feed results back to the LLM so SYNAPSE can formulate its actual response knowing the tool's real result.
            if executed_actions and chosen_model and not reply_text:
                try:
                    tool_feedback_prompt = (
                        "The internal studio tools have finished execution with the following results:\n"
                        + json.dumps(executed_actions, indent=2, default=str)
                        + "\n\nProvide your concise, natural-language response to the Commander summarizing the outcome. "
                        + "Do NOT output raw JSON tool calls in this final answer."
                    )
                    second_pass_messages = list(messages_payload)
                    second_pass_messages.append({"role": "assistant", "content": "Running requested tool..."})
                    second_pass_messages.append({"role": "user", "content": tool_feedback_prompt})

                    second_payload = {
                        "model": chosen_model,
                        "messages": second_pass_messages,
                        "stream": False,
                        "keep_alive": "5m",
                        "options": {"temperature": 0.5, "num_predict": 800}
                    }
                    second_res = requests.post(f"{OLLAMA_HOST}/api/chat", json=second_payload, timeout=60)
                    if second_res.status_code == 200:
                        second_reply = second_res.json().get("message", {}).get("content", "").strip()
                        if second_reply:
                            reply_text = second_reply
                except Exception as e:
                    # Gracefully proceed to fallback narration if second pass is offline/unavailable
                    pass

            # If the model's response is still empty after execution,
            # fall back to a short natural confirmation instead of showing an empty bubble.
            if not reply_text and executed_actions:
                if any(a.get("blueprint") for a in executed_actions):
                    reply_text = "Here's the shoot blueprint you asked for, Commander."
                elif any(a.get("images") for a in executed_actions):
                    reply_text = "Here are the generated concepts, Commander."
                elif any(a.get("media") for a in executed_actions):
                    reply_text = "Here's the finished piece, Commander - view or download it below."
                else:
                    reply_text = "Done, Commander."

            # Structured quick-pick suggestions for clarifying questions (backlog item 3) -
            # lets the frontend render clickable chips instead of forcing free-text guessing.
            quick_options = []
            qopt_blocks = re.findall(r'\{"quick_options":\s*\[.*?\]\s*\}', reply_text, re.DOTALL)
            for block in qopt_blocks:
                try:
                    qdata = json.loads(block)
                    opts = qdata.get("quick_options", [])
                    if isinstance(opts, list):
                        quick_options = [str(o).strip() for o in opts if str(o).strip()][:5]
                except Exception:
                    pass
            if qopt_blocks:
                reply_text = re.sub(r'\{"quick_options":\s*\[.*?\]\s*\}', '', reply_text, flags=re.DOTALL).strip()

            session_history.append({"role": "user", "content": message})
            session_history.append({
                "role": "assistant",
                "content": reply_text,
                "model": chosen_model,
                "actions": executed_actions,
                "web_sources": web_sources,
                "quick_options": quick_options
            })
            self._save_history(session_id)

            return {
                "status": "ok",
                "reply": reply_text,
                "model": chosen_model,
                "web_sources": web_sources,
                "web_search_status": web_search_status,
                "web_search_auto_detected": auto_search_reason is not None,
                "web_search_reason": auto_search_reason,
                "executed_actions": executed_actions,
                "attached_files_count": len(attached_files) if attached_files else 0,
                "vision_auto_detected": is_vision,
                "vision_reason": reason,
                "images_processed": len(images_base64),
                "article_urls_detected": article_urls,
                "link_ingestion_results": link_ingestion_results,
                "quick_options": quick_options
            }

        except requests.exceptions.Timeout:
            self.log_error("ollama_chat", f"Ollama request timed out after retry on {OLLAMA_HOST}", context={"model": chosen_model})
            return {
                "status": "error",
                "reply": f"SYNAPSE [100 Fm]: Ollama on {OLLAMA_HOST} is still loading/warming the model after an extended wait - this usually happens right after a cold start or when switching into Vision mode. Please send your message again now that the weights should be resident in VRAM.",
                "model": chosen_model
            }
        except Exception as e:
            self.log_error("ollama_chat", str(e), context={"model": chosen_model})
            return {
                "status": "error",
                "reply": f"Failed to contact local Ollama on {OLLAMA_HOST}: {e}",
                "model": chosen_model
            }

    def clear_history(self, session_id: Optional[str] = None):
        session_id = session_id or "default"
        self._histories[session_id] = []
        try:
            f_path = self._session_file(session_id)
            if f_path.exists():
                f_path.unlink()
        except Exception as e:
            print(f"[SYNAPSE Chat Memory] Failed to clear session '{session_id}': {e}")

ai_operator = AIOperatorEngine()