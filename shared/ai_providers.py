import os
import sys
import json
import base64
import requests
from pathlib import Path
from typing import List, Optional, Dict, Any

from shared.vram_manager import vram_manager

class AIProviderService:
    def __init__(self, config_path: str = "F:/WORKHORSE/config.json"):
        self.config_path = Path(config_path)
        self.load_config()

    def load_config(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        except Exception:
            self.config = {}

    def is_strict_local(self) -> bool:
        return self.config.get("privacy", {}).get("strict_local_only", True)

    def get_ollama_url(self) -> str:
        return self.config.get("ai_engine", {}).get("ollama_url", "http://localhost:11434")

    def get_text_model(self) -> str:
        agent_model = self.config.get("agents", {}).get("aura", {}).get("text_model")
        return agent_model or self.config.get("ai_engine", {}).get("ollama_text_model", "huihui_ai/qwen3-abliterated:14b")

    def get_vision_model(self) -> str:
        agent_model = self.config.get("agents", {}).get("iris", {}).get("vision_model")
        return agent_model or self.config.get("ai_engine", {}).get("ollama_vision_model", "huihui_ai/qwen3-vl-abliterated:8b-instruct")

    def image_to_base64(self, img_path: Path, max_dim: int = 768) -> str:
        try:
            from PIL import Image
            import io
            with Image.open(img_path) as img:
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                if max(img.size) > max_dim:
                    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=85)
                return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            with open(img_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")

    def call_ollama_text(self, prompt: str, system_prompt: str = "", model: Optional[str] = None) -> str:
        url = f"{self.get_ollama_url()}/api/generate"
        active_model = model or self.get_text_model()

        # Dynamic Pre-Flight Block Swap on GPU 0
        vram_manager.prepare_for_model(active_model)

        payload = {
            "model": active_model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "keep_alive": "5m",
            "options": {
                "temperature": 0.7,
                "top_p": 0.9
            }
        }
        try:
            resp = requests.post(url, json=payload, timeout=90)
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()
            
            # Check for memory / OOM error: Self-Healing Retry
            err_text = resp.text.lower()
            if "memory" in err_text or "out of memory" in err_text or resp.status_code == 500:
                print(f"[AI PROVIDER] Memory warning from Ollama ({resp.status_code}). Triggering emergency VRAM purge & retry...")
                vram_manager.purge_vram(reason="emergency_oom_retry")
                resp_retry = requests.post(url, json=payload, timeout=90)
                if resp_retry.status_code == 200:
                    return resp_retry.json().get("response", "").strip()

            return f"Error from Local Ollama: HTTP {resp.status_code} - {resp.text}"
        except Exception as e:
            return f"Ollama connection error: {str(e)}"

    def call_ollama_vision(self, prompt: str, image_paths: List[Path], system_prompt: str = "", model: Optional[str] = None, num_predict: int = 180) -> str:
        url = f"{self.get_ollama_url()}/api/generate"
        active_model = model or self.get_vision_model()

        # Dynamic Pre-Flight Block Swap on GPU 0 (Evicts 14B text model to guarantee room for 8B-VL)
        vram_manager.prepare_for_model(active_model)

        b64_images = []
        for p in image_paths:
            if Path(p).exists():
                b64_images.append(self.image_to_base64(Path(p)))

        payload = {
            "model": active_model,
            "prompt": prompt,
            "images": b64_images,
            "system": system_prompt,
            "stream": False,
            "keep_alive": "2m",
            "options": {
                "temperature": 0.1,
                "num_predict": num_predict
            }
        }
        try:
            resp = requests.post(url, json=payload, timeout=60)
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()

            # Check for memory / OOM error: Self-Healing Retry
            err_text = resp.text.lower()
            if "memory" in err_text or "out of memory" in err_text or resp.status_code == 500:
                print(f"[AI PROVIDER VISION] Memory warning from Ollama ({resp.status_code}). Triggering emergency VRAM purge & retry...")
                vram_manager.purge_vram(reason="emergency_vision_oom_retry")
                resp_retry = requests.post(url, json=payload, timeout=60)
                if resp_retry.status_code == 200:
                    return resp_retry.json().get("response", "").strip()

            return f"Error from Local Ollama Vision: HTTP {resp.status_code} - {resp.text}"
        except requests.exceptions.Timeout:
            print(f"[AI PROVIDER VISION] Request timed out (>60s) on {active_model}! Aborting to release GPU compute...")
            try:
                requests.post(f"{self.get_ollama_url()}/api/generate", json={"model": active_model, "keep_alive": 0}, timeout=2)
            except Exception:
                pass
            return '{"passed": false, "error": "Vision QC timed out (>60s) and was aborted to release GPU."}'
        except Exception as e:
            try:
                requests.post(f"{self.get_ollama_url()}/api/generate", json={"model": active_model, "keep_alive": 0}, timeout=2)
            except Exception:
                pass
            return f"Ollama Vision error: {str(e)}"

    def generate(self, prompt: str, image_paths: Optional[List[Path]] = None, system_prompt: str = "") -> str:
        self.load_config()

        # Enforce 100% Local GPU Execution (Air-gapped privacy for adult creators)
        if image_paths and len(image_paths) > 0:
            return self.call_ollama_vision(prompt, image_paths, system_prompt)

        return self.call_ollama_text(prompt, system_prompt)

if __name__ == "__main__":
    service = AIProviderService()
    print("Strict Local Privacy Enabled:", service.is_strict_local())
    print("Text Model:", service.get_text_model())
    print("Vision Model:", service.get_vision_model())
