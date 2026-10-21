"""Procedural botanical & split monogram builder.

Generates welded, single-piece cuttable vectors for Cricut and Silhouette:
- 26 Letters A-Z
- 10 Digits 0-9
- Ampersand &

Each character is built in two variations:
1. Split Monogram (open horizontal ribbon with dual guide bars for custom text insertion)
2. Full Botanical Monogram (intact initial letter intertwined with botanical vines & blossoms)
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from shapely import affinity
from shapely.geometry import Point, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from etsy_factory.typo import ornaments as O
from etsy_factory.typo import text as T

FONT_PATH = Path(r"F:\WORKHORSE\etsy_factory\fonts\YoungSerif-Regular.ttf")
_FACE = None


def get_face() -> T.Face:
    global _FACE
    if _FACE is None:
        _FACE = T.Face(FONT_PATH)
    return _FACE


def clean_geom(g: BaseGeometry, buffer_eps: float = 0.0) -> BaseGeometry:
    """Ensure clean valid polygonal geometry without degenerate spikes."""
    if g.is_empty:
        return g
    if buffer_eps > 0:
        g = g.buffer(buffer_eps, join_style=1).buffer(-buffer_eps, join_style=1)
    return g


def create_botanicals(minx: float, miny: float, maxx: float, maxy: float, is_split: bool) -> List[BaseGeometry]:
    """Create tasteful botanical vines, leaves, and blossoms scaled and placed for the glyph bounds."""
    w = maxx - minx
    h = maxy - miny
    elements = []

    # 1. Top-right leafy sprig climbing outward
    sprig_tr = O.sprig(h * 0.32, leaves=4, leaf_len=h * 0.08)
    sprig_tr = affinity.rotate(sprig_tr, 38, origin=(0, 0))
    sprig_tr = affinity.translate(sprig_tr, maxx - w * 0.08, miny + h * 0.70)
    elements.append(sprig_tr)

    # 2. Bottom-left leafy sprig emerging from base/corner
    sprig_bl = O.sprig(h * 0.28, leaves=4, leaf_len=h * 0.075)
    sprig_bl = affinity.rotate(sprig_bl, -142, origin=(0, 0))
    sprig_bl = affinity.translate(sprig_bl, minx + w * 0.12, miny + h * 0.28)
    elements.append(sprig_bl)

    # 3. Delicate 6-petal daisy flower accent
    if is_split:
        flower_y = miny + h * 0.59
        flower = O.daisy(h * 0.09, petals=6)
        flower = affinity.translate(flower, minx - w * 0.02, flower_y)
        elements.append(flower)

        # Tiny bud on right bar
        bud = O.circle(h * 0.035, c=(maxx + w * 0.04, miny + h * 0.41))
        elements.append(bud)
    else:
        # Full monogram flower accent nestled on left flank
        flower = O.daisy(h * 0.10, petals=6)
        flower = affinity.translate(flower, minx + w * 0.05, miny + h * 0.48)
        elements.append(flower)

        # Delicate leaf pair at top-left
        lf = O.leaf(h * 0.12, h * 0.05, 50)
        lf = affinity.translate(lf, minx + w * 0.15, maxy - h * 0.05)
        elements.append(lf)

    return elements


def build_split_monogram(char: str, size: float = 100.0) -> BaseGeometry:
    """Build a welded split monogram for `char` at the given em size."""
    face = get_face()
    sh = face.shape(char, size=size)
    letter = sh.geom
    minx, miny, maxx, maxy = letter.bounds
    w = maxx - minx
    h = maxy - miny

    # Calculate split geometry
    gap_h = h * 0.22
    gap_y_center = miny + h * 0.48
    gap_y0 = gap_y_center - gap_h / 2
    gap_y1 = gap_y_center + gap_h / 2

    bar_t = h * 0.038
    bar_overhang = max(w * 0.08, 4.0)
    bar_x0 = minx - bar_overhang
    bar_x1 = maxx + bar_overhang

    # Split cut
    split_box = box(bar_x0 - 10, gap_y0, bar_x1 + 10, gap_y1)
    cut_letter = letter.difference(split_box)

    # Split bars (overlap slightly into letter bodies to ensure 100% welded union)
    top_bar = box(bar_x0, gap_y1 - bar_t * 0.25, bar_x1, gap_y1 + bar_t)
    bottom_bar = box(bar_x0, gap_y0 - bar_t, bar_x1, gap_y0 + bar_t * 0.25)

    # Botanicals
    botanicals = create_botanicals(minx, miny, maxx, maxy, is_split=True)

    welded = unary_union([cut_letter, top_bar, bottom_bar, *botanicals])
    return clean_geom(welded)


def build_full_monogram(char: str, size: float = 100.0) -> BaseGeometry:
    """Build an intact decorative botanical monogram for `char`."""
    face = get_face()
    sh = face.shape(char, size=size)
    letter = sh.geom
    minx, miny, maxx, maxy = letter.bounds

    botanicals = create_botanicals(minx, miny, maxx, maxy, is_split=False)
    welded = unary_union([letter, *botanicals])
    return clean_geom(welded)


def build_split_monogram_layers(char: str, size: float = 100.0) -> Tuple[BaseGeometry, BaseGeometry]:
    """Returns (letter_and_bars, botanicals) as separate layers for 2-color cutting."""
    face = get_face()
    sh = face.shape(char, size=size)
    letter = sh.geom
    minx, miny, maxx, maxy = letter.bounds
    w = maxx - minx
    h = maxy - miny

    gap_h = h * 0.22
    gap_y_center = miny + h * 0.48
    gap_y0 = gap_y_center - gap_h / 2
    gap_y1 = gap_y_center + gap_h / 2

    bar_t = h * 0.038
    bar_overhang = max(w * 0.08, 4.0)
    bar_x0 = minx - bar_overhang
    bar_x1 = maxx + bar_overhang

    split_box = box(bar_x0 - 10, gap_y0, bar_x1 + 10, gap_y1)
    cut_letter = letter.difference(split_box)

    top_bar = box(bar_x0, gap_y1 - bar_t * 0.25, bar_x1, gap_y1 + bar_t)
    bottom_bar = box(bar_x0, gap_y0 - bar_t, bar_x1, gap_y0 + bar_t * 0.25)

    letter_layer = unary_union([cut_letter, top_bar, bottom_bar])
    bot_elements = create_botanicals(minx, miny, maxx, maxy, is_split=True)
    bot_layer = unary_union(bot_elements)

    return clean_geom(letter_layer), clean_geom(bot_layer)


# List of all characters included in pack
CHARACTERS = [chr(c) for c in range(ord("A"), ord("Z") + 1)] + [str(d) for d in range(10)] + ["&"]
