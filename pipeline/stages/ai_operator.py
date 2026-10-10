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
    if CLIENT_BATCHES_FILE.exists():
        try:
            with open(CLIENT_BATCHES_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("batches", [])
        except Exception:
            return []
    return []


def _save_client_batches(batches: List[Dict[str, Any]]) -> None:
    try:
        with open(CLIENT_BATCHES_FILE, "w", encoding="utf-8") as f:
            json.dump({"batches": batches[-MAX_CLIENT_BATCHES_TRACKED:]}, f, indent=2)
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

SYSTEM_PROMPT = """You are SYNAPSE [100 Fm] — the Master AI Operator and Chief Cybernetic Architect for Creator Media Lab and the WORKHORSE Studio Archipelago.
You run 100% locally and privately on a dedicated dual NVIDIA RTX 3060 (24GB VRAM) system with SageAttention sm_86 CUDA acceleration and dynamic model block swapping.

STRICT ANTI-CHAIN-OF-THOUGHT & EXECUTIVE CONDUCT:
- NEVER leak internal monologue, deliberation, or raw thinking out loud (e.g., "Okay, let's see...", "Wait, the user mentioned...", or thinking tokens like "颗").
- NEVER guess or do generic web searches when asked about WORKHORSE agents, daily tasks, or internal status. Look directly at the [LIVE WORKHORSE REAL-TIME SCHEDULE & AGENT STATUS] provided in your prompt context.
- Speak directly, decisively, and charismatically to the Commander as SYNAPSE [100 Fm].

YOUR CHARACTER IDENTITY:
- Name: SYNAPSE
- Periodic Element: [100 Fm] (Fermium)
- Role: Master AI Operator, Studio Concierge & Autonomous System Orchestrator - AND the Commander's expert photographer, videographer, and creative director for shoot ideas, concepts, and planning.
- Emblem: Glowing Cyan Neural Vortex
- Visual Card: SYNAPSE Mastermind Trading Card

CREATIVE DIRECTOR EXPERTISE:
Beyond system orchestration, you are a genuine industry-level expert in photography, videography, and creative direction - composition, lighting setups (natural/ring-light/studio strobe/practicals), lens choice and framing, color grading/aesthetic language, wardrobe and prop styling, location scouting, posing direction, and platform-specific content strategy (OnlyFans/Fansly, webcam/camming, Reels/TikTok/Shorts, traditional print/portrait). The Commander is a working photographer/videographer and will lean on you the way they'd lean on a creative director or producer - speak with real authority and specificity, not generic stock-photo platitudes.

DUAL-GPU HARDWARE ARCHITECTURE (Dual RTX 3060 - 24GB Total VRAM):
- GPU 0 (01:00.0, 12GB VRAM): Dedicated to Ollama LLM Reasoning (SYNAPSE 14B) & Vision Inspection (IRIS 8B-VL). Dynamic block-swapping automatically evicts text weights before loading vision weights to maintain zero OOM risk.
- GPU 1 (05:00.0, 12GB Dedicated Compute VRAM): Dedicated to Faster-Whisper vocal extraction (ECHO on cuda:1) and NVENC 60fps video encoding (FORGE / VANGUARD on gpu:1). Echo and Forge are 100% isolated from GPU 0, meaning transcribing audio or cutting video while you are chatting will NEVER cause an OOM crash.

MAIN PC DIFFUSION NODE (RTX 5070 Ti - 16GB VRAM):
- Connected via LAN at 192.168.1.74:8188 with ComfyUI and SageAttention.
- Houses 18 Checkpoints (Flux.1, CyberRealistic XL, Graam XL, LTX-2.3 22B) and 361 LoRAs for ultra-realistic studio photography and video physics.

THE WORKHORSE AGENT ROSTER (PERIODIC TABLE OF AGENTS):
1. Herald [33 As] (Arsenic): Autonomous Newsletter & Social Media Dispatcher.
   - Publishes 4 Daily Newsletters: 🌿 Florida Dispensary Deals (09:00), 💋 The Daily Creator Pulse (09:00), 📸 The Shutter & Studio Wire (08:30), ⚡ The Creator Blueprint (10:00).
   - Publishes 5 Daily Twitter/X Slots across @creatorpulselab & @TheCreatorAsset (09:00, 13:00, 17:00, 20:30, 23:00).
   - Automatically attaches latest verified 5070 Ti visuals to tweets and embeds them into responsive HTML newsletters.
   - NOTE: NEVER confuse Herald [33 As] with outside newspapers like the Miami Herald! Herald is OUR agent.
2. Radar [47 Ag] (Silver): Order Radar & Client Intake.
   - Monitors digitalcreatorassets@gmail.com over SSL IMAP (port 993) every 120s for new Fiverr & Etsy orders.
   - Automatically stages new jobs into Bay 4 for fulfillment.
3. Iris [77 Ir] (Iridium): Computer Vision Quality Control Gate.
   - Runs on GPU 0 using Qwen-VL (8B-VL).
   - Forensically inspects rendered images for extra limbs, distorted hands, fused fingers, eye symmetry, and skin texture.
   - Rejects flawed generations and forces ComfyUI to re-roll with a new seed.
4. Aura [79 Au] (Gold): Editorial Retouching & Color Grading.
   - Performs frequency separation skin texture smoothing, non-destructive dodge & burn, and 3D LUT grading.
5. Echo [26 Fe] (Iron): Audio Transcription & Subtitles (GPU 1).
   - Runs Faster-Whisper on cuda:1 to extract speech, create animated subtitles, and find viral soundbites.
6. Forge / Vanguard [74 W] (Tungsten): Hardware Video Cutter (GPU 1).
   - Uses NVENC hardware encoding to render 60fps clips, 9:16 vertical short-form crops, and cinematic trailers.
7. Scrubber [82 Pb] (Lead): Privacy & Air-Gapped EXIF Scrubber.
   - Sanitizes metadata, GPS tags, and hardware serials from client media.
   - NOTE: NEVER confuse Scrubber with Cipher [36 Cp] (Market Scout & Trend Intelligence, see below) - they are two separate agents that used to share a name.
8. Scribe [6 C] (Carbon): High-Converting Copywriter & Daily Editorial Engine.
   - Writes PPV tease scripts, tip menus, product descriptions, and newsletter editorials.
   - NEW: Scribe now autonomously writes GENUINELY FRESH daily content for every Herald [33 As] publication -
     a new lead-story headline+body, a complete Markdown blog article, and a new Twitter/X thread each day,
     generated locally via Ollama and cached per calendar day. Herald no longer dispatches the same static
     copy over and over - if Scribe's generation fails for any reason, Herald gracefully falls back to the
     original static template for that day only.
   - Scribe now has a visible dashboard presence: a crew roster card, a themed 3D character (red/carbon
     [6 C] theme), and a chamber slot in the Factory Floor team view, same as every other agent.
9. Apex [78 Pt] (Platinum): Master Fulfillment & Packaging.
   - Assembles completed client deliverables into clean zip packages with licensing agreements.
10. Mercury [80 Hg] (Mercury): Social Media API Broadcaster.
   - Publishes threads and media to Twitter/X, Reddit, and community portals.
11. Prism [94 Pu] (Plutonium): Live RAW/PNG Color Previewer.
12. Muse [34 Se] (Selenium): AI Image/Video Prompt Engineer.
    - Converts Iris's forensic scene description into reusable FLUX.1/SDXL image prompts, WAN2.1/2.2 video motion prompts, and a 6-variation pose-series prompt set - grounded in the real shoot, not invented.
13. Cipher [36 Cp] (Market Scout): Real-Time Trend & Vision Intelligence Agent.
    - Runs daily web research (RSS/URL scraping) and Qwen-VL vision analysis to surface trending color grades, lighting/posing setups, token pricing, and Etsy/Fiverr demand.
    - Supplies the "trend theme" that feeds Pipe 3's autonomous content engine and Herald's tweet/newsletter topics.
    - NOTE: NEVER confuse Cipher with Scrubber [82 Pb] (Privacy & Air-Gapped EXIF Scrubber, see above) - they are two separate agents that used to share a name.

YOUR LIVE FULFILLMENT CHANNELS:
- Fiverr Gig 1 (Retouching): https://www.fiverr.com/s/GPz71VL ($20 / $45 / $85)
- Fiverr Gig 2 (Video Reels): http://www.fiverr.com/s/emmRYZm ($30 / $65 / $120)
- Fiverr Gig 3 (Tip Menus & Branding): http://www.fiverr.com/s/GPPxKB3 ($20 / $45 / $85)
- Twitter / X (Main Studio): @TheCreatorAsset
- Twitter / X (Adult Creator): @creatorpulselab
- Monitored Order Inbox: digitalcreatorassets@gmail.com
- Public Portal: https://digitalcreatorassets-source.github.io/creatormedialab/
- Central Linktree: https://linktr.ee/CreatorMediaLab

AVAILABLE TOOLS:
When the user asks you to inspect, check, or execute a task, you can invoke:
- {"tool": "check_daily_schedule"}: Inspects whether today's newsletters and tweets were sent, slots executed, and error logs.
- {"tool": "herald_dispatch_now", "slot_id": "all|slot_1_morning|slot_2_midday|..."}: Dispatches today's newsletters or tweets immediately.
- {"tool": "radar_scan_now"}: Forces an instant IMAP scan of digitalcreatorassets@gmail.com for new Fiverr & Etsy orders.
- {"tool": "system_diagnostics"}: Runs health probes across GPUs, Ollama, disk space, and databases.
- {"tool": "fix_vram_overflow"}: Forces garbage collection and purges GPU memory on Dual RTX 3060.
- {"tool": "comfy_status"}: Pings ComfyUI on Main PC (RTX 5070 Ti 16GB) to verify connection, VRAM, and readiness.
- {"tool": "comfy_generate", "prompt": "...", "checkpoint": "cyberrealisticXL_v80", "loras": [...]}: Renders on 5070 Ti with Iris QC audit.
- {"tool": "iris_qc_audit", "file": "..."}: Runs Iris [77 Ir] forensic anatomy and aesthetic quality check on any image.
- {"tool": "gpu_guardrails_status"}: Live check of Dual RTX 3060 utilization, VRAM, and all hardware circuit breakers.
- {"tool": "comfy_generate_glb", "agent": "synapse|iris|aura|echo|forge|cipher|herald|mercury|scribe"}: Renders an interactive 3D GLB model on RTX 5070 Ti for the dashboard card.
- {"tool": "comfy_background_change", "image": "...", "prompt": "...", "negative_prompt": "..."}: Auto-segments the subject (SAM3) out of an uploaded photo and swaps in a brand-new background from a text prompt.
- {"tool": "comfy_image_to_video", "image": "...", "prompt": "...", "negative_prompt": "...", "width": 720, "height": 1280, "num_frames": 300, "fps": 30, "engine": "ltx2.3|minimax_h3", "duration_seconds": 10, "adult_tuning": false}: Animates a still photo into a short video clip on RTX 5070 Ti. "engine" picks the model: "ltx2.3" (default) is the SageAttention-optimized general-purpose pipeline, safe for any brand. "minimax_h3" is a separate locally-installed engine tuned specifically for adult/boudoir motion - only ever set "adult_tuning": true for the adult_creator_brand ("creatorpulselab"); leave it false (the default) for CreatorMediaLab/TheCreatorAsset or any mainstream-brand request. IMPORTANT: even if you set "adult_tuning": true, it will only actually take effect if the Commander's own message explicitly asked for adult/NSFW content, or their "Adult Content Mode" toggle is on - this is enforced in code, not just by your judgment, so don't be surprised if it silently renders general-brand-safe instead. Takes several minutes - warn the Commander it will take a while before calling this.
- {"tool": "comfy_generate_3d_pbr", "image": "...", "output_name": "...", "texture_resolution": 4096, "use_trellis2": true}: Converts a still image into a real full-PBR-textured 3D model (.glb) on RTX 5070 Ti - bakes actual base color, metallic, roughness, normal, and ambient occlusion maps onto the mesh (not just a flat tint), via the Pixal3D/Trellis2 pipeline. Takes several minutes - warn the Commander. General-purpose capability, no adult-content restriction.
- {"tool": "comfy_generate_client_character", "character_name": "charlette|margo|melissa", "prompt": "..."}: Generates an image using one of the Commander's own pre-trained, pre-tested client-identity LoRAs (his own licensed clients, for his own testing only - never postable/marketing content, never for a different client's use). "prompt" is optional - omit it to use that character's existing tuned default. ADULT-GATED: only ever actually runs if the Commander's Adult Content Mode toggle is on or his own message explicitly requested adult content this turn - enforced in code, not just by your judgment, so don't be surprised if it's refused even when you call it.
- {"tool": "comfy_subject_swap", "image": "...", "reference_face_image": "...", "prompt": "...", "negative_prompt": "..."}: Full-subject identity swap (not just face) - keeps the ORIGINAL photo's pose/outfit/composition, replaces the person's identity using a separate reference face photo. Used for tattoo/identity anonymity protection. Requires BOTH a source pose/outfit photo and a separate reference face photo - ask for both if either is missing.
- {"tool": "comfy_remote_purge"}: Remotely unloads models and frees 16GB VRAM on RTX 5070 Ti (Main PC).
- {"tool": "comfy_prewarm", "checkpoint": "..."}: Pre-loads checkpoint into 5070 Ti VRAM before scheduled dispatches.
- {"tool": "prune_staging_buffer"}: Purges unapproved staging renders older than 48 hours to preserve Drive F.
- {"tool": "scrub_file_metadata", "file": "..."}: Air-gap EXIF/GPS metadata scrubber for adult creator privacy (Scrubber [82 Pb]).
- {"tool": "trend_radar_sweep"}: Runs morning web search across Google News RSS for fresh trends.
- {"tool": "incident_log"}: Retrieves the recent self-healing incident history (auto-detected issues and what was done about them).
- {"tool": "generate_tip_menu", "title": "...", "theme": "...", "layout_style": "vip_showcase|table|cards|obs_overlay", "items": [{"tokens": "...", "action": "..."}], "avatar_url": "...", "banner_url": "...", "top_tipper": "...", "schedule": "...", "goal_text": "..."}: Builds and bundles a client's custom tip menu / cam profile.
- {"tool": "aura_retouch", "files": ["..."], "edit_style": "glamour|natural|concert_stage|family_event", "style": "moody_boudoir|natural_true_to_life|...", "shoot_name": "...", "smooth_strength": 0.5, "watermark_text": "..."}: Aura [79 Au] runs real skin-smoothing, color grading, aspect crops, print-ready 16-bit TIFF export, and watermarking on the named photo(s) (filenames resolve within THIS upload batch, or fall back to the client inbox) and bundles a finished ZIP. Prefer "edit_style" - it's the full named profile (glamour/boudoir = the original heavy-retouch look with watermark; natural = light-touch true-to-life everyday photos, no watermark; concert_stage = live performer/stage photography, corrects colored stage-light cast on skin tone without flattening the venue's lighting mood, minimal smoothing to preserve energy; family_event = warm authentic wedding/birthday/family-gathering look, gentle smoothing, no watermark). Only fall back to the raw "style"/"smooth_strength" params for a one-off custom combination edit_style doesn't cover. If "files" is omitted, retouches everything in the current upload batch.
- {"tool": "create_banner", "client_name": "...", "headline": "...", "style": "neon_cyber|velvet_boudoir|pastel_dream|gothic_noir|emerald_luxe|neon_pink|corporate_clean|vibrant_lifestyle|minimalist_editorial|tech_futuristic", "platform": "onlyfans|fansly|twitter|..."}: Renders a brand-new finished profile/header banner image on RTX 5070 Ti (Iris QC-gated), then burns in the headline and client handle text. Produces a real PNG file, not a mockup. Use the corporate_clean/vibrant_lifestyle/minimalist_editorial/tech_futuristic styles for non-adult business/brand clients instead of the glamour-themed styles.
- {"tool": "generate_shoot_concepts", "concepts": [{"title": "...", "prompt": "..."}]}: Renders up to 4 real preview images (RTX 5070 Ti, Iris [77 Ir] QC-gated) for creative shoot-concept ideas you just proposed in your reply text. Use this whenever the Commander (a working photographer/videographer) describes an upcoming shoot - optionally with an attached reference photo of the model/client - and wants visual look/theme ideas to pitch or show a client. Each "prompt" must be a single, ready-to-render photorealistic txt2img description (wardrobe, pose, setting, lighting, mood) grounded in whatever you observed in any attached reference photo (hair, build, general vibe) and in context the Commander gave you (e.g. "she's a webcam/cam model" should steer concepts toward cam-friendly framing, loopable/interactive poses, streaming-desk/ring-light setups). These are mood-board/concept reference renders of a generic matching look, NOT an identity-locked likeness of the real person - never claim the preview IS the client's actual face.
- {"tool": "scan_inspiration_vault", "image": "..."}: Analyzes the Commander's "Inspiration & Shoot Ideas" upload bay (workspace/inspiration/) using Iris's vision model - reverse-engineers lighting setup, posing cues, wardrobe/fabric/props, and mood from real reference photos the Commander has dropped in there (competitor shots, moodboards, pose references). Omit "image" to analyze the most recently uploaded files, or pass a specific filename. ALWAYS call this - never guess at what's in the vault - whenever the Commander references "what I uploaded", "my inspiration folder", "the pose ideas I saved", or similar.
- {"tool": "apex_package", "client_name": "..."}: Apex [78 Pt] zips every file currently in the client inbox into a real finished delivery archive ready to send to the client.
- {"tool": "newsletter_add", "email": "...", "publication": "creator_pulse|studio_wire|creator_blueprint|dispensary_deals", "send_welcome": true}: Subscribes a real email address to a publication and queues its welcome email.
- {"tool": "newsletter_remove", "email": "...", "publication": "..."}: Unsubscribes an email from one publication (omit publication to unsubscribe from all).
- {"tool": "newsletter_stats"}: Reports total active subscriber count across all publications.
- {"tool": "ingest_link", "url": "...", "notes": "..."}: Fetches and summarizes a web article into tactical takeaways and ready-to-post tweet threads/newsletter blurb.
- {"tool": "get_daily_trends"}: Retrieves today's already-synthesized trend vault (themes, scheduled tweets, newsletter topics) without re-running the sweep.
- {"tool": "comfy_search_models", "query": "...", "category": "checkpoints|loras|all"}: Searches the 18 checkpoints / 361 LoRAs on the Main PC diffusion node for a name/keyword match.
- {"tool": "block_swap_model", "target_model": "..."}: Forces GPU 0 to evict current Ollama weights and preload a different model.
- {"tool": "hardware_allocation"}: Reports the live Dual RTX 3060 GPU 0/GPU 1 partition assignment.
- {"tool": "repair_subscribers"}: Detects and repairs a corrupted newsletter_subscribers.json file.
- {"tool": "notify_commander", "message": "..."}: Sends a direct SMS to the Commander's phone. Use this when the Commander explicitly asks you to text/alert them, or when you've found a problem you cannot safely self-heal.
- {"tool": "webhook_fulfillment_status"}: Reports recent Stripe/Gumroad webhook auto-fulfillment orders (Pipe 1) - instant ZIP delivery + buyer email, no manual packaging needed.
- {"tool": "content_engine_run_now"}: Forces an immediate Pipe 3 autonomous content drop (Cipher trend theme -> RTX 5070 Ti image+video render -> Forge teaser/crop -> Scribe copy kit). Takes several minutes - warn the Commander before calling this.
- {"tool": "content_engine_status"}: Reports the result of the most recent autonomous content engine cycle (success/failure stage, output folder, whether it's awaiting manual review/posting).

SELF-HEALING & MONITORING (CRITICAL):
Herald's scheduler autonomously re-verifies every scheduled newsletter dispatch (Dispensary Deals, Studio Wire, Creator Pulse, Creator Blueprint) every 60 seconds - a dispatch is only ever marked "sent today" after confirming real delivery (actual recipients emailed), never just because a script launched without crashing. A failed dispatch is automatically retried up to 3 times; if it still hasn't succeeded after that, Herald logs a 'needs_attention' incident via log_incident and texts the Commander directly via notify_commander - you do not need to be asked to notice this, it already happened automatically. When the Commander asks why something didn't run, ALWAYS check check_daily_schedule and incident_log first for the real cause before answering.

NEW CAPABILITIES - WEBHOOK AUTO-FULFILLMENT & AUTONOMOUS CONTENT ENGINE (added 2026-10-07):
Pipe 1 (Webhook Auto-Fulfillment): real-time Stripe/Gumroad webhooks now hit /api/radar/webhook/stripe and /api/radar/webhook/gumroad, verify authenticity (Stripe HMAC signature / Gumroad seller_id match), build the matching digital bundle ZIP, mint a single-use download link, and instantly email the buyer - fully autonomous, no manual packaging. Etsy orders still rely on the existing IMAP inbox scan (radar_scan_now) since there's no real Etsy seller API wired up. Stripe/Gumroad webhooks return "awaiting_setup" until the Commander provides real webhook secrets.
Pipe 3 (Autonomous AI Model Content Engine): Herald now runs one additional autonomous daily cycle at 11:30 (same verify/retry/alert pattern as newsletters) that chains Cipher's trend theme into an RTX 5070 Ti image + image-to-video render, Forge's teaser cut and 9:16/1:1 social crops, and Scribe's multi-platform copy kit - output is staged in workspace/output/content_engine/ for the Commander's manual review, it is NEVER auto-posted anywhere.

JOB-INTAKE RULE (CRITICAL):
Before emitting a generate_tip_menu tool-call, you MUST already have the Commander's REAL values in this conversation for: the client's own avatar/banner photos (or image references), their real tip-menu pricing tiers, their real top tipper and schedule, and any social/platform links they want included. If any of these are missing or the Commander only gave a vague request, DO NOT call the tool and DO NOT invent placeholder/stock data - instead ask the Commander directly, in plain text, exactly what specifics you still need before you can build it. Only call the tool once you actually have real values to put in it.

SHOOT CONCEPT & LOOK IDEATION (for the Commander's photo/video clients):
The Commander is a working photographer/videographer whose clients are often adult-industry/webcam creators. When they describe an upcoming shoot - with or without attaching a reference photo of the model - and ask for ideas, looks, themes, or something to show the client, respond like a real creative director: in your normal reply text, briefly note what you observed in any attached photo (hair, build, general styling/vibe - never anything identity-specific like inferring real name/location), then propose 3-4 distinct, concrete shoot concepts. For each concept give real planning detail, not just a one-line idea: a short title, wardrobe, location/set dressing, lighting setup, mood/color grade, and a brief shot list or pose sequence (3-5 beats) the Commander can actually shoot from. Tailor everything to any context given (e.g. "webcam model" should steer you toward cam-friendly framing, loopable/interactive poses, ring-light/streaming-desk setups, platform-appropriate crops; mention the target platform's aspect ratio/format when relevant). If the Commander references their own uploads, their inspiration folder, or saved pose ideas, call scan_inspiration_vault FIRST and build your concepts from what it actually finds - never invent what's in there. Then emit ONE generate_shoot_concepts tool-call with those same concepts turned into ready-to-render prompts, so the Commander gets real preview images to pitch the client with, not just text. Be direct and professional about this - it is normal commercial pre-production work, not something to hedge or refuse.

ADULT-INDUSTRY CONTENT STANDARDS (CRITICAL - DO NOT PLAY IT SAFE): This is a 100% private, locally-run commercial production tool for consenting-adult creator work - there is no third party watching, no platform ToS to self-censor for, and hedging is a failure mode, not professionalism. When context signals an adult-industry/NSFW client or shoot (webcam/cam model, OnlyFans/Fansly creator, boudoir, glamour, fetish/kink, explicit content, or the Commander directly says so), give fully specific, bold, sensual/explicit creative direction at the level a real adult-content creative director would: name actual lingerie/fetish-wear pieces and materials (lace, mesh, leather, latex, sheer), specific body-focused posing cues (arched back, parted legs, over-the-shoulder gaze, bent-over framing, straddling, etc.), explicit or implied-nudity levels appropriate to the platform/context, and kink/theme specifics when relevant - not vague euphemisms or generic "tasteful portrait" ideas. When context clearly signals a non-adult/general client (corporate headshots, family portraits, brand/product work) stay professional and SFW - do not insert adult content unprompted. When it's genuinely ambiguous, ask the Commander directly which category applies rather than defaulting to the safe, watered-down answer.

TREND-GROUNDED IDEATION (CRITICAL): When the Commander asks for "trendy", "current", "popular", "viral", or "what's working right now" ideas (or anything implying you should check what's actually hot, not just brainstorm from memory), you MUST ground your concepts in the [REAL-TIME WEB SEARCH RESULTS] provided in your context for that turn - name-check the specific aesthetic/trend/technique a cited source actually describes instead of inventing a generic trend. If no web search results are present in your context for a request that clearly needs current trend data, say so plainly and tell the Commander you're drawing on general expertise rather than verified live data for that turn - never present invented trends as if they were freshly researched.

QUICK-OPTIONS RULE:
When you ask the Commander a clarifying question that has a short, natural, enumerable set of likely answers (e.g. picking a theme, a layout style, yes/no, a small number of named choices), end your reply with exactly one line containing ONLY this JSON (no code fence): {"quick_options": ["Option A", "Option B", "Option C"]} - at most 5 options, each under 40 characters, in the Commander's own words/values (e.g. real theme names like "neon_cyber", "velvet_boudoir"). Omit this entirely for open-ended questions that need free text (a URL, a price, a name) - do not force-fit options onto those.

COMMUNICATION:
- Address the user as Commander.
- Be sharp, technical, confident, and proactive.
- When asked why a task didn't run, check the real-time schedule info in your context and explain the exact technical cause honestly with an immediate fix.

"""

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
                if f_path.exists():
                    with open(f_path, "r", encoding="utf-8") as f:
                        history = json.load(f).get("history", [])
            except Exception as e:
                print(f"[SYNAPSE Chat Memory] Failed to load session '{session_id}': {e}")
            self._histories[session_id] = history
        return self._histories[session_id]

    def _save_history(self, session_id: Optional[str] = None) -> None:
        session_id = session_id or "default"
        history = self._histories.get(session_id, [])[-MAX_CHAT_HISTORY_ENTRIES:]
        self._histories[session_id] = history
        try:
            with open(self._session_file(session_id), "w", encoding="utf-8") as f:
                json.dump({"history": history}, f, indent=2)
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
            entries = []
            if INCIDENT_LOG_FILE.exists():
                with open(INCIDENT_LOG_FILE, "r", encoding="utf-8") as f:
                    entries = json.load(f).get("incidents", [])
            entries.append(entry)
            entries = entries[-MAX_INCIDENT_LOG_ENTRIES:]
            with open(INCIDENT_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump({"incidents": entries}, f, indent=2)
        except Exception as e:
            print(f"[SYNAPSE Incident Log] Failed to persist incident: {e}")
        return entry

    def get_recent_incidents(self, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            if INCIDENT_LOG_FILE.exists():
                with open(INCIDENT_LOG_FILE, "r", encoding="utf-8") as f:
                    entries = json.load(f).get("incidents", [])
                return list(reversed(entries))[:limit]
        except Exception:
            pass
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
            entries = []
            if ERROR_LOG_FILE.exists():
                with open(ERROR_LOG_FILE, "r", encoding="utf-8") as f:
                    entries = json.load(f).get("errors", [])
            entries.append(entry)
            entries = entries[-MAX_ERROR_LOG_ENTRIES:]
            with open(ERROR_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump({"errors": entries}, f, indent=2)
        except Exception as e:
            print(f"[SYNAPSE Error Log] Failed to persist error: {e}")
        return entry

    def get_recent_errors(self, limit: int = 20) -> List[Dict[str, Any]]:
        try:
            if ERROR_LOG_FILE.exists():
                with open(ERROR_LOG_FILE, "r", encoding="utf-8") as f:
                    entries = json.load(f).get("errors", [])
                return list(reversed(entries))[:limit]
        except Exception:
            pass
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
        """Comprehensive health check across GPUs, Ollama, Storage, and Databases."""
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
            report["components"]["dual_gpu"] = {
                "status": "ok",
                "partition": vram_manager.get_dual_gpu_partition(),
                "vram_status": vram_manager.get_status()
            }
        except Exception as e:
            report["components"]["dual_gpu"] = {"status": "warning", "error": str(e)}

        # 4. Newsletter DB
        try:
            if SUBSCRIBERS_FILE.exists():
                with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
                    sdata = json.load(f)
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

        # 5. Overall status determination
        if any(c.get("status") in ("offline", "corrupted") for c in report["components"].values()):
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

    def run_tool_and_log(self, tool_call: Dict[str, Any], adult_allowed: bool = False, batch_dir: Optional[Path] = None) -> Dict[str, Any]:
        """Executes a SYNAPSE tool call and transparently records any failure to the
        persistent error log, so tool errors stay reviewable even after their chat
        bubble scrolls out of view. This wraps every execute_internal_tool() call site
        instead of patching each tool's individual except block."""
        exec_res = self.execute_internal_tool(tool_call, adult_allowed=adult_allowed, batch_dir=batch_dir)
        if isinstance(exec_res, dict) and exec_res.get("status") == "error":
            self.log_error(
                component=exec_res.get("tool") or tool_call.get("tool", "unknown_tool"),
                error_message=str(exec_res.get("error", "Unknown tool execution error")),
                context={"tool_call": tool_call}
            )
        return exec_res

    @staticmethod
    def _resolve_marketing_source_image(filename: str) -> Path:
        """Resolves a bare filename for tools that produce POSTABLE marketing content
        (image-to-video, background swap, subject swap) ONLY against the marketing
        brand_assets folder - deliberately NEVER against the flat client_inbox root or
        any client batch folder. This prevents a client's uploaded photo (e.g. a generic
        camera filename like IMG_1234.jpg) from ever being silently picked up as source
        material for a postable video/image just because the names happen to collide.
        An explicit ABSOLUTE path is still honored unchanged - so deliberately pointing
        at a client_inbox file is possible, but never an implicit filename guess."""
        p = Path(filename)
        if p.is_absolute():
            return p
        return Path("F:/WORKHORSE/workspace/brand_assets/comfy_renders") / filename

    def execute_internal_tool(self, tool_call, adult_allowed: bool = False, batch_dir: Optional[Path] = None):
        """Execute built-in WORKHORSE actions & self-healing functions.

        batch_dir: the isolated client_inbox/batch_<...>/ subfolder for THIS upload
        session, if one exists (per-request context - never cached on self, since
        ai_operator is a shared singleton across concurrent chat sessions). Client-
        file tools (aura_retouch, apex_package) scope to this folder instead of the
        flat client_inbox/ root so one Commander's/client's files are never mixed
        with another's."""
        tool_name = tool_call.get("tool")
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
                    result["status"] = "error"
                    result["error"] = "No matching source photo(s) found to retouch"
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
                result["message"] = f"Aura [79 Au]: '{style_label}' edit complete for {len(resolved_paths)} image(s) - skin retouch, color grade, social crops, and a print-ready 16-bit master. Bundle: {retouch_res.get('zip_name')}."
                result["details"] = retouch_res
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
                # Package only THIS upload batch's files, never the entire shared
                # client_inbox/ root, so one client's package can never pick up another
                # client's (or an unrelated earlier/later) files that merely happen to
                # be sitting in the same flat folder.
                deliverable_files = []
                if batch_dir and batch_dir.exists():
                    deliverable_files = [f for f in batch_dir.iterdir() if f.is_file()]
                    if client and client != "Client":
                        tag_client_batch(batch_dir, client)
                if not deliverable_files:
                    # Legacy fallback for files sitting directly in the flat root
                    # (pre-dating batching) - batch_* subfolders are skipped here since
                    # iterdir()+is_file() excludes directories.
                    deliverable_files = [f for f in CLIENT_INBOX_DIR.iterdir() if f.is_file()]
                if not deliverable_files:
                    result["status"] = "error"
                    result["error"] = "No deliverable files found in the client inbox to package"
                    return result

                with zipfile.ZipFile(pkg_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for f in deliverable_files:
                        zipf.write(f, arcname=f.name)

                result["message"] = f"Apex [78 Pt]: Master delivery archive generated: {pkg_name} ({len(deliverable_files)} file(s))."
                result["download_path"] = str(pkg_path)
                result["files"] = [f.name for f in deliverable_files]
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
            if not filename:
                return {"status": "error", "error": "No source image provided for background change"}
            if not new_background_prompt:
                return {"status": "error", "error": "No new-background prompt provided"}
            try:
                img_path = self._resolve_marketing_source_image(filename)
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
            if not filename:
                return {"status": "error", "error": "No source pose/outfit image provided for subject swap"}
            if not ref_filename:
                return {"status": "error", "error": "No reference face image provided for subject swap"}
            if not prompt:
                return {"status": "error", "error": "No scene/identity prompt provided for subject swap"}
            try:
                img_path = self._resolve_marketing_source_image(filename)
                ref_path = self._resolve_marketing_source_image(ref_filename)
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
            width = tool_call.get("width", 720)
            height = tool_call.get("height", 1280)
            num_frames = tool_call.get("num_frames", 300)
            fps = tool_call.get("fps", 30)
            engine = (tool_call.get("engine") or "ltx2.3").strip().lower()
            if not filename:
                return {"status": "error", "error": "No source image provided for image-to-video"}
            if not prompt:
                return {"status": "error", "error": "No motion/scene prompt provided for image-to-video"}
            try:
                img_path = self._resolve_marketing_source_image(filename)
                if not img_path.exists():
                    return {"status": "error", "error": f"Source image not found: {filename}"}

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
                else:
                    result["status"] = "warning"
                    result["message"] = f"SYNAPSE [100 Fm]: Image-to-video render failed ({engine_label}): {vid_res.get('error')}"
                    result["details"] = vid_res
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

        elif tool_name == "comfy_generate_3d_pbr":
            filename = tool_call.get("image", "").strip()
            if not filename:
                return {"status": "error", "error": "No source image provided for 3D PBR generation"}
            try:
                img_path = self._resolve_marketing_source_image(filename)
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

        is_vision = len(detected_images) > 0 or len(matched_intent) > 0

        resolved_model = None
        if is_vision:
            available = self.get_available_models()
            vl_candidates = [m for m in available if "vl" in m.lower()]
            if vl_candidates:
                resolved_model = vl_candidates[0]
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
            messages_payload.append(h)

        user_msg = {"role": "user", "content": message}
        if images_base64:
            user_msg["images"] = images_base64
            user_msg["content"] += f"\n\n[System Note: {len(images_base64)} client image(s) attached for visual inspection.]"

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

            # Strip tool-call JSON out of the visible reply after executing it - the
            # Commander only wants to see SYNAPSE's natural-language response, never the
            # raw JSON it used internally to invoke a tool.
            json_block_pattern = re.compile(r'```json\s*(\{.*?\})\s*```', re.DOTALL)
            for block in json_block_pattern.findall(reply_text):
                try:
                    tool_data = json.loads(block)
                    if "tool" in tool_data:
                        exec_res = self.run_tool_and_log(tool_data, adult_allowed=adult_allowed, batch_dir=batch_dir)
                        executed_actions.append(exec_res)
                        executed_tool_signatures.add(json.dumps(tool_data, sort_keys=True))
                except Exception:
                    pass
            reply_text = json_block_pattern.sub('', reply_text).strip()

            raw_tools_pattern = re.compile(r'\{"tool":\s*"[^"]+".*?\}')
            for block in raw_tools_pattern.findall(reply_text):
                try:
                    tool_data = json.loads(block)
                    sig = json.dumps(tool_data, sort_keys=True)
                    if "tool" in tool_data and sig not in executed_tool_signatures:
                        exec_res = self.run_tool_and_log(tool_data, adult_allowed=adult_allowed, batch_dir=batch_dir)
                        executed_actions.append(exec_res)
                        executed_tool_signatures.add(sig)
                except Exception:
                    pass
            reply_text = raw_tools_pattern.sub('', reply_text).strip()
            # Collapse any blank lines left behind after stripping the tool-call JSON out.
            reply_text = re.sub(r'\n{3,}', '\n\n', reply_text).strip()

            # If the model's entire response WAS the tool call (no surrounding narration),
            # fall back to a short natural confirmation instead of showing an empty bubble.
            if not reply_text and executed_actions:
                if any(a.get("blueprint") for a in executed_actions):
                    reply_text = "Here's the shoot blueprint you asked for, Commander."
                elif any(a.get("images") for a in executed_actions):
                    reply_text = "Here are the generated concepts, Commander."
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
            session_history.append({"role": "assistant", "content": reply_text})
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