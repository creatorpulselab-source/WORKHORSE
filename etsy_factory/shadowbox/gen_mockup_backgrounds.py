"""Generate photorealistic product mockup backdrops for 3D Layered Shadow Boxes using local ComfyUI SDXL.
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
        "shadowbox_nursery_shelf",
        "professional interior product photography, eye-level straight-on view of an empty blank square white wooden shadow box picture frame standing upright on a light natural oak floating wall shelf, clean empty interior frame cavity with soft subtle warm ambient glow, cream neutral wall in background, small green potted succulent and children's book beside it, warm cozy evening lighting, 8k, sharp focus",
        601,
        1024,
        1024,
    ),
    (
        "shadowbox_nursery_dresser",
        "professional interior product photography, front centered view of an empty blank square natural birch wood shadow box frame placed upright on a white modern nursery dresser, completely blank clean empty frame interior, soft warm nursery room lighting, blurred neutral baby room background, small knitted plush toy beside it, 8k, sharp focus",
        702,
        1024,
        1024,
    ),
    (
        "shadowbox_living_bookshelf",
        "professional interior product photography, front view of an empty blank square deep black wooden shadow box frame sitting upright on a minimalist oak bookshelf, clean blank empty frame interior, soft warm light, neat hardcover books beside the frame, cozy elegant home interior, 8k, sharp focus",
        803,
        1024,
        1024,
    ),
    (
        "shadowbox_craft_flatlay",
        "professional craft photography, 90-degree overhead flat lay view of a bright clean craft studio desk, empty square wooden frame, mint green vinyl cutting machine at the top edge, precision craft tweezers, roll of double-sided foam tape squares, craft cutting mat, bright morning sunlight, organized clean workspace, 8k, sharp focus",
        904,
        1024,
        1024,
    ),
]


def generate_backdrops():
    for name, prompt_text, seed, w, h in TARGETS:
        out_file = OUT_DIR / f"{name}_{seed}.png"
        if out_file.exists() and out_file.stat().st_size > 50000:
            print(f"[EXISTS] {name}_{seed}.png")
            continue
        neg_text = (
            "art, picture, drawing, photo inside frame, print inside frame, artwork inside frame, "
            "faces, people, hands, text, letters, logos, cluttered, ugly, distorted, blurry, scratches, dark"
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
            "7": {"class_type": "SaveImage", "inputs": {"filename_prefix": f"etsy_{name}", "images": ["6", 0]}},
        }
        client_id = str(uuid.uuid4())
        payload = json.dumps({"prompt": wf, "client_id": client_id}).encode("utf-8")
        req = urllib.request.Request(f"{COMFY}/prompt", data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
        prompt_id = data["prompt_id"]
        print(f"Queued {name} (prompt_id={prompt_id}, seed={seed})")

        while True:
            time.sleep(1.5)
            with urllib.request.urlopen(f"{COMFY}/history/{prompt_id}") as h_resp:
                hist = json.loads(h_resp.read())
            if prompt_id in hist and "outputs" in hist[prompt_id]:
                node_out = hist[prompt_id]["outputs"].get("7", {})
                images = node_out.get("images", [])
                if images:
                    img_info = images[0]
                    params = urllib.parse.urlencode({
                        "filename": img_info["filename"],
                        "subfolder": img_info.get("subfolder", ""),
                        "type": img_info.get("type", "output"),
                    })
                    view_url = f"{COMFY}/view?{params}"
                    with urllib.request.urlopen(view_url) as v_resp:
                        img_bytes = v_resp.read()
                    out_file.write_bytes(img_bytes)
                    print(f"Saved {out_file.name} ({len(img_bytes)} bytes)")
                break


if __name__ == "__main__":
    generate_backdrops()
