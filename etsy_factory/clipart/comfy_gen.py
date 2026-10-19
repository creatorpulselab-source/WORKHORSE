"""Z-Image Turbo text-to-image client for illustrated clipart, via the ComfyUI REST API.

(Qwen-Image-2512 + Lightning LoRA was tried first and returned all-black images on this server - likely the server's
--use-sage-attention flag, not verified.)

Images are cached by (name, seed) so interrupted runs resume. Several prompts are queued at once; ComfyUI executes them
serially on the GPU, so queue depth only hides HTTP latency.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

COMFY = "http://192.168.1.74:8188"
UNET = "z_image_turbo_bf16.safetensors"
CLIP = "qwen_3_4b.safetensors"
VAE = "ae.safetensors"


def _post(path: str, payload: dict, timeout: int = 30) -> dict:
    req = urllib.request.Request(COMFY + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())


def _get(path: str, timeout: int = 60) -> bytes:
    return urllib.request.urlopen(COMFY + path, timeout=timeout).read()


def available() -> bool:
    try:
        _get("/system_stats", timeout=5)
        return True
    except Exception:
        return False


def _wf_zimage(prompt: str, seed: int, w: int, h: int) -> dict:
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": UNET, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": CLIP, "type": "lumina2", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "5": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 3.0}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "7": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["6", 0]}},
        "8": {"class_type": "EmptySD3LatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "9": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": 8, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple",
                                                   "denoise": 1.0, "model": ["5", 0], "positive": ["6", 0], "negative": ["7", 0],
                                                   "latent_image": ["8", 0]}},
        "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["3", 0]}},
        "11": {"class_type": "SaveImage", "inputs": {"filename_prefix": "etsy_clipart", "images": ["10", 0]}},
    }


QWEN21_UNET = "qwen_image_2.1_int8_convrot.safetensors"
QWEN21_CLIP = "qwen3vl_8b_w4a8.safetensors"          # the template's qwen3vl_8b_int8_convrot is not installed on this server
QWEN21_VAE = "qwen_image_2.1_vae_bf16.safetensors"


def _wf_qwen21(prompt: str, seed: int, w: int, h: int, steps: int = 25) -> dict:
    """Mirrors ComfyUI's 'Qwen Image 2.1: Text to Image' template (UNET -> QwenImage21Cache -> KSampler, cfg 1)."""
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": QWEN21_UNET, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": QWEN21_CLIP, "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": QWEN21_VAE}},
        "4": {"class_type": "QwenImage21Cache", "inputs": {"model": ["1", 0], "device": "auto", "dtype": "default"}},
        "6": {"class_type": "TextEncodeQwenImage21", "inputs": {"clip": ["2", 0], "prompt": prompt, "negative_prompt": "", "resolution": 1024}},
        "8": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "9": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": steps, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple",
                                                   "denoise": 1.0, "model": ["4", 0], "positive": ["6", 0], "negative": ["6", 1],
                                                   "latent_image": ["8", 0]}},
        "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["3", 0]}},
        "11": {"class_type": "SaveImage", "inputs": {"filename_prefix": "etsy_clipart", "images": ["10", 0]}},
    }


def _wf_flux(prompt: str, seed: int, w: int, h: int, steps: int = 20) -> dict:
    """FLUX.1 Krea [dev] (fp8): DualCLIP (clip_l + t5xxl), FluxGuidance 3.5, cfg 1."""
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux1-krea-dev_fp8_scaled.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "clip_l.safetensors", "clip_name2": "t5xxl_fp8_e4m3fn_scaled.safetensors",
                                                          "type": "flux", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "7": {"class_type": "FluxGuidance", "inputs": {"conditioning": ["6", 0], "guidance": 3.5}},
        "12": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["6", 0]}},
        "8": {"class_type": "EmptySD3LatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "9": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": steps, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple",
                                                   "denoise": 1.0, "model": ["1", 0], "positive": ["7", 0], "negative": ["12", 0],
                                                   "latent_image": ["8", 0]}},
        "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["3", 0]}},
        "11": {"class_type": "SaveImage", "inputs": {"filename_prefix": "etsy_clipart", "images": ["10", 0]}},
    }


ENGINES = {"zimage": _wf_zimage, "qwen21": _wf_qwen21, "flux": _wf_flux}


def workflow(prompt: str, seed: int, w: int = 1328, h: int = 1328, engine: str = "zimage") -> dict:
    return ENGINES[engine](prompt, seed, w, h)


def _run(prompt: str, seed: int, out: Path, w: int, h: int, timeout: int = 600) -> Optional[Path]:
    pid = _post("/prompt", {"prompt": workflow(prompt, seed, w, h), "client_id": uuid.uuid4().hex})["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < timeout:
        hist = json.loads(_get(f"/history/{pid}"))
        if pid in hist:
            h_ = hist[pid]
            if h_.get("status", {}).get("status_str") == "error":
                raise RuntimeError(f"ComfyUI error: {json.dumps(h_['status'])[:600]}")
            if h_.get("outputs"):
                img = h_["outputs"]["11"]["images"][0]
                q = urllib.parse.urlencode({"filename": img["filename"], "subfolder": img.get("subfolder", ""), "type": img["type"]})
                out.write_bytes(_get("/view?" + q, timeout=120))
                return out
        time.sleep(1.0)
    return None


def generate_many(jobs: Iterable[Tuple[str, str, int]], raw_dir: Path, w: int = 1328, h: int = 1328, parallel: int = 3,
                  progress: Optional[Callable[[int, int, str], None]] = None) -> Dict[str, Optional[Path]]:
    """jobs = (name, prompt, seed). Returns name -> path (None on failure). Existing files are reused."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    jobs = list(jobs)
    res: Dict[str, Optional[Path]] = {}
    done = [0]

    def one(job):
        name, prompt, seed = job
        out = raw_dir / f"{name}.png"
        if not out.exists() or out.stat().st_size < 1000:
            for attempt in range(2):
                try:
                    _run(prompt, seed, out, w, h)
                    break
                except Exception as e:  # noqa: BLE001
                    print(f"  ! {name} attempt {attempt + 1}: {e}")
                    time.sleep(3)
        done[0] += 1
        if progress:
            progress(done[0], len(jobs), name)
        return name, (out if out.exists() else None)

    with ThreadPoolExecutor(max_workers=parallel) as ex:
        for name, p in ex.map(one, jobs):
            res[name] = p
    return res
