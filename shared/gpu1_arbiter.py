import os
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("workhorse.gpu1_arbiter")

class GPU1Arbiter:
    """
    Coordinates GPU 1 hardware access between ECHO (Faster-Whisper on cuda:1)
    and FORGE (NVENC 60fps video cuts).
    Prevents simultaneous memory bandwidth and CUDA kernel contention.
    """
    def __init__(self, workspace_dir: Path = Path(r"F:\WORKHORSE\workspace")):
        self.lock_file = workspace_dir / ".gpu1_busy.lock"

    def acquire(self, task_name: str, pid: Optional[int] = None, timeout_seconds: int = 45) -> bool:
        pid = pid or os.getpid()
        start = time.time()

        while time.time() - start < timeout_seconds:
            if not self.lock_file.exists():
                try:
                    self.lock_file.write_text(f"{task_name}:{pid}", encoding="utf-8")
                    return True
                except Exception:
                    pass
            else:
                # Check if locking process is alive
                try:
                    content = self.lock_file.read_text(encoding="utf-8").strip()
                    parts = content.split(":")
                    if len(parts) == 2:
                        locked_pid = int(parts[1])
                        if locked_pid == pid:
                            return True
                        # If process dead, steal lock
                        import subprocess
                        res = subprocess.run(f'tasklist /FI "PID eq {locked_pid}"', shell=True, capture_output=True, text=True)
                        if str(locked_pid) not in res.stdout:
                            self.lock_file.unlink(missing_ok=True)
                            continue
                except Exception:
                    pass
            time.sleep(0.5)

        logger.warning(f"[GPU 1 ARBITER] Timeout ({timeout_seconds}s) waiting to acquire GPU 1 lock for {task_name}.")
        return False

    def release(self, task_name: str, pid: Optional[int] = None):
        pid = pid or os.getpid()
        if self.lock_file.exists():
            try:
                content = self.lock_file.read_text(encoding="utf-8").strip()
                if str(pid) in content or task_name in content:
                    self.lock_file.unlink(missing_ok=True)
            except Exception:
                pass

    def get_status(self) -> Dict[str, Any]:
        if self.lock_file.exists():
            try:
                content = self.lock_file.read_text(encoding="utf-8").strip()
                parts = content.split(":")
                return {
                    "is_locked": True,
                    "active_task": parts[0] if parts else "unknown",
                    "pid": int(parts[1]) if len(parts) > 1 else None
                }
            except Exception:
                pass
        return {"is_locked": False, "active_task": None, "pid": None}

gpu1_arbiter = GPU1Arbiter()
