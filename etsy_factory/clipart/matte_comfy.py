"""Matting via ComfyUI (BiRefNet through ComfyUI's core background-removal nodes; RMBG-2.0 is gated and BiRefNet-General is not installed) - a stronger matte than rembg isnet for
pink / cream / blush subjects and subjects with ground shadows, where the colour-key cut (cutkey.py) fails.

    mask = matte_mask(Path("raw.png"))             # PIL 'L' image, same size as the input
    cutkey.cut_key(src, dst, matte=mask)           # reuses the colour-key edge refinement and tight crop
"""
from __future__ import annotations

import io
import json
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Optional

from PIL import Image

COMFY = "http://192.168.1.74:8188"


def _post_json(path: str, payload: dict, timeout: int = 30) -> dict:
    req = urllib.request.Request(COMFY + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())


def _get(path: str, timeout: int = 120) -> bytes:
    return urllib.request.urlopen(COMFY + path, timeout=timeout).read()


def _upload(path: Path, name: str) -> str:
    b = uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{name}\"\r\nContent-Type: image/png\r\n\r\n").encode() \
        + path.read_bytes() + (f"\r\n--{b}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--{b}--\r\n").encode()
    req = urllib.request.Request(COMFY + "/upload/image", data=body, headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())["name"]


def _workflow(image_name: str) -> dict:
    """ComfyUI core nodes: LoadBackgroundRemovalModel (birefnet.safetensors) -> RemoveBackground -> mask -> PNG."""
    return {
        "1": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "2": {"class_type": "LoadBackgroundRemovalModel", "inputs": {"bg_removal_name": "birefnet.safetensors"}},
        "3": {"class_type": "RemoveBackground", "inputs": {"bg_removal_model": ["2", 0], "image": ["1", 0]}},
        "4": {"class_type": "MaskToImage", "inputs": {"mask": ["3", 0]}},
        "5": {"class_type": "SaveImage", "inputs": {"filename_prefix": "etsy_matte", "images": ["4", 0]}},
    }


def matte_mask(src: Path, timeout: int = 300) -> Optional[Image.Image]:
    """Foreground mask (white = keep) for `src`, or None if ComfyUI failed."""
    name = _upload(src, f"matte_{uuid.uuid4().hex[:8]}.png")
    pid = _post_json("/prompt", {"prompt": _workflow(name), "client_id": uuid.uuid4().hex})["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < timeout:
        hist = json.loads(_get(f"/history/{pid}", 30))
        if pid in hist:
            h = hist[pid]
            if h.get("status", {}).get("status_str") == "error":
                raise RuntimeError("ComfyUI matte error: " + json.dumps(h["status"])[:800])
            if h.get("outputs"):
                im = h["outputs"]["5"]["images"][0]
                q = urllib.parse.urlencode({"filename": im["filename"], "subfolder": im.get("subfolder", ""), "type": im["type"]})
                return Image.open(io.BytesIO(_get("/view?" + q))).convert("L")
        time.sleep(0.8)
    return None
