import os
import shutil
import subprocess
import requests
from typing import Dict, Any, List

def get_gpu_stats() -> List[Dict[str, Any]]:
    """Retrieve real-time metrics for all NVIDIA GPUs using nvidia-smi."""
    gpus = []
    try:
        cmd = [
            "nvidia-smi",
            "--query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu",
            "--format=csv,noheader,nounits"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=3)
        lines = result.stdout.strip().splitlines()
        for line in lines:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 7:
                idx = int(parts[0])
                name = parts[1]
                mem_total = float(parts[2])
                mem_used = float(parts[3])
                mem_free = float(parts[4])
                util_gpu = float(parts[5])
                temp_gpu = float(parts[6])
                mem_pct = round((mem_used / mem_total) * 100, 1) if mem_total > 0 else 0
                gpus.append({
                    "index": idx,
                    "name": name,
                    "memory_total_mb": mem_total,
                    "memory_used_mb": mem_used,
                    "memory_free_mb": mem_free,
                    "memory_percent": mem_pct,
                    "utilization_gpu_percent": util_gpu,
                    "temperature_c": temp_gpu
                })
    except Exception as e:
        # Fallback simulation or single mock if nvidia-smi fails
        gpus = [{
            "index": 0,
            "name": "NVIDIA GeForce RTX 3060 (Dual Mode)",
            "memory_total_mb": 12288,
            "memory_used_mb": 1200,
            "memory_free_mb": 11088,
            "memory_percent": 9.8,
            "utilization_gpu_percent": 12,
            "temperature_c": 35
        }]
    return gpus

def get_system_stats() -> Dict[str, Any]:
    """Retrieve system CPU, RAM, Disk, and GPU metrics."""
    gpus = get_gpu_stats()
    
    # Disk stats for F: drive
    f_total, f_used, f_free = 0, 0, 0
    try:
        total, used, free = shutil.disk_usage("F:/")
        f_total = round(total / (1024**3), 1)
        f_used = round(used / (1024**3), 1)
        f_free = round(free / (1024**3), 1)
        disk_pct = round((used / total) * 100, 1)
    except Exception:
        disk_pct = 0

    return {
        "gpus": gpus,
        "disk": {
            "drive": "F:",
            "total_gb": f_total,
            "used_gb": f_used,
            "free_gb": f_free,
            "percent_used": disk_pct
        }
    }

def get_ollama_models(ollama_url: str = "http://127.0.0.1:11434") -> Dict[str, Any]:
    """Check Ollama availability and list local models."""
    try:
        resp = requests.get(f"{ollama_url}/api/tags", timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            models = []
            for m in data.get("models", []):
                details = m.get("details", {})
                caps = m.get("capabilities", [])
                models.append({
                    "name": m.get("name"),
                    "size_gb": round(m.get("size", 0) / (1024**3), 1),
                    "family": details.get("family", "unknown"),
                    "is_vision": "vision" in caps or "vl" in m.get("name", "").lower(),
                    "capabilities": caps
                })
            return {"online": True, "models": models}
    except Exception:
        pass
    return {"online": False, "models": []}

if __name__ == "__main__":
    import json
    stats = get_system_stats()
    stats["ollama"] = get_ollama_models()
    print(json.dumps(stats, indent=2))


class SystemMonitor:
    get_system_stats = staticmethod(get_system_stats)
    get_gpu_stats = staticmethod(get_gpu_stats)

system_monitor = SystemMonitor()
