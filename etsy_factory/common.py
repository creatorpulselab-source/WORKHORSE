"""Shared helpers for the WORKHORSE Etsy listing factory (runs under F:\\WORKHORSE\\.venv, not inside the server)."""
from __future__ import annotations

import json
import time
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List

LISTINGS_ROOT = Path(r"F:\WORKHORSE\workspace\etsy_listings")
ETSY_MAX_FILE_BYTES = 20 * 1024 * 1024      # Etsy digital listings: max 20 MB per file
ETSY_MAX_FILES = 5                           # ...and at most 5 files per listing
ETSY_MAX_IMAGES = 10


class RunReport:
    """Records per-stage wall-clock so the real start-to-finish time of every bundle is known, not guessed."""

    def __init__(self, slug: str) -> None:
        self.slug = slug
        self.t0 = time.time()
        self.stages: List[Dict[str, Any]] = []
        self.facts: Dict[str, Any] = {}

    @contextmanager
    def stage(self, name: str):
        t = time.time()
        print(f"[{self.slug}] > {name} ...", flush=True)
        try:
            yield
        finally:
            dt = round(time.time() - t, 1)
            self.stages.append({"stage": name, "seconds": dt})
            print(f"[{self.slug}] < {name} done in {dt}s", flush=True)

    def save(self, folder: Path) -> Dict[str, Any]:
        data = {"slug": self.slug, "total_seconds": round(time.time() - self.t0, 1), "stages": self.stages, **self.facts}
        (folder / "run_report.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data


def listing_dirs(slug: str) -> Dict[str, Path]:
    root = LISTINGS_ROOT / slug
    d = {"root": root, "files": root / "files", "images": root / "images", "work": root / "_work"}
    for p in d.values():
        p.mkdir(parents=True, exist_ok=True)
    return d


def zip_folder(src: Path, dest_zip: Path, patterns=("*",)) -> Path:
    """Zip a folder (flat names preserved relative to src) and enforce Etsy's 20 MB per-file cap."""
    with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for pat in patterns:
            for f in sorted(src.rglob(pat)):
                if f.is_file():
                    z.write(f, arcname=str(f.relative_to(src)))
    size = dest_zip.stat().st_size
    if size > ETSY_MAX_FILE_BYTES:
        raise RuntimeError(f"{dest_zip.name} is {size/1e6:.1f} MB - over Etsy's 20 MB per-file limit; split it.")
    return dest_zip


LICENSE_TEXT = """LICENSE & TERMS OF USE
======================
You may:
  * Use these files for personal projects and gifts.
  * Sell PHYSICAL items you make from these files (for example printed cutters, keychains or crafts),
    in any quantity, with no credit required.

You may NOT:
  * Resell, share, give away, upload or redistribute the digital files themselves (original or modified).
  * Include the digital files in another bundle, file pack, subscription or marketplace listing.
  * Claim the designs as your own original digital product.

All designs are original. No licensed characters, brands or logos are included.
This is a digital download - no physical item is shipped. Because files can't be returned, refunds are
not available, but if anything is wrong with a file contact the shop and it will be fixed.
"""
