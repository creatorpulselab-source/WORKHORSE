"""ComfyUI-generated photographic backdrops for listing images (cached; reusable across listings).

Uses the existing ComfyUI server (SDXL checkpoint) through its plain REST API. If the server is unreachable a procedural
gradient backdrop is returned instead so the pipeline never blocks.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Dict, Optional

from PIL import Image

COMFY = "http://192.168.1.74:8188"
CACHE = Path(r"F:\WORKHORSE\workspace\etsy_backgrounds")
CHECKPOINT = "cyberrealisticXL_v80.safetensors"

NEG = ("text, watermark, logo, signature, people, hands, faces, animals, ugly, blurry, low quality, deformed, "
       "cluttered center, objects in the center, dark, dull, desaturated, noise")

_COMMON = ("professional product photography backdrop, ultra detailed, vibrant saturated colors, high contrast, "
           "sharp focus, 8k, ")

BACKGROUNDS: Dict[str, str] = {
    "plants_flatlay": (_COMMON + "top-down flat lay, bright light wooden table, green monstera and fern leaves and small succulents "
                       "only around the edges, warm sunlight shadows, large clear empty wooden surface in the center"),
    "christmas_table": (_COMMON + "Christmas scene, a large empty rustic wooden tabletop filling the lower 60 percent of the "
                        "frame in warm light, background blurred with glowing golden fairy lights and a decorated Christmas "
                        "tree far out of focus, red and green accents, nothing on the table"),
    "christmas_flatlay": (_COMMON + "top-down flat lay, festive Christmas baking scene, rustic dark wooden table, scattered "
                          "flour, cinnamon sticks, star anise, pine branches with red berries, red ribbon, glowing warm fairy "
                          "lights, red and green and gold, props only around the edges, large clear empty wooden surface "
                          "in the center"),
    "christmas_bokeh": (_COMMON + "cozy Christmas kitchen counter, empty polished wooden countertop in the foreground, "
                        "background blurred with warm golden bokeh lights, red and green decorations, snow outside the window"),
    "desk_flatlay": (_COMMON + "top-down flat lay of a modern home office desk, bright oak desk surface, leaves of a plant, "
                     "notebook, coffee cup and pencils only at the edges, large clear empty desk surface in the center, "
                     "colorful teal and orange accents"),
    "desk_bokeh": (_COMMON + "bright modern workspace, empty light wood desk surface in the foreground, window light, blurred "
                   "background with plants and shelves, teal and orange accents"),
    "summer_flatlay": (_COMMON + "top-down flat lay, sunny summer picnic, turquoise and yellow beach towels, sand, sunglasses "
                       "and shells only at the edges, large clear empty wooden deck surface in the center"),
    "summer_bokeh": (_COMMON + "sunny backyard party table, empty wooden table surface in the foreground, blurred background "
                     "with string lights, green trees and blue sky, summer vibe"),
    "colorful_flatlay": (_COMMON + "top-down flat lay, bright playful craft background, teal coral yellow and purple paper "
                         "confetti and ribbon around the edges, large clear empty colorful surface in the center"),
    "plants_bokeh": (_COMMON + "bright sunny windowsill shelf, empty light wooden shelf surface in the foreground, blurred "
                     "green houseplants and white wall in the background, warm sunlight"),
    "craft_flatlay": (_COMMON + "top-down flat lay craft room, pastel pink and teal washi tape, scissors, colorful paper and "
                      "string lights only at the edges, large clear empty white marble surface in the center"),
    "valentine_flatlay": (_COMMON + "top-down flat lay, romantic Valentine baking scene, white marble surface, scattered pink and red rose "
                          "petals, flour, strawberries, pink ribbon, small gold heart confetti only around the edges, soft pink and "
                          "red and gold, large clear empty marble surface in the center"),
}

# ---- 3/4 "table view" scenes: camera ~20-28 degrees above an EMPTY surface that fills the lower 60% of the frame, so 3D
# renders rendered at the same elevation sit ON the surface (no floating). Natural, muted, premium product-photo look.
_TABLE = ("professional product photography scene, photorealistic, eye-level three-quarter view looking slightly down at an "
          "empty tabletop, the empty surface fills the lower two thirds of the frame, soft natural light, shallow depth of "
          "field, background softly blurred, muted natural color palette, high detail, nothing on the surface, ")
BACKGROUNDS.update({
    "desk_table": _TABLE + "light oak desk in a bright modern home office, window light from the left, blurred green plant "
                  "and bookshelf and laptop far in the background, calm neutral tones with soft sage and warm wood",
    "desk_table_dark": _TABLE + "walnut desk in a cozy study, warm lamp glow, blurred bookshelf in the background, moody warm tones",
    "picnic_table": _TABLE + "weathered wooden outdoor table on a sunny backyard deck, golden hour light, blurred green trees and "
                    "warm string lights far behind, summer evening mood",
    "kitchen_table": _TABLE + "scrubbed light wooden kitchen table, bright airy farmhouse kitchen blurred behind, soft window "
                     "light, white and warm wood tones",
    "christmas_table_view": _TABLE + "rustic wooden table, cozy Christmas living room blurred behind with a softly glowing "
                            "tree and warm golden fairy lights, deep green and red accents, warm light",
    "plant_shelf": _TABLE + "light wooden shelf by a sunny window, blurred leafy houseplants and white wall behind, bright airy "
                   "natural light, soft greens",
    "craft_table": _TABLE + "white-washed wooden craft table in a bright studio, blurred shelves with fabric and paper rolls "
                   "behind, airy pastel neutrals",
    "stone_counter": _TABLE + "pale marble and light wood workshop bench, clean bright studio, blurred neutral wall, soft light",
    "valentine_table": _TABLE + "white marble kitchen counter, romantic Valentine kitchen blurred behind with soft pink and red bokeh "
                       "lights and a few blurred roses, pink and red and white tones, warm soft light",
})


NEG_TABLE = ("text, watermark, logo, signature, people, hands, faces, animals, ugly, blurry foreground, low quality, deformed, "
             "objects on the table, cups, mugs, plates, books on the table, clutter on the surface, cartoon, illustration, "
             "oversaturated, neon, tilted horizon, fisheye")


def _post(path: str, payload: dict, timeout: int = 30) -> dict:
    req = urllib.request.Request(COMFY + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())


def _get(path: str, timeout: int = 30) -> bytes:
    return urllib.request.urlopen(COMFY + path, timeout=timeout).read()


def available() -> bool:
    try:
        _get("/system_stats", timeout=4)
        return True
    except Exception:
        return False


def _workflow(prompt: str, seed: int, w: int, h: int, steps: int = 30, cfg: float = 6.0) -> dict:
    neg = NEG_TABLE if prompt.startswith("professional product photography scene") else NEG
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CHECKPOINT}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "dpmpp_2m",
                                                    "scheduler": "karras", "denoise": 1.0, "model": ["1", 0],
                                                    "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"filename_prefix": "etsy_bg", "images": ["6", 0]}},
    }


def generate(name: str, seed: int = 20261018, size: int = 1280, timeout: int = 420, force: bool = False) -> Optional[Path]:
    """Generate (or return the cached) backdrop `name`. Returns None if ComfyUI is unavailable or fails."""
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / f"{name}_{seed}.png"
    if out.exists() and not force:
        return out
    if not available():
        return None
    wf = _workflow(BACKGROUNDS[name], seed, size, size)
    pid = _post("/prompt", {"prompt": wf, "client_id": uuid.uuid4().hex})["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < timeout:
        hist = json.loads(_get(f"/history/{pid}"))
        if pid in hist and hist[pid].get("outputs"):
            img = hist[pid]["outputs"]["7"]["images"][0]
            q = urllib.parse.urlencode({"filename": img["filename"], "subfolder": img.get("subfolder", ""), "type": img["type"]})
            out.write_bytes(_get("/view?" + q, timeout=60))
            return out
        time.sleep(1.5)
    return None


def load(name: str, size: int = 2000, seed: int = 20261018) -> Image.Image:
    """Backdrop as a size x size RGB image (ComfyUI photo, or gradient fallback)."""
    p = generate(name, seed=seed)
    if p:
        return Image.open(p).convert("RGB").resize((size, size), Image.LANCZOS)
    from .kit import vgrad
    return vgrad(size, size, (60, 40, 140), (10, 10, 50))
