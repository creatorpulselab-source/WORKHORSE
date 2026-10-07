"""
Generates 5 patent drawing figures for Prism provisional patent application.
Output: F:\QUE\patent_drawings\ (PNG + combined PDF)
Run: f:\Que\.venv\Scripts\python.exe f:\Que\generate_patent_drawings.py
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from pathlib import Path

OUT_DIR = Path(r"F:\QUE\patent_drawings")
OUT_DIR.mkdir(exist_ok=True)

BG    = "white"
BOX   = "#f0f0f0"
DIAM  = "#d8d8d8"
DARK  = "#111111"
LINE  = "#444444"
BOLD  = {"fontsize": 8.5, "fontweight": "bold", "color": DARK, "fontfamily": "monospace"}
NORM  = {"fontsize": 7.5, "color": DARK, "fontfamily": "monospace"}
SMALL = {"fontsize": 6.8, "color": "#333333", "fontfamily": "monospace"}

# --- Drawing helpers ---------------------------------------------------------

def rbox(ax, cx, ytop, w, h, label, sub="", color=BOX):
    """Rounded rectangle centered at cx, top edge at ytop."""
    x = cx - w / 2
    y = ytop - h
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03",
                        facecolor=color, edgecolor=DARK, linewidth=1.1, zorder=2)
    ax.add_patch(p)
    if sub:
        # Anchor sub to the box TOP (grows downward with line count, never
        # spills above the box) and anchor label to the box BOTTOM so the
        # two never collide regardless of how many lines sub contains.
        ax.text(cx, y + 0.16, sub, ha="center", va="top", zorder=3, **SMALL)
        ax.text(cx, ytop - 0.24, label, ha="center", va="center", zorder=3, **BOLD)
    else:
        ax.text(cx, ytop - h / 2, label, ha="center", va="center", zorder=3, **BOLD)
    return ytop - h  # bottom edge

def diamond(ax, cx, ytop, w, h, label, sub=""):
    """Diamond centered at cx, top vertex at ytop."""
    mid_y = ytop - h / 2
    pts = [(cx, ytop), (cx + w/2, mid_y), (cx, ytop - h), (cx - w/2, mid_y)]
    poly = plt.Polygon(pts, closed=True, facecolor=DIAM, edgecolor=DARK, linewidth=1.1, zorder=2)
    ax.add_patch(poly)
    ax.text(cx, mid_y + 0.05, label, ha="center", va="center", zorder=3, **BOLD)
    if sub:
        ax.text(cx, mid_y - 0.15, sub, ha="center", va="center", zorder=3, **SMALL)
    return ytop - h  # bottom vertex y

def down(ax, x, y1, y2, label=""):
    """Downward arrow from y1 to y2 at x."""
    ax.annotate("", xy=(x, y2), xytext=(x, y1),
                arrowprops=dict(arrowstyle="-|>", color=LINE, lw=1.2))
    if label:
        ax.text(x + 0.07, (y1 + y2) / 2, label, va="center", **SMALL)

def right(ax, x1, x2, y, label=""):
    ax.annotate("", xy=(x2, y), xytext=(x1, y),
                arrowprops=dict(arrowstyle="-|>", color=LINE, lw=1.2))
    if label:
        ax.text((x1+x2)/2, y+0.07, label, ha="center", **SMALL)

def left(ax, x1, x2, y, label=""):
    ax.annotate("", xy=(x2, y), xytext=(x1, y),
                arrowprops=dict(arrowstyle="-|>", color=LINE, lw=1.2))
    if label:
        ax.text((x1+x2)/2, y+0.07, label, ha="center", **SMALL)

def hline(ax, x1, x2, y):
    ax.plot([x1, x2], [y, y], color=LINE, lw=1.2, zorder=2)

def vline(ax, x, y1, y2):
    ax.plot([x, x], [y1, y2], color=LINE, lw=1.2, zorder=2)

def save(fig, name):
    path = OUT_DIR / name
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"  Saved: {path}")

def setup(w, h, title, fig_num):
    fig, ax = plt.subplots(figsize=(w, h))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.invert_yaxis()  # y=0 at top, increases downward — natural reading order
    ax.axis("off")
    ax.text(w/2, 0.3, f"FIG. {fig_num}  —  {title}",
            ha="center", va="top", fontsize=10, fontweight="bold",
            color=DARK, fontfamily="monospace")
    ax.text(w/2, h - 0.1, "PRISM — AI Social Media Content Studio  |  Provisional Patent Application",
            ha="center", va="bottom", fontsize=6.5, color="#666666", fontfamily="monospace")
    return fig, ax


# ================================================================
# FIG. 1 — SYSTEM ARCHITECTURE OVERVIEW
# ================================================================
fig, ax = setup(14, 13, "SYSTEM ARCHITECTURE OVERVIEW", 1)
W = 14

def layer(ax, y, label):
    ax.text(0.35, y, label, fontsize=8, fontweight="bold", color=DARK, fontfamily="monospace")

def hrow(ax, ytop, boxes):
    """boxes = list of (cx, w, label, sub, color)"""
    bh = 0.75
    for cx, w, label, sub, color in boxes:
        rbox(ax, cx, ytop, w, bh, label, sub, color)
    return ytop + bh

GAP = 0.35
BH  = 0.75

y = 1.3
layer(ax, y, "USER LAYER")
y += 0.8
rows = [
    (2.3,  3.5, "Web Browser (Vanilla JS)",   "5-Step Wizard UI  |  SSE Streaming",  BOX),
    (6.2,  3.5, "Media Upload",               "Image / Video  (up to 500 MB)",        BOX),
    (10.5, 3.5, "User Preferences",           "Brand Voice / Signature / Gender",     BOX),
]
for cx, w, l, s, c in rows:
    rbox(ax, cx, y, w, BH, l, s, c)
y += BH + GAP

layer(ax, y, "SERVER LAYER  (FastAPI + Uvicorn, Python 3.11)")
y += 0.8
srv = [
    (1.5,  2.3, "Auth Middleware",       "PBKDF2 sessions",         BOX),
    (4.1,  2.6, "/api/prefetch",         "Warm cache on upload",    BOX),
    (7.0,  2.8, "/api/generate-stream",  "SSE multi-mode",          BOX),
    (9.9,  2.4, "/api/video",            "Video pipeline",          BOX),
    (12.6, 2.5, "/api/generate-image",   "Pose image gen",          BOX),
]
srv_cx = []
for cx, w, l, s, c in srv:
    rbox(ax, cx, y, w, BH, l, s, c)
    srv_cx.append(cx)
y += BH + GAP

layer(ax, y, "CORE SUBSYSTEMS")
y += 0.8
sub = [
    (2.0,  3.1, "Subsystem 2",  "Prefetch Cache\n+ Deduplication",       "#e4e4e4"),
    (5.5,  3.1, "Subsystem 1",  "Motion-Adaptive\nVideo Sampling",        "#e4e4e4"),
    (9.0,  3.1, "Subsystem 3",  "Feedback-Reinforced\nPrompt Construction","#e4e4e4"),
    (12.5, 3.1, "Subsystem 4",  "Appearance-Locked\nImage Synthesis",     "#e4e4e4"),
]
sub_cx = []
for cx, w, l, s, c in sub:
    rbox(ax, cx, y, w, BH, l, s, c)
    sub_cx.append(cx)
y += BH + GAP

layer(ax, y, "AI PROVIDER ABSTRACTION LAYER  (_call_provider)")
y += 0.8
prov = [
    (2.0,  3.0, "Gemini 2.5 Flash", "Primary · Search · Video", BOX),
    (5.5,  3.0, "OpenAI GPT-4o",    "DALL-E 2/3 image gen",     BOX),
    (9.0,  2.8, "Grok (xAI)",       "grok-2-vision-1212",       BOX),
    (12.5, 2.8, "Ollama (Local)",   "Qwen2.5-VL + Whisper",     BOX),
]
prov_cx = []
for cx, w, l, s, c in prov:
    rbox(ax, cx, y, w, BH, l, s, c)
    prov_cx.append(cx)
y += BH + GAP

layer(ax, y, "STORAGE LAYER")
y += 0.8
stor = [
    (2.2,  3.4, "SQLite (WAL mode)",    "history · sessions · usage\nhubs · vaults · metrics", BOX),
    (6.0,  3.6, "In-Memory Cache",      "SHA-256 keyed desc cache\n10-min TTL + Event registry", BOX),
    (9.6,  3.2, "Fly.io Volume /data",  "history.db · users.json\nwhisper_cache/",              BOX),
    (12.7, 2.5, "users.json",           "PBKDF2 credentials\nper-user settings",                BOX),
]
stor_cx = []
for cx, w, l, s, c in stor:
    rbox(ax, cx, y, w, BH, l, s, c)
    stor_cx.append(cx)
y += BH + GAP

layer(ax, y, "EXTERNAL SERVICES")
y += 0.8
ext = [
    (2.0,  3.0, "Gemini Files API",   "Native video upload\n+ polling",        BOX),
    (5.5,  3.2, "Google Search API",  "Brand research\n+ trend grounding",      BOX),
    (9.0,  2.8, "Imagen 3",           "Pose image\ngeneration",                 BOX),
    (12.5, 2.8, "ffmpeg / Whisper",   "Audio extract\n+ transcription",         BOX),
]
for cx, w, l, s, c in ext:
    rbox(ax, cx, y, w, BH, l, s, c)

# Downward arrows between layers
for cx in [2.0, 5.5, 9.0, 12.5]:
    for y_pair in [(0.85+0.3+BH, 0.85+0.3+BH+GAP+0.3),
                   (0.85+0.3+BH+GAP+0.3+BH, 0.85+0.3+BH+GAP+0.3+BH+GAP+0.3),
                   (0.85+0.3+BH+GAP+0.3+BH+GAP+0.3+BH, 0.85+0.3+BH+GAP+0.3+BH+GAP+0.3+BH+GAP+0.3)]:
        pass  # skip complex offset math — visual grouping is enough

save(fig, "FIG1_system_architecture.png")


# ================================================================
# FIG. 2 — MOTION-ADAPTIVE VIDEO FRAME SAMPLING (Subsystem 1)
# ================================================================
fig, ax = setup(11, 18, "MOTION-ADAPTIVE VIDEO FRAME SAMPLING  (Subsystem 1)", 2)
cx = 5.5
bw = 6.2
gap = 0.35
bh = 0.72

y = 1.3
rbox(ax, cx, y, bw, bh, "START — Video file received (MP4 / MOV / WEBM)", "", "#cccccc")
y += bh + gap; down(ax, cx, y-bh-gap+bh, y-gap)
rbox(ax, cx, y, bw, bh, "STEP 1 — Resize each frame to 854 x 480", "INTER_AREA interpolation — matches AI pipeline resolution")
y += bh + gap; down(ax, cx, y-bh-gap+bh, y-gap)
rbox(ax, cx, y, bw, bh, "STEP 2 — Convert to grayscale + Gaussian blur", "Kernel size 21x21 — suppresses high-frequency noise")
y += bh + gap; down(ax, cx, y-bh-gap+bh, y-gap)
rbox(ax, cx, y, bw, bh, "STEP 3 — Compute absdiff vs previous frame", "Binary threshold at pixel value 25  →  binary motion mask")
y += bh + gap; down(ax, cx, y-bh-gap+bh, y-gap)
rbox(ax, cx, y, bw, bh, "STEP 4 — motion_score = nonzero_pixels / total_pixels * 100", "Percentage of frame showing detected motion", BOX)

# Diamond
y += bh + gap; down(ax, cx, y-bh-gap+bh, y-gap)
d_top = y; d_h = 0.9; d_w = bw
diamond(ax, cx, d_top, d_w, d_h, "motion_score  <  2.5 ?", "(static frame threshold)")
d_bot = d_top + d_h
mid_d = d_top + d_h/2

# YES branch — left side
yes_x = cx - bw/2 - 1.2
ax.text(cx - bw/2 - 0.08, mid_d, "YES (static)", ha="right", fontsize=6.8, color=DARK, fontfamily="monospace")
hline(ax, cx - bw/2, yes_x, mid_d)
vline(ax, yes_x, mid_d, mid_d + 1.0)
ax.annotate("", xy=(yes_x, mid_d + 1.0), xytext=(yes_x, mid_d + 0.7),
            arrowprops=dict(arrowstyle="-|>", color=LINE, lw=1.2))
rbox(ax, yes_x, mid_d + 1.0, 2.2, 0.72, "frame_count % 30 == 0?", "→ save 1 frame", "#eeeeee")
ax.text(yes_x, mid_d + 1.72 + 0.12, "(discard — static scene)", ha="center", fontsize=6.5, color="#555", fontfamily="monospace")
# arrow from static box back to main flow — continues below diamond
vline(ax, yes_x, mid_d + 1.72, d_bot + 2.2)
hline(ax, yes_x, cx - bw/2, d_bot + 2.2)

# NO branch — continue down
ax.text(cx + bw/2 + 0.08, mid_d, "NO (motion)", ha="left", fontsize=6.8, color=DARK, fontfamily="monospace")
y = d_bot + gap
down(ax, cx, d_bot, y)

# burst diamond
b_top = y; b_h = 0.9; b_w = bw
rbox(ax, cx, b_top, bw, bh, "STEP 5 — BURST MODE: Save frame to extraction set", "burst_counter += 1")
y = b_top + bh + gap; down(ax, cx, y-gap, y)
diamond(ax, cx, y, b_w, b_h, "burst_counter  >=  5 ?", "(5 burst frames captured?)")
b_mid = y + b_h/2; b_bot = y + b_h

# NO — keep bursting (loop back left)
no_x = cx - bw/2 - 1.2
ax.text(cx - bw/2 - 0.08, b_mid, "NO", ha="right", fontsize=6.8, color=DARK, fontfamily="monospace")
hline(ax, cx - bw/2, no_x, b_mid)
vline(ax, no_x, b_mid, b_top + bh/2)
hline(ax, no_x, cx - bw/2, b_top + bh/2)
ax.annotate("", xy=(cx - bw/2, b_top + bh/2), xytext=(no_x + 0.1, b_top + bh/2),
            arrowprops=dict(arrowstyle="-|>", color=LINE, lw=1.2))
ax.text(no_x - 0.1, (b_mid + b_top + bh/2)/2, "loop", ha="right", fontsize=6.5, color="#555", fontfamily="monospace")

# YES — enter skip mode
ax.text(cx + bw/2 + 0.08, b_mid, "YES (5 captured)", ha="left", fontsize=6.8, color=DARK, fontfamily="monospace")
y = b_bot + gap; down(ax, cx, b_bot, y)
rbox(ax, cx, y, bw, bh, "STEP 6 — Enter SKIP mode: skip next 10 frames", "burst_counter reset  →  after 10 skipped, return to burst mode")
y += bh + gap * 1.5; down(ax, cx, y-bh-gap*1.5+bh, y-gap*1.5)

# Converge here (static branch also arrives)
conv_y = y
rbox(ax, cx, conv_y, bw+1.0, bh, "Max 30 frames extracted  |  Repeat until end of video", "", "#e0e0e0")
y += bh + gap; down(ax, cx, y-bh-gap+bh, y-gap)

# Grid box
rbox(ax, cx, y, bw+1.0, 1.1,
     "STEP 7 — HOLD-AND-WAIT GRID COMPOSITION",
     "Group 3 frames  →  resize each to 400 x 225\n"
     "Stitch side-by-side onto 1200 x 225 canvas (dark fill)\n"
     "Encode as single JPEG quality=82  →  ONE AI batch call",
     "#cccccc")
y += 1.1 + gap; down(ax, cx, y-1.1-gap+1.1, y-gap)
rbox(ax, cx, y, bw, bh, "STEP 8 — Synthesize: all batch descriptions + audio transcript", "Final caption / Flux / WAN prompt generated")
y += bh + 0.4
ax.text(cx, y, "Parallel track: ffmpeg extracts audio  →  Whisper (tiny/int8/cpu) transcription", ha="center", fontsize=6.8, color="#444", fontfamily="monospace")

save(fig, "FIG2_video_sampling_pipeline.png")


# ================================================================
# FIG. 3 — CONCURRENT AI INFERENCE DEDUPLICATION (Subsystem 2)
# ================================================================
fig, ax = setup(14, 9, "CONCURRENT AI INFERENCE DEDUPLICATION  (Subsystem 2)", 3)

# Swim lane setup (y increases downward due to invert_yaxis)
LANES = [
    ("USER BROWSER",          2.25,  2.8),
    ("WEB SERVER",            5.35,  2.8),
    ("CACHE + EVENT REGISTRY",8.45,  3.0),
    ("AI PROVIDER",          11.75,  2.8),
]
lane_top = 0.65
lane_bot = 8.0

for label, lcx, lw in LANES:
    r = plt.Rectangle((lcx - lw/2, lane_top), lw, lane_bot - lane_top,
                       facecolor="#f7f7f7", edgecolor="#aaaaaa", linewidth=0.8, zorder=0)
    ax.add_patch(r)
    ax.text(lcx, lane_top + 0.25, label, ha="center", va="top",
            fontsize=8, fontweight="bold", color=DARK, fontfamily="monospace")

def sl(ax, lane_i, ytop, label, sub="", color=BOX):
    lcx, lw = LANES[lane_i][1], LANES[lane_i][2]
    rbox(ax, lcx, ytop, lw - 0.3, 0.65, label, sub, color)
    return ytop + 0.65

def harrLR(ax, from_i, to_i, y, label="", below=False):
    """Horizontal arrow between lane centers at y.

    Lane-skipping arrows (|to_i - from_i| >= 2) pass over an intermediate
    lane where an adjacent-lane arrow's label already sits just above the
    line — pass below=True to place this arrow's label below the line
    instead, so the two labels never collide.
    """
    x1 = LANES[from_i][1] + (LANES[from_i][2]/2 - 0.15) * (1 if to_i > from_i else -1)
    x2 = LANES[to_i][1]   - (LANES[to_i][2]/2   - 0.15) * (1 if to_i > from_i else -1)
    ax.annotate("", xy=(x2, y), xytext=(x1, y),
                arrowprops=dict(arrowstyle="-|>", color=LINE, lw=1.2))
    if label:
        ly = y + (0.24 if below else -0.12)
        ax.text((x1+x2)/2, ly, label, ha="center", fontsize=6.5, color=DARK, fontfamily="monospace")

y = 2.0
sl(ax, 0, y, "User uploads image", "JPEG / PNG / WEBP / GIF")
harrLR(ax, 0, 1, y + 0.32, "POST /api/prefetch")
sl(ax, 1, y, "Compute SHA-256 hash", "cache_key = hash[:20]")
harrLR(ax, 1, 2, y + 0.32, "lookup cache(key)")
sl(ax, 2, y, "Cache MISS — no entry", "Create threading.Event(key)", "#e0e0e0")
harrLR(ax, 1, 3, y + 0.32, "AI vision call  (SCENE_DESCRIBE_PROMPT)", below=True)
sl(ax, 3, y, "AI Inference Running", "~2-5 seconds", "#e0e0e0")

y += 0.65 + 0.6
ax.text(LANES[0][1], y - 0.1, "-- concurrent --", ha="center", fontsize=7, color="#777", fontfamily="monospace")
sl(ax, 0, y, "User clicks Generate", "(while prefetch in-flight)")
harrLR(ax, 0, 1, y + 0.32, "POST /api/generate")
sl(ax, 1, y, "Compute SHA-256 hash", "Same image → same key")
harrLR(ax, 1, 2, y + 0.32, "lookup cache(key)")
sl(ax, 2, y, "Cache MISS but Event EXISTS", "→ event.wait(timeout=90s)", "#e0e0e0")
ax.text(LANES[2][1], y + 0.65 + 0.1, "Deduplication path: block until\ncomputing thread finishes",
        ha="center", fontsize=6.5, color="#333", fontfamily="monospace")

y += 0.65 + 1.0
harrLR(ax, 3, 1, y + 0.32, "description text returned", below=True)
sl(ax, 1, y, "Store result in cache", "cache[key] = {desc, expires=+600s}")
harrLR(ax, 1, 2, y + 0.32, "cache.write()  +  event.set()")
sl(ax, 2, y, "event.set() — unblocks waiter", "Waiting Generate thread reads cache", "#cccccc")

y += 0.65 + 0.5
ax.text(LANES[2][1], y - 0.05, "Stale entries evicted on each write\n(TTL = 600 seconds / 10 minutes)",
        ha="center", fontsize=6.5, color="#444", fontfamily="monospace")

y += 0.55
sl(ax, 1, y, "Inject description as text prefix", '"[IMAGE DESCRIPTION]...\\n" + prompt')
ax.text(LANES[1][1], y + 0.65 + 0.1, "No image bytes re-transmitted —\ncached text replaces vision call",
        ha="center", fontsize=6.5, color="#333", fontfamily="monospace")
harrLR(ax, 1, 3, y + 0.32, "text-only prompt  (no image bytes)", below=True)
sl(ax, 3, y, "Generate content", "Caption / Flux / WAN / Poses")
harrLR(ax, 3, 0, y + 0.32, "streamed result  (SSE)")
sl(ax, 0, y, "Result displayed in UI", "token-by-token SSE stream", "#cccccc")

save(fig, "FIG3_inference_deduplication.png")


# ================================================================
# FIG. 4 — FEEDBACK-REINFORCED PROMPT CONSTRUCTION (Subsystem 3)
# ================================================================
fig, ax = setup(11, 17, "FEEDBACK-REINFORCED PROMPT CONSTRUCTION  (Subsystem 3)", 4)
cx = 5.5; bw = 7.0; gap = 0.4; bh = 0.72

def phase(ax, y, label):
    ax.text(0.3, y, label, fontsize=8.5, fontweight="bold", color=DARK, fontfamily="monospace")
    ax.plot([0.3, 10.7], [y + 0.22, y + 0.22], color="#aaaaaa", lw=0.8, linestyle="--")

y = 0.7
phase(ax, y, "PHASE A — SIGNAL COLLECTION  (ongoing, per user)")
y += 0.85
rbox(ax, cx, y, bw, bh, "User generates content (any mode)", "Caption / Flux Image Prompt / WAN Video Prompt / Pose Series")
y += bh + gap; down(ax, cx, y-bh-gap+bh, y-gap)
rbox(ax, cx, y, bw, bh, "Result stored in history table", "id · mode · platform · results · created_at · thumb")
y += bh + gap; down(ax, cx, y-bh-gap+bh, y-gap)
rbox(ax, cx, y, bw, 0.85, "User action: mark entry 'Posted'  +  assign rating  1-5 stars",
     "posted = 1  |  rating = 1..5  |  posted_at = timestamp  →  written to history table", "#e8e8e8")

y += 0.85 + 0.7
phase(ax, y, "PHASE B — RETRIEVAL  (fires on every new generation request)")
y += 0.9
rbox(ax, cx, y, bw, bh, "New generation request received", "mode = post  |  platform = instagram (or any platform)")
y += bh + gap; down(ax, cx, y-bh-gap+bh, y-gap)
rbox(ax, cx, y, bw, 1.0,
     "Database query: SELECT FROM history",
     "WHERE  posted = 1  AND  rating >= 4\nORDER BY  created_at DESC   LIMIT 20", "#e0e0e0")
y += 1.0 + gap; down(ax, cx, y-1.0-gap+1.0, y-gap)
rbox(ax, cx, y, bw, bh, "Filter results to matching platform", "e.g.  keep only rows where platform = 'instagram'")
y += bh + gap; down(ax, cx, y-bh-gap+bh, y-gap)
rbox(ax, cx, y, bw, bh, "Select up to 2 most recently rated qualifying captions", "_top_performer_examples(platform, limit=2)")

y += bh + 0.7
phase(ax, y, "PHASE C — INJECTION  (into generation prompt, same inference call)")
y += 1.15
rbox(ax, cx, y, bw, 1.0,
     "Append few-shot style reference block to prompt",
     '"TOP-PERFORMING PAST CAPTIONS (style/structure reference, don\'t copy):\n'
     '- {example_1 text}\n- {example_2 text}"', "#e0e0e0")
y += 1.0 + gap; down(ax, cx, y-1.0-gap+1.0, y-gap)
rbox(ax, cx, y, bw, bh, "AI generates new caption", "Influenced by user's own proven writing style + structure")
y += bh + gap; down(ax, cx, y-bh-gap+bh, y-gap)
rbox(ax, cx, y, bw, bh,
     "Result — no model retraining, no explicit style config",
     "System continuously adapts as user rates more content over time", "#cccccc")

save(fig, "FIG4_feedback_reinforced_prompts.png")


# ================================================================
# FIG. 5 — APPEARANCE-LOCKED IMAGE SYNTHESIS (Subsystem 4)
# ================================================================
fig, ax = setup(12, 19, "APPEARANCE-LOCKED MULTI-SHOT IMAGE SYNTHESIS  (Subsystem 4)", 5)
cx = 6.0; bw = 8.0; gap = 0.4; bh = 0.72

y = 1.3
rbox(ax, cx, y, bw, bh, "START — User uploads reference photograph", "Subject for multi-pose AI image generation series", "#cccccc")
y += bh + gap; down(ax, cx, y-bh-gap+bh, y-gap)
rbox(ax, cx, y, bw, bh, "STEP 1 — Appearance Extraction AI Vision Call", "Reference image  →  vision model using APPEARANCE_EXTRACT_PROMPT")

# Extraction record box
y += bh + gap; down(ax, cx, y-bh-gap+bh, y-gap)
ext_rows = [
    "FACE     shape · eye color/shape · nose · lips · jawline · distinctive features",
    "HAIR     exact shade (specific) · length · texture (straight/wavy/curly) · style",
    "SKIN     specific tone descriptor  (e.g. 'light olive', 'deep warm brown')",
    "TATTOOS  EVERY visible tattoo with EXACT body location",
    "         e.g.  'full sleeve right arm'   |   'rose tattoo inner left wrist'",
    "HANDS    all held items · which hand (left/right) · how held",
    "OUTFIT   every garment · shoes (type/heel/material) · accessories",
    "BACKGROUND  exact setting, surfaces, environment visible in reference",
]
box_h = 0.28 * len(ext_rows) + 0.45
r = FancyBboxPatch((cx - bw/2, y), bw, box_h, boxstyle="round,pad=0.03",
                    facecolor="#e8e8e8", edgecolor=DARK, linewidth=1.1, zorder=2)
ax.add_patch(r)
ax.text(cx, y + 0.22, "Extracted Appearance Record  (output of APPEARANCE_EXTRACT_PROMPT)",
        ha="center", fontsize=8, fontweight="bold", color=DARK, fontfamily="monospace", zorder=3)
for i, row in enumerate(ext_rows):
    ax.text(cx - bw/2 + 0.2, y + 0.45 + i * 0.28, row,
            ha="left", va="top", fontsize=6.8, color=DARK, fontfamily="monospace", zorder=3)
y += box_h + gap + bh; down(ax, cx, y-box_h-gap-bh+box_h, y-gap-bh)

rbox(ax, cx, y, bw, bh, "STEP 2 — Construct POSE_CONSISTENCY_RULES constraint block", "Explicit cannot-change rules appended to every pose prompt in the series")

# Constraint block
y += bh + gap; down(ax, cx, y-bh-gap+bh, y-gap)
con_rows = [
    "CANNOT CHANGE:   face · facial features · skin tone  (exact match required)",
    "CANNOT CHANGE:   ALL tattoos at EXACT same body locations — no add/remove/move",
    "CANNOT CHANGE:   held items — same item · same hand · clearly visible to camera",
    "CANNOT CHANGE:   background · location · environment  (exact match)",
    "CANNOT CHANGE:   outfit · clothing · accessories",
    "ONLY CHANGE:     body pose · posture · arm angles · head/face direction · camera angle",
]
con_h = 0.28 * len(con_rows) + 0.45
r2 = FancyBboxPatch((cx - bw/2, y), bw, con_h, boxstyle="round,pad=0.03",
                     facecolor="#e0e0e0", edgecolor=DARK, linewidth=1.1, zorder=2)
ax.add_patch(r2)
ax.text(cx, y + 0.22, "Constraint Block  (POSE_CONSISTENCY_RULES — appended to every prompt)",
        ha="center", fontsize=8, fontweight="bold", color=DARK, fontfamily="monospace", zorder=3)
for i, row in enumerate(con_rows):
    ax.text(cx - bw/2 + 0.2, y + 0.45 + i * 0.28, row,
            ha="left", va="top", fontsize=6.8, color=DARK, fontfamily="monospace", zorder=3)
y += con_h + gap + 0.85; down(ax, cx, y-con_h-gap-0.85+con_h, y-gap-0.85)

rbox(ax, cx, y, bw, 0.85,
     "STEP 3 — For each pose [1..6]: build enriched prompt",
     '"SUBJECT REFERENCE — maintain exact appearance: {appearance_description}"'
     "\n+ pose_variation_prompt + POSE_CONSISTENCY_RULES")

# Provider fork diamond
y += 0.85 + gap; down(ax, cx, y-0.85-gap+0.85, y-gap)
d_top = y; d_h = 0.9; d_w = bw - 1.0
diamond(ax, cx, d_top, d_w, d_h, "AI Image Provider?", "")
d_mid = d_top + d_h/2; d_bot = d_top + d_h

# OpenAI LEFT branch
oa_cx = cx - 3.5
ax.text(cx - d_w/2 - 0.1, d_mid, "OpenAI", ha="right", fontsize=7, color=DARK, fontfamily="monospace")
hline(ax, cx - d_w/2, oa_cx + 1.4, d_mid)
vline(ax, oa_cx + 1.4, d_mid, d_bot + 0.4)
ax.annotate("", xy=(oa_cx + 1.4, d_bot + 0.4), xytext=(oa_cx + 1.4, d_mid + 0.3),
            arrowprops=dict(arrowstyle="-|>", color=LINE, lw=1.2))
rbox(ax, oa_cx + 1.4, d_bot + 0.4, 2.6, 0.72, "DALL-E 2 Edit endpoint", "Pad ref img to square PNG\nthen submit with prompt")
# Success diamond
y_oa = d_bot + 0.4 + 0.72 + 0.35; down(ax, oa_cx + 1.4, d_bot + 0.4 + 0.72, y_oa)
diamond(ax, oa_cx + 1.4, y_oa, 2.5, 0.8, "Success?", "")
oa_mid = y_oa + 0.4
# YES
ax.text(oa_cx + 1.4 - 1.35, oa_mid, "YES", ha="right", fontsize=6.8, color=DARK, fontfamily="monospace")
hline(ax, oa_cx + 1.4 - 1.25, oa_cx - 0.2, oa_mid)
vline(ax, oa_cx - 0.2, oa_mid, oa_mid + 1.1)
ax.annotate("", xy=(oa_cx - 0.2, oa_mid + 1.1), xytext=(oa_cx - 0.2, oa_mid + 0.8),
            arrowprops=dict(arrowstyle="-|>", color=LINE, lw=1.2))
rbox(ax, oa_cx - 0.2, oa_mid + 1.1, 2.0, 0.65, "Image returned", "PNG base64", "#cccccc")
# NO fallback
ax.text(oa_cx + 1.4 + 1.35, oa_mid, "NO", ha="left", fontsize=6.8, color=DARK, fontfamily="monospace")
hline(ax, oa_cx + 1.4 + 1.25, cx - 1.3, oa_mid)
vline(ax, cx - 1.3, oa_mid, d_bot + 2.7)
ax.annotate("", xy=(cx - 1.3, d_bot + 2.7), xytext=(cx - 1.3, d_bot + 2.4),
            arrowprops=dict(arrowstyle="-|>", color=LINE, lw=1.2))

# DALL-E 3 fallback center
rbox(ax, cx, d_bot + 2.7, 2.8, 0.72, "DALL-E 3 generation", "Text-only fallback prompt")
down(ax, cx, d_bot + 2.7 + 0.72, d_bot + 2.7 + 0.72 + 0.4)

# Gemini RIGHT branch
gm_cx = cx + 3.5
ax.text(cx + d_w/2 + 0.1, d_mid, "Gemini", ha="left", fontsize=7, color=DARK, fontfamily="monospace")
hline(ax, cx + d_w/2, gm_cx - 1.4, d_mid)
vline(ax, gm_cx - 1.4, d_mid, d_bot + 0.4)
ax.annotate("", xy=(gm_cx - 1.4, d_bot + 0.4), xytext=(gm_cx - 1.4, d_mid + 0.3),
            arrowprops=dict(arrowstyle="-|>", color=LINE, lw=1.2))
rbox(ax, gm_cx - 1.4, d_bot + 0.4, 2.6, 0.72, "Imagen 3 generation", "Enriched text prompt\n+ appearance reference")
down(ax, gm_cx - 1.4, d_bot + 0.4 + 0.72, d_bot + 0.4 + 0.72 + 1.0)
rbox(ax, gm_cx - 1.4, d_bot + 0.4 + 0.72 + 1.0, 2.6, 0.65, "Image returned", "PNG base64", "#cccccc")
# connect Gemini result to merge
vline(ax, gm_cx - 1.4, d_bot + 0.4 + 0.72 + 1.0 + 0.65, d_bot + 2.7 + 0.72 + 0.4)
hline(ax, gm_cx - 1.4, cx + 1.4, d_bot + 2.7 + 0.72 + 0.4)
ax.annotate("", xy=(cx + 1.4, d_bot + 2.7 + 0.72 + 0.4), xytext=(cx + 0.6, d_bot + 2.7 + 0.72 + 0.4),
            arrowprops=dict(arrowstyle="-|>", color=LINE, lw=1.2))

# Final display step
fy = d_bot + 2.7 + 0.72 + 0.4
rbox(ax, cx, fy, bw, 0.85,
     "STEP 4 — Display generated pose image",
     "Full-width display · tap for lightbox preview · download button · repeat for all 6 poses", "#cccccc")

save(fig, "FIG5_appearance_locked_synthesis.png")


# ================================================================
# COMBINED PDF
# ================================================================
from matplotlib.backends.backend_pdf import PdfPages

png_files = [
    OUT_DIR / "FIG1_system_architecture.png",
    OUT_DIR / "FIG2_video_sampling_pipeline.png",
    OUT_DIR / "FIG3_inference_deduplication.png",
    OUT_DIR / "FIG4_feedback_reinforced_prompts.png",
    OUT_DIR / "FIG5_appearance_locked_synthesis.png",
]

pdf_path = OUT_DIR / "Prism_Patent_Drawings.pdf"
with PdfPages(pdf_path) as pdf:
    for png in png_files:
        img = plt.imread(str(png))
        h, w = img.shape[:2]
        fig_pdf, ax_pdf = plt.subplots(figsize=(w/150, h/150))
        fig_pdf.patch.set_facecolor("white")
        ax_pdf.imshow(img)
        ax_pdf.axis("off")
        pdf.savefig(fig_pdf, bbox_inches="tight", facecolor="white")
        plt.close(fig_pdf)

print("  Combined PDF: " + str(pdf_path))
print("Done. Files in: " + str(OUT_DIR))
for f in png_files:
    print("  " + f.name)
print("  Prism_Patent_Drawings.pdf")
