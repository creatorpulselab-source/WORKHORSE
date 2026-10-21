"""Generate photorealistic product mockup backdrops for Laser-Cut Keychains & Earrings using local ComfyUI SDXL.
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
        "laser_keychains_wood_flatlay",
        "professional product photography, overhead 90-degree flat lay of a blank natural birch plywood laser-cut keychain blank with an antique brass split keyring and beige suede tassel resting on a light oak workbench, clean blank smooth wooden surface, soft natural morning window lighting, dried eucalyptus leaves and brass calipers at the outer border, no logos, no text, no branding, 8k, sharp focus",
        1101,
        1024,
        1024,
    ),
    (
        "laser_earrings_jewelry_stand",
        "professional product photography, eye-level close-up of a modern white linen jewelry earring display T-stand with small hooks, standing on a bright white marble vanity countertop, soft morning sunlight casting gentle diagonal shadows, small green succulent plant in soft blurred background, clean empty display stand, 8k, sharp focus",
        1202,
        1024,
        1024,
    ),
    (
        "laser_backpack_keychain_lifestyle",
        "professional lifestyle product photography, close-up of a clean cream canvas backpack zipper pull with a blank natural birch wooden keychain tag attached via a small brass carabiner clip, soft outdoor natural morning daylight, clean blank wood surface, shallow depth of field, 8k, sharp focus",
        1303,
        1024,
        1024,
    ),
    (
        "laser_workshop_glowforge",
        "professional craft studio photography, eye-level angled view of a modern clean desktop laser cutting machine on a solid wood craft table, flat sheet of natural 3mm birch plywood resting on the laser honey comb bed, laser safety glasses on the desk, bright sunlit maker workshop, 8k, sharp focus",
        1404,
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
            "text, letters, words, logo, typography, brand name, illustration, drawing, "
            "faces, people, hands, cluttered, blurry, scratched, noisy, dark"
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
