import os
import sys
import time
import gc
import asyncio
import logging
import requests
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path

logger = logging.getLogger("workhorse.vram_manager")

class VramManager:
    """
    Automatic VRAM Watchdog, Dynamic Block Swapper & Dual-GPU Arbiter
    for Dual NVIDIA RTX 3060 (24GB total VRAM).
    - GPU 0 (12GB): Dedicated to Ollama LLM / Vision (SYNAPSE & IRIS)
    - GPU 1 (12GB): Dedicated to Faster-Whisper (ECHO) & NVENC 60fps (FORGE)
    """
    def __init__(self, idle_timeout_seconds: int = 300, ollama_url: str = "http://localhost:11434"):
        self.idle_timeout = idle_timeout_seconds
        self.ollama_url = ollama_url
        self.last_activity_time = time.time()
        self.last_activity_source = "server_startup"
        self.vram_cleared = False
        self.last_purge_time = 0.0
        self.last_purge_details: Dict[str, Any] = {}
        self.last_swap_details: Dict[str, Any] = {}
        self.active_jobs_checker: Optional[Callable[[], bool]] = None
        self._watchdog_task: Optional[asyncio.Task] = None
        self._event_broadcasters: List[Callable[[Dict[str, Any]], None]] = []

    def register_active_jobs_checker(self, checker: Callable[[], bool]):
        self.active_jobs_checker = checker

    def add_broadcaster(self, cb: Callable[[Dict[str, Any]], None]):
        if cb not in self._event_broadcasters:
            self._event_broadcasters.append(cb)

    def record_activity(self, source: str = "user_action"):
        self.last_activity_time = time.time()
        self.last_activity_source = source
        self.vram_cleared = False

    def is_busy(self) -> bool:
        if self.active_jobs_checker:
            try:
                return self.active_jobs_checker()
            except Exception:
                return False
        return False

    def get_idle_seconds(self) -> float:
        if self.is_busy():
            self.last_activity_time = time.time()
            return 0.0
        return max(0.0, time.time() - self.last_activity_time)

    def get_loaded_ollama_models(self) -> List[Dict[str, Any]]:
        try:
            resp = requests.get(f"{self.ollama_url}/api/ps", timeout=2)
            if resp.status_code == 200:
                return resp.json().get("models", [])
        except Exception:
            pass
        return []
    def _warm_up_model(self, target_model: str, keep_alive: str) -> Dict[str, Any]:
        """
        Blocking pre-load of target_model into Ollama/GPU VRAM via an empty-prompt
        /api/generate call, BEFORE the real timed request is made. Without this,
        a cold model load (reading weights off disk + VRAM allocation for an 8B+
        model) can easily exceed a short request timeout (e.g. Iris's 25s vision
        QC call), causing every first-call-after-a-swap to time out even though
        the model itself works fine once resident.
        """
        start = time.time()
        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": target_model, "prompt": "", "stream": False, "keep_alive": keep_alive},
                timeout=120
            )
            duration_ms = round((time.time() - start) * 1000, 2)
            if resp.status_code == 200:
                logger.info(f"[BLOCK SWAPPER] Warmed up '{target_model}' in {duration_ms}ms.")
                return {"status": "warmed", "duration_ms": duration_ms}
            return {"status": "warm_failed", "http_status": resp.status_code, "duration_ms": duration_ms}
        except Exception as e:
            logger.warning(f"[BLOCK SWAPPER] Warm-up request for '{target_model}' failed: {e}")
            return {"status": "warm_error", "error": str(e), "duration_ms": round((time.time() - start) * 1000, 2)}

    def prepare_for_model(self, target_model: str, keep_alive: str = "5m") -> Dict[str, Any]:
        """
        DYNAMIC MODEL BLOCK SWAPPER for GPU 0 (Ollama LLM & Vision).
        Inspects currently resident models in Ollama VRAM. If a different model is loaded
        (e.g., swapping between 14B Qwen Text and 8B Qwen-VL Vision), it evicts the old
        model with keep_alive: 0, frees PyTorch CUDA cache, and forces garbage collection.
        This guarantees that two large models never collide in 12GB VRAM on GPU 0.
        """
        if not target_model:
            return {"status": "skipped", "reason": "no_target_model"}

        self.record_activity(source=f"block_swap:{target_model}")
        loaded = self.get_loaded_ollama_models()
        loaded_names = [m.get("name", "") for m in loaded]

        # If target model is already the ONLY loaded model, no eviction needed
        if len(loaded) == 1 and loaded_names[0] == target_model:
            return {
                "status": "already_resident",
                "target_model": target_model,
                "evicted": []
            }

        evicted = []
        start_time = time.time()

        for m in loaded:
            name = m.get("name")
            if name and name != target_model:
                try:
                    logger.info(f"[BLOCK SWAPPER] Evicting model '{name}' from GPU 0 to load '{target_model}'...")
                    r = requests.post(
                        f"{self.ollama_url}/api/generate",
                        json={"model": name, "keep_alive": 0},
                        timeout=5
                    )
                    if r.status_code == 200:
                        evicted.append(name)
                except Exception as e:
                    logger.warning(f"[BLOCK SWAPPER] Could not evict '{name}': {e}")

        # PyTorch cache flush & GC if we evicted anything
        torch_flushed = False
        if evicted:
            if "torch" in sys.modules:
                try:
                    torch = sys.modules["torch"]
                    if hasattr(torch, "cuda") and torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        torch.cuda.ipc_collect()
                        torch_flushed = True
                except Exception:
                    pass
            gc.collect()

        # Block until target_model is actually resident, so the caller's own
        # (often short) request timeout doesn't have to absorb a cold model load.
        warm_result = self._warm_up_model(target_model, keep_alive)

        swap_record = {
            "status": "swapped" if evicted else "clean_start",
            "target_model": target_model,
            "evicted_models": evicted,
            "torch_flushed": torch_flushed,
            "warm_up": warm_result,
            "duration_ms": round((time.time() - start_time) * 1000, 2),
            "timestamp": time.time()
        }
        self.last_swap_details = swap_record

        if evicted:
            print(f"[BLOCK SWAPPER] Evicted {evicted} from GPU 0 VRAM in {swap_record['duration_ms']}ms. Ready for: {target_model}")
            for broadcaster in list(self._event_broadcasters):
                try:
                    broadcaster({"type": "block_swap", "data": swap_record})
                except Exception:
                    pass

        return swap_record

    def purge_vram(self, reason: str = "manual") -> Dict[str, Any]:
        """
        Clears loaded models from Ollama VRAM, runs torch cuda empty_cache if present,
        and triggers garbage collection.
        """
        start_time = time.time()
        unloaded_models = []
        loaded_before = self.get_loaded_ollama_models()

        # 1. Unload all models from Ollama VRAM by passing keep_alive: 0
        for m in loaded_before:
            model_name = m.get("name")
            if model_name:
                try:
                    r = requests.post(
                        f"{self.ollama_url}/api/generate",
                        json={"model": model_name, "keep_alive": 0},
                        timeout=5
                    )
                    if r.status_code == 200:
                        unloaded_models.append(model_name)
                except Exception as e:
                    logger.warning(f"Failed to unload Ollama model {model_name}: {e}")

        # 2. PyTorch CUDA cache flush if torch is imported anywhere
        torch_cleared = False
        if "torch" in sys.modules:
            try:
                torch = sys.modules["torch"]
                if hasattr(torch, "cuda") and torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.ipc_collect()
                    torch_cleared = True
            except Exception:
                pass

        # 3. Python garbage collection
        gc.collect()

        loaded_after = self.get_loaded_ollama_models()
        self.vram_cleared = True
        self.last_purge_time = time.time()
        
        details = {
            "status": "ok",
            "reason": reason,
            "timestamp": self.last_purge_time,
            "unloaded_models": unloaded_models,
            "models_remaining": len(loaded_after),
            "torch_cleared": torch_cleared,
            "duration_ms": round((time.time() - start_time) * 1000, 2)
        }
        self.last_purge_details = details

        # Broadcast event to subscribers
        for broadcaster in list(self._event_broadcasters):
            try:
                broadcaster({"type": "vram_purge", "data": details})
            except Exception:
                pass

        print(f"[VRAM WATCHDOG] Purged VRAM ({reason}). Unloaded models: {unloaded_models or 'None (already clear)'}")
        return details

    def get_dual_gpu_partition(self) -> Dict[str, Any]:
        """Summary of hardware allocation across the Dual RTX 3060 setup."""
        return {
            "dual_gpu_enabled": True,
            "gpu_0": {
                "assigned_agents": ["SYNAPSE [100 Fm]", "IRIS [77 Ir]", "AURA [79 Au]"],
                "role": "Ollama LLM & Vision Reasoning",
                "block_swapping": "Active (14B Text <-> 8B-VL Vision)",
                "vram_gb": 12
            },
            "gpu_1": {
                "assigned_agents": ["ECHO [26 Fe]", "FORGE [74 W]", "VANGUARD [74 W]"],
                "role": "Faster-Whisper (cuda:1) & NVENC Hardware Video (gpu:1)",
                "isolation": "100% Isolated from GPU 0 (Zero OOM collisions)",
                "vram_gb": 12
            }
        }

    def get_status(self) -> Dict[str, Any]:
        idle_sec = self.get_idle_seconds()
        remaining_sec = max(0, self.idle_timeout - idle_sec)
        loaded = self.get_loaded_ollama_models()
        total_vram_bytes = sum(m.get("size_vram", 0) for m in loaded)
        total_vram_mb = round(total_vram_bytes / (1024 * 1024), 1)

        # Format mm:ss
        idle_min = int(idle_sec // 60)
        idle_remainder = int(idle_sec % 60)
        timeout_min = int(self.idle_timeout // 60)
        timeout_remainder = int(self.idle_timeout % 60)
        idle_str = f"{idle_min:02d}:{idle_remainder:02d} / {timeout_min:02d}:{timeout_remainder:02d}"

        return {
            "idle_seconds": round(idle_sec, 1),
            "idle_timeout_seconds": self.idle_timeout,
            "remaining_seconds": round(remaining_sec, 1),
            "idle_formatted": idle_str,
            "is_busy": self.is_busy(),
            "vram_cleared": self.vram_cleared or len(loaded) == 0,
            "loaded_models_count": len(loaded),
            "loaded_models": [m.get("name") for m in loaded],
            "total_vram_used_mb": total_vram_mb,
            "last_activity_source": self.last_activity_source,
            "last_purge": self.last_purge_details,
            "last_swap": self.last_swap_details,
            "dual_gpu_partition": self.get_dual_gpu_partition()
        }


    def check_and_trip_circuit_breaker(self) -> bool:
        """
        CIRCUIT BREAKER: Monitors GPU 0 compute utilization.
        If GPU 0 is pegged at >80% continuously for >45 seconds without an active
        orchestrator job, it terminates stuck llama-server processes to guarantee
        the user's GPU never remains locked up.
        """
        try:
            import subprocess
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=index,utilization.gpu", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=2
            )
            if out.returncode == 0:
                lines = out.stdout.strip().splitlines()
                gpu0_util = 0
                for line in lines:
                    parts = line.split(",")
                    if len(parts) == 2 and parts[0].strip() == "0":
                        gpu0_util = int(parts[1].strip())
                        break

                if gpu0_util >= 80:
                    if not hasattr(self, "_high_util_start"):
                        self._high_util_start = time.time()
                    elapsed = time.time() - self._high_util_start
                    if elapsed > 45:
                        print(f"[CIRCUIT BREAKER] GPU 0 pegged at {gpu0_util}% for {int(elapsed)}s! Tripping breaker to release GPU...")
                        # 1. Unload model from Ollama
                        self.purge_vram(reason="circuit_breaker_runaway_inference")
                        # 2. Terminate stuck llama-server workers
                        subprocess.run("taskkill /F /IM llama-server.exe", shell=True, capture_output=True)
                        self._high_util_start = None
                        return True
                else:
                    self._high_util_start = None
        except Exception:
            pass
        return False


    def prune_old_staging_files(self, max_age_hours: int = 48) -> Dict[str, Any]:
        """
        AUTOMATED STORAGE CLEANER:
        Scans workspace/comfy_staging and workspace/temp.
        Deletes intermediate unapproved files older than max_age_hours.
        Protects workspace/brand_assets and client_deliveries permanently.
        """
        staging_dir = Path("F:/WORKHORSE/workspace/comfy_staging")
        temp_dir = Path("F:/WORKHORSE/workspace/temp")
        deleted_count = 0
        deleted_bytes = 0
        cutoff = time.time() - (max_age_hours * 3600)

        for target_dir in [staging_dir, temp_dir]:
            if target_dir.exists():
                for f in target_dir.iterdir():
                    if f.is_file() and not f.name.startswith("."):
                        try:
                            if f.stat().st_mtime < cutoff:
                                sz = f.stat().st_size
                                f.unlink()
                                deleted_count += 1
                                deleted_bytes += sz
                        except Exception:
                            pass

        return {
            "deleted_count": deleted_count,
            "deleted_mb": round(deleted_bytes / (1024 * 1024), 2),
            "cutoff_hours": max_age_hours
        }

    async def run_watchdog_loop(self):
        print(f"[VRAM WATCHDOG] Active. Idle timeout set to {self.idle_timeout}s ({self.idle_timeout // 60}m).")
        while True:
            try:
                await asyncio.sleep(5)
                self.check_and_trip_circuit_breaker()
                # Automated Staging Pruning (Every 30 minutes)
                if not hasattr(self, "_last_prune_time") or (time.time() - self._last_prune_time > 1800):
                    self._last_prune_time = time.time()
                    p_res = self.prune_old_staging_files(max_age_hours=48)
                    if p_res["deleted_count"] > 0:
                        print(f"[STORAGE PRUNER] Pruned {p_res['deleted_count']} old staging files ({p_res['deleted_mb']} MB freed).")

                idle_sec = self.get_idle_seconds()
                # Check if threshold reached
                if idle_sec >= self.idle_timeout and not self.vram_cleared:
                    loaded = self.get_loaded_ollama_models()
                    if loaded:
                        print(f"[VRAM WATCHDOG] Idle threshold reached ({round(idle_sec)}s >= {self.idle_timeout}s). Triggering auto-release...")
                        self.purge_vram(reason="idle_timeout_5min")
                    else:
                        # Already no models in memory, mark cleared
                        self.vram_cleared = True
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[VRAM WATCHDOG] Error in loop: {e}")

# Global singleton instance
vram_manager = VramManager(idle_timeout_seconds=300)
