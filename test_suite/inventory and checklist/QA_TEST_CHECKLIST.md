# WORKHORSE — QA End-to-End Test Coverage Checklist

Generated via full-codebase audit (dashboard/server.py, pipeline/*, shared/*, dashboard/static/js/*)
against existing `test_suite/` coverage. This is the review checklist — NOT yet translated into test code.

**Legend:** ✅ = existing automated coverage already exists (extend, don't duplicate) · 🆕 = no automated coverage found yet

---

## ⚠️ FLAGGED — Needs a decision before tests are written/run

These behaviors are ambiguous (could be intentional or a bug). Do not write an assertion that
locks in behavior until we've decided which way each one should go.

1. **Order download tokens are reusable** — `/api/download/order/{token}` has no single-use/consumed
   flag despite the fulfillment docstring saying "single-use." A valid token can be reused by anyone
   who has it until the 14-day expiry. (`pipeline/stages/order_radar.py`)
2. **IRIS QC audit fails open** — if vision parsing of the QC response fails, the system falls back to
   a permissive "approved, score 8.0" result rather than rejecting/retrying. (`pipeline/stages/comfyui_bridge.py`)
3. **`PackageExporter` appears unused** — not called by Etsy, Fiverr, dropzone, or order-radar fulfillment
   flows. Possibly dead code, or a missing integration. (`pipeline/stages/package_exporter.py`)
4. **`system_monitor.py` fakes GPU data on failure** — when `nvidia-smi` fails, it returns a hardcoded
   mock RTX 3060 record instead of an error/offline state, which could mask a real GPU failure in the UI.
5. **Order Radar's `auto_check` config does nothing** — it's stored/configurable but no scheduler/loop
   actually polls on an interval; scans only happen via manual `/api/radar/check` or an AI operator tool call.

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

## B. Background Timers / Scheduled Loops (backend) 🆕
- [ ] VRAM watchdog: idle timeout **300s (5 min)**, checks every **5s**, skips purge while `is_any_orchestrator_job_active()` is true
- [ ] VRAM watchdog staging-prune sub-cycle: runs **~every 30 min**, `max_age_hours=48`, only scans `comfy_staging` + `temp` (non-recursive), never touches `brand_assets`/`client_deliveries`
- [ ] Herald scheduler `run_loop()`: polls every **60s**; runs daily radar sweep from **08:00**, retries degraded radar until **10:30** then accepts fallback
- [ ] ComfyUI health monitor: polls every **45s**; online→offline logs `needs_attention` incident; offline→online logs `resolved` incident; exception path marks offline with error text
- [ ] Auto-remediation loop: runs every **600s (10 min)**; calls `ai_operator.auto_remediate()`; cancellation exits cleanly, other exceptions logged and loop continues
- [ ] Startup daily health check: runs once in executor on boot; no-ops if today's entry already exists; `force=True` replaces (not duplicates) today's entry
- [ ] Lifespan shutdown: all 4 background tasks (watchdog, herald, comfy-health, auto-remediation) are cancelled cleanly on server stop

## C. WebSocket (`/ws/telemetry`) 🆕
- [ ] Connect without valid session cookie → closed with code `4401`
- [ ] Connect with valid cookie → accepted, added to `connected_websockets`
- [ ] Broadcasts `{"type":"telemetry", stats}` every **3s** (system stats + Ollama models + VRAM status + cached Comfy health)
- [ ] Orchestrator job events broadcast as `{"type":"job_update", job}` to all connected sockets
- [ ] Socket removed from list on disconnect or send exception; one broken socket doesn't break broadcast to others
- [ ] Frontend reconnects automatically **3s** after close (`pipeline.js`)

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

## E. File Upload / Download & Path-Traversal Safety 🆕
- [ ] Upload filename sanitization strips directory components (`/api/photos/upload`, `/inspiration/upload`, `/upload`, `/operator/chat`)
- [ ] `/api/media/{file_path:path}` rejects paths outside approved dirs via `is_relative_to()`
- [ ] All `/api/download/*` ZIP routes return 404 for a missing file (never leak path info)
- [ ] Output category resolver rejects unregistered categories (404) and traversal outside category base (403)

## F. Output Gallery / Preview / Archive Browsing ✅ `test_output_gallery.py` (built this session — regression-lock it)
- [ ] View (inline) vs Download (attachment) content-disposition separation for every media type
- [ ] Video/audio range requests (206 partial content)
- [ ] ZIP archive listing without extraction; per-member preview/download URLs; unsafe members (traversal, symlink, encrypted) excluded
- [ ] 256 MiB member size cap (413), unsupported format (415), damaged ZIP (422), >2000-entry archive (413)
- [ ] HTML previews sandboxed (CSP `sandbox;`, `X-Content-Type-Options: nosniff`) — scripts don't execute
- [ ] All three endpoints require login (401 when logged out)

## G. Pipeline Orchestrator (`orchestrator.py`) 🆕
- [ ] `create_job` generates `wh_<8hex>` ID, initial status `queued`, no video-existence check at creation
- [ ] `run_job_async` runs in daemon thread; no duplicate-job or cancellation protection (document as known gap or test the actual behavior)
- [ ] 8-stage pipeline: inspection → 6-pose extraction → teaser/social crops → audio transcription → visual/forensic analysis → prompt synthesis → copy generation → package export
- [ ] Progress clamps to 0–99% until final completion (100%)
- [ ] Any stage exception → job transitions to `failed`, error stored, event emitted
- [ ] Successful run → `completed` at 100%
- [ ] `to_dict()` retains only last 50 log entries; duration computed only when both timestamps exist
- [ ] Subscriber callback exceptions are swallowed (don't crash the pipeline)

## H. Photo Retoucher ✅ `test_photo_retoucher_engine.py`
- [ ] Four style profiles (`glamour`, `natural`, `concert_stage`, `family_event`) each produce same-shaped `uint8` output
- [ ] Unknown style falls back to raw args rather than rejecting
- [ ] Skin smoothing/clarity/color-grade/blemish-heal/tone-correct/shine-reduce/eye-redness passes stay within skin mask, errors return original image unmodified
- [ ] LAB reference color-matching
- [ ] 16-bit TIFF export: ICC tag 34675, configurable DPI (default 300)
- [ ] `process_photo_batch` output structure: 5 numbered subfolders, one package ZIP named `<shoot>_RETOUCHED_PACKAGE`
- [ ] `edit_style` override vs legacy watermark-always-on backward compatibility
- [ ] Per-file failure doesn't necessarily abort the whole batch

## I. Metadata Scrubber ✅ `test_scrubber.py`
- [ ] In-place JPEG scrub, separate PNG output, zero EXIF after processing
- [ ] Atomic temp-file write + replace; temp file removed on error
- [ ] Missing input file returns structured error (not exception)
- [ ] `scrubbed_count` increments only on success

## J. Inspiration Scanner / Cipher Vault 🆕
- [ ] `scan_and_analyze`: named-file lookup falls back silently to newest 4 images if name not found
- [ ] Empty vault → `status: empty`
- [ ] Vision call 180s timeout; result cached by content hash (`blueprint:<hash>`); cache survives file untouched, invalidates on mtime change
- [ ] `generate_comfyui_prompts`: regex parses Sections 1–3; malformed model output falls back to hardcoded prompts rather than failing
- [ ] Vault cache trimmed to newest 50 entries on save

## K. Cam Template Generator / Tip Menu Builder 🆕
- [ ] `validate_tip_menu_inputs` flags missing/placeholder avatar, banner, top tipper, schedule, empty items — returns human-readable list, doesn't raise
- [ ] Unknown theme silently falls back to `neon_cyber`
- [ ] `bundle_tip_menu_product` writes VIP profile + table/card menus + OBS overlay + chatbot text + install guide + ZIP, all under `<bundle_name>/`
- [ ] Missing avatar/banner/top-tipper values replaced by demo defaults (not rejected) in `generate_full_bundle`
- [ ] Items missing `tokens`/`action` keys raise (should be tested as expected-failure, not silently handled)

## L. DaVinci Resolve Bridge ✅ `test_davinci_bridge.py`
- [ ] All 9 photo-retoucher styles have CDL entries (Slope/Offset/Power/Saturation); unsupported style falls back to `natural`
- [ ] Resolve-not-running → `DaVinciBridgeUnavailable`, never touches native DLL
- [ ] `check_connection()` never raises, returns structured connected/error dict
- [ ] `grade_still_image` polls every 1s up to 120s; `grade_video_clip` polls every 2s up to 600s
- [ ] Missing source file, Resolve-offline grading → structured `success: false` (not exception)

## M. Package Exporter 🆕
- [ ] `export_bundle` skips missing optional assets (poses/previews/crops) rather than failing
- [ ] Output structure: 5 numbered folders + `PROMO_MEDIA_PACKAGE.md` + ZIP named `<video_stem>_PROMO_PACKAGE`
- [ ] Progress callback fires at 20/80/100
- [ ] See FLAGGED item #3 above before deciding how to test this module's integration status

## N. Dropzone Watcher / Fulfiller 🆕
- [ ] `run_watcher` polls `F:\WORKHORSE\dropzone` every **3s**, continues after per-cycle exceptions
- [ ] Processed inputs renamed with `PROCESSED_` prefix only on success
- [ ] Missing/empty/unreadable images are skipped (not aborting the whole folder)
- [ ] **Known gap to verify:** no transaction/rollback — mid-loop exception can leave partial output + un-renamed input simultaneously

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

## P. Etsy Digital Store 🆕
- [ ] `all` bundle contains exactly: Lightroom presets (5 `.xmp`), model contracts, posing guide HTML, social promo templates, listing metadata/tags
- [ ] Bundle naming: `ETSY_DIGITAL_CREATOR_{TYPE}_PACK`; ZIP entries relative (no absolute paths leaking local filesystem structure)

## Q. Fiverr Service Bot 🆕
- [ ] Asset selection per gig type: `gig_retouch`→newest photos ZIP, `gig_teaser`→newest output ZIP, `gig_copy`/`gig_banner`→newest cam-template ZIP
- [ ] Delivery packages use guessable `{order_number}_DELIVERY_PACKAGE.zip` names (no token) — confirm this is accepted risk vs Etsy/Stripe's tokenized flow

## R. Trend Researcher (Cipher) 🆕
- [ ] `offline_cache_only: true` config respected — verify no live network call happens unless explicitly invoked
- [ ] `ingest_user_link` produces summary + insights + thread + newsletter blurb from a user URL
- [ ] `run_daily_radar_sweep` validates all 5 daily tweet slots + per-publication topics; synthesis failure → fallback content + `used_fallback` flag

## S. Omni Marketer 🆕
- [ ] Campaign builders per channel: Fiverr, Etsy, social, website, generic fallback — each produces channel-appropriate copy/CTA/hashtags
- [ ] Campaign history persistence and `limit` param on retrieval

## T. Herald Scheduler — Daily Drop ✅ `test_herald_dispatch_healing.py` (critical automation core)
- [ ] 5 daily slots at fixed times: 09:00, 13:00, 17:00, 20:30, 23:00 — correct brand/handle resolution per slot (`creatorpulselab` vs `TheCreatorAsset`)
- [ ] "3/5 Slots" badge = count of **verified-successful** dispatches, not attempts
- [ ] Slot only marked executed when **all** required posts for that slot succeed
- [ ] `MAX_DISPATCH_RETRIES = 3`; failed/exception Twitter post stays retryable; success is never re-posted
- [ ] Incident + Commander notification fires **exactly once** after retry exhaustion (not every poll tick)
- [ ] Pinterest watchdog is a true no-op (no incident/alert) when `pinterest.enabled=false`
- [ ] Day rollover resets slot/publication/Pinterest/alert state
- [ ] `run_loop()` 60s poll interval; radar sweep 08:00→10:30 retry window then fallback acceptance
- [ ] Content engine dispatched once daily at 11:30, staged for manual review (never auto-posted)

## U. Newsletter Manager ✅ `test_newsletter_content_freshness.py`
- [ ] Per-publication issue counter: stable within a day, increments on a new day, independent across `creator_pulse`/`studio_wire`/`creator_blueprint`
- [ ] Scribe-generated content actually renders into HTML output (not silently discarded)
- [ ] Missing/empty Scribe content falls back to static copy without crashing
- [ ] `unsubscribe(email, "all")` clears every publication; removing last publication sets `status=unsubscribed`
- [ ] Email normalization to lowercase; unknown email → error
- [ ] `/api/newsletter/preview?pub=X` returns correct HTML per publication, default `creator_pulse`

## V. Twitter Poster 🆕
- [ ] Case-insensitive handle→credential resolution (`@TheCreatorAsset`, `@creatorpulselab`)
- [ ] SHA-256 duplicate-tweet prevention window: **7 days**
- [ ] Chunked video upload + processing-status poll; image metadata scrubbed before upload
- [ ] Missing credentials / empty payload / partial thread failure → `success:false`, slot stays retryable

## W. Pinterest Poster 🆕
- [ ] Token refresh within 5-minute expiry buffer
- [ ] `is_pinterest_safe()`: only `content_type="general"` allowed — adult terms/paths hard-blocked (compliance-critical, test explicitly)
- [ ] Duplicate-pin prevention window: **7 days**
- [ ] Missing board/image/credentials → rejected before API call
- [ ] Disabled in config (`pinterest.enabled=false`) → Herald never attempts a post, no failure recorded

## X. Content Engine 🆕
- [ ] `run_autonomous_cycle`: image→video→export pipeline; failure at any stage reports which stage failed
- [ ] Result staged for manual review, not auto-published

## Y. Copy/Prompt Synthesizers 🆕
- [ ] Aura config (tone preset, PPV price `$18.00`, hashtag count 25, CTA text) flows into generated copy
- [ ] **Verify discrepancy:** fallback schema default PPV is `$15.00` vs configured `$18.00` — confirm runtime value wins
- [ ] Prompt kit generates FLUX image prompt + sub-90-word motion prompt + 6 pose variations; malformed model output falls back to single-prompt default

## Z. Synapse AI Operator — chat tool dispatch ✅ `test_client_isolation.py`, `test_client_character_and_pbr3d.py`
- [ ] Each of the ~25 tool actions (`comfy_generate`, `comfy_image_to_video`, `comfy_generate_3d_pbr`, `comfy_generate_client_character`, `comfy_background_change`, `comfy_subject_swap`, `aura_retouch`, `create_banner`, `apex_package`, `generate_tip_menu`, `newsletter_add/remove`, `herald_dispatch_now`, `radar_scan_now`, `system_diagnostics`, `fix_vram_overflow`, `comfy_status`, `iris_qc_audit`, `comfy_remote_purge`, `comfy_prewarm`, `prune_staging_buffer`, `scrub_file_metadata`, `trend_radar_sweep`, `incident_log`, `notify_commander`, `generate_shoot_concepts`) — required-param validation + error path
- [ ] `_attach_media()`: no-op on missing/invalid/uncategorized path, never raises (✅ covered)
- [ ] **Session isolation:** per-session chat history file; upload batch dir never crosses sessions; `aura_retouch`/`apex_package` only see current session's files (✅ covered)
- [ ] **Adult-mode gating:** `adult_allowed = toggle OR explicit-keyword-detection`; client-character generation is **hard-gated** — tool JSON cannot bypass; `minimax_h3`/adult video tuning only active when `adult_allowed`
- [ ] **Self-healing:** `auto_remediate()` — storage warning→prune+log; corrupted subscribers DB→repair; Ollama offline→log only (no restart attempt)
- [ ] `run_daily_health_check`: one snapshot/day, `force=True` replaces not duplicates
- [ ] Vision auto-detection switches model when images/image-language present; web-search toggle + automatic trend-keyword override; link ingestion for detected URLs
- [ ] Client-character generation: only `charlette`/`margo`/`melissa` valid; PBR 3D requires existing source image + online ComfyUI (✅ covered)

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

## AB. Shared Infrastructure 🆕
- [ ] **`ai_providers.py`:** agent-specific model override takes precedence over `ai_engine` default; empty response triggers one retry; OOM/500 triggers VRAM purge + one retry; vision timeout issues best-effort unload (`keep_alive:0`); no cloud fallback exists — Ollama-down returns error string, doesn't silently fail over
- [ ] **`atomic_writer.py`:** temp-file write→fsync→validate-reread→backup→`os.replace()`; crash before replace leaves original intact; crash after replace leaves new file; `safe_read_json()` falls back to `.bak` on missing/corrupt primary, restores it
- [ ] **`gpu1_arbiter.py`:** lock file `task_name:pid`; dead-PID stale-lock auto-recovery via `tasklist`; 45s acquisition timeout → returns `False`; same-PID reentrant acquire; no FIFO ordering — test for fairness/starvation under contention
- [ ] **`system_monitor.py`:** see FLAGGED item #4; Ollama `/api/tags` failure → `online:false, models:[]`
- [ ] **`vram_manager.py`:** idle timeout exactly 300s, watchdog tick every 5s, `is_busy()` resets idle timer while callback reports active jobs; staging prune only scans `comfy_staging`+`temp` non-recursively

## AC. Frontend UI 🆕
**Polling/timers**
- [ ] Telemetry poll every 4s (`app.js`) — stale HUD on fetch failure (no crash)
- [ ] SYNAPSE health poll every 20s; Herald status poll every 30s; Radar status poll every 30s
- [ ] WebSocket reconnect after 3s on close
- [ ] Transient UI auto-resets: quick-feedback (4s), agent idle-return (1.8s), health modal delay (800ms), copy-button label restore (1.5–2s)

**Bays/navigation**
- [ ] Each of the 11 bays loads its expected data on first activation (Completed Work, Etsy, Fiverr, Cam Templates, Marketing Hub, Newsletter Hub, Photo, Inspiration, Pipeline, Operator, Factory/3D)
- [ ] Mobile 3-pane switcher (SYNAPSE/DOCK/FULFILLMENT) shows exactly one pane at a time; bay-nav auto-switches to viewport pane at ≤1024px width

**Output viewer** (built this session)
- [ ] View/Download separation across every bay and chat card; archive browsing; unsupported/oversized format messaging (already smoke-tested; needs permanent regression test)

**3D character viewer**
- [ ] Sprite↔GLB model-viewer toggle loads `/static/models/{charKey}.glb` only on first activation; Idle/Working clip looping

**Uploads/dropzones**
- [ ] Drag-drop + picker + clipboard-paste for Operator; video-only for Pipeline; image-only for Photo/Inspiration; no client-side size/count/MIME validation beyond `accept` hint — confirm backend is the real enforcement point

**Form validation**
- [ ] Empty-message / duplicate-submit-while-generating guards on chat inputs
- [ ] Pipeline requires a selected file before start
- [ ] Newsletter subscribe requires non-blank email (relies on HTML5 `type=email`, not JS regex)

## AD. Config-Driven Business Rules (cross-cutting, from `config.json`)
- [ ] Changing `agents.iris.pose_count`/`forge.preview_duration_sec` actually changes pipeline output counts/durations
- [ ] `comfyui.quality_control.min_quality_score`/`max_retries`/`reject_on_*` flags change QC accept/reject behavior when flipped
- [ ] `marketing_channels.*.pinterest.enabled=false` suppresses Pinterest dispatch entirely
- [ ] `privacy.strict_local_only` — confirm no outbound cloud AI call is ever made regardless of this flag (since `ai_providers.py` has no cloud path at all — is that intentional or a stub?)
