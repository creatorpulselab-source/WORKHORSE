"""Test running a harmonizing img2img pass on ComfyUI to seamlessly integrate stickers into the background.
"""
import json
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

COMFY = "http://192.168.1.74:8188"
CKPT = "cyberrealisticXL_v80.safetensors"

img_path = Path(r"F:\WORKHORSE\workspace\etsy_listings\cute_animal_sticker_sheets_printable_cut_files\images\04_mockup_laptop.jpg")

# 1. Upload image to ComfyUI
boundary = uuid.uuid4().hex
body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="image"; filename="laptop_mockup_in.jpg"\r\n'
    f"Content-Type: image/jpeg\r\n\r\n"
).encode("utf-8") + img_path.read_bytes() + f"\r\n--{boundary}--\r\n".encode("utf-8")

req = urllib.request.Request(
    f"{COMFY}/upload/image",
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
)
upload_info = json.loads(urllib.request.urlopen(req, timeout=15).read())
print("Upload success:", upload_info)

uploaded_name = upload_info["name"]

# 2. Run img2img with light denoise (0.22) to physically harmonize shadows, edge specular, and surface reflection
prompt = "professional product photography, cute vinyl animal die-cut stickers on silver laptop, warm morning sunlight, natural reflections, high resolution, 8k, photorealistic"
neg = "ugly, blurry, deformed, scratches, dirty, dark, text on laptop"

wf = {
    "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
    "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
    "3": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["1", 1]}},
    "4": {"class_type": "LoadImage", "inputs": {"image": uploaded_name}},
    "5": {"class_type": "VAEEncode", "inputs": {"pixels": ["4", 0], "vae": ["1", 2]}},
    "6": {
        "class_type": "KSampler",
        "inputs": {
            "seed": 1234,
            "steps": 25,
            "cfg": 5.0,
            "sampler_name": "dpmpp_2m",
            "scheduler": "karras",
            "denoise": 0.22,
            "model": ["1", 0],
            "positive": ["2", 0],
            "negative": ["3", 0],
            "latent_image": ["5", 0],
        },
    },
    "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
    "8": {"class_type": "SaveImage", "inputs": {"filename_prefix": "harmonized_laptop", "images": ["7", 0]}},
}

req_p = urllib.request.Request(
    f"{COMFY}/prompt",
    data=json.dumps({"prompt": wf, "client_id": uuid.uuid4().hex}).encode(),
    headers={"Content-Type": "application/json"},
)
res = json.loads(urllib.request.urlopen(req_p, timeout=10).read())
pid = res["prompt_id"]
print("Prompt queued, PID:", pid)

t0 = time.time()
while time.time() - t0 < 120:
    hist = json.loads(urllib.request.urlopen(f"{COMFY}/history/{pid}", timeout=10).read())
    if pid in hist and hist[pid].get("outputs"):
        out_img = hist[pid]["outputs"]["8"]["images"][0]
        q = urllib.parse.urlencode({
            "filename": out_img["filename"],
            "subfolder": out_img.get("subfolder", ""),
            "type": out_img["type"],
        })
        data = urllib.request.urlopen(f"{COMFY}/view?{q}").read()
        out_path = Path(r"F:\WORKHORSE\workspace\etsy_mockups\harmonized_laptop.png")
        out_path.write_bytes(data)
        print("Harmonized image saved to:", out_path)
        break
    time.sleep(2.0)
