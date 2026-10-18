# WORKHORSE Bug Check — 2026-10-18
Scope: Synapse image-to-video ("similar but different" / "a whole different video"), the new viral
moments, and the Iris **Style & Pose Lab** ("not writing prompts from the images").

Everything below was reproduced from your real logs/files, fixed, and re-verified **live** on your
real photo (`JT2A6087_teaser_preview.jpg`) — not just unit-tested.

---

## A. What happened to your two Synapse commands

### Command 1 (last night) — "make this image into a video … lick the controller … slowly zoom to her mouth"
Result: right subject, but a different-feeling video. Frames showed an **extreme macro of the tongue/controller** by
the end and the framing was cropped.

| # | Root cause | Evidence |
|---|-----------|----------|
| 1 | **Photo forced from 4:5 to 9:16.** Every I2V was hard-wired to 720×1280, so your 3648×4560 (4:5) portrait lost its sides before frame 0. | video was 704×1280 |
| 2 | **The prompt told the model to START tight.** The LLM wrote *"A close-up shot of a woman with her tongue extended…"* although your photo is a medium shot, then zoomed for ~10 s → extreme macro. | `expanded_prompt` in the session file |
| 3 | **The motion prompt was written blind.** For animate commands the operator LLM deliberately never receives the photo. | `is_vision=False, images_sent_to_LLM=0` (reproduced) |
| 4 | **Every video got "sensual chill melodic beat" appended**, even SFW/brand ones. | `build_image_to_video_workflow` |

### Command 2 (this morning) — "use the micro cinema image to video workflow on this image"
Result: **a man walking down a rainy neon street.** Frame 0 was your photo, then it cut to that scene.

| # | Root cause | Evidence |
|---|-----------|----------|
| 1 | **No route to the viral director.** "micro cinema" (with a space) never mapped to `comfy_viral_video_director`; the generic I2V tool ran instead. | tool = `comfy_image_to_video` |
| 2 | **The LLM invented the scene** ("rain-slicked city street at night, neon…") because it couldn't see the photo — and LTX treats the text as authoritative after frame 0. | frames 60+ |
| 3 | **Weaker model, no image.** The browser flips the dropdown to the 8B vision model when a photo is attached; the server then ran *that* model blind. | session `model` field |
| 4 | **Web search polluted the turn** ("best cinema cameras 2026" articles). | `web_sources_count=4` |

### The big hidden one — Synapse was reading ~29% of its own instructions
Ollama's log, at the exact second each of your videos finished:
```
06:37:56 WARN truncating input prompt limit=4098 prompt=14385 keep=4 new=4098
22:02:56 WARN truncating input prompt limit=4098 prompt=13648 keep=4 new=4098
```
Synapse sent ~14K tokens; Ollama silently cut it to ~4K (keeps only the first 4 tokens + the tail). Verified by experiment:
when a prompt doesn't fit `num_ctx`, Ollama truncates to **`num_ctx/2 + 2`** — so `num_ctx: 8192` really meant 4,098.
The tool documentation lived in the discarded middle, which is why the only tool the model "knew" was the one named in the
injected upload note. It has been happening since at least 10-15 (8 truncation events logged).

---

## B. Iris Style & Pose Lab — why it wrote nothing from your images
All four attempts this morning (06:26–06:31) failed with:
`HTTP 400 … request (5868–8017 tokens) exceeds the available context size (4096)`.

| # | Root cause |
|---|-----------|
| 1 | The vision call used **`num_ctx=4096`** and **`num_predict=350`** — the Iris system prompt alone is ~3.7K tokens, plus ~0.9K instructions, plus ~1.2K per image ⇒ ~5.9K tokens. **Every call failed**, and even one that fit could only emit 350 tokens (the answer needs ~1,200+). |
| 2 | The failure string was **cached**, and the parser then **fell back to a hard-coded "glamour model / sheer lace" prompt** — shown in the UI as if it came from your photo, under a green "✓ ready". |
| 3 | The UI never checked for errors. |
| 4 | The test suite had poisoned the real cache with a "blocked network connection" message (10-12). |
| 5 | (found while verifying) At low temperature the model fell into a **repetition loop** — `oversaturated, oversharpened, oversmoothed` ×400 — that ate the whole token budget and starved the video prompt. |

---

## C. What was fixed

**Synapse / image-to-video**
- Prompt now **fits the window**: `num_ctx` 8192 → **16384**, knowledge slice sized to the room left, low-value blocks shed
  if still tight; budget logged on every turn (`[SYNAPSE Prompt Budget]`) and returned as `prompt_budget`.
- The second-pass summary no longer re-sends the 13K-token system prompt (it was truncated too).
- **Deterministic viral routing** (`synapse_media_router.py`): *micro cinema / handheld camera / fast cut / one take / time lapse*
  go straight to `comfy_viral_video_director`. "Use a viral moment" with no mode **asks which of the 5** (clickable options).
- **Grounded motion prompts**: Iris captions the photo (cached); a prompt describing scenery that's in neither the photo nor your
  words is **discarded** and rebuilt from *your* wording; "close-up shot of…" openers are rewritten; a continuity anchor is
  appended ("same subject/outfit/setting/lighting, no cut").
- **Aspect-correct video size**: 4:5 photo → 768×960 (same pixel budget, multiples of 64) instead of 704×1280.
- Media commands use the **14B** operator even if the UI sent the vision model; **web search is skipped** on media commands.
- Neutral default soundtrack (no forced "sensual").
- Removed substring bugs: `"remove the background"` no longer matches "**move**", `"click"` no longer matches "**lick**".
- Removed a fallback that could animate **another client's** newest upload.

**Viral Video Director** (bugs only visible once the route reached it)
- **Plates leaked between photos**: work folder was per *mode*, plates cached by file name — a 2nd photo reused the 1st photo's
  plates (a video of the previous subject). Now keyed to the photo's bytes **and** each plate to its exact prompt.
- **False success**: it returned `success: True` for a reel that didn't exist when Resolve was closed. Now validated; if Resolve
  isn't running it **falls back to an ffmpeg NVENC master** (Lanczos + 3D LUT) and says so honestly.
- **Invented objects**: Micro Cinema's prompt said "jewelry or sunlit glass/prop", so Klein painted gold rings and glassware onto a
  photo that had neither. All 5 modes now describe real detail *types* and carry a "use only what's visible" guard.
- **Black bars**: 4:5 clips letter-boxed in the 9:16 reel; clips are now center-cropped at native resolution before Resolve.

**Style & Pose Lab**
- Window/outputs sized for the real prompt (`num_ctx` 12288, `num_predict` 1600), Iris knowledge trimmed to 6,500 chars
  (keeps the prompt-writing module whole), one image at higher detail.
- Anti-loop sampling + repetition collapsing; negative prompt deduped; the video prompt is generated *before* the negative.
- If the video prompt is still missing → **one focused retry** against the same photo.
- **No canned prompts, no caching of failures**; poisoned cache entries are purged automatically (5 removed on first run).
- UI shows real errors/partials/warnings and a **"👁️ What Iris saw"** line so you can confirm it read the right photo.
  Video card relabelled for the engines you actually run (LTX 2.3 / MiniMax FastH3).

---

## D. Live verification (real server, real photo, real GPUs)
- **Lab:** 42 s HTTP-400 failure → 22 s success; description (cowboy hat, snakeskin boots, barn slats, backlight) matches the photo.
- **Command 1:** subject, couch, outfit, framing and watermark held for all 297 frames at 768×960; model=14B, web search skipped,
  prompt budget 13.8K/16.4K.
- **Command 2:** routed to Micro Cinema, Resolve Neural Engine Super Scale 3× actually used (355 s). The first run exposed the invented
  objects (gold rings, glassware) and black bars; after the fixes the re-run (349 s) shows **only your photo's real details**
  (hand/skin, green plaid skirt, white fabric) and the reel is **full-bleed 1080×1920** with no bars. The shots are very tight macros and
  the first two are soft/out of focus — that is the "dreamy" look of the mode, not a defect, but say so if you want it crisper.

**Tests:** 397 → **479 passing** (new: `test_bugcheck_i2v_viral_and_style_lab.py`, `test_viral_director_bugcheck.py`).

---

## E. Things worth knowing (not changed)
- **Adult Content Mode matters for adult photos.** With it OFF, the image-to-video tool appends an anti-nudity negative prompt
  (`nude, topless, bare breasts, genitals…`) — on an adult source photo that pushes the render *away from its own first frame*,
  which can read as "similar but different". Turn the toggle on for adult-creator work.
- LTX only loosely obeys camera instructions: "slowly zoom toward her mouth" produced a gentle push-in plus a refocus, not a
  precise move. Shorter clips (`num_frames` ~160) drift less than the 10 s default.
- Synapse's system prompt is ~6.7K tokens by itself. It now fits, but splitting it into a compact core + per-topic detail would
  make every turn faster.
