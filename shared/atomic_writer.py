import os
import json
import shutil
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("workhorse.atomic_writer")

def atomic_write_json(file_path: Path, data: Any, indent: int = 2, make_backup: bool = True) -> bool:
    """
    Safely and atomically writes JSON data to disk.
    1. Writes to temporary file (.tmp)
    2. Validates JSON integrity
    3. Creates a rolling backup (.bak) of the existing file
    4. Atomically replaces target file using os.replace
    Guarantees 0-byte or corrupted files can never occur.
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    bak_path = path.with_suffix(".bak")

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        # Validate readability
        with open(tmp_path, "r", encoding="utf-8") as f:
            _ = json.load(f)

        # Rolling backup
        if make_backup and path.exists() and path.stat().st_size > 0:
            try:
                shutil.copy2(path, bak_path)
            except Exception as e:
                logger.warning(f"Failed to create backup for {path.name}: {e}")

        # Atomic replace
        os.replace(tmp_path, path)
        return True

    except Exception as e:
        logger.error(f"[ATOMIC WRITER] Failed to atomically write {path}: {e}")
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
        return False

def safe_read_json(file_path: Path, default: Optional[Any] = None) -> Any:
    """
    Safely reads JSON file with automatic fallback to .bak if primary is corrupted or empty.
    """
    path = Path(file_path)
    bak_path = path.with_suffix(".bak")

    if not path.exists():
        if bak_path.exists():
            try:
                with open(bak_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return default if default is not None else {}

    try:
        if path.stat().st_size == 0:
            raise ValueError(f"{path.name} is 0 bytes")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"[ATOMIC WRITER] Primary file {path.name} corrupted ({e}). Attempting recovery from backup...")
        if bak_path.exists() and bak_path.stat().st_size > 0:
            try:
                with open(bak_path, "r", encoding="utf-8") as f:
                    recovered = json.load(f)
                shutil.copy2(bak_path, path)
                print(f"[ATOMIC WRITER] Successfully restored {path.name} from {bak_path.name}!")
                return recovered
            except Exception as be:
                logger.error(f"[ATOMIC WRITER] Backup file {bak_path.name} also unreadable: {be}")

        return default if default is not None else {}
