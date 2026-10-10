# WORKHORSE — QA End-to-End Test Coverage Checklist (Rev 2)

Generated via full-codebase audit (`dashboard/server.py`, `pipeline/*`, `shared/*`, `dashboard/static/js/*`)
against existing `test_suite/` coverage, and updated following the agent ecosystem inventory & evaluation report
(`WORKHORSE_AGENT_INVENTORY_AND_CHECKLIST_EVALUATION.md` in the WORKHORSE root).

**Legend:**
- ✅ = existing automated coverage already exists (extend, don't duplicate)
- 🆕 = no automated coverage found yet
- 🔧 = added / updated in Rev 2 based on ecosystem findings
- **[CORRECTED]** = prior checklist statement that conflicted with actual codebase implementation

> **Rev 2 Notice (2026-10-10):**
> This file is a non-destructive separate checklist created for user review. No application code or existing tests have been modified.
> Corrections include FLAGGED #3, Section M, Section Q, Section Z, and Section AD-1/2/4.
> New additions include FLAGGED #6–#14 and Sections AE (Test Isolation & Safety), AF (Security & Exposure), AG (Dead / Decorative Config Controls), and AH (Agent Roster Consistency).

---

## ⚠️ FLAGGED — Needs a decision before tests are written/run

These behaviors are ambiguous (could be intentional, incomplete, or a bug). Do not write an assertion that locks in behavior until we've decided which way each one should go.

1. **Order download tokens are reusable** — `/api/download/order/{token}` has no single-use/consumed flag despite the fulfillment docstring saying "single-use." A valid token can be reused by anyone who has it until the 14-day expiry. (`pipeline/stages/order_radar.py`)
2. **IRIS QC audit fails open** — if vision parsing of the QC response fails, the system falls back to a permissive "approved, score 8.0" result rather than rejecting/retrying. (`pipeline/stages/comfyui_bridge.py`)
3. **[CORRECTED] `PackageExporter` IS used by the video pipeline** — `orchestrator.py` calls `export_bundle` as stage 8 (~lines 68/281). It is NOT used by Etsy, Fiverr, dropzone, or order-radar fulfillment flows; the open question is whether those flows should also use it. (`pipeline/stages/package_exporter.py`)
4. **`system_monitor.py` fakes GPU data on failure** — when `nvidia-smi` fails, it returns a hardcoded mock RTX 3060 record (12288 MB / 9.8%) instead of an error/offline state, which could mask a real GPU failure in the UI.
5. **Order Radar's `auto_check` config does nothing** — it's stored/configurable but no scheduler/loop actually polls on an interval; scans only happen via manual `/api/radar/check` or an AI operator tool call. (`last_checked` is stale; Synapse's prompt wrongly claims "every 120s".)
6. 🔧 **Failed-QC images are saved as `success: True`** — after retries, `generate_and_audit` returns `success: True` + `warning` + `qc_audit.passed=False`, stored in `brand_assets/comfy_renders`. `content_engine.py` checks only `success`, so a rejected image feeds into image-to-video and copy generation. Herald does check `passed`. Decide: reject, quarantine, or accept-with-flag.
7. 🔧 **QC fail-open is inconsistent** — timeout results in `passed: false` (rejected), but connection or HTTP error strings from `ai_providers` (returned as raw strings, not exceptions) cause JSON parsing to fail, falling back to auto-approve at 8.0. If Ollama is offline, everything auto-approves.
8. 🔧 **Fiverr fulfillment picks the wrong ZIP** — `/api/fiverr/fulfill` uses `list(glob("*.zip"))[-1]`, which is the last in directory order (alphabetical), NOT the newest, and is NOT bound to the specific client. Cross-client delivery risk exists.
9. 🔧 **VRAM circuit breaker may kill live work** — GPU0 ≥80% for >45s triggers `purge_vram` + `taskkill /F /IM llama-server.exe`. The docstring says "without an active orchestrator job" but the code never checks for active jobs. Also blocks the event loop with synchronous calls.
10. 🔧 **`privacy.strict_local_only` is decorative** — `ai_providers.is_strict_local()` is defined but never called, yet outbound calls exist (DDGS, Google News, link/image fetch, Twilio, Twitter, Pinterest, SMTP, IMAP, Stripe).
11. 🔧 **Most agent-dossier config controls do nothing** — see Section AG.
12. 🔧 **Secret tracked in Git repository** — `config/order_radar_config.json` is tracked (not in `.gitignore`) and contains a non-empty `app_password` in git history (commits 441ceb0, 5eb3f5f). Requires untracking and rotation.
13. 🔧 **Radar download URL is hardcoded** — set to `https://100.66.45.48:8800/...` (a private Tailscale IP over HTTPS while the server speaks plain HTTP). External buyers and Stripe cannot reach this URL.
14. 🔧 **Server binds `0.0.0.0`** — config and `.bat` specify `127.0.0.1` (`config.system.host` unused); CORS is set to `*`.

---

## A. Authentication & Session (`dashboard/server.py`, `shared/auth.py`) ✅ `test_auth.py`
- [ ] `GET /setup` public when no password configured
- [ ] `POST /api/setup` rejects password < 8 chars (400)
- [ ] `POST /api/setup` rejects a second setup attempt once password exists (403)
- [ ] `POST /api/login` with correct password → session cookie set, `{"status":"ok"}`
- [ ] `POST /api/login` with wrong password → 401
- [ ] `POST /api/login` with no password configured → 503
- [ ] `POST /api/logout` clears cookie, requires prior auth
- [ ] `auth_gate_middleware`: unauth `/api/*` request → 401 JSON (not redirect)
- [ ] `auth_gate_middleware`: unauth non-API request → redirect to `/login`
- [ ] `PUBLIC_PATHS`/`PUBLIC_PREFIXES` bypass list is exhaustive — verify every public route truly needs no cookie, and every protected route truly rejects without one
- [ ] Session cookie: `HttpOnly`, `SameSite=Lax`, 7-day `max_age`
- [ ] scrypt hash/verify round-trip, wrong password rejected, malformed salt rejected (✅ covered)
- [ ] Session token: sid.expiry.signature format, tamper/expiry/wrong-secret rejection, legacy 2-part token rejection, unique sid per login (✅ covered)
- [ ] 🔧 Cookie has no `Secure` flag; no login rate limiting / lockout (document as known gap or test actual behavior)
- [ ] 🔧 CORS `allow_origins=*` — verify credentialed cross-origin requests behave as intended

---

## B. Background Timers / Scheduled Loops (backend) 🆕
- [ ] VRAM watchdog: idle timeout **300s (5 min)**, checks every **5s**, skips purge while `is_any_orchestrator_job_active()` is true
- [ ] VRAM watchdog staging-prune sub-cycle: runs **~every 30 min**, `max_age_hours=48`, only scans `comfy_staging` + `temp` (non-recursive), never touches `brand_assets`/`client_deliveries`
- [ ] Herald scheduler `run_loop()`: polls every **60s**; runs daily radar sweep from **08:00**, retries degraded radar until **10:30** then accepts fallback
- [ ] ComfyUI health monitor: polls every **45s**; online→offline logs `needs_attention` incident; offline→online logs `resolved` incident; exception path marks offline with error text
- [ ] Auto-remediation loop: runs every **600s (10 min)**; calls `ai_operator.auto_remediate()`; cancellation exits cleanly, other exceptions logged and loop continues
- [ ] Startup daily health check: runs once in executor on boot; no-ops if today's entry already exists; `force=True` replaces (not duplicates) today's entry
- [ ] Lifespan shutdown: all 4 background tasks (watchdog, herald, comfy-health, auto-remediation) are cancelled cleanly on server stop
- [ ] 🔧 VRAM circuit breaker (`check_and_trip_circuit_breaker`, every 5s): GPU0 ≥80% for >45s → `purge_vram` + `taskkill llama-server`; verify whether it fires during an active orchestrator job/long inference (FLAGGED #9); runs sync subprocess/requests in the async loop
- [ ] 🔧 `auto_remediate` logs an Ollama-offline incident every 10 min with no dedup — verify it doesn't flood/evict the 200-entry incident cap
- [ ] 🔧 Startup/import: `python dashboard/server.py` → `uvicorn.run("dashboard.server:app")` imports the module twice (singletons/import side effects run twice)

---

## C. WebSocket (`/ws/telemetry`) 🆕
- [ ] Connect without valid session cookie → closed with code `4401`
- [ ] Connect with valid cookie → accepted, added to `connected_websockets`
- [ ] Broadcasts `{"type":"telemetry", stats}` every **3s** (system stats + Ollama models + VRAM status + cached Comfy health)
- [ ] Orchestrator job events broadcast as `{"type":"job_update", job}` to all connected sockets
- [ ] Socket removed from list on disconnect or send exception; one broken socket doesn't break broadcast to others
- [ ] Frontend reconnects automatically **3s** after close (`pipeline.js`)
- [ ] 🔧 Handler uses sync `requests`/`nvidia-smi` in an async path — verify one slow call doesn't stall other sockets/requests

---

## D. REST API Surface — full route inventory (grouped)
*(All protected unless marked public; verify success path + every documented error status for each)*

**System/Agents**
- [ ] `GET /api/system/stats`, `/api/system/models`, `/api/system/gpu-partition`
- [ ] `GET/POST /api/agents/{agent_key}/config` (404 missing, 500 write failure, partial-merge semantics)
- [ ] `POST /api/open-folder`, `POST /api/open-brand-folder` (500 on launch failure)

**Photos**
- [ ] `GET /api/photos/list-input`, `POST /api/photos/upload` (filename path-stripping)
- [ ] `POST /api/photos/retouch` (400 when no input photos)

**Inspiration**
- [ ] `GET /api/inspiration/files`, `POST /api/inspiration/upload`, `GET /api/inspiration/analyze`, `GET /api/inspiration/comfyui-prompts`

**Templates**
- [ ] `POST /api/templates/generate-cam`, `POST /api/templates/tip-menu/generate`

**Herald**
- [ ] `GET /api/herald/schedule-status`, `POST /api/herald/dispatch-daily`, `POST /api/herald/dispatch-slot`

**Etsy**
- [ ] `GET /api/etsy/products`, `POST /api/etsy/bundle` (default `product_type=all`), `GET /api/download/etsy/{bundle_name}` (404)

**Fiverr**
- [ ] `GET /api/fiverr/gigs`, `POST /api/fiverr/fulfill`, `GET /api/download/fiverr/{order_number}` (404)

**Research**
- [ ] `GET /api/research/trends`, `POST /api/research/briefing`

**Order Radar / Webhooks**
- [ ] `POST /api/radar/webhook/stripe` (public, raw body + signature)
- [ ] `POST /api/radar/webhook/gumroad` (public, form body)
- [ ] `POST /api/radar/webhook/config`, `GET /api/radar/status`, `POST /api/radar/config`, `POST /api/radar/check`, `POST /api/radar/simulate`, `POST /api/radar/fulfill/{order_id}` (404 unknown)
- [ ] `GET /api/download/order/{token}` (public, 404 invalid/expired)

**Content Engine / Upload / Pipeline**
- [ ] `GET /api/content-engine/status`, `POST /api/content-engine/run-now`
- [ ] `POST /api/upload`, `POST /api/pipeline/start` (400 missing path, 404 nonexistent file)
- [ ] `GET /api/pipeline/jobs/{job_id}` (404 unknown)
- [ ] `GET /api/media/{file_path:path}` (sandboxed to approved dirs)
- [ ] `GET /api/download/photos-zip/{shoot_name}`, `/api/download/zip/{job_id}`, `/api/download/cam-template/{bundle_name}` (404 each)

**Prism / VRAM**
- [ ] `POST /api/prism/launch`
- [ ] `GET /api/vram/status`, `POST /api/vram/purge`, `POST /api/vram/config` (min 30s, 400 invalid), `POST /api/vram/swap`

**Marketing / Newsletter**
- [ ] `POST /api/marketing/generate`, `GET /api/marketing/history`
- [ ] `GET /api/newsletter/subscribers`, `POST /api/newsletter/subscribe` (public), `POST /api/newsletter/unsubscribe` (public)
- [ ] `GET /api/newsletter/config`, `POST /api/newsletter/subscribers/add|remove`, `POST /api/newsletter/elements/update`, `POST /api/newsletter/run`, `GET /api/newsletter/logs|publications|preview|blog-post|thread`, `POST /api/newsletter/send-test`

**Social**
- [ ] `GET /api/twitter/status`, `POST /api/twitter/publish`
- [ ] `GET /api/pinterest/status|boards`, `POST /api/pinterest/post-now`

**Diagnostics / Operator**
- [ ] `GET /api/system/health-check|incidents|daily-health-log|error-log`, `POST /api/system/self-heal` (actions: `all`/`vram`/`subscribers`)
- [ ] `GET /api/operator/models|history`, `POST /api/operator/chat` (multipart, per-session isolation), `POST /api/operator/clear`, `GET /api/operator/client-files`
- [ ] `GET /api/trends/vault`, `POST /api/trends/sweep`, `POST /api/trends/ingest-link` (400 missing URL)

**ComfyUI**
- [ ] `GET /api/comfy/status`, `POST /api/comfy/generate` (400 missing prompt), `POST /api/comfy/qc-audit` (400/404), `GET /api/comfy/audit-log`
- [ ] `POST /api/comfy/generate-glb`, `POST /api/comfy/purge-vram`, `POST /api/comfy/prewarm`
- [ ] `POST /api/system/prune-staging` (default `hours=48`)

**Outputs** ✅ `test_output_gallery.py`
- [ ] `GET /api/outputs/file|preview|archive|categories|gallery` — already covered this session; re-verify after any future route change

**Cross-cutting route checks 🔧**
- [ ] Every route in this inventory: unauthenticated → 401/redirect unless it is in `PUBLIC_PATHS`/`PUBLIC_PREFIXES`
- [ ] `/api/radar/webhook/config` response must not echo the Stripe secret
- [ ] `/api/newsletter/send-test` has a hardcoded default recipient — verify/decide
- [ ] `/api/system/prune-staging?hours=0` or negative must not delete everything
- [ ] `/api/vram/config` change is not persisted across restart (document)
- [ ] `/api/comfy/generate-glb`, `/purge-vram`, `/prewarm` run blocking calls inside async handlers

---

## E. File Upload / Download & Path-Traversal Safety 🆕
- [ ] Upload filename sanitization strips directory components (`/api/photos/upload`, `/inspiration/upload`, `/upload`, `/operator/chat`)
- [ ] `/api/media/{file_path:path}` rejects paths outside approved dirs via `is_relative_to()`
- [ ] All `/api/download/*` ZIP routes return 404 for a missing file (never leak path info)
- [ ] Output category resolver rejects unregistered categories (404) and traversal outside category base (403)
- [ ] 🔧 `/api/download/{etsy|fiverr|cam-template|photos-zip}/{name}`: name is not sanitized — test `..\`, `../`, absolute path, and `.zip`-only enforcement (Windows backslash traversal)
- [ ] 🔧 Absolute-path inputs: `/api/pipeline/start`, `/api/open-folder`, `/api/comfy/qc-audit`, `iris_qc_audit` tool — should they be sandboxed? (arbitrary read/open today)
- [ ] 🔧 Synapse scrapes any URL in a message (image/article fetch incl. LAN) — SSRF behavior

---

## F. Output Gallery / Preview / Archive Browsing ✅ `test_output_gallery.py`
- [ ] View (inline) vs Download (attachment) content-disposition separation for every media type
- [ ] Video/audio range requests (206 partial content)
- [ ] ZIP archive listing without extraction; per-member preview/download URLs; unsafe members (traversal, symlink, encrypted) excluded
- [ ] 256 MiB member size cap (413), unsupported format (415), damaged ZIP (422), >2000-entry archive (413)
- [ ] HTML previews sandboxed (CSP `sandbox;`, `X-Content-Type-Options: nosniff`) — scripts don't execute
- [ ] All three endpoints require login (401 when logged out)

---

## G. Pipeline Orchestrator (`orchestrator.py`) 🆕
- [ ] `create_job` generates `wh_<8hex>` ID, initial status `queued`, no video-existence check at creation
- [ ] `run_job_async` runs in daemon thread; no duplicate-job or cancellation protection (document as known gap or test the actual behavior)
- [ ] 8-stage pipeline: inspection → 6-pose extraction → teaser/social crops → audio transcription → visual/forensic analysis → prompt synthesis → copy generation → package export
- [ ] Progress clamps to 0–99% until final completion (100%)
- [ ] Any stage exception → job transitions to `failed`, error stored, event emitted
- [ ] Successful run → `completed` at 100%
- [ ] `to_dict()` retains only last 50 log entries; duration computed only when both timestamps exist
- [ ] Subscriber callback exceptions are swallowed (don't crash the pipeline)
- [ ] 🔧 Stage 8 `export_bundle` is invoked (PackageExporter is wired here) — **[CORRECTED]** from FLAGGED #3
- [ ] 🔧 Config reloaded per job (unlike ComfyUIBridge, which loads once at init)
- [ ] 🔧 `workspace/temp/<job_id>/` is never pruned (prune is non-recursive/files-only) — disk leak
- [ ] 🔧 LLM/Whisper error strings ("Ollama connection error…", "[Transcription error: …]") must not end up as deliverable content in `vision_agent`, `prompt_synthesizer`, `audio_agent` output or the package
- [ ] 🔧 Echo ignores `gpu1_arbiter.acquire` result; Forge/NVENC never acquires; ffmpeg timeouts (120s/180s) can leave a partial file treated as success; teaser always cuts from t=0

---

## H. Photo Retoucher ✅ `test_photo_retoucher_engine.py`
- [ ] Four style profiles (`glamour`, `natural`, `concert_stage`, `family_event`) each produce same-shaped `uint8` output
- [ ] Unknown style falls back to raw args rather than rejecting
- [ ] Skin smoothing/clarity/color-grade/blemish-heal/tone-correct/shine-reduce/eye-redness passes stay within skin mask, errors return original image unmodified
- [ ] LAB reference color-matching
- [ ] 16-bit TIFF export: ICC tag 34675, configurable DPI (default 300)
- [ ] `process_photo_batch` output structure: 5 numbered subfolders, one package ZIP named `<shoot>_RETOUCHED_PACKAGE`
- [ ] `edit_style` override vs legacy watermark-always-on backward compatibility
- [ ] Per-file failure doesn't necessarily abort the whole batch

---

## I. Metadata Scrubber ✅ `test_scrubber.py`
- [ ] In-place JPEG scrub, separate PNG output, zero EXIF after processing
- [ ] Atomic temp-file write + replace; temp file removed on error
- [ ] Missing input file returns structured error (not exception)
- [ ] `scrubbed_count` increments only on success
- [ ] 🔧 Integration: Scrubber runs only on Herald's QC-passed branch — verify it is skipped (or not) on QC-bypassed, failed-QC and video paths and decide if that is acceptable

---

## J. Inspiration Scanner / Cipher Vault 🆕
*(Audit taken as-is; not re-verified independently)*
- [ ] `scan_and_analyze`: named-file lookup falls back silently to newest 4 images if name not found
- [ ] Empty vault → `status: empty`
- [ ] Vision call 180s timeout; result cached by content hash (`blueprint:<hash>`); cache survives file untouched, invalidates on mtime change
- [ ] `generate_comfyui_prompts`: regex parses Sections 1–3; malformed model output falls back to hardcoded prompts rather than failing
- [ ] Vault cache trimmed to newest 50 entries on save

---

## K. Cam Template Generator / Tip Menu Builder 🆕
*(Audit taken as-is; not re-verified independently)*
- [ ] `validate_tip_menu_inputs` flags missing/placeholder avatar, banner, top tipper, schedule, empty items — returns human-readable list, doesn't raise
- [ ] Unknown theme silently falls back to `neon_cyber`
- [ ] `bundle_tip_menu_product` writes VIP profile + table/card menus + OBS overlay + chatbot text + install guide + ZIP, all under `<bundle_name>/`
- [ ] Missing avatar/banner/top-tipper values replaced by demo defaults (not rejected) in `generate_full_bundle`
- [ ] Items missing `tokens`/`action` keys raise (should be tested as expected-failure, not silently handled)

---

## L. DaVinci Resolve Bridge ✅ `test_davinci_bridge.py`
- [ ] All 9 photo-retoucher styles have CDL entries (Slope/Offset/Power/Saturation); unsupported style falls back to `natural`
- [ ] Resolve-not-running → `DaVinciBridgeUnavailable`, never touches native DLL
- [ ] `check_connection()` never raises, returns structured connected/error dict
- [ ] `grade_still_image` polls every 1s up to 120s; `grade_video_clip` polls every 2s up to 600s
- [ ] Missing source file, Resolve-offline grading → structured `success: false` (not exception)

---

## M. Package Exporter 🆕
- [ ] `export_bundle` skips missing optional assets (poses/previews/crops) rather than failing
- [ ] Output structure: 5 numbered folders + `PROMO_MEDIA_PACKAGE.md` + ZIP named `<video_stem>_PROMO_PACKAGE`
- [ ] Progress callback fires at 20/80/100
- [ ] **[CORRECTED]** Integration is tested via orchestrator stage 8 (see G). Etsy/Fiverr/dropzone do not use it (FLAGGED #3)

---

## N. Dropzone Watcher / Fulfiller 🆕
- [ ] `run_watcher` polls `F:\WORKHORSE\dropzone` every **3s**, continues after per-cycle exceptions
- [ ] Processed inputs renamed with `PROCESSED_` prefix only on success
- [ ] Missing/empty/unreadable images are skipped (not aborting the whole folder)
- [ ] **Known gap to verify:** no transaction/rollback — mid-loop exception can leave partial output + un-renamed input simultaneously
- [ ] 🔧 `dropzone_watcher` is standalone — not launched by `server.py` or `run_workhorse.bat`, so "hands-off" fulfillment is not wired
- [ ] 🔧 Leftover `_extracting_*` dirs after a crash get re-processed as new orders
- [ ] 🔧 Flat-copy filename collisions silently overwrite/lose photos
- [ ] 🔧 `photos_processed` counts unreadable files (e.g. `.dng` via cv2 returns None)
- [ ] 🔧 No file-stability check — half-copied zips fail
- [ ] 🔧 Duplicates retouch logic instead of `process_photo_batch`; docstring claims RAW/Dual-GPU but it is CPU OpenCV
- [ ] 🔧 Output `*_FINAL_DELIVERY_PACKAGE.zip` does not match the `/api/download/fiverr/{order_number}` naming — verify download works

---

## O. Order Radar & Webhooks 🆕 (business-critical — highest priority)
- [ ] **Stripe:** HMAC-SHA256(`t.payload`) signature validation via `hmac.compare_digest`; missing/malformed header → `invalid_signature` (400); malformed JSON → failure; only `checkout.session.completed` processed, other event types ignored with `success:true`; missing buyer email fails
- [ ] **Gumroad:** no signature — exact `seller_id` string match required; missing config → `awaiting_setup`; mismatch → `invalid_seller`; `test=true` pings ignored; missing buyer email fails
- [ ] **Email radar (IMAP):** subject keyword gate (`order|sale|bought|purchased|sold|payment|receipt|booked|gig`); Fiverr vs Etsy classification by sender/subject substring; missing app password → `awaiting_app_password`; auth failure → `auth_error`; duplicate order ID skipped
- [ ] **Download token:** `secrets.token_urlsafe(24)`, **14-day TTL**, public route — see FLAGGED item #1
- [ ] Simulated Fiverr order starts `pending`; simulated Etsy order starts `fulfilled_auto`
- [ ] Manual fulfill transitions `pending → fulfilled`, records `fulfilled_at`; 404 for unknown order ID
- [ ] Duplicate webhook (same external order ID) → `ignored:true`, no re-fulfillment
- [ ] Missing Fiverr delivery assets → ZIP still created with just the delivery note (not a hard failure)
- [ ] See FLAGGED item #5 above re: `auto_check` polling
- [ ] 🔧 `_extract_order_id` regex `#?([A-Z0-9]{5,10})` can match plain words (e.g. "ORDER") → collisions → real orders silently deduped
- [ ] 🔧 Email-order amounts are hardcoded ($35 / $24.99); only last 10 messages scanned
- [ ] 🔧 Stripe: no timestamp-tolerance/replay check; `payment_status` not checked (unpaid `checkout.session.completed`); no idempotency lock (concurrent duplicate webhooks may double-fulfill)
- [ ] 🔧 Download URL hardcoded to a private IP over `https` (FLAGGED #13)
- [ ] 🔧 `/api/radar/simulate` writes to the real `orders_history.json` (needs isolation, see AE)
- [ ] 🔧 `orders_history.json`, radar config use plain `open('w')` (not `atomic_writer`) — read-modify-write races; only download tokens are atomic
- [ ] 🔧 Tracked config contains a secret (FLAGGED #12)

---

## P. Etsy Digital Store 🆕
*(Audit taken as-is; not re-verified independently)*
- [ ] `all` bundle contains exactly: Lightroom presets (5 `.xmp`), model contracts, posing guide HTML, social promo templates, listing metadata/tags
- [ ] Bundle naming: `ETSY_DIGITAL_CREATOR_{TYPE}_PACK`; ZIP entries relative (no absolute paths leaking local filesystem structure)

---

## Q. Fiverr Service Bot 🆕
- [ ] **[CORRECTED — see FLAGGED #8]** Documented intent only; actual code uses `list(glob("*.zip"))[-1]` (last in directory order, not newest, not client-bound). Asset selection per gig type: `gig_retouch`→newest photos ZIP, `gig_teaser`→newest output ZIP, `gig_copy`/`gig_banner`→newest cam-template ZIP
- [ ] Delivery packages use guessable `{order_number}_DELIVERY_PACKAGE.zip` names (no token) — confirm this is accepted risk vs Etsy/Stripe's tokenized flow

---

## R. Trend Researcher (Cipher) 🆕
*(Audit taken as-is; not re-verified independently)*
- [ ] `offline_cache_only: true` config respected — verify no live network call happens unless explicitly invoked
- [ ] `ingest_user_link` produces summary + insights + thread + newsletter blurb from a user URL
- [ ] `run_daily_radar_sweep` validates all 5 daily tweet slots + per-publication topics; synthesis failure → fallback content + `used_fallback` flag

---

## S. Omni Marketer 🆕
- [ ] Campaign builders per channel: Fiverr, Etsy, social, website, generic fallback — each produces channel-appropriate copy/CTA/hashtags
- [ ] Campaign history persistence and `limit` param on retrieval
- [ ] 🔧 Mercury is a campaign-copy generator only — no Reddit/Twitter broadcast exists despite the Synapse prompt (see AH)

---

## T. Herald Scheduler — Daily Drop ✅ `test_herald_dispatch_healing.py`
- [ ] 5 daily slots at fixed times: 09:00, 13:00, 17:00, 20:30, 23:00 — correct brand/handle resolution per slot (`creatorpulselab` vs `TheCreatorAsset`)
- [ ] "3/5 Slots" badge = count of **verified-successful** dispatches, not attempts
- [ ] Slot only marked executed when **all** required posts for that slot succeed
- [ ] `MAX_DISPATCH_RETRIES = 3`; failed/exception Twitter post stays retryable; success is never re-posted
- [ ] Incident + Commander notification fires **exactly once** after retry exhaustion (not every poll tick)
- [ ] Pinterest watchdog is a true no-op (no incident/alert) when `pinterest.enabled=false`
- [ ] Day rollover resets slot/publication/Pinterest/alert state
- [ ] `run_loop()` 60s poll interval; radar sweep 08:00→10:30 retry window then fallback acceptance
- [ ] Content engine dispatched once daily at 11:30, staged for manual review (never auto-posted)
- [ ] 🔧 Restart mid-day: all missed slots fire back-to-back with stale content — verify/decide
- [ ] 🔧 Run loop awaits tasks sequentially; a long content-engine/video-upgrade run delays other dispatches
- [ ] 🔧 `dispatch_today_all_now` dispatches only slot 1 (name implies all)
- [ ] 🔧 Herald brand visual: fresh render + QC pass else last QC-passed visual; video upgrade on `slot_4_evening`
- [ ] 🔧 `daily_schedule_state.json` uses non-atomic writes

---

## U. Newsletter Manager ✅ `test_newsletter_content_freshness.py`
- [ ] Per-publication issue counter: stable within a day, increments on a new day, independent across `creator_pulse`/`studio_wire`/`creator_blueprint`
- [ ] Scribe-generated content actually renders into HTML output (not silently discarded)
- [ ] Missing/empty Scribe content falls back to static copy without crashing
- [ ] `unsubscribe(email, "all")` clears every publication; removing last publication sets `status=unsubscribed`
- [ ] Email normalization to lowercase; unknown email → error
- [ ] `/api/newsletter/preview?pub=X` returns correct HTML per publication, default `creator_pulse`
- [ ] 🔧 Send times: `studio_wire` 08:30, `creator_pulse` 09:00, `creator_blueprint` 10:00
- [ ] 🔧 `dispensary_deals` (legacy subprocess, 09:00) — verified via the "[Email] Sent to" log; `email_disabled` currently counts as success — decide if it should
- [ ] 🔧 `/api/newsletter/send-test` hardcoded default recipient

---

## V. Twitter Poster 🆕
*(Audit taken as-is; not re-verified independently)*
- [ ] Case-insensitive handle→credential resolution (`@TheCreatorAsset`, `@creatorpulselab`)
- [ ] SHA-256 duplicate-tweet prevention window: **7 days**
- [ ] Chunked video upload + processing-status poll; image metadata scrubbed before upload
- [ ] Missing credentials / empty payload / partial thread failure → `success:false`, slot stays retryable

---

## W. Pinterest Poster 🆕
*(Audit taken as-is; not re-verified independently)*
- [ ] Token refresh within 5-minute expiry buffer
- [ ] `is_pinterest_safe()`: only `content_type="general"` allowed — adult terms/paths hard-blocked (compliance-critical, test explicitly)
- [ ] Duplicate-pin prevention window: **7 days**
- [ ] Missing board/image/credentials → rejected before API call
- [ ] Disabled in config (`pinterest.enabled=false`) → Herald never attempts a post, no failure recorded

---

## X. Content Engine 🆕
- [ ] `run_autonomous_cycle`: image→video→export pipeline; failure at any stage reports which stage failed
- [ ] Result staged for manual review, not auto-published
- [ ] 🔧 Cycle order: Cipher theme → ComfyUI image (Iris QC) → image-to-video → Forge teaser/crops → Scribe copy
- [ ] 🔧 A QC-failed image (returned `success: True`, `qc_audit.passed=False`) must not feed video/copy (FLAGGED #6)

---

## Y. Copy/Prompt Synthesizers 🆕
- [ ] Aura config (tone preset, PPV price `$18.00`, hashtag count 25, CTA text) flows into generated copy
- [ ] **Verify discrepancy:** fallback schema default PPV is `$15.00` vs configured `$18.00` — confirm runtime value wins
- [ ] Prompt kit generates FLUX image prompt + sub-90-word motion prompt + 6 pose variations; malformed model output falls back to single-prompt default
- [ ] 🔧 LLM error strings from `ai_providers` are not embedded in prompt/copy output; `copy_synthesizer` falls back to a static kit on JSON failure
- [ ] 🔧 `ai_providers.get_text_model` reads `agents.aura.text_model`, not `agents.scribe.text_model`

---

## Z. Synapse AI Operator — chat tool dispatch ✅ `test_client_isolation.py`, `test_client_character_and_pbr3d.py`
- [ ] **[CORRECTED]** Synapse has ~44 tools; the list below is the original ~25 (missing: `check_daily_schedule`, `gpu_guardrails_status`, `comfy_generate_glb`, `comfy_search_models`, `block_swap_model`, `hardware_allocation`, `repair_subscribers`, `newsletter_stats`, `ingest_link`, `get_daily_trends`, `scan_inspiration_vault`, `webhook_fulfillment_status`, `content_engine_run_now`, `content_engine_status`). Each tool action (`comfy_generate`, `comfy_image_to_video`, `comfy_generate_3d_pbr`, `comfy_generate_client_character`, `comfy_background_change`, `comfy_subject_swap`, `aura_retouch`, `create_banner`, `apex_package`, `generate_tip_menu`, `newsletter_add/remove`, `herald_dispatch_now`, `radar_scan_now`, `system_diagnostics`, `fix_vram_overflow`, `comfy_status`, `iris_qc_audit`, `comfy_remote_purge`, `comfy_prewarm`, `prune_staging_buffer`, `scrub_file_metadata`, `trend_radar_sweep`, `incident_log`, `notify_commander`, `generate_shoot_concepts`) — required-param validation + error path
- [ ] `_attach_media()`: no-op on missing/invalid/uncategorized path, never raises (✅ covered)
- [ ] **Session isolation:** per-session chat history file; upload batch dir never crosses sessions; `aura_retouch`/`apex_package` only see current session's files (✅ covered)
- [ ] **Adult-mode gating:** `adult_allowed = toggle OR explicit-keyword-detection`; client-character generation is **hard-gated** — tool JSON cannot bypass; `minimax_h3`/adult video tuning only active when `adult_allowed`
- [ ] **Self-healing:** `auto_remediate()` — storage warning→prune+log; corrupted subscribers DB→repair; Ollama offline→log only (no restart attempt)
- [ ] `run_daily_health_check`: one snapshot/day, `force=True` replaces not duplicates
- [ ] Vision auto-detection switches model when images/image-language present; web-search toggle + automatic trend-keyword override; link ingestion for detected URLs
- [ ] Client-character generation: only `charlette`/`margo`/`melissa` valid; PBR 3D requires existing source image + online ComfyUI (✅ covered)
- [ ] 🔧 Tool-call parsing: `raw_tools_pattern` is non-greedy and truncates nested JSON (items, loras); unfenced nested calls are silently dropped (`except: pass`)
- [ ] 🔧 Tool results are not fed back to the LLM (single pass)
- [ ] 🔧 Vision model chosen as first model containing "vl" — ignores `agents.iris.vision_model`
- [ ] 🔧 `get_live_task_status_context` calls `comfy_bridge.check_connection()` synchronously every turn
- [ ] 🔧 "update ideas"/"update tweets" keywords trigger a blocking full radar sweep
- [ ] 🔧 Adult-keyword detection is broad ("lingerie", "boudoir", "onlyfans") with no negation handling
- [ ] 🔧 Status text claims a "25s socket timeout"; actual vision default is 60s
- [ ] 🔧 Synapse has no tools for: video pipeline start, Fiverr/Etsy bundle fulfillment, Mercury campaigns, tweet publish, radar order fulfill, newsletter send, content-engine approval — confirm this is intended
- [ ] 🔧 `run_system_diagnostics` does not check ComfyUI, Whisper/GPU1, Herald, IMAP, Twitter credentials or ffmpeg; `dual_gpu` always "ok"
- [ ] 🔧 `notify_commander` depends on `F:/AI_Media_Scripts/deals_config.json` (outside repo)

---

## AA. ComfyUI Bridge 🆕 (large surface, GPU-dependent — mock network calls)
- [ ] `check_connection()`: tries primary host then each fallback host in `config.json`; ~1.2s timeout; online requires HTTP 200 + parseable JSON
- [ ] **IRIS QC audit:** rejects on `extra_limbs_detected`, `facial_distortion_detected`, or `aesthetic_score < 7.5`; retries with new seed up to `max_retries=2`; vision-parse failure → permissive fallback (score 8.0, approved) — see FLAGGED item #2
- [ ] Standard generation: workflow patch → queue → poll `/history` every 1.5s → download → QC → seed-retry loop
- [ ] Image-to-video: upload → queue → poll every tick, default 900s timeout → download → move to `VIDEO_RENDERS_DIR[/dest_subdir]`
- [ ] `dest_subdir` correctly isolates per-brand social video output from ad-hoc Synapse renders (✅ partially covered)
- [ ] GLB/3D character: concept-plate generation → mesh conversion; mesh failure still returns concept art with `glb_ready:false` (doesn't silently claim success)
- [ ] PBR/GLB: missing source/template/offline Comfy/timeout/missing GLB are explicit distinguishable failures
- [ ] Background-change & subject-swap: both required source files validated before queueing; subject-swap requires both pose image AND reference face image
- [ ] `remote_purge_vram()` / `prewarm_model()`: online/offline branches, prewarm doesn't wait for full render
- [ ] 🔧 Failed QC after retries returns `success: True` + `warning` + `passed=False` (FLAGGED #6)
- [ ] 🔧 QC error paths: timeout → reject, but connection/HTTP error strings → auto-approve 8.0 (FLAGGED #7)
- [ ] 🔧 `wait_for_execution` timeout is 90s for images and does not cancel the ComfyUI job
- [ ] 🔧 `.comfy_bridge.lock` is PID-based: threads in one process share a PID (no mutual exclusion); `finally` deletes the lock when the first caller finishes
- [ ] 🔧 `ComfyUIBridge.load_config` runs only at init — QC config changes need restart

---

## AB. Shared Infrastructure 🆕
- [ ] **`ai_providers.py`:** agent-specific model override takes precedence over `ai_engine` default; empty response triggers one retry; OOM/500 triggers VRAM purge + one retry; vision timeout issues best-effort unload (`keep_alive:0`); no cloud fallback exists — Ollama-down returns error string, doesn't silently fail over
- [ ] **`atomic_writer.py`:** temp-file write→fsync→validate-reread→backup→`os.replace()`; crash before replace leaves original intact; crash after replace leaves new file; `safe_read_json()` falls back to `.bak` on missing/corrupt primary, restores it
- [ ] **`gpu1_arbiter.py`:** lock file `task_name:pid`; dead-PID stale-lock auto-recovery via `tasklist`; 45s acquisition timeout → returns `False`; same-PID reentrant acquire; no FIFO ordering — test for fairness/starvation under contention
- [ ] **`system_monitor.py`:** see FLAGGED item #4; Ollama `/api/tags` failure → `online:false, models:[]`
- [ ] **`vram_manager.py`:** idle timeout exactly 300s, watchdog tick every 5s, `is_busy()` resets idle timer while callback reports active jobs; staging prune only scans `comfy_staging`+`temp` non-recursively
- [ ] 🔧 `gpu1_arbiter`: `release` uses substring match (`str(pid) in content`); `acquire` is non-atomic (exists→write); same-PID reentrant returns True even across threads
- [ ] 🔧 `ai_providers`: any HTTP 500 (not just OOM) triggers a global VRAM purge + retry; errors are returned as strings
- [ ] 🔧 `atomic_writer` is used only for download tokens; incident/error/daily-health/chat-session logs, `client_batches.json`, `orders_history.json`, radar config, `daily_schedule_state.json`, agent `config.json` writes are plain `open('w')`
- [ ] 🔧 `system_monitor` / `get_status()` block the loop with sync `requests` + `nvidia-smi`

---

## AC. Frontend UI 🆕
**Polling/timers**
- [ ] Telemetry poll every 4s (`app.js`) — stale HUD on fetch failure (no crash)
- [ ] SYNAPSE health poll every 20s; Herald status poll every 30s; Radar status poll every 30s
- [ ] WebSocket reconnect after 3s on close
- [ ] Transient UI auto-resets: quick-feedback (4s), agent idle-return (1.8s), health modal delay (800ms), copy-button label restore (1.5–2s)

**Bays/navigation**
- [ ] Each of the 11 bays loads its expected data on first activation (Completed Work, Etsy, Fiverr, Cam Templates, Marketing Hub, Newsletter Hub, Photo, Inspiration, Pipeline, Operator, Factory/3D)
- [ ] Mobile 3-pane switcher (SYNAPSE/DOCK/FULFILLMENT) shows exactly one pane at a time; bay-nav auto-switches to viewport pane at ≤1024px width

**Output viewer**
- [ ] View/Download separation across every bay and chat card; archive browsing; unsupported/oversized format messaging (already smoke-tested; needs permanent regression test)

**3D character viewer**
- [ ] Sprite↔GLB model-viewer toggle loads `/static/models/{charKey}.glb` only on first activation; Idle/Working clip looping

**Uploads/dropzones**
- [ ] Drag-drop + picker + clipboard-paste for Operator; video-only for Pipeline; image-only for Photo/Inspiration; no client-side size/count/MIME validation beyond `accept` hint — confirm backend is the real enforcement point

**Form validation**
- [ ] Empty-message / duplicate-submit-while-generating guards on chat inputs
- [ ] Pipeline requires a selected file before start
- [ ] Newsletter subscribe requires non-blank email (relies on HTML5 `type=email`, not JS regex)

**Agent crew / dossier 🔧**
- [ ] `AGENTS_METADATA` in `agents.js` has 10 agents; missing muse, apex, prism, radar, scrubber — `pipeline.js` calls `setActiveAgent` with muse/scribe/apex (no pod to highlight)
- [ ] Each dossier control either takes effect or is removed (see AG)

---

## AD. Config-Driven Business Rules (cross-cutting, from `config.json`)
- [ ] Changing `agents.iris.pose_count`/`forge.preview_duration_sec` actually changes pipeline output counts/durations — **[CORRECTED]** today only `forge.preview_duration_sec` is honored (output filename is still `preview_60s_*`); `iris.pose_count` is hardcoded to 6 (UI message only). Mark xfail pending the AG decision
- [ ] `comfyui.quality_control.min_quality_score`/`max_retries`/`reject_on_*` flags change QC accept/reject behavior when flipped (**caveat:** `ComfyUIBridge.load_config` loads once at init — restart/re-instantiate to test; the orchestrator reloads per job)
- [ ] `marketing_channels.*.pinterest.enabled=false` suppresses Pinterest dispatch entirely
- [ ] `privacy.strict_local_only` — confirm no outbound cloud AI call is ever made regardless of this flag — **[CORRECTED]** `ai_providers.is_strict_local()` exists but is never called, so the flag is decorative; outbound calls exist (DDGS, Google News, link/image fetch, Twilio, Twitter, Pinterest, SMTP, IMAP, Stripe). Define the intended semantics first (FLAGGED #10).

---

## AE. Test Isolation & Safety 🔧🆕 (do this FIRST)
- [ ] Modules hardcode `F:/WORKHORSE/...` paths; tests must redirect to temp dirs so real `orders_history.json`, `client_batches.json`, `daily_schedule_state.json`, `config.json`, tokens and `.comfy_bridge.lock` are never touched (`conftest.py` currently only sets `sys.path`)
- [ ] Import-time singletons (`order_radar`, `herald_scheduler`, `ai_operator`, `comfy_bridge`) have file side effects — need patch/reset fixtures
- [ ] Network blocked by default: Twitter, SMTP, Twilio, IMAP, Stripe, Ollama, ComfyUI, DDGS/Google News, Pinterest — a real socket opening fails the test
- [ ] `notify_commander` reads `F:/AI_Media_Scripts/deals_config.json` — always mocked
- [ ] `/api/radar/simulate` and tests that create orders must not write the real `orders_history.json`
- [ ] `system_monitor` mock-GPU fallback (FLAGGED #4) must not be mistaken for a real GPU reading in tests
- [ ] Double module import (`python dashboard/server.py`) must not double-run side effects in the test harness

---

## AF. Security & Exposure 🔧🆕
- [ ] `config/order_radar_config.json` is git-tracked with a non-empty `app_password` (FLAGGED #12) — assert it is untracked/ignored and contains no secret (never print values)
- [ ] Server bind host vs `config.system.host` (FLAGGED #14)
- [ ] Path traversal / absolute-path handling for downloads and absolute-path inputs (see E)
- [ ] SSRF via URL scraping in Synapse chat and `/api/trends/ingest-link`
- [ ] Stripe webhook replay/idempotency/unpaid-session handling (see O)
- [ ] Secrets never returned by any config endpoint (`/api/radar/webhook/config`, `/api/radar/status`, `/api/*/config`)
- [ ] Public routes (`/api/download/order/{token}`, webhooks, newsletter subscribe/unsubscribe) rate-limit / abuse behavior documented

---

## AG. Dead / Decorative Config Controls 🔧🆕
Each control: decide **wire it** or **remove it**; until then test as xfail or document.
- [ ] `agents.iris.pose_count` (hardcoded 6)
- [ ] Forge: `video_codec`, `generate_vertical_9x16`, `generate_square_1x1`, `watermark_*`, `nvenc_gpu_index`
- [ ] Echo: `whisper_model`, `compute_type`, `vad_filter`, `device_index`, hook word limits (hardcoded 3–12)
- [ ] Herald `schedule_time`; Vanguard `order_radar_email` / `active_gigs`; Scribe `text_model` / `tone_preset`; Aura retouch fields — saved to `agents.<key>` but nothing reads them
- [ ] `order_radar.auto_check` / `check_interval_seconds` (FLAGGED #5)
- [ ] `privacy.strict_local_only` (FLAGGED #10); `config.system.host` (FLAGGED #14)
- [ ] `trend_researcher` `offline_cache_only` — grep shows no enforcement outside config/UI (re-verify)

---

## AH. Agent Roster Consistency 🔧🆕
- [ ] One authoritative roster across `ai_operator.py` SYSTEM_PROMPT (~14 agents), `agents.js` (10), README ("8 core"), `pipeline.js` active-agent names
- [ ] Vanguard role is consistent (orchestrator: job start/finish; `agents.js`: Fiverr automation; README/`vram_manager`: system watchdog)
- [ ] Mercury role matches reality (campaign-copy generator; no Reddit/Twitter broadcast)
- [ ] Cipher described correctly (trend researcher, not "encryption/crawler")
- [ ] Every pipeline `active_agent` value has a UI pod / highlight
