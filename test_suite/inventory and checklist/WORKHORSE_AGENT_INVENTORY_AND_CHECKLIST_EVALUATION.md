# WORKHORSE — Ecosystem Inventory (List 1) and Checklist Evaluation (List 2)

Analysis only. **No files were changed.** `secrets.json` was not read. `order_radar_config.json` was inspected with values masked.

Not independently verified (checklist claims taken as-is): `newsletter_manager.py`, `twitter_poster.py`, `pinterest_poster.py`, `trend_researcher.py` (internals), `omni_marketer.py`, `fiverr_service_bot.py`, `etsy_digital_store.py`, `cam_template_generator.py`, `atomic_writer.py`, `auth.py`, and most frontend JS (`bays.js`, `operator.js`, `factory.js`).

---

# LIST 1 — The WORKHORSE ecosystem as it actually is

## 1.1 Infrastructure

| Component | Detail |
|---|---|
| Server | FastAPI `dashboard/server.py`. Binds `0.0.0.0` (config and .bat say 127.0.0.1). Port 8800. Auth cookie and `PUBLIC_PATHS`. |
| GPU0 (RTX 3060 12GB) | Ollama. Synapse chat (qwen3-abliterated:14b), Iris vision (Qwen-VL), Aura/Scribe text. |
| GPU1 (RTX 3060 12GB) | Echo (Faster-Whisper) and Forge (NVENC). Guarded by `gpu1_arbiter` (PID file). |
| Remote ComfyUI (5070 Ti) | 192.168.1.74:8188, fallbacks 100.114.140.7, 127.0.0.1, localhost. Image, video, 3D (GLB), client-character renders. |
| Background server tasks (4) | VRAM watchdog (5s), Herald loop (60s), ComfyUI health (45s), auto-remediation (600s). |
| Telemetry | WebSocket `/ws/telemetry`, every 3s. |
| Escalation | `notify_commander` sends SMS via Twilio. Credentials come from `F:/AI_Media_Scripts/deals_config.json`, which is outside the repo. |
| Other apps | Prism (`prism_local/`, port 7862, launched via `/api/prism/launch`). `dropzone_watcher` is standalone and is not started by the server or the .bat. |

## 1.2 Agent roster

| Agent | Real implementation | Runs on | Trigger | Output / hand-off |
|---|---|---|---|---|
| **SYNAPSE** [100 Fm] | `ai_operator.py`. Chat LLM with ~44 JSON tool calls, self-healing, per-session history, vision auto-switch, adult-mode gating, link ingestion. | GPU0 | User chat. Auto-remediate every 10 min. Daily health snapshot. | Tool results to chat. Incidents. SMS. |
| **Herald** [33 As] | `herald_scheduler.py`. | CPU/network | 60s loop. | 5 Twitter slots × 2 handles. Newsletters. Radar sweep. Content engine. Pinterest (disabled). Retries 3×, then incident + SMS. |
| **Radar** [47 Ag] | `order_radar.py`. | CPU/network | Stripe/Gumroad webhooks. IMAP scan (manual only). | Orders, download tokens (14-day TTL), fulfillment ZIP, SMTP email. |
| **Iris** [77 Ir] | `vision_agent.py` (poses, forensic scene analysis). `comfyui_bridge.run_iris_qc_audit` (QC gate). | GPU0 | Pipeline stages 2 and 5. Every ComfyUI render. | Pose frames, scene report, QC score. |
| **Aura** [79 Au] | `photo_retoucher.py`. Also owns copy config keys. | CPU (OpenCV) | Client retouch, dropzone. | Retouched photos, 16-bit TIFF. |
| **Echo** [26 Fe] | `audio_agent.py`. | GPU1 | Pipeline stage 4. | Transcript, hooks. |
| **Forge** [74 W] | `scene_extractor.py`. | GPU1 (NVENC) | Pipeline stage 3. Content engine. Herald video upgrade. | Teaser, 9:16 and 1:1 crops. |
| **Vanguard** | Role is inconsistent (see 1.5). | — | Orchestrator job start/finish. | Stage 1 video info. |
| **Scrubber** [82 Pb] | `scrubber.py`. | CPU | Called only on the QC-passed Herald path. | EXIF-stripped image. |
| **Scribe** [6 C] | `copy_synthesizer.py`, plus daily Herald and newsletter copy. | GPU0 (Ollama) | Pipeline stage 7. Daily content. | Release kit. Static fallback on JSON failure. |
| **Apex** [78 Pt] | `package_exporter.py` (pipeline stage 8). `apex_package` tool. Fulfillment ZIPs. | CPU | Stage 8. | Export bundle. |
| **Mercury** [80 Hg] | `omni_marketer.py`. Campaign-copy generator. **No Reddit or live broadcast exists**, although the prompt says so. | GPU0 | Dashboard only. | Campaign copy. |
| **Prism** [94 Pu] | `prism_local/`. RAW/PNG previewer. | Local | `/api/prism/launch`. | Viewer on port 7862. |
| **Muse** [34 Se] | `prompt_synthesizer.py`. | GPU0 | Pipeline stage 6. | Flux, WAN and pose prompts. |
| **Cipher** [36 Cp] | `trend_researcher.py`. | CPU/network | Daily radar sweep. Link ingestion. | Trend vault, themes. |

## 1.3 Schedules (Herald)

| Item | Time |
|---|---|
| Twitter slots (2 handles) | 09:00, 13:00, 17:00, 20:30, 23:00 |
| Newsletters | studio_wire 08:30, creator_pulse 09:00, creator_blueprint 10:00, dispensary_deals 09:00 (legacy subprocess) |
| Radar sweep | From 08:00, retries to 10:30 |
| Content engine | 11:30 |
| Pinterest | 12:00 (disabled) |
| Video upgrade | slot_4_evening |

## 1.4 Intended hand-off flows

1. **Video pipeline (8 stages).** Vanguard (video info) → Iris (poses) → Forge (teaser, crops) → Echo (Whisper) → Iris (vision + forensic) → Muse (prompts) → Scribe (copy) → Apex (export).
2. **Paid order (Pipe 1).** Stripe/Gumroad webhook → Radar → Etsy bundle → download token → SMTP email.
3. **Content engine (Pipe 3).** Cipher theme → ComfyUI image → Iris QC → image-to-video → Forge teaser/crops → Scribe copy. Staged for manual review, never auto-posted.
4. **Herald daily post.** `_get_brand_visual_for_post` (fresh render with QC pass, else last QC-passed visual) → Scrubber → Twitter. Video upgrade on the evening slot.
5. **Fiverr / Etsy / cam-template / dropzone.** Each bot produces ZIPs. Dropzone does its own retouch.
6. **Self-healing.** Synapse auto-remediation → incident log → `notify_commander`.

## 1.5 Where the docs, UI and prompt disagree

| Source | Says | Reality |
|---|---|---|
| `agents.js` | 10 agents. Missing muse, apex, prism, radar, scrubber. | `pipeline.js` calls `setActiveAgent` with muse, scribe and apex, so some have no pod to highlight. |
| README | "8 core agents". Omits Synapse, Scribe, Muse, Apex, Radar, Scrubber, Prism. | ~14 exist in code. |
| Vanguard | Orchestrator: stream integrity. `agents.js`: Fiverr automation. README / `vram_manager`: system watchdog. | Three different roles. |
| Mercury | Prompt: social API broadcaster (Twitter/Reddit). README: stream routing. | Campaign-copy generator only. |
| Cipher | README: encryption/crawler. | Trend researcher. |

## 1.6 Synapse tool catalog (~44) and gaps

Domains: system and diagnostics, GPU/VRAM, ComfyUI (generate, GLB, models, block swap), QC (`iris_qc_audit`), newsletter and subscribers, Herald schedule, trends and inspiration, link ingestion, content engine, webhook fulfillment status, Apex packaging.

**Synapse has no tool for:** starting the video pipeline, Fiverr/Etsy bundle fulfillment, Mercury campaigns, tweet publish, radar order fulfill, newsletter send, or approving content-engine output.

## 1.7 Config → consumer map

**Live (read by code):** `preview_duration_sec`, Herald slot times, retry cap, radar window, ComfyUI hosts, QC config (loaded once at init), orchestrator (reloaded per job), `agents.aura.text_model` (used as the text model for all text).

**Dead or decorative:**
- `agents.iris.pose_count`: UI message only; `extract_6_poses` is hardcoded to 6.
- Forge: `video_codec`, `generate_vertical_9x16`, `generate_square_1x1`, `watermark_*`, `nvenc_gpu_index`.
- Echo: `whisper_model`, `compute_type`, `vad_filter`, `device_index`, hook word limits.
- Herald `schedule_time`. Vanguard `order_radar_email` and `active_gigs`. Scribe `text_model` and `tone_preset`. Aura retouch fields.
- `order_radar.auto_check` and `check_interval_seconds` (`last_checked` is stale at 10/06).
- `strict_local_only` (`is_strict_local()` is never called).
- `config.system.host`. `trend_researcher` `offline_cache_only` (likely unused).

## 1.8 Known orchestration gaps (summary)

- Failed-QC images are saved as `success: True`, and `content_engine` feeds them onward.
- LLM and Whisper error strings flow into deliverables as content.
- PID-based locks give no mutual exclusion between threads in the same process.
- The VRAM circuit breaker can kill legitimate long inference.
- Herald runs sequentially and replays missed slots after a restart.

---

# LIST 2 — Checklist evaluation (`QA_TEST_CHECKLIST.md`)

## 2.1 Section verdicts

| § | Topic | Verdict | Notes |
|---|---|---|---|
| FLAGGED | 5 flagged items | **1 wrong, 4 accurate** | #3 is wrong (see 2.2). #1, #2, #4, #5 confirmed. |
| A | Auth | Covered | `PUBLIC_PATHS` accurate. Missing: cookie `Secure` flag, login rate limit, CORS `*`. |
| B | Timers | Covered | Intervals confirmed. Missing: circuit-breaker side effects, blocking calls on the loop. |
| C | WebSocket | Partial | Uses sync `requests` and `nvidia-smi` in an async path. |
| D | Route inventory | Covered | Appears complete. No security-focused cases per route. |
| E | Upload/download safety | Partial | Does not mention unsanitized names, absolute paths in `/api/pipeline/start`, `/api/open-folder`, or `/api/comfy/qc-audit`. |
| F | Output gallery | Covered | |
| G | Orchestrator | Partial | Missing: temp-dir leak, error strings as content, `PackageExporter` use. |
| H | Retoucher | Covered | |
| I | Scrubber | Partial | Missing: runs only on the QC-passed branch. |
| J | Inspiration / Cipher vault | Taken as-is | Not verified. |
| K | Cam template | Taken as-is | Not verified. |
| L | DaVinci | Covered | |
| M | Package exporter | Partial | Should be tested as pipeline stage 8. |
| N | Dropzone | **Weak** | Misses nearly every defect (see 2.3). |
| O | Order Radar | Partial | Right priority, but misses most of the issues in 2.3. |
| P | Etsy | Taken as-is | |
| Q | Fiverr | **Wrong** | Asset-selection claim is incorrect. |
| R | Trend researcher | Taken as-is | |
| S | Omni Marketer | Partial | Should state it is not a social broadcaster. |
| T | Herald | Partial | Missing: restart replay, sequential awaits, `dispatch_today_all_now` only slot 1. |
| U | Newsletter | Partial | Missing: `dispensary_deals`, send times, `email_disabled` counted as success. |
| V | Twitter | Taken as-is | |
| W | Pinterest | Taken as-is | |
| X | Content engine | **Weak** | Missing: failed-QC images accepted. |
| Y | Synthesizers | Partial | Missing: error strings as content. |
| Z | Synapse tools | **Wrong count** | Says "~25"; the real count is ~44. Missing tool-parsing bugs. |
| AA | ComfyUI bridge | Partial | Missing: PID lock, 90s timeout without cancel, QC fail-open variants. |
| AB | Shared infra | Partial | Missing: circuit breaker, arbiter flaws, `atomic_writer` coverage. |
| AC | Frontend | Partial | Dead controls and roster mismatch not covered. |
| AD | Config-driven rules | **Wrong** | AD-1 and AD-4 will fail as written. AD-2 needs a caveat. |

## 2.2 Checklist claims that are incorrect

1. **FLAGGED #3.** `PackageExporter` is used. `orchestrator.py` lines 68 and 281 call `export_bundle` (stage 8). It is only unused by Etsy, Fiverr and dropzone.
2. **AD-1.** Changing the config will not change behavior for the dead keys listed in 1.7. Only `preview_duration_sec` is honored, and the filename is still `preview_60s_*`.
3. **AD-2.** `ComfyUIBridge.load_config` runs only at init, so QC config changes need a restart. The orchestrator reloads config per job.
4. **AD-4.** `strict_local_only` is never enforced. Outbound calls exist for DDGS, Google News, link and image fetch, Twilio, Twitter, Pinterest, SMTP, IMAP and Stripe.
5. **Q.** `/api/fiverr/fulfill` uses `list(glob("*.zip"))[-1]`. That is the last in directory order, not the newest, and it is not bound to the client. This creates a cross-client delivery risk.
6. **Z.** Tool count is ~44, not ~25. Missing from the checklist's list: `check_daily_schedule`, `gpu_guardrails_status`, `comfy_generate_glb`, `comfy_search_models`, `block_swap_model`, `hardware_allocation`, `repair_subscribers`, `newsletter_stats`, `ingest_link`, `get_daily_trends`, `scan_inspiration_vault`, `webhook_fulfillment_status`, `content_engine_run_now`, `content_engine_status`.

**Confirmed accurate:** FLAGGED #1 (tokens are reusable, though "single-use" is claimed in `_fulfill_web_order` and the Synapse prompt), #2 (QC fail-open), #4 (mock GPU returns a fake RTX 3060 at 12288 MB), #5 (`auto_check` is a no-op). Also accurate: the watchdog (300s idle, 5s tick), prune (30 min, 48h), comfy health 45s, auto-remediate 600s, Herald 60s loop, WebSocket 3s, radar window 08:00–10:30, content engine 11:30, `MAX_DISPATCH_RETRIES=3`, the 5 slot times.

## 2.3 Missing from the checklist, by severity

### Security
- `config/order_radar_config.json` is **tracked in git** (not in `.gitignore`) with a **non-empty `app_password`**. It is in commits 441ceb0 and 5eb3f5f. Stripe secret and Gumroad seller_id are empty.
- Server binds `0.0.0.0` despite the 127.0.0.1 config. `config.system.host` is unused.
- CORS `allow_origins=*`. No `Secure` cookie flag. No login rate limit.
- Arbitrary file read or access: `/api/comfy/qc-audit` and the `iris_qc_audit` tool (absolute paths), `/api/pipeline/start` (any absolute path), `/api/open-folder` (any existing path).
- `/api/download/{etsy|fiverr|cam-template|photos-zip}/{name}` take unsanitized names (Windows backslash traversal, `.zip` only).
- Synapse scrapes any URL in a message (SSRF, including LAN addresses).
- `/api/radar/webhook/config` returns the Stripe secret in its response.
- `/api/newsletter/send-test` has a hardcoded default recipient.
- Stripe webhook: no timestamp tolerance or replay check, `payment_status` not checked (an unpaid `checkout.session.completed` can fulfill), no idempotency lock (concurrent duplicates double-fulfill).

### Data integrity and delivery
- Fiverr asset selection (see 2.2 #5).
- Radar `_extract_order_id` regex `#?([A-Z0-9]{5,10})` can match plain words and collide, so real orders are deduped away silently.
- Email-order amounts are hardcoded ($35 / $24.99). Only the last 10 messages are scanned.
- Download URL is hardcoded to `https://100.66.45.48:8800/...`, a private Tailscale IP, while the server speaks plain HTTP. Buyers and Stripe likely cannot reach it.
- Simulated orders write to the real `orders_history.json`.
- Dropzone defects:
  - `dropzone_watcher` is not launched anywhere.
  - Leftover `_extracting_*` dirs are re-processed after a crash.
  - Flat copy name collisions silently lose photos.
  - `photos_processed` counts unreadable files (`.dng` via cv2 returns None).
  - No file-stability check, so half-copied zips fail.
  - It duplicates the retouch logic instead of `process_photo_batch`, and the docstring overstates it (claims RAW and Dual-GPU).
  - Output name `*_FINAL_DELIVERY_PACKAGE.zip` mismatches the `/api/download/fiverr` route.
- Failed-QC images saved as `success: True` into `brand_assets/comfy_renders`, then used by `content_engine` for video and copy.
- QC fail-open inconsistency: timeout is rejected, but a connection or HTTP error string from `ai_providers` fails JSON parsing and **auto-approves at 8.0**. If Ollama is down, everything is approved.
- LLM and Whisper error strings are placed into deliverables (`vision_agent`, `prompt_synthesizer`, Echo's `full_text`).
- Scrubber is skipped on the QC-bypassed, failed-QC and video paths.
- Non-atomic writes (plain `open('w')`) with read-modify-write races: incident, error, daily-health and chat-session logs, `client_batches.json`, `orders_history.json`, the radar config, `daily_schedule_state.json`, and `config.json`. Only the download-tokens file uses `atomic_write_json`.
- `scene_extractor`: ffmpeg timeouts (120s / 180s) can leave a partial file treated as success. The teaser always cuts from t=0.

### Correctness and robustness
- `vram_manager` circuit breaker: GPU0 ≥80% for >45s triggers `purge_vram` plus `taskkill /F /IM llama-server.exe`. The docstring says "without an active orchestrator job" but the code never checks. It can kill Scribe, vision or pipeline work. It also blocks the event loop.
- `.comfy_bridge.lock` and `gpu1_arbiter` are PID-based.
  - All server threads share one PID, so there is no intra-process exclusion.
  - The lock's finally-block deletes it when the first caller finishes.
  - Arbiter `release` uses substring matching, and `acquire` is non-atomic.
  - Echo ignores the `acquire` result, and Forge never acquires.
- Image generation timeout is 90s with no cancel of the ComfyUI job.
- Any HTTP 500 triggers a global VRAM purge and retry, not just OOM.
- Synapse chat bugs:
  - `raw_tools_pattern` is non-greedy and truncates nested JSON; unfenced nested calls are silently dropped.
  - Tool results are not fed back to the LLM (single pass).
  - Vision model picks "first model containing vl", ignoring `agents.iris.vision_model`.
  - `get_live_task_status_context` calls `check_connection()` synchronously every turn.
  - "update ideas" and "update tweets" run a full blocking radar sweep.
  - Adult-detection keywords are broad with no negation handling.
  - Status text says "25s socket timeout", but the default is 60s.
- Orders: `auto_check` and `check_interval_seconds` never run, yet Synapse's prompt claims "every 120s".
- Herald: after a mid-day restart, all missed slots fire back-to-back with stale content. A long content-engine or video run delays other dispatches. `dispatch_today_all_now` dispatches only slot 1.
- `/api/system/prune-staging?hours=0` or negative deletes everything. `workspace/temp/<job_id>/` is never pruned (disk leak). `/api/vram/config` is not persisted.
- `auto_remediate` logs an Ollama-offline incident every 10 min with no dedup, flooding the 200-entry cap.
- `run_system_diagnostics` does not check ComfyUI, Whisper/GPU1, Herald, IMAP, Twitter credentials or ffmpeg. The `dual_gpu` component is always "ok".
- `notify_commander` depends on a file outside the repo.
- `python dashboard/server.py` imports the module twice (`uvicorn.run("dashboard.server:app")`), so singletons and import side effects run twice. There is no supervisor, and no dependency start-up for Ollama or ComfyUI.

### Test safety
- Modules hardcode `F:/WORKHORSE/...`. Singletons (`order_radar`, `herald_scheduler`, `ai_operator`, `comfy_bridge`) are created at import with file side effects. `conftest.py` only sets `sys.path`. Tests could mutate real data or reach real Twitter, SMTP, Twilio or IMAP.
- The checklist has no isolation or mocking section.

### Roster and docs
- No test that the agent roster is consistent across `ai_operator.py`, `agents.js`, README and `pipeline.js`.
- Nothing verifies that dead dossier controls either work or are removed.

## 2.4 Suggested checklist edits (not applied)

1. Correct FLAGGED #3, AD-1, AD-2, AD-4, Q and Z as in 2.2.
2. Add a **test-isolation section** (temp-dir path override, mocked network, singleton reset), placed before everything else.
3. Add a **security section** for the items under Security above.
4. Expand N, O, T, U, X, AA and AB with the items in 2.3.
5. Add an **agent roster consistency** section.
6. Add a **dead config** section. Each control is either "wire it" or "remove it".

---

## Decisions needed from you

1. Rotate the Gmail app password and untrack `order_radar_config.json`?
2. Dead config controls: wire them up, or remove them from the UI?
3. QC on failure or error: fail closed (reject) or stay fail-open?
4. Fiverr fulfillment: bind assets to the client, or just pick the newest?
5. Circuit breaker: should it skip when a job is active?
6. Should the roster (README, `agents.js`, prompt) be unified, and what should Vanguard and Mercury actually be?
7. Should `dropzone_watcher` be started with the server?
