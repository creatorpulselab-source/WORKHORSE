# WORKHORSE — QA Priority Execution Plan

**Purpose of this document:** Rev 2 (`QA_TEST_CHECKLIST_REV2.md`) and the ecosystem evaluation
(`WORKHORSE_AGENT_INVENTORY_AND_CHECKLIST_EVALUATION.md`) between them surfaced ~230 distinct
checklist items, 14 flagged ambiguous behaviors, and 7 open policy decisions. That's correct and
thorough, but it's organized alphabetically by subsystem (A→AH), which is not the order you should
actually work through it in. This document re-sequences everything by **business risk and blast
radius** — what could cost you money, leak a client's files, or break a live payment flow TODAY,
down to what's just cosmetic.

**How to use this:** Work top to bottom. Each tier lists concrete action items. Where an item needs
deeper technical detail than fits here, it points back to the relevant section letter in
`QA_TEST_CHECKLIST_REV2.md`. Nothing in this document has been implemented yet — it's a plan, same
as the original checklist was, pending your review.

---

## The one rule that governs the ordering

> **Fix-or-decide items are not test-writing exercises.** A few things found during the audit are
> just active bugs or security holes with one obviously-correct fix (a secret shouldn't be in git,
> ever). Those go first and get fixed directly, the same way the Ashley Esteves retouch bug was
> fixed earlier today — find it, prove it with evidence, fix it, write the regression test, verify.
> Everything else goes through: **build safe test infrastructure → write tests in priority order →
> resolve ambiguous-behavior decisions as you reach them.**

---

## TIER 0 — Fix immediately (active risk, not test-dependent)

These aren't "write a test and see" items. They're confirmed problems with a clear correct
direction. Each should be fixed and then locked in with a regression test, the same pattern used
for today's retouch-pipeline fix.

| # | Issue | Why it's Tier 0 | Source |
|---|---|---|---|
| 0.1 | `config/order_radar_config.json` is **tracked in git** with a non-empty Gmail app password, present in commit history (441ceb0, 5eb3f5f) | A live credential is sitting in version control. Anyone with repo access (now or in the future, including any backup/clone) has your email password. | FLAGGED #12 |
| 0.2 | Stripe webhook does not check `payment_status` and has no replay/idempotency protection | An **unpaid** `checkout.session.completed`-shaped event can trigger full fulfillment, and a duplicated/replayed webhook call can double-fulfill the same paid order. This is a direct revenue-loss and fraud vector. | §O / Evaluation §2.3 Security |
| 0.3 | Order-radar customer download URL is hardcoded to `https://100.66.45.48:8800/...` — a private Tailscale IP, while the server speaks plain HTTP | **Paying customers may not be able to download what they bought.** This is the same class of bug as the Ashley Esteves retouch failure — something is "succeeding" on your end while silently failing for the actual recipient. Check this first; it may already be costing you support tickets or refund requests you don't know about yet. | FLAGGED #13 |
| 0.4 | Fiverr fulfillment (`/api/fiverr/fulfill`) selects the delivery asset via `glob("*.zip")[-1]` — last in **alphabetical/directory order**, not newest, and not bound to the specific client at all | A different client's retouched photos or delivery can be sent to the wrong buyer. This is a direct client-trust and possibly privacy/confidentiality breach. | FLAGGED #8 |
| 0.5 | `/api/radar/webhook/config` echoes the Stripe secret back in its response | Any authenticated session (or anyone who can see a screen share/log) can read the live Stripe secret through a normal API call. | Evaluation §2.3 Security |

**Recommended immediate action:** confirm with you on each of these (direction is obvious for
0.1–0.3 and 0.5; 0.4 needs a quick decision on whether Fiverr delivery should always require an
explicit file/order binding rather than "newest-ish guess") and then fix + test them exactly like
the retouch bug was handled today.

---

## TIER 1 — Build test-safety infrastructure (must exist before writing more tests) ✅ DONE (2026-10-10)

This blocks every tier below it. Several modules (`order_radar`, `herald_scheduler`, `ai_operator`,
`comfy_bridge`) create real singleton objects at import time with real file-system side effects, and
hardcode `F:/WORKHORSE/...` paths. `conftest.py` currently only sets `sys.path`. Writing tests
against the real codebase right now risks:
- Sending a real tweet, SMS (Twilio), or email (SMTP) during a test run
- Mutating the real `orders_history.json`, `client_batches.json`, or `daily_schedule_state.json`
- Opening a real socket to Stripe, Twitter, IMAP, Ollama, or ComfyUI from a unit test

**Action items:**
- [x] Add `conftest.py` fixtures that redirect every hardcoded workspace path to a `tmp_path` —
      done for the three singletons confirmed to do real file I/O at import time: `order_radar`
      (secrets + orders + tokens), `herald_scheduler` (daily schedule state + its internal
      `NewsletterManager`), and `newsletter_mgr`. `HeraldScheduler` gained optional
      `state_file`/`newsletter_workspace_base` constructor overrides so this works for both the
      shared singleton and any freshly-constructed instance (back-compat preserved: defaults unchanged).
- [x] Add a fixture/autouse guard that blocks real socket creation by default in the test suite —
      implemented at the `socket.socket.connect`/`connect_ex` level; loopback ephemeral-range IPC
      (needed by asyncio/TestClient) stays allowed, well-known local service ports (Ollama `:11434`,
      ComfyUI `:8188`, WORKHORSE itself `:8800`, IMAP `:993`, SMTP `:587`) stay blocked even on loopback.
- [ ] Add patch/reset fixtures for the import-time singletons so each test starts from clean state —
      **not done**: the three redirected singletons currently persist mutated state across tests
      within a single `pytest` run (they're redirected once, not reset per-test). Tests that need a
      guaranteed-clean instance should keep constructing their own fresh instance pointed at `tmp_path`
      (the pattern already used throughout `test_tier0_security_fixes.py`/`test_client_retouch_pipeline.py`),
      rather than relying on the shared singleton's state between tests.
- [x] Mock `notify_commander`'s dependency on `F:/AI_Media_Scripts/deals_config.json` unconditionally —
      covered indirectly: this file read only happens if/when `notify_commander()` is actually called
      (it's not an import-time singleton risk), and any resulting Twilio API call is now blocked by the
      network guard above regardless. No test currently calls this method directly without mocking it.
- [x] Verify `/api/radar/simulate` and any other order-creating test path never touches the real
      `orders_history.json` — automatic once `order_radar`'s singleton is redirected, since
      `dashboard/server.py` imports and uses that exact (now-redirected) object.
- [x] Confirm the `system_monitor` mock-GPU fallback is never mistaken for a real reading inside a
      test — exposed as `MOCK_GPU_FALLBACK_NAME`/`MOCK_GPU_FALLBACK_MEMORY_TOTAL_MB` constants in
      `conftest.py` for any test that needs to assert against it explicitly.
- [x] Double module import (`python dashboard/server.py`) must not double-run side effects in the
      test harness — fixed at the source: `uvicorn.run()` now receives the already-constructed `app`
      object instead of the string `"dashboard.server:app"`, so there's no second import at all
      (previously this duplicated every singleton's construction on every real production launch too,
      not just in tests).

**Known residual scope (not covered, lower risk, documented rather than silently skipped):**
`inspiration_scanner`, `comfyui_bridge`, and `trend_researcher` also do light file I/O at import
(creating an empty `workspace/inspiration` dir, reading the non-secret `config.json`) but were left
redirect-free since the risk is materially lower (no secrets, no business data mutation). Revisit if
a future test needs stronger isolation here.

Verification: 11 new regression tests (`test_tier1_isolation_infra.py`) covering the block/allowlist
boundary and each redirected singleton. Full suite: 147/147 passing. Committed and pushed.

*(Full detail: REV2 §AE)*

---

## TIER 2 — Business-critical money & client-trust flows

This is where real revenue and client relationships live — and where the Ashley Esteves incident
happened. Highest-value testing target after Tier 0/1.

- [ ] **Order Radar & webhooks (§O):** 🚩 **FLAGGED — come back to this later.** Not yet configured
      (Stripe/Gumroad secrets are empty, no real traffic flowing through this path yet) — deferring
      full test coverage until webhook setup is actually in progress. Tier 0 already fixed the
      confirmed active bugs (payment_status check, replay protection, race condition, secret
      redaction, configurable download URL) with regression tests, so this path is safe-by-default
      even while idle; the remaining items below are the broader test-coverage work, not fixes:
  - Stripe/Gumroad signature & payload validation edge cases, download token lifecycle,
    duplicate-order dedup, `_extract_order_id` regex collision risk (can match plain words like
    "ORDER" and silently dedupe real distinct orders), hardcoded email-order amounts,
    only-last-10-messages IMAP scan limit
- [x] **Fiverr Service Bot (§Q):** ✅ DONE (2026-10-10) — asset-selection safety fixed/tested in
      Tier 0; `fulfill_order()` packaging/delivery flow now covered too (correct ZIP naming,
      missing-asset handling, delivery note content, gig catalog). **Correction to the original
      evaluation:** the "guessable filename" concern is lower-severity than stated — confirmed
      `/api/download/fiverr/{order_number}` is NOT in `PUBLIC_PATHS`/`PUBLIC_PREFIXES`, so it already
      requires a valid WORKHORSE login session, unlike the deliberately-public, token-protected
      Stripe/Gumroad download flow. 7 new tests in `test_fiverr_service_bot.py`.
- [x] **Etsy Digital Store (§P):** ✅ DONE (2026-10-10) — bundle contents/integrity verified (5
      Lightroom presets, 3 legal contracts, posing guide, 2 social templates, listing metadata),
      ZIP entries confirmed relative (no absolute-path leakage). **Bug found and fixed:**
      `bundle_etsy_product()` had no validation of `product_type` — an unrecognized value (e.g. a
      typo in `webhook_product_map`, reachable from the Stripe/Gumroad webhook path) silently
      produced a near-empty bundle (just the listing text file) while still returning `status:"ok"`,
      which could have shipped a paying customer an empty deliverable with no error anywhere. Now
      falls back to `"all"` and reports both the resolved and originally-requested product type.
      9 new tests (`test_etsy_digital_store.py`).
- [ ] **Client retouch/delivery pipeline:** extend today's new `test_client_retouch_pipeline.py`
      coverage — this is proven, recent, high-value ground
- [ ] **Dropzone Watcher/Fulfiller (§N):** this section was flagged "weak" in the evaluation and has
      the most individually serious defects of any single subsystem:
  - `dropzone_watcher` is **not launched** by `server.py` or the `.bat` — if you believe
    hands-off dropzone fulfillment is active, it currently is not running at all
  - Leftover `_extracting_*` folders after a crash get silently reprocessed as new orders
  - Flat-copy filename collisions silently overwrite/lose a client's photos
  - No file-stability check — a half-uploaded zip is processed as if complete
  - Output filename (`*_FINAL_DELIVERY_PACKAGE.zip`) doesn't match what `/api/download/fiverr/{order_number}` expects
  - **Decide first:** is dropzone an active part of your workflow, or legacy/unused? This
    determines whether it's Tier 2 or can be deprioritized entirely.

---

## TIER 3 — Content & brand quality (what actually gets delivered or posted)

Doesn't lose money directly, but determines whether what reaches a client or goes out under your
brand is actually correct.

- [ ] **IRIS QC fail-open behavior (FLAGGED #2, #6, #7):** a vision-parse failure auto-approves at
      score 8.0; a failed-QC image after retries is still saved with `success: True`, and
      `content_engine.py` only checks `success` (not `passed`), so a rejected image can flow into
      video generation and copy. **Policy decision needed:** should QC failures fail closed
      (reject/block) instead of fail open? See "Decisions Needed" below.
- [ ] **Error strings leaking into deliverables:** LLM/Whisper connection-error text (e.g. `"Ollama
      connection error: ..."`, `"[Transcription error: ...]"`) can end up embedded in actual
      generated copy, transcripts, or prompt text instead of being caught as a failure
- [ ] **Scrubber only runs on Herald's QC-passed branch** — verify whether QC-bypassed, failed-QC,
      and video paths should also strip metadata (privacy/client-safety question)
- [ ] Photo Retoucher (§H), Metadata Scrubber (§I), DaVinci Bridge (§L), Package Exporter (§M) —
      already well-covered by existing tests; extend per REV2 detail

---

## TIER 4 — Automation reliability (Herald, Newsletter, Social)

Reputational/consistency risk — a missed or duplicated post is embarrassing, not financially
catastrophic, but this is your daily-operating automation and deserves solid coverage.

- [ ] **Herald Scheduler (§T):** retry/healing contract (already has `test_herald_dispatch_healing.py`),
      plus new findings: after a mid-day restart, all missed slots fire back-to-back with stale
      content; a long-running content-engine/video job delays other same-cycle dispatches;
      `dispatch_today_all_now` only actually dispatches slot 1 despite the name
- [ ] **Newsletter Manager (§U):** freshness contract (already covered), plus `dispensary_deals`
      legacy publication, actual per-publication send times, and whether `email_disabled` is
      incorrectly counted as a successful send
- [ ] **Twitter Poster (§V) / Pinterest Poster (§W):** duplicate-post windows, Pinterest safety gate
      (adult-content blocking is compliance-critical — test explicitly)
- [ ] **Trend Researcher / Omni Marketer (§R/§S):** correct Omni Marketer is campaign-copy only, not
      a live social broadcaster (no Reddit/X posting exists despite some docs implying it)

---

## TIER 5 — Infrastructure stability (crash/downtime risk)

Could interrupt active work or require a manual restart, but doesn't directly cost money or leak
data.

- [ ] **VRAM circuit breaker:** trips at GPU0 ≥80% for >45s and force-kills `llama-server.exe` — the
      docstring claims it skips this "without an active orchestrator job," but the code never
      actually checks that. **This could kill a legitimate long inference job mid-run.** Policy
      decision needed (see below).
- [ ] **GPU1 arbiter PID-lock issues:** all server threads share one PID, so there's no real
      mutual exclusion between concurrent threads in the same process; `release()` uses a loose
      substring match; `acquire()` isn't atomic; Echo ignores the acquire result entirely and Forge
      never acquires the lock at all
- [ ] **`atomic_writer` is barely used:** only the download-tokens file uses it. Incident log, error
      log, daily-health log, chat-session history, `client_batches.json`, `orders_history.json`,
      radar config, `daily_schedule_state.json`, and `config.json` all use plain `open('w')` with
      read-modify-write races possible
- [ ] **Blocking sync calls inside async code paths:** `system_monitor.get_status()`,
      `comfy_bridge.check_connection()` (called synchronously every chat turn), and the VRAM circuit
      breaker all run synchronous `requests`/`subprocess`/`nvidia-smi` calls inside the async event
      loop — one slow call can stall unrelated requests/websocket traffic
- [ ] `workspace/temp/<job_id>/` is never pruned (disk leak over time); `/api/system/prune-staging?hours=0`
      or a negative value would delete everything in scope

---

## TIER 6 — Synapse chat-operator correctness

Affects what Synapse can reliably do and say, but issues here tend to be visible/catchable in a
normal conversation rather than silently wrong (unlike Tiers 0–3).

- [ ] Tool-call JSON parsing: the regex used to extract tool calls is non-greedy and can truncate
      nested JSON (e.g. a `loras` array or `items` list); an unfenced/malformed nested tool call is
      silently dropped rather than surfaced as a parse error
- [ ] Tool results are not fed back to the LLM for a second pass — Synapse can't react to a tool's
      actual output within the same turn
- [ ] Vision model selection picks "the first installed model with 'vl' in its name" rather than
      honoring `agents.iris.vision_model` from config
- [ ] `run_system_diagnostics` doesn't actually check ComfyUI, Whisper/GPU1, Herald, IMAP, Twitter
      credentials, or ffmpeg — `dual_gpu` always reports "ok" regardless of real state
- [ ] Confirm as intentional (not a bug): Synapse currently has **no chat tool** to start the video
      pipeline, trigger Fiverr/Etsy bundle fulfillment, publish a tweet, fulfill a radar order, send
      a newsletter, or approve content-engine output — all of those require the dashboard UI instead
- [ ] Tool catalog size correction: ~44 tools exist, not ~25 — see REV2 §Z for the corrected list
      before writing per-tool test cases

---

## TIER 7 — Decisions needed before some tests can be written

These aren't bugs with an obvious fix — they're policy calls. A test can't assert "correct"
behavior until you've picked what correct means. Recommend resolving these in order, right before
their corresponding tier is tackled (you don't need to decide #6/#7 today, for instance).

1. **Rotate the Gmail app password and untrack `order_radar_config.json`?** *(blocks Tier 0.1 — recommend yes, immediately)*
2. **Dead config controls** (Forge codec/crop toggles, Echo Whisper settings, pose count, etc.) — wire them up for real, or remove the UI controls so they stop implying something configurable that isn't? *(blocks Tier 5/6 cleanup)*
3. **QC on failure or parse-error: fail closed (reject) or stay fail-open (auto-approve)?** *(blocks Tier 3 IRIS QC tests)*
4. **Fiverr fulfillment: require an explicit client/order-bound file, or keep "pick the newest-ish match"?** *(blocks Tier 0.4 / Tier 2)*
5. **Should the VRAM circuit breaker actually skip tripping while an orchestrator job is active**, matching its own docstring? *(blocks Tier 5)*
6. **Should the agent roster be unified** across README, `agents.js`, the Synapse system prompt, and `pipeline.js`? What should Vanguard and Mercury's roles actually be, given each source currently describes them differently? *(blocks Tier 8 below)*
7. **Should `dropzone_watcher` be started automatically with the server**, or is it legacy/manual-only? *(blocks Tier 2 dropzone scope)*

---

## TIER 8 — Documentation & cosmetic consistency (lowest priority)

- [ ] Agent roster consistency across `ai_operator.py` system prompt (~14 agents), `agents.js` (10),
      README ("8 core"), and `pipeline.js` active-agent references — depends on Decision #6
- [ ] Frontend polling/timer/bay-activation/upload-validation coverage (§AC) — functional but not
      business-critical
- [ ] Remaining broad-regression items from §J, §K, §R, §S, §Y not already elevated above

---

## Recommended execution order, summarized

```
Tier 0  → Fix now (5 items, each: evidence → fix → regression test)
Tier 1  → Build test isolation/safety infra (blocks everything below)
Tier 2  → Order Radar, Fiverr, Etsy, client delivery, Dropzone
Tier 3  → QC integrity, error-as-content leaks, metadata scrubbing
Tier 4  → Herald/Newsletter/Twitter/Pinterest reliability
Tier 5  → VRAM/GPU-arbiter/atomic-writes/blocking-call stability
Tier 6  → Synapse tool-dispatch correctness
Tier 7  → (ongoing) resolve policy decisions as each tier is reached
Tier 8  → Roster/docs/frontend cosmetic cleanup
```

This document does not replace `QA_TEST_CHECKLIST_REV2.md` — that remains the exhaustive,
section-by-section reference for exact test cases. This file is the sequencing layer on top of it.
