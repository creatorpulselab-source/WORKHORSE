import os
import sys
import json
import base64
import requests
from pathlib import Path
from typing import List, Optional, Dict, Any

from shared.vram_manager import vram_manager

# Context windows requested from Ollama. IMPORTANT (verified against the local Ollama
# build on 2026-10-18): when a prompt does NOT fit in num_ctx, Ollama does not just
# refuse or trim a little - it truncates the prompt down to num_ctx/2 + 2 tokens
# (keeping only the first 4 tokens plus the tail). A 14K-token Synapse prompt sent with
# num_ctx=8192 therefore reached the model as only ~4,098 tokens, silently dropping most
# of the system prompt/tool documentation. Callers must size prompts to FIT these windows.
TEXT_NUM_CTX = 16384   # 14B text model; measured ~7.4 GB on GPU 0 at this size (fits 12 GB)
VISION_NUM_CTX = 12288  # 8B vision model; image tokens + knowledge + instructions need headroom

# Every known prefix call_ollama_text()/call_ollama_vision() themselves return on
# failure (connection errors, non-200 HTTP responses, timeouts) - since those methods
# always return a plain string (never raise, never a structured {"success": bool}
# wrapper), a caller that doesn't check for one of these exact prefixes will silently
# treat the error text as if it were real generated content. This happened for real in
# prompt_synthesizer.py (an infra error became the literal FLUX image-generation
# prompt) and vision_agent.py (an infra error became a client-visible "visual_summary"
# in package_exporter.py's delivered package). copy_synthesizer.py is NOT vulnerable to
# this because it always requires valid JSON and falls back otherwise - an error
# string is never valid JSON, so it already can't be mistaken for real content there.
AI_ERROR_RESPONSE_PREFIXES = (
    "Ollama connection error:",
    "Error from Local Ollama:",
    "Ollama Vision error:",
    "Error from Local Ollama Vision:",
)


def is_ai_error_response(text: str) -> bool:
    """True if `text` is one of ai_providers.py's own failure-string returns rather
    than real model-generated content. Use this to gate any caller that treats a
    call_ollama_text()/call_ollama_vision() return value as literal content."""
    if not isinstance(text, str):
        return False
    stripped = text.strip()
    if stripped.startswith(AI_ERROR_RESPONSE_PREFIXES):
        return True
    # The vision timeout path returns a JSON error envelope rather than a plain
    # prefix - still not real content.
    return stripped.startswith('{"passed": false, "error": "Vision QC timed out')


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
        return self.config.get("ai_engine", {}).get("ollama_url", "http://127.0.0.1:11434")

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

    def call_ollama_text(self, prompt: str, system_prompt: str = "", model: Optional[str] = None, num_ctx: int = 8192) -> str:
        url = f"{self.get_ollama_url()}/api/generate"
        active_model = model or self.get_text_model()

        # Dynamic Pre-Flight Block Swap on GPU 0
        vram_manager.prepare_for_model(active_model)

        effective_system = f"/no_think\n{system_prompt}" if system_prompt else "/no_think"

        payload = {
            "model": active_model,
            "prompt": prompt,
            "system": effective_system,
            "stream": False,
            "keep_alive": "5m",
            "think": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "num_ctx": num_ctx
            }
        }
        tracker = None
        task_id = f"ollama_text_{int(os.getpid())}"
        try:
            from pipeline.stages.ai_operator import active_task_tracker
            tracker = active_task_tracker
            tracker.start_task(
                agent="scribe",
                task_desc=f"Scribe [6 C]: Generating text on {active_model} (GPU 0)...",
                task_id=task_id,
                progress=50
            )
        except Exception:
            tracker = None
        try:
            resp = requests.post(url, json=payload, timeout=90)
            if resp.status_code == 200:
                text = resp.json().get("response", "").strip()
                if not text:
                    print(f"[AI PROVIDER] {active_model} returned an empty response (likely consumed its budget on hidden 'thinking') - retrying once with thinking suppressed.")
                    resp_retry = requests.post(url, json=payload, timeout=90)
                    if resp_retry.status_code == 200:
                        text = resp_retry.json().get("response", "").strip()
                return text

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
        finally:
            if tracker:
                try:
                    tracker.finish_task(task_id)
                except Exception:
                    pass

    def call_ollama_vision(self, prompt: str, image_paths: List[Path], system_prompt: str = "", model: Optional[str] = None, num_predict: int = 350, timeout: int = 60, num_ctx: int = VISION_NUM_CTX, image_max_dim: int = 768, temperature: float = 0.1, repeat_penalty: Optional[float] = None) -> str:
        url = f"{self.get_ollama_url()}/api/generate"
        active_model = model or self.get_vision_model()

        # Dynamic Pre-Flight Block Swap on GPU 0 (Evicts 14B text model to guarantee room for 8B-VL).
        # Pass the SAME num_ctx used for the real request below, otherwise the warm-up loads the
        # model at one window size and the request forces a second reload at another.
        vram_manager.prepare_for_model(active_model, num_ctx=num_ctx)

        b64_images = []
        for p in image_paths:
            if Path(p).exists():
                b64_images.append(self.image_to_base64(Path(p), max_dim=image_max_dim))

        effective_system = f"/no_think\n{system_prompt}" if system_prompt else "/no_think"

        options = {
            "temperature": temperature,
            "num_predict": num_predict,
            "num_ctx": num_ctx
        }
        if repeat_penalty is not None:
            options["repeat_penalty"] = repeat_penalty

        payload = {
            "model": active_model,
            "prompt": prompt,
            "images": b64_images,
            "system": effective_system,
            "stream": False,
            "keep_alive": "2m",
            "think": False,
            "options": options
        }
        tracker = None
        task_id = f"ollama_vision_{int(os.getpid())}"
        try:
            from pipeline.stages.ai_operator import active_task_tracker
            tracker = active_task_tracker
            tracker.start_task(
                agent="iris",
                task_desc=f"Iris [77 Ir]: Inspecting visual frame on {active_model} (GPU 0)...",
                task_id=task_id,
                progress=60
            )
        except Exception:
            tracker = None
        try:
            resp = requests.post(url, json=payload, timeout=timeout)
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()

            # Check for memory / OOM error: Self-Healing Retry
            err_text = resp.text.lower()
            if "memory" in err_text or "out of memory" in err_text or resp.status_code == 500:
                print(f"[AI PROVIDER VISION] Memory warning from Ollama ({resp.status_code}). Triggering emergency VRAM purge & retry...")
                vram_manager.purge_vram(reason="emergency_vision_oom_retry")
                resp_retry = requests.post(url, json=payload, timeout=timeout)
                if resp_retry.status_code == 200:
                    return resp_retry.json().get("response", "").strip()

            return f"Error from Local Ollama Vision: HTTP {resp.status_code} - {resp.text}"
        except requests.exceptions.Timeout:
            print(f"[AI PROVIDER VISION] Request timed out (>{timeout}s) on {active_model}! Aborting to release GPU compute...")
            try:
                requests.post(f"{self.get_ollama_url()}/api/generate", json={"model": active_model, "keep_alive": 0}, timeout=2)
            except Exception:
                pass
            return f'{{"passed": false, "error": "Vision QC timed out (>{timeout}s) and was aborted to release GPU."}}'
        except Exception as e:
            try:
                requests.post(f"{self.get_ollama_url()}/api/generate", json={"model": active_model, "keep_alive": 0}, timeout=2)
            except Exception:
                pass
            return f"Ollama Vision error: {str(e)}"
        finally:
            if tracker:
                try:
                    tracker.finish_task(task_id)
                except Exception:
                    pass

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
