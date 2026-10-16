import os
import time
import logging
import threading
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("workhorse.gpu1_arbiter")

class GPU1Arbiter:
    """
    Coordinates GPU 1 hardware access between ECHO (Faster-Whisper on cuda:1)
    and FORGE (NVENC 60fps video cuts).
    Prevents simultaneous memory bandwidth and CUDA kernel contention.
    Provides intra-process thread safety (RLock) and inter-process atomic locking
    via exclusive OS file creation (open(..., "x")).
    """
    def __init__(self, workspace_dir: Path = Path(r"F:\WORKHORSE\workspace")):
        self.workspace_dir = Path(workspace_dir)
        self.lock_file = self.workspace_dir / ".gpu1_busy.lock"
        self._thread_lock = threading.RLock()
        self._owner_thread_id: Optional[int] = None
        self._owner_task: Optional[str] = None
        self._owner_pid: Optional[int] = None

    def acquire(self, task_name: str, pid: Optional[int] = None, timeout_seconds: int = 45) -> bool:
        pid = pid or os.getpid()
        thread_id = threading.get_ident()
        start = time.time()

        # 1. Acquire intra-process thread lock first
        acquired_thread_lock = False
        while time.time() - start < timeout_seconds:
            remaining = max(0.1, timeout_seconds - (time.time() - start))
            if self._thread_lock.acquire(timeout=min(0.5, remaining)):
                acquired_thread_lock = True
                break

        if not acquired_thread_lock:
            logger.warning(f"[GPU 1 ARBITER] Thread contention timeout ({timeout_seconds}s) waiting for {task_name}.")
            return False

        # 2. Check if already owned by this same thread (re-entrant support)
        if self._owner_pid == pid and self._owner_thread_id == thread_id and self._owner_task == task_name:
            return True

        # 3. Acquire atomic OS-level file lock
        try:
            self.workspace_dir.mkdir(parents=True, exist_ok=True)
            while time.time() - start < timeout_seconds:
                try:
                    # Atomic creation: fails with FileExistsError if another process holds it
                    with open(self.lock_file, "x", encoding="utf-8") as f:
                        f.write(f"{task_name}:{pid}:{thread_id}:{time.time()}\n")
                        f.flush()
                    self._owner_pid = pid
                    self._owner_thread_id = thread_id
                    self._owner_task = task_name
                    return True
                except FileExistsError:
                    # Inspect lock file for dead process or stale lock
                    try:
                        content = self.lock_file.read_text(encoding="utf-8").strip()
                        parts = content.split(":")
                        if len(parts) >= 2:
                            locked_pid = int(parts[1])
                            # If owned by current pid and thread
                            if locked_pid == pid and len(parts) >= 3 and int(parts[2]) == thread_id:
                                self._owner_pid = pid
                                self._owner_thread_id = thread_id
                                self._owner_task = parts[0]
                                return True

                            # Check if other process is dead
                            if locked_pid != pid:
                                res = subprocess.run(
                                    f'tasklist /FI "PID eq {locked_pid}"',
                                    shell=True, capture_output=True, text=True, timeout=2
                                )
                                if str(locked_pid) not in res.stdout:
                                    logger.info(f"[GPU 1 ARBITER] Stealing stale lock from dead PID {locked_pid}.")
                                    self.lock_file.unlink(missing_ok=True)
                                    continue
                    except Exception:
                        pass
                except Exception as e:
                    logger.debug(f"[GPU 1 ARBITER] OS lock attempt error: {e}")

                time.sleep(0.2)

            logger.warning(f"[GPU 1 ARBITER] Timeout ({timeout_seconds}s) acquiring GPU 1 lock for {task_name}.")
            self._thread_lock.release()
            return False

        except Exception as e:
            logger.error(f"[GPU 1 ARBITER] Unexpected error acquiring lock for {task_name}: {e}")
            self._thread_lock.release()
            return False

    def release(self, task_name: str, pid: Optional[int] = None):
        pid = pid or os.getpid()
        thread_id = threading.get_ident()

        try:
            if self.lock_file.exists():
                try:
                    content = self.lock_file.read_text(encoding="utf-8").strip()
                    parts = content.split(":")
                    if len(parts) >= 2:
                        locked_task = parts[0]
                        locked_pid = int(parts[1])
                        locked_thread = int(parts[2]) if len(parts) >= 3 else None

                        # Strict match: must match task and pid (and thread if present)
                        task_matches = (locked_task == task_name)
                        pid_matches = (locked_pid == pid)
                        thread_matches = (locked_thread is None or locked_thread == thread_id)

                        if task_matches and pid_matches and thread_matches:
                            self.lock_file.unlink(missing_ok=True)
                            self._owner_pid = None
                            self._owner_thread_id = None
                            self._owner_task = None
                        else:
                            logger.warning(
                                f"[GPU 1 ARBITER] Release rejected: owner mismatch. "
                                f"Lock={locked_task}:{locked_pid}:{locked_thread} vs Caller={task_name}:{pid}:{thread_id}"
                            )
                except Exception as e:
                    logger.warning(f"[GPU 1 ARBITER] Error releasing lock file: {e}")
        finally:
            # Release intra-process lock if held by current thread
            try:
                self._thread_lock.release()
            except RuntimeError:
                pass  # Lock was not held by this thread

    def get_status(self) -> Dict[str, Any]:
        if self.lock_file.exists():
            try:
                content = self.lock_file.read_text(encoding="utf-8").strip()
                parts = content.split(":")
                return {
                    "is_locked": True,
                    "active_task": parts[0] if parts else "unknown",
                    "pid": int(parts[1]) if len(parts) > 1 else None,
                    "thread_id": int(parts[2]) if len(parts) > 2 else None
                }
            except Exception:
                pass
        return {"is_locked": False, "active_task": None, "pid": None, "thread_id": None}

    status = get_status

gpu1_arbiter = GPU1Arbiter()
