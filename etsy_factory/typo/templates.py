"""Design templates: quote text -> layered welded geometry (roles: main / accent / orn / frame).

All geometry is built in abstract units where the main block is ~1000 wide; `engine.finalize` scales to physical mm.
"""
from __future__ import annotations

import itertools
import math
import random
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from shapely import affinity
from shapely.geometry import Point, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from . import ornaments as O
from .fonts import FontSpec
from .text import fit_width, move_to, on_arc, polys

STOP = set("a an the and or but if of to in on at for with from by as is are was be been it its i me my you your we our they their this that "
           "these those not no so than then just do does did have has had am can will would should could".split())


@dataclass
class Ctx:
    rng: random.Random
    main: FontSpec
    accent: FontSpec
    alt: FontSpec
    orn: Sequence[str] = ("sparkle", "swash", "divider", "stars")
    caps: Optional[bool] = None       # None -> font default


@dataclass
class Layered:
    layers: Dict[str, BaseGeometry] = field(default_factory=dict)
    template: str = ""

    def add(self, role: str, g: BaseGeometry) -> None:
        if g is None or g.is_empty:
            return
        self.layers[role] = unary_union([self.layers[role], g]) if role in self.layers else g

    def union(self) -> BaseGeometry:
        return unary_union(list(self.layers.values()))

    def clear_orn(self, gap: float) -> None:
        """Knock the ornament layer out of the text/frame so decorations never collide with letters."""
        if "orn" not in self.layers:
            return
        text = unary_union([g for k, g in self.layers.items() if k != "orn"])
        o = self.layers["orn"].difference(text.buffer(gap, join_style=1))
        o = unary_union([q for q in polys(o) if q.area > 40])
        if o.is_empty:
            self.layers.pop("orn")
        else:
            self.layers["orn"] = o

    def transform(self, fn) -> "Layered":
        out = Layered(template=self.template)
        for k, g in self.layers.items():
            out.layers[k] = fn(g)
        return out


# ----------------------------------------------------------------------------- text parsing
def parse(q: str) -> Tuple[List[str], Optional[str], List[int]]:
    """-> (words, emphasised word or None, explicit break indices). Markup: *word* emphasis, '/' line break."""
    words, emph, breaks = [], None, []
    in_span = False
    for tok in q.split():
        if tok == "/":
            breaks.append(len(words))
            continue
        m = re.fullmatch(r"\*(.+)\*([^\w]*)", tok)
        if m:
            emph = len(words)
            words.append(m.group(1) + m.group(2))
            continue
        # multi-word span: "*within" ... "her*" -> emphasise the last word of the span
        if not in_span and tok.startswith("*") and len(tok) > 1 and "*" not in tok[1:]:
            in_span = True
            words.append(tok[1:])
            continue
        if in_span:
            m2 = re.fullmatch(r"(.*?)\*([^\w]*)", tok)
            if m2:
                in_span = False
                emph = len(words)
                words.append(m2.group(1) + m2.group(2))
                continue
        words.append(tok.replace("*", ""))
    return words, emph, breaks


def auto_emphasis(words: List[str], rng: random.Random) -> int:
    cands = [(len(re.sub(r"\W", "", w)), i) for i, w in enumerate(words) if re.sub(r"\W", "", w).lower() not in STOP and len(re.sub(r"\W", "", w)) >= 4]
    if not cands:
        return len(words) - 1
    best = max(c[0] for c in cands)
    top = [i for L, i in cands if L >= best - 1]
    return top[-1] if rng.random() < 0.6 else rng.choice(top)


def balance(words: List[str], k: int) -> List[List[str]]:
    """Split words into k contiguous lines with the most even character counts."""
    n = len(words)
    k = max(1, min(k, n))
    if k == 1:
        return [list(words)]
    lens = [len(w) + 1 for w in words]
    best, best_s = None, None
    for cuts in itertools.combinations(range(1, n), k - 1):
        idx = (0, *cuts, n)
        tot = [sum(lens[idx[i]:idx[i + 1]]) for i in range(k)]
        mean = sum(tot) / k
        s = sum((t - mean) ** 2 for t in tot)
        if best_s is None or s < best_s:
            best, best_s = idx, s
    return [list(words[best[i]:best[i + 1]]) for i in range(k)]


def auto_lines(words: List[str], breaks: List[int], max_lines: int = 5) -> List[List[str]]:
    if breaks:
        idx = [0, *breaks, len(words)]
        return [words[idx[i]:idx[i + 1]] for i in range(len(idx) - 1) if words[idx[i]:idx[i + 1]]]
    n = len(words)
    chars = sum(len(w) for w in words)
    k = 1 if n <= 2 and chars < 11 else max(2, min(max_lines, round(n / 2.1)))
    return balance(words, k)


# ----------------------------------------------------------------------------- shaping helpers
def shaped(spec: FontSpec, text: str, upper: bool = False, size: float = 100.0) -> Tuple[BaseGeometry, float, float, float]:
    t = text.upper() if upper else text
    sh = spec.face().shape(t, size=size, tracking=spec.track, keep_glyphs=False)
    g = sh.geom
    if spec.embolden:
        g = g.buffer(spec.embolden * size, join_style=1)
    return g, sh.cap, sh.xh, sh.advance


def use_caps(spec: FontSpec, ctx: Ctx, force: Optional[bool] = None) -> bool:
    if force is not None:
        return force
    if ctx.caps is not None and spec.role in ("display", "serif", "retro", "brush"):
        return ctx.caps
    return spec.upper


def line_fit(spec: FontSpec, text: str, width: float, upper: bool) -> Tuple[BaseGeometry, float]:
    """Shape a line, scale to `width`, baseline at y=0, centred on x=0. Returns (geometry, cap height after scaling)."""
    g, cap, xh, _ = shaped(spec, text, upper)
    if g.is_empty:
        return g, 0.0
    x0, y0, x1, y1 = g.bounds
    s = width / (x1 - x0)
    g = affinity.scale(g, s, s, origin=(0, 0))
    g = affinity.translate(g, -(g.bounds[0] + g.bounds[2]) / 2, 0)
    return g, cap * s


def vstack(lines: List[Tuple[BaseGeometry, float, str]], gap_ratio: float = 0.16) -> List[Tuple[BaseGeometry, str]]:
    """Place lines top-down by cap height/descender so baselines are optically even. Returns [(geom_at_position, role)].

    After the optical placement each line is pushed down until its real ink no longer comes within `min_gap` of the previous two
    lines, so script descenders / tall ascenders never touch neighbouring lines (this also keeps cut files weedable)."""
    out = []
    y = 0.0
    prev_desc = 0.0
    caps = [c for _, c, _ in lines if c > 0]
    avg_cap = (sum(caps) / len(caps)) if caps else 100.0
    gap = gap_ratio * avg_cap if caps else 10.0
    min_gap = 0.075 * avg_cap
    step = 0.03 * avg_cap
    for i, (g, cap, role) in enumerate(lines):
        if g.is_empty:
            continue
        top = min(g.bounds[3], cap * 1.12) if cap else g.bounds[3]
        if i == 0:
            y = -top
        else:
            y = y - prev_desc - gap - top
        placed = affinity.translate(g, 0, y)
        recent = [p for p, _ in out[-2:]]
        for _ in range(120):
            if not any(p.buffer(min_gap, join_style=1).intersects(placed) for p in recent):
                break
            y -= step
            placed = affinity.translate(g, 0, y)
        out.append((placed, role))
        prev_desc = max(0.0, -g.bounds[1]) * 0.6
    return out


def knockout(base: BaseGeometry, top: BaseGeometry, gap: float) -> BaseGeometry:
    return base.difference(top.buffer(gap, join_style=1))


# ----------------------------------------------------------------------------- ornament placement
def add_ornaments(L: Layered, ctx: Ctx, bounds: Tuple[float, float, float, float], kinds: Sequence[str], unit: float) -> None:
    x0, y0, x1, y1 = bounds
    w, h = x1 - x0, y1 - y0
    cx = (x0 + x1) / 2
    rng = ctx.rng
    for k in kinds:
        if k == "sparkle":
            r = unit * rng.uniform(0.55, 0.8)
            L.add("orn", affinity.translate(O.sparkle_cluster(r, rng), x1 - r * 0.5, y1 + r * 1.35))
            if rng.random() < 0.6:
                L.add("orn", affinity.translate(O.sparkle(r * 0.55), x0 + r * 0.1, y0 - r * 0.9))
        elif k == "swash":
            L.add("orn", affinity.translate(O.swash(w * 0.62, unit * 0.16, rng.uniform(0.8, 1.2), flip=rng.random() < 0.3), cx, y0 - unit * 0.55))
        elif k == "divider":
            kind = rng.choice(["diamond", "star", "heart", "dots", "sparkle"])
            L.add("orn", affinity.translate(O.divider(w * 0.55, unit * 0.11, kind), cx, y1 + unit * 0.7))
            if rng.random() < 0.5:
                L.add("orn", affinity.translate(O.divider(w * 0.55, unit * 0.11, kind), cx, y0 - unit * 0.7))
        elif k == "stars":
            L.add("orn", affinity.translate(O.stars_row(3, unit * 0.34, unit * 1.0), cx, y1 + unit * 0.75))
        elif k == "hearts":
            L.add("orn", affinity.translate(O.hearts_row(3, unit * 0.7, unit * 1.05), cx, y0 - unit * 0.8))
        elif k == "sprig":
            L.add("orn", affinity.translate(O.sprig(w * 0.45, 5), cx, y0 - unit * 0.9))
        elif k == "daisy":
            L.add("orn", affinity.translate(O.daisy(unit * 0.75), x0 + unit * 0.55, y1 + unit * 1.0))
        elif k == "bolt":
            L.add("orn", affinity.translate(O.bolt(unit * 1.6), x1 + unit * 0.3, (y0 + y1) / 2))
        elif k == "cross":
            L.add("orn", affinity.translate(O.cross(unit * 2.0), cx, y1 + unit * 1.3))
        elif k == "mug":
            L.add("orn", affinity.translate(O.mug(unit * 2.0), x1 - unit * 0.6, y1 + unit * 1.0))
        elif k == "wave":
            L.add("orn", affinity.translate(O.wave(w * 0.5, unit * 0.14, 3, unit * 0.12), cx, y0 - unit * 0.6))


# ----------------------------------------------------------------------------- template: stack
def t_stack(q: str, ctx: Ctx) -> Layered:
    rng = ctx.rng
    words, emph, breaks = parse(q)
    use_accent = len(words) >= 3 and ctx.accent is not None
    if use_accent and emph is None:
        emph = auto_emphasis(words, rng)
    W = 1000.0
    main_upper = use_caps(ctx.main, ctx)
    segs = None
    if breaks:
        idx = [0, *breaks, len(words)]
        segs = [(idx[i], idx[i + 1]) for i in range(len(idx) - 1) if idx[i + 1] > idx[i]]
    groups: List[Tuple[str, str]] = []
    if use_accent and emph is not None:
        if segs:
            for a0, b0 in segs:
                if a0 <= emph < b0:
                    if emph > a0:
                        groups.append((" ".join(words[a0:emph]), "main"))
                    groups.append((words[emph], "accent"))
                    if b0 > emph + 1:
                        groups.append((" ".join(words[emph + 1:b0]), "main"))
                else:
                    groups.append((" ".join(words[a0:b0]), "main"))
        else:
            pre, post = words[:emph], words[emph + 1:]
            nch = lambda ws: len(" ".join(ws))
            kpre = 0 if not pre else max(1, min(3, round(nch(pre) / 17)))
            kpost = 0 if not post else max(1, min(3, round(nch(post) / 17)))
            if pre:
                groups += [(" ".join(l), "main") for l in balance(pre, kpre)]
            groups.append((words[emph], "accent"))
            if post:
                groups += [(" ".join(l), "main") for l in balance(post, kpost)]
    else:
        groups = [(" ".join(l), "main") for l in auto_lines(words, breaks)]

    lines: List[Tuple[BaseGeometry, float, str]] = []
    for text, role in groups:
        spec = ctx.accent if role == "accent" else ctx.main
        up = False if role == "accent" else main_upper
        lw = W * rng.uniform(0.74, 0.98) if role == "accent" else W
        g, cap = line_fit(spec, text, lw, up)
        maxcap = 235.0 if role == "main" else 400.0
        if cap > maxcap:                                    # keep very short lines from becoming gigantic
            g, cap = line_fit(spec, text, lw * maxcap / cap, up)
        lines.append((g, cap, role))

    placed = vstack(lines)
    L = Layered(template="stack")
    main_caps = [c for _, c, r in lines if r == "main"] or [100.0]
    mains = unary_union([g for g, r in placed if r == "main"]) if any(r == "main" for _, r in placed) else Polygon()
    accents = [g for g, r in placed if r == "accent"]
    if accents:
        acc = unary_union(accents)
        mains = knockout(mains, acc, 1000 * 0.004)
        L.add("accent", acc)
    L.add("main", mains)
    b = L.union().bounds
    kinds = [k for k in ctx.orn if rng.random() < 0.55][:2]
    add_ornaments(L, ctx, b, kinds, 1000 * 0.06 * 2.4)
    L.clear_orn(1000 * 0.018)
    return L


# ----------------------------------------------------------------------------- template: retro shadow
def t_retro(q: str, ctx: Ctx) -> Layered:
    rng = ctx.rng
    words, emph, breaks = parse(q)
    lines_w = auto_lines(words, breaks, max_lines=4)
    W = 1000.0
    ls = []
    up = use_caps(ctx.main, ctx)
    for l in lines_w:
        g, cap = line_fit(ctx.main, " ".join(l), W * rng.uniform(0.9, 1.0), up)
        if cap > 230:
            g, cap = line_fit(ctx.main, " ".join(l), W * 230 / cap, up)
        ls.append((g, cap, "main"))
    placed = vstack(ls, gap_ratio=0.34)
    text = unary_union([g for g, _ in placed])
    cap_avg = sum(c for _, c, _ in ls) / len(ls)
    d = cap_avg * rng.uniform(0.05, 0.075)
    gap = cap_avg * 0.035
    shadow = affinity.translate(text, d, -d).difference(text.buffer(gap, join_style=1))
    shadow = shadow.buffer(0)
    L = Layered(template="retro")
    L.add("main", text)
    L.add("accent", shadow)
    add_ornaments(L, ctx, L.union().bounds, [k for k in ctx.orn if rng.random() < 0.35][:1], 1000 * 0.09)
    L.clear_orn(1000 * 0.018)
    return L


# ----------------------------------------------------------------------------- template: badge
def t_badge(q: str, ctx: Ctx) -> Layered:
    rng = ctx.rng
    words, emph, breaks = parse(q)
    n = len(words)
    if emph is None:
        emph = auto_emphasis(words, rng)
    pre, post = words[:emph], words[emph + 1:]
    if not pre and not post:
        raise ValueError("badge needs context words")
    top = " ".join(pre) if pre else " ".join(post[: max(1, len(post) // 2)])
    bottom = " ".join(post) if pre else " ".join(post[max(1, len(post) // 2):])
    R = 500.0
    L = Layered(template="badge")
    L.add("frame", O.ring(R, R * 0.035))
    L.add("frame", O.ring(R * 0.9, R * 0.012))
    rr = R * 0.74
    up = use_caps(ctx.main, ctx, force=True if ctx.main.role in ("display", "serif", "retro") else None)

    def arc_text(text, outside, radius, max_deg):
        spec = ctx.main
        t = text.upper() if up else text
        size = 70.0
        sh = spec.face().shape(t, size=size, tracking=0.02, keep_glyphs=False)
        arc_len = math.radians(max_deg) * radius
        size = min(size * arc_len / max(sh.advance, 1), R * 0.20)
        g = on_arc(spec.face(), t, size, radius if outside else radius, 90.0 if outside else 270.0, outside, tracking=0.02)
        return g, size
    if top:
        g, s = arc_text(top, True, rr, 150)
        L.add("main", g)
    if bottom:
        g, s = arc_text(bottom, False, rr, 150)
        L.add("main", g)
    cw, cap = line_fit(ctx.accent if ctx.accent else ctx.main, words[emph], R * rng.uniform(1.15, 1.3), False)
    if cap > R * 0.55:
        cw, cap = line_fit(ctx.accent if ctx.accent else ctx.main, words[emph], R * 1.2 * (R * 0.55) / cap, False)
    cw = affinity.translate(cw, 0, -(cw.bounds[1] + cw.bounds[3]) / 2)
    L.add("accent", cw)
    for ang in (180, 0):
        L.add("orn", affinity.translate(O.star(R * 0.07), (R * 0.72 if ang == 0 else -R * 0.72), 0))
    L.add("orn", affinity.translate(O.divider(R * 0.9, R * 0.014, "star"), 0, -cap * 0.72 - R * 0.06) if cap else Polygon())
    return L


# ----------------------------------------------------------------------------- template: arch (boho rainbow)
def t_arch(q: str, ctx: Ctx) -> Layered:
    rng = ctx.rng
    words, emph, breaks = parse(q)
    text = " ".join(words)
    if len(text) > 34:
        raise ValueError("too long for arch")
    R = 520.0
    up = use_caps(ctx.main, ctx, force=True) if ctx.main.role in ("display", "serif") else False
    face = ctx.main.face()
    t = text.upper() if up else text
    sh = face.shape(t, size=100, tracking=0.03, keep_glyphs=False)
    arc_len = math.radians(165) * R
    size = min(100 * arc_len / sh.advance, R * 0.34)
    L = Layered(template="arch")
    L.add("main", on_arc(face, t, size, R, 90.0, True, tracking=0.03))
    inner = R - size * 0.9
    L.add("orn", O.rainbow(inner * 0.92, bands=rng.choice([3, 4, 5]), bw=inner * 0.12, gap=inner * 0.05))
    if rng.random() < 0.7:
        L.add("orn", affinity.translate(O.sun(inner * 0.14, 12), 0, inner * 0.0 + inner * 0.0))
    L.add("orn", O.bar(inner * 1.7, inner * 0.03))
    return L


# ----------------------------------------------------------------------------- template: frame
def t_frame(q: str, ctx: Ctx) -> Layered:
    rng = ctx.rng
    inner = t_stack(q, ctx)
    inner.layers.pop("orn", None)
    b = inner.union().bounds
    w, h = b[2] - b[0], b[3] - b[1]
    pad = 1000 * 0.11
    fw, fh = w + 2 * pad, h + 2 * pad * 1.15
    kind = rng.choice(["round", "scallop", "double", "oval"])
    th = 1000 * 0.014
    if kind == "round":
        fr = O.outline(O.rounded_rect(fw, fh, min(fw, fh) * 0.14), th)
    elif kind == "scallop":
        n_w = max(6, int(fw / 62)); n_h = max(3, int(fh / 62))
        sc = O.scallop_rect(fw, fh, n_w, n_h, 0)
        fr = O.outline(sc, th)
    elif kind == "double":
        a = O.rounded_rect(fw, fh, 36)
        fr = unary_union([O.outline(a, th * 1.6), O.outline(a.buffer(-pad * 0.22, join_style=1), th * 0.7)])
    else:
        e = affinity.scale(O.circle(1.0, (0, 0), 160), fw * 0.62, fh * 0.66)
        fr = unary_union([O.outline(e, th * 1.4), O.outline(e.buffer(-pad * 0.25), th * 0.6)])
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    L = Layered(template="frame")
    L.layers = dict(inner.layers)
    L.add("frame", affinity.translate(fr, cx, cy))
    return L


# ----------------------------------------------------------------------------- template: banner
def t_banner(q: str, ctx: Ctx) -> Layered:
    rng = ctx.rng
    words, emph, breaks = parse(q)
    text = " ".join(words)
    if len(text) > 26 or len(words) < 2:
        raise ValueError("banner needs short text")
    W = 1000.0
    up = use_caps(ctx.main, ctx)
    g, cap = line_fit(ctx.main, text, W * 0.8, up)
    cap = min(cap, 150)
    if cap == 150:
        g, cap = line_fit(ctx.main, text, W * 0.8 * 150 / (g.bounds[3] - 0 + 1e-9), up)
    h = max(cap * 2.2, 190.0)
    rb = O.banner(W, h, tail=W * 0.16, drop=h * 0.22)
    outl = O.outline(rb, W * 0.012)
    g = affinity.translate(g, 0, -(g.bounds[1] + g.bounds[3]) / 2)
    L = Layered(template="banner")
    L.add("frame", outl)
    L.add("main", g)
    L.add("orn", affinity.translate(O.stars_row(3, h * 0.17, h * 0.48), 0, h / 2 + h * 0.5))
    return L


TEMPLATES: Dict[str, Callable[[str, Ctx], Layered]] = {
    "stack": t_stack, "retro": t_retro, "badge": t_badge, "arch": t_arch, "frame": t_frame, "banner": t_banner,
}
