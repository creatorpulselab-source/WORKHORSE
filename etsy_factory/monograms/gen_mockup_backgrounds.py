"""Generate photorealistic lifestyle product mockups for Monogram cut files using local ComfyUI SDXL.
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
        "tote_bag_lifestyle",
        "professional product photography, overhead 90-degree flat lay of a plain blank natural cream cotton canvas tote bag lying flat on a rustic light oak wood desk, smooth blank center of tote bag with clean unprinted fabric texture, soft natural morning window lighting, dried eucalyptus leaves and brass scissors on the outer desk border, no logos, no text, no branding, high quality, 8k, sharp focus",
        101,
        1024,
        1024,
    ),
    (
        "nursery_wooden_plaque",
        "professional product photography, eye-level front view of a blank round natural light birch wooden sign plaque hanging against a soft warm cream pastel nursery wall, beautiful subtle wood grain, completely clean blank smooth center, soft baby room ambient lighting, small eucalyptus sprig draping at the top, shallow depth of field, 8k, sharp focus",
        202,
        1024,
        1024,
    ),
    (
        "ceramic_mug_lifestyle",
        "professional product photography, eye-level close-up of a blank white ceramic coffee mug standing upright on a bright white marble kitchen countertop, soft morning sunlight casting gentle diagonal shadow from window, small potted green succulent in soft blurred background, clean empty mug surface, no text, no print, 8k",
        303,
        1024,
        1024,
    ),
    (
        "acrylic_keychain_flatlay",
        "professional product photography, top-down flat lay view of a blank clear transparent acrylic hexagon keychain with a small gold ring and beige suede tassel resting on textured ivory linen fabric, blank surface, bright clean natural daylight, shallow depth of field, 8k",
        404,
        1024,
        1024,
    ),
    (
        "craft_room_desk",
        "professional product photography, high angle view of an organized craft studio desk with a modern mint green electronic vinyl cutting machine, green grid craft cutting mat, metallic weeding hook tool and roll of transfer tape placed neatly, bright sunlight from craft room window, realistic clean workspace, 8k",
        505,
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
            "stickers, decals, logos, printed text, typography, letters, brand name, graphics, illustrations, "
            "hands, faces, deformed, blurry, cluttered center, objects in center, scratches, dark, noisy"
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

        # Wait for completion
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
