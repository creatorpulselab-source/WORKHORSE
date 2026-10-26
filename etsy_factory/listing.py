"""Etsy listing copy writer + validator. Produces listing.md / listing.json next to the images and files.

Hard Etsy limits enforced here: title <= 140 chars, exactly 13 tags each <= 20 chars, <= 10 images, <= 5 files x 20 MB.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Sequence

from .common import ETSY_MAX_FILE_BYTES, ETSY_MAX_FILES, ETSY_MAX_IMAGES

AI_DISCLOSURE = ("Etsy asks how the item was made (creation process / AI disclosure) - answer it honestly. For clipart PNGs, "
                 "sticker sheets, and sculpted 3D STLs, select 'Designed by me' with 'With the help of an AI generator' (or "
                 "'Created by me' + 'Digital tools/AI-assisted' depending on the prompt) and include the Design & Creation "
                 "Transparency block in the description.")


def validate(title: str, tags: Sequence[str], images: Sequence[Path], upload_files: Sequence[Path]) -> List[str]:
    problems: List[str] = []
    if len(title) > 140:
        problems.append(f"title is {len(title)} chars (max 140)")
    if len(tags) != 13:
        problems.append(f"{len(tags)} tags (Etsy allows 13 - use all 13)")
    for t in tags:
        if len(t) > 20:
            problems.append(f"tag '{t}' is {len(t)} chars (max 20)")
    if len({t.lower() for t in tags}) != len(tags):
        problems.append("duplicate tags")
    if len(images) > ETSY_MAX_IMAGES:
        problems.append(f"{len(images)} images (max {ETSY_MAX_IMAGES})")
    if len(upload_files) > ETSY_MAX_FILES:
        problems.append(f"{len(upload_files)} upload files (max {ETSY_MAX_FILES})")
    for f in upload_files:
        if f.stat().st_size > ETSY_MAX_FILE_BYTES:
            problems.append(f"{f.name} is {f.stat().st_size/1e6:.1f} MB (max 20)")
    return problems


def write_listing(root: Path, *, title: str, tags: Sequence[str], description: str, price_usd: float, sale_hint: str,
                  category: str, materials: str, whats_in_the_files: Sequence[str], notes: Sequence[str] = ()) -> Dict:
    images = sorted((root / "images").glob("[0-9][0-9]_*.jpg"))
    uploads = sorted((root / "etsy_upload").glob("*"))
    problems = validate(title, tags, images, uploads)
    data = {
        "title": title, "title_chars": len(title), "tags": list(tags), "price_usd": price_usd, "sale_hint": sale_hint,
        "category": category, "materials": materials, "description": description,
        "images_in_upload_order": [p.name for p in images],
        "upload_files": [{"name": p.name, "mb": round(p.stat().st_size / 1e6, 2)} for p in uploads],
        "contents": list(whats_in_the_files), "notes": list(notes), "validation_problems": problems,
    }
    (root / "listing.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    md = [f"# {title}", "", f"**Title length:** {len(title)}/140  ", f"**Price:** ${price_usd:.2f}  ({sale_hint})  ",
          f"**Category:** {category}  ", f"**Materials field:** {materials}  ", "", "## Tags (13)", ", ".join(tags), "",
          "## Description", "", description, "", "## Photos - upload in this order"]
    md += [f"{i}. `{p.name}`" for i, p in enumerate(images, 1)]
    md += ["", "## Digital files to attach"] + [f"- `{u['name']}` ({u['mb']} MB)" for u in data["upload_files"]]
    md += ["", "## Contents"] + [f"- {c}" for c in whats_in_the_files]
    md += ["", "## Before you publish", f"- {AI_DISCLOSURE}"] + [f"- {n}" for n in notes]
    md += ["", "## Validation", "OK - all Etsy limits satisfied" if not problems else "\n".join(f"- PROBLEM: {p}" for p in problems)]
    (root / "listing.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return data
