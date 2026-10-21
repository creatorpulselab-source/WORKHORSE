"""Generate high-end photographic product mockup backdrops using local ComfyUI SDXL.
"""
import json
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

COMFY = "http://192.168.1.74:8188"
CKPT = "cyberrealisticXL_v80.safetensors"
OUT_DIR = Path(r"F:\WORKHORSE\workspace\etsy_mockups")
OUT_DIR.mkdir(parents=True, exist_ok=True)

TARGETS = [
    (
        "laptop_topdown",
        "professional product photography, directly overhead 90-degree flat lay view looking straight down at a closed sleek modern silver metallic laptop centered on a bright oak desk, clean blank brushed aluminum lid, no logo, no branding, cup of tea and pen at the outer edges, soft morning sunlight, sharp focus, 8k",
        777,
        1024,
        1024,
    ),
    (
        "water_bottle_clean",
        "professional product photography, eye-level front centered view of a blank pastel insulated stainless steel tumbler water bottle standing upright on a light wooden table, soft natural daylight, clean matte powder-coated surface, completely blank, no logos, no branding, no text, shallow depth of field, 8k, sharp focus",
        888,
        1024,
        1024,
    ),
    (
        "ipad_planner_clean",
        "professional product photography, directly overhead flat lay view of a modern white iPad tablet centered on a bright marble desk, the tablet screen is completely empty and blank white, a sleek stylus pen beside it and small green succulent plant at the corner, soft daylight, 8k, sharp focus",
        999,
        1024,
        1024,
    ),
]


def generate_backdrops():
    for name, prompt_text, seed, w, h in TARGETS:
        out_file = OUT_DIR / f"{name}_{seed}.png"
        if out_file.exists():
            print(f"[EXISTS] {name}_{seed}.png")
            continue
        neg_text = (
            "stickers, decals, logos, text, brand name, print, pattern, graphics, "
            "hands, faces, ugly, deformed, blurry, cluttered center, objects in center, scratches, dark"
        )
        wf = {
            "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
            "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt_text, "clip": ["1", 1]}},
            "3": {"class_type": "CLIPTextEncode", "inputs": {"text": neg_text, "clip": ["1", 1]}},
            "4": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": 28,
                    "cfg": 6.0,
                    "sampler_name": "dpmpp_2m",
                    "scheduler": "karras",
                    "denoise": 1.0,
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["4", 0],
                },
            },
            "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
            "7": {"class_type": "SaveImage", "inputs": {"filename_prefix": f"etsy_mockup_{name}", "images": ["6", 0]}},
        }
        req = urllib.request.Request(
            COMFY + "/prompt",
            data=json.dumps({"prompt": wf, "client_id": uuid.uuid4().hex}).encode(),
            headers={"Content-Type": "application/json"},
        )
        res = json.loads(urllib.request.urlopen(req, timeout=10).read())
        pid = res["prompt_id"]
        print(f"[QUEUED] {name} (PID: {pid})...")
        t0 = time.time()
        while time.time() - t0 < 180:
            hist = json.loads(urllib.request.urlopen(COMFY + f"/history/{pid}", timeout=10).read())
            if pid in hist and hist[pid].get("outputs"):
                img_info = hist[pid]["outputs"]["7"]["images"][0]
                q = urllib.parse.urlencode({
                    "filename": img_info["filename"],
                    "subfolder": img_info.get("subfolder", ""),
                    "type": img_info["type"],
                })
                url = f"{COMFY}/view?{q}"
                data = urllib.request.urlopen(url, timeout=30).read()
                out_file.write_bytes(data)
                print(f"[SAVED] {name} -> {out_file} ({len(data)} bytes)")
                break
            time.sleep(2.0)


if __name__ == "__main__":
    generate_backdrops()
