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

for d in (CLIENT_INBOX_DIR, CLIENT_OUTPUTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

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
- Role: Master AI Operator, Studio Concierge & Autonomous System Orchestrator
- Emblem: Glowing Cyan Neural Vortex
- Visual Card: SYNAPSE Mastermind Trading Card

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
7. Cipher [82 Pb] (Lead): Privacy & Air-Gapped EXIF Scrubber.
   - Sanitizes metadata, GPS tags, and hardware serials from client media.
8. Scribe [6 C] (Carbon): High-Converting Copywriter.
   - Writes PPV tease scripts, tip menus, product descriptions, and newsletter editorials.
9. Apex [78 Pt] (Platinum): Master Fulfillment & Packaging.
   - Assembles completed client deliverables into clean zip packages with licensing agreements.
10. Mercury [80 Hg] (Mercury): Social Media API Broadcaster.
   - Publishes threads and media to Twitter/X, Reddit, and community portals.
11. Prism [94 Pu] (Plutonium): Live RAW/PNG Color Previewer.

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
- {"tool": "comfy_generate_glb", "agent": "synapse|iris|aura|echo|forge|cipher|herald|mercury"}: Renders an interactive 3D GLB model on RTX 5070 Ti for the dashboard card.
- {"tool": "comfy_background_change", "image": "...", "prompt": "...", "negative_prompt": "..."}: Auto-segments the subject (SAM3) out of an uploaded photo and swaps in a brand-new background from a text prompt.
- {"tool": "comfy_image_to_video", "image": "...", "prompt": "...", "negative_prompt": "...", "width": 720, "height": 1280, "num_frames": 300, "fps": 30}: Animates a still photo into a short video clip on RTX 5070 Ti using the local LTX 2.3 image-to-video pipeline (SageAttention-optimized). Takes several minutes - warn the Commander it will take a while before calling this.
- {"tool": "comfy_subject_swap", "image": "...", "reference_face_image": "...", "prompt": "...", "negative_prompt": "..."}: Full-subject identity swap (not just face) - keeps the ORIGINAL photo's pose/outfit/composition, replaces the person's identity using a separate reference face photo. Used for tattoo/identity anonymity protection. Requires BOTH a source pose/outfit photo and a separate reference face photo - ask for both if either is missing.
- {"tool": "comfy_remote_purge"}: Remotely unloads models and frees 16GB VRAM on RTX 5070 Ti (Main PC).
- {"tool": "comfy_prewarm", "checkpoint": "..."}: Pre-loads checkpoint into 5070 Ti VRAM before scheduled dispatches.
- {"tool": "prune_staging_buffer"}: Purges unapproved staging renders older than 48 hours to preserve Drive F.
- {"tool": "cipher_scrub_file", "file": "..."}: Air-gap EXIF/GPS metadata scrubber for adult creator privacy.
- {"tool": "trend_radar_sweep"}: Runs morning web search across Google News RSS for fresh trends.
- {"tool": "incident_log"}: Retrieves the recent self-healing incident history (auto-detected issues and what was done about them).
- {"tool": "generate_tip_menu", "title": "...", "theme": "...", "layout_style": "vip_showcase|table|cards|obs_overlay", "items": [{"tokens": "...", "action": "..."}], "avatar_url": "...", "banner_url": "...", "top_tipper": "...", "schedule": "...", "goal_text": "..."}: Builds and bundles a client's custom tip menu / cam profile.
- {"tool": "aura_retouch", "files": ["..."], "style": "moody_boudoir|natural|...", "shoot_name": "...", "smooth_strength": 0.5, "watermark_text": "..."}: Aura [79 Au] runs real skin-smoothing, color grading, aspect crops, and watermarking on the named photo(s) (filenames from the client inbox) and bundles a finished ZIP. If "files" is omitted, retouches everything currently in the client inbox.
- {"tool": "create_banner", "client_name": "...", "headline": "...", "style": "neon_cyber|velvet_boudoir|pastel_dream|gothic_noir|emerald_luxe|neon_pink|corporate_clean|vibrant_lifestyle|minimalist_editorial|tech_futuristic", "platform": "onlyfans|fansly|twitter|..."}: Renders a brand-new finished profile/header banner image on RTX 5070 Ti (Iris QC-gated), then burns in the headline and client handle text. Produces a real PNG file, not a mockup. Use the corporate_clean/vibrant_lifestyle/minimalist_editorial/tech_futuristic styles for non-adult business/brand clients instead of the glamour-themed styles.
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

JOB-INTAKE RULE (CRITICAL):
Before emitting a generate_tip_menu tool-call, you MUST already have the Commander's REAL values in this conversation for: the client's own avatar/banner photos (or image references), their real tip-menu pricing tiers, their real top tipper and schedule, and any social/platform links they want included. If any of these are missing or the Commander only gave a vague request, DO NOT call the tool and DO NOT invent placeholder/stock data - instead ask the Commander directly, in plain text, exactly what specifics you still need before you can build it. Only call the tool once you actually have real values to put in it.

QUICK-OPTIONS RULE:
When you ask the Commander a clarifying question that has a short, natural, enumerable set of likely answers (e.g. picking a theme, a layout style, yes/no, a small number of named choices), end your reply with exactly one line containing ONLY this JSON (no code fence): {"quick_options": ["Option A", "Option B", "Option C"]} - at most 5 options, each under 40 characters, in the Commander's own words/values (e.g. real theme names like "neon_cyber", "velvet_boudoir"). Omit this entirely for open-ended questions that need free text (a URL, a price, a name) - do not force-fit options onto those.

COMMUNICATION:
- Address the user as Commander.
- Be sharp, technical, confident, and proactive.
- When asked why a task didn't run, check the real-time schedule info in your context and explain the exact technical cause honestly with an immediate fix.

"""

class AIOperatorEngine:
    def __init__(self):
        self.history = []
        self.last_search_status = "ok"
        self.last_search_error = None

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
        return diag

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
            r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=2)
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

    def execute_internal_tool(self, tool_call):
        """Execute built-in WORKHORSE actions & self-healing functions."""
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

        elif tool_name == "cipher_scrub_file":
            target_f = tool_call.get("file", "")
            try:
                from pipeline.stages.cipher import cipher_scrubber
                scrub_res = cipher_scrubber.scrub_image(target_f)
                result["message"] = f"CIPHER [82 Pb]: {scrub_res.get('privacy_status', scrub_res.get('error'))}"
                result["details"] = scrub_res
                return result
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)
                return result

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
            style = tool_call.get("style", "natural")
            try:
                resolved_paths = []
                for fn in files:
                    p = Path(fn)
                    if not p.is_absolute():
                        p = CLIENT_INBOX_DIR / fn
                    if p.exists():
                        resolved_paths.append(p)
                if not resolved_paths and not files:
                    # No specific files named - default to everything the Commander just dropped in
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
                    preset=style,
                    smooth_strength=float(tool_call.get("smooth_strength", 0.5)),
                    watermark_text=tool_call.get("watermark_text", "@ExclusiveDrop")
                )
                result["message"] = f"Aura [79 Au]: Frequency separation & '{style}' color grade complete for {len(resolved_paths)} image(s). Bundle: {retouch_res.get('zip_name')}."
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

        elif tool_name == "apex_package":
            client = tool_call.get("client_name", "Client")
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            pkg_name = f"Delivery_{client}_{timestamp}.zip"
            pkg_path = CLIENT_OUTPUTS_DIR / pkg_name
            try:
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
                img_path = Path(filename)
                if not img_path.is_absolute():
                    img_path = Path("F:/WORKHORSE/workspace/client_inbox") / filename
                    if not img_path.exists():
                        img_path = Path("F:/WORKHORSE/workspace/brand_assets/comfy_renders") / filename
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
                def _resolve(fn):
                    p = Path(fn)
                    if not p.is_absolute():
                        p = Path("F:/WORKHORSE/workspace/client_inbox") / fn
                        if not p.exists():
                            p = Path("F:/WORKHORSE/workspace/brand_assets/comfy_renders") / fn
                    return p

                img_path = _resolve(filename)
                ref_path = _resolve(ref_filename)
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
            if not filename:
                return {"status": "error", "error": "No source image provided for image-to-video"}
            if not prompt:
                return {"status": "error", "error": "No motion/scene prompt provided for image-to-video"}
            try:
                img_path = Path(filename)
                if not img_path.is_absolute():
                    img_path = Path("F:/WORKHORSE/workspace/client_inbox") / filename
                    if not img_path.exists():
                        img_path = Path("F:/WORKHORSE/workspace/brand_assets/comfy_renders") / filename
                if not img_path.exists():
                    return {"status": "error", "error": f"Source image not found: {filename}"}

                from pipeline.stages.comfyui_bridge import comfy_bridge
                vid_res = comfy_bridge.generate_image_to_video(
                    source_image_path=img_path,
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    width=width,
                    height=height,
                    num_frames=num_frames,
                    fps=fps
                )
                if vid_res.get("success"):
                    result["message"] = f"SYNAPSE [100 Fm]: Image-to-video render complete on RTX 5070 Ti (LTX 2.3). Saved to: {vid_res.get('filename')}."
                    result["details"] = vid_res
                else:
                    result["status"] = "warning"
                    result["message"] = f"SYNAPSE [100 Fm]: Image-to-video render failed: {vid_res.get('error')}"
                    result["details"] = vid_res
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

    def detect_vision_requirement(self, message: str, attached_files: Optional[List[str]] = None) -> Tuple[bool, str, List[str], Optional[str]]:
        """
        Comprehensive Auto-Detection Engine for Synapse Vision:
        Detects if a query requires Vision (Qwen-VL on GPU 0) based on:
        1. Explicitly attached or uploaded files
        2. Local image file paths or filenames in the message text
        3. Image URLs in the message text
        4. Recent client inbox images when user asks visual questions
        5. Semantic visual intent keywords (inspect, analyze photo, OCR, etc.)
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
                candidates = [
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
            
            # If visual intent is present but no image was found yet, check client_inbox
            if not detected_images and CLIENT_INBOX_DIR.exists():
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

    def chat(self, message: str, model=None, web_search=False, attached_files=None):
        chosen_model = model or DEFAULT_TEXT_MODEL
        
        # Comprehensive Auto-Detection for Vision Mode
        is_vision, reason, detected_images, resolved_vl_model = self.detect_vision_requirement(
            message=message,
            attached_files=attached_files
        )
        
        if is_vision:
            chosen_model = resolved_vl_model or DEFAULT_VISION_MODEL
            images_base64 = detected_images
            print(f"[SYNAPSE Auto-Vision] Auto-switched to Vision ({chosen_model})! Signals: {reason}")
        else:
            images_base64 = []

        # Dynamic Pre-Flight Block Swap on GPU 0 before sending request to Ollama
        vram_manager.prepare_for_model(chosen_model)

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

        for h in self.history[-6:]:
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

        try:
            ollama_res = requests.post(
                f"{OLLAMA_HOST}/api/chat",
                json=payload,
                timeout=120
            )

            # Self-healing OOM retry
            if ollama_res.status_code != 200:
                err_text = ollama_res.text.lower()
                if "memory" in err_text or "out of memory" in err_text or ollama_res.status_code == 500:
                    print(f"[SYNAPSE] Memory threshold detected in chat ({ollama_res.status_code}). Purging VRAM & retrying...")
                    vram_manager.purge_vram(reason="chat_emergency_retry")
                    ollama_res = requests.post(f"{OLLAMA_HOST}/api/chat", json=payload, timeout=120)

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
            json_blocks = re.findall(r'```json\s*(\{.*?\})\s*```', reply_text, re.DOTALL)
            for block in json_blocks:
                try:
                    tool_data = json.loads(block)
                    if "tool" in tool_data:
                        exec_res = self.execute_internal_tool(tool_data)
                        executed_actions.append(exec_res)
                except Exception:
                    pass

            raw_tools = re.findall(r'(\{"tool":\s*"[^"]+".*?\})', reply_text)
            for block in raw_tools:
                try:
                    tool_data = json.loads(block)
                    if "tool" in tool_data and tool_data not in [a.get("tool") for a in executed_actions]:
                        exec_res = self.execute_internal_tool(tool_data)
                        executed_actions.append(exec_res)
                except Exception:
                    pass

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

            self.history.append({"role": "user", "content": message})
            self.history.append({"role": "assistant", "content": reply_text})

            return {
                "status": "ok",
                "reply": reply_text,
                "model": chosen_model,
                "web_sources": web_sources,
                "web_search_status": web_search_status,
                "executed_actions": executed_actions,
                "attached_files_count": len(attached_files) if attached_files else 0,
                "vision_auto_detected": is_vision,
                "vision_reason": reason,
                "images_processed": len(images_base64),
                "article_urls_detected": article_urls,
                "link_ingestion_results": link_ingestion_results,
                "quick_options": quick_options
            }

        except Exception as e:
            return {
                "status": "error",
                "reply": f"Failed to contact local Ollama on {OLLAMA_HOST}: {e}",
                "model": chosen_model
            }

    def clear_history(self):
        self.history = []

ai_operator = AIOperatorEngine()