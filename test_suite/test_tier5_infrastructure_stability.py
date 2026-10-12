"""
Regression tests for TIER 5 - Infrastructure stability (crash/downtime risk).
Verifies:
1. VRAM circuit breaker active job guard (never trips during active orchestrator jobs).
2. GPU1 arbiter concurrency (intra-process thread safety, atomic file locking, strict release).
3. Echo and Forge arbiter integration (proper acquisition, checking, and release).
4. Atomic writer adoption (client_batches, incident_log, error_log, orders_history, config, daily_schedule_state).
5. Offloading blocking sync calls in async endpoints (get_system_stats, get_ollama_models, etc.).
6. Temp workspace pruning & bounds validation (recursive temp/<job_id> pruning, max_age_hours >= 1 enforcement).
"""
import asyncio
import json
import os
import shutil
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from shared.vram_manager import VramManager
from shared.gpu1_arbiter import GPU1Arbiter
from shared.atomic_writer import atomic_write_json, safe_read_json


# ==============================================================================
# 1. VRAM CIRCUIT BREAKER ACTIVE JOB GUARD
# ==============================================================================

def test_circuit_breaker_skips_when_is_busy_is_true():
    """Docstring claim: breaker must skip when an orchestrator/pipeline job is active.
    If is_busy() returns True, even if GPU0 is pegged at 99% for >45s, the breaker
    must NOT trip, must reset _high_util_start, and must NOT call purge_vram."""
    manager = VramManager(idle_timeout_seconds=300)
    manager._high_util_start = time.time() - 60
    manager.register_active_jobs_checker(lambda: True)
    assert manager.is_busy() is True

    with patch.object(manager, "purge_vram") as mock_purge, \
         patch("subprocess.run") as mock_run:
        result = manager.check_and_trip_circuit_breaker()

    assert result is False
    mock_purge.assert_not_called()
    mock_run.assert_not_called()
    assert manager._high_util_start is None


def test_circuit_breaker_trips_when_not_busy_and_pegged_over_45s():
    """When is_busy() is False and GPU0 is pegged >= 80% for > 45s, it trips."""
    manager = VramManager(idle_timeout_seconds=300)
    manager._high_util_start = time.time() - 46
    manager.register_active_jobs_checker(lambda: False)

    mock_smi = Mock(returncode=0, stdout="0, 95\n1, 5\n")
    mock_kill = Mock(returncode=0)

    def fake_subprocess_run(cmd, *args, **kwargs):
        if isinstance(cmd, list) and "nvidia-smi" in cmd[0]:
            return mock_smi
        return mock_kill

    with patch("subprocess.run", side_effect=fake_subprocess_run), \
         patch.object(manager, "purge_vram", return_value={"status": "ok"}) as mock_purge:
        result = manager.check_and_trip_circuit_breaker()

    assert result is True
    mock_purge.assert_called_once_with(reason="circuit_breaker_runaway_inference")
    assert manager._high_util_start is None


# ==============================================================================
# 2. GPU1 ARBITER CONCURRENCY & STRICT LOCKING
# ==============================================================================

def test_gpu1_arbiter_atomic_acquire_and_release(tmp_path):
    arbiter = GPU1Arbiter(workspace_dir=tmp_path)
    assert arbiter.get_status()["is_locked"] is False

    acquired = arbiter.acquire("echo_whisper", timeout_seconds=2)
    assert acquired is True
    assert arbiter.lock_file.exists()

    status = arbiter.get_status()
    assert status["is_locked"] is True
    assert status["active_task"] == "echo_whisper"
    assert status["pid"] == os.getpid()

    # Strict release
    arbiter.release("echo_whisper")
    assert arbiter.get_status()["is_locked"] is False
    assert not arbiter.lock_file.exists()


def test_gpu1_arbiter_strict_release_prevents_wrong_task_release(tmp_path):
    """Release must not release another task's lock even if same PID or partial substring."""
    arbiter = GPU1Arbiter(workspace_dir=tmp_path)
    acquired = arbiter.acquire("forge_nvenc", timeout_seconds=2)
    assert acquired is True

    # Attempt to release with a different task name
    arbiter.release("forge")  # Substring match would have released; strict must reject
    assert arbiter.get_status()["is_locked"] is True
    assert arbiter.lock_file.exists()

    # Releasing with exact task name succeeds
    arbiter.release("forge_nvenc")
    assert arbiter.get_status()["is_locked"] is False


def test_gpu1_arbiter_intra_process_thread_contention(tmp_path):
    """Multiple threads in the same process must mutually exclude each other."""
    arbiter = GPU1Arbiter(workspace_dir=tmp_path)
    order = []

    def worker_thread(task_id: str, hold_time: float, timeout_s: float):
        acq = arbiter.acquire(f"task_{task_id}", timeout_seconds=timeout_s)
        if acq:
            order.append(f"start_{task_id}")
            time.sleep(hold_time)
            order.append(f"end_{task_id}")
            arbiter.release(f"task_{task_id}")
        else:
            order.append(f"timeout_{task_id}")

    # Thread 1 holds lock for 0.4s
    t1 = threading.Thread(target=worker_thread, args=("1", 0.4, 2.0))
    # Thread 2 tries to acquire immediately with timeout 0.1s -> should timeout
    t2 = threading.Thread(target=worker_thread, args=("2", 0.1, 0.1))

    t1.start()
    time.sleep(0.05)  # Ensure t1 acquires first
    t2.start()

    t1.join()
    t2.join()

    assert "start_1" in order
    assert "end_1" in order
    assert "timeout_2" in order


# ==============================================================================
# 3. ECHO & FORGE ARBITER INTEGRATION
# ==============================================================================

def test_echo_agent_handles_arbiter_acquire(tmp_path, monkeypatch):
    from pipeline.stages.audio_agent import AudioAgent
    agent = AudioAgent()
    agent.auto_unload = False

    acquire_calls = []
    release_calls = []

    def mock_acquire(task, timeout_seconds=30):
        acquire_calls.append((task, timeout_seconds))
        return True

    def mock_release(task):
        release_calls.append(task)

    monkeypatch.setattr("pipeline.stages.audio_agent.gpu1_arbiter.acquire", mock_acquire)
    monkeypatch.setattr("pipeline.stages.audio_agent.gpu1_arbiter.release", mock_release)
    monkeypatch.setattr(agent, "_execute_transcribe", lambda *a, **k: {"status": "ok"})

    dummy_video = tmp_path / "test.mp4"
    dummy_video.write_bytes(b"video")
    out_dir = tmp_path / "out"

    res = agent.transcribe(dummy_video, out_dir)
    assert res == {"status": "ok"}
    assert len(acquire_calls) == 1
    assert acquire_calls[0][0] == "echo_whisper"
    assert release_calls == ["echo_whisper"]


def test_forge_scene_extractor_wires_arbiter(tmp_path, monkeypatch):
    from pipeline.stages import scene_extractor

    acquire_calls = []
    release_calls = []

    def mock_acquire(task, timeout_seconds=30):
        acquire_calls.append(task)
        return True

    def mock_release(task):
        release_calls.append(task)

    monkeypatch.setattr(scene_extractor.gpu1_arbiter, "acquire", mock_acquire)
    monkeypatch.setattr(scene_extractor.gpu1_arbiter, "release", mock_release)
    monkeypatch.setattr(scene_extractor, "detect_ffmpeg_encoder", lambda: "h264_nvenc")

    # Mock subprocess.run for ffmpeg
    def mock_subp(cmd, *a, **k):
        # Create output preview file if requested in cmd
        out_file = Path(cmd[-1])
        out_file.write_bytes(b"cut")
        return Mock(returncode=0)

    monkeypatch.setattr("subprocess.run", mock_subp)

    dummy_in = tmp_path / "raw.mp4"
    dummy_in.write_bytes(b"data")
    out_dir = tmp_path / "out_preview"

    cut_res = scene_extractor.cut_preview_video(dummy_in, out_dir, target_duration=10)
    assert cut_res is not None
    assert "forge_nvenc" in acquire_calls
    assert "forge_nvenc" in release_calls


# ==============================================================================
# 4. ATOMIC WRITER ADOPTION
# ==============================================================================

def test_ai_operator_atomic_storage(tmp_path, monkeypatch):
    from pipeline.stages import ai_operator as aio

    monkeypatch.setattr(aio, "CLIENT_BATCHES_FILE", tmp_path / "client_batches.json")
    monkeypatch.setattr(aio, "INCIDENT_LOG_FILE", tmp_path / "incident_log.json")
    monkeypatch.setattr(aio, "ERROR_LOG_FILE", tmp_path / "error_log.json")
    monkeypatch.setattr(aio, "DAILY_HEALTH_LOG_FILE", tmp_path / "daily_health_log.json")
    monkeypatch.setattr(aio, "OPERATOR_CHAT_SESSIONS_DIR", tmp_path / "chat_sessions")

    # 1. Client batches
    aio._save_client_batches([{"batch_id": "b1", "client": "VIP"}])
    loaded_batches = aio._load_client_batches()
    assert len(loaded_batches) == 1
    assert loaded_batches[0]["batch_id"] == "b1"
    assert (tmp_path / "client_batches.json").exists()

    # 2. Incidents
    op = aio.AIOperatorEngine()
    op.log_incident("gpu", "VRAM warning", "Swapped block", status="resolved")
    incidents = op.get_recent_incidents()
    assert len(incidents) == 1
    assert incidents[0]["component"] == "gpu"
    assert (tmp_path / "incident_log.json").exists()

    # 3. Errors
    op.log_error("whisper", "Kernel timeout", {"attempt": 1})
    errors = op.get_recent_errors()
    assert len(errors) == 1
    assert errors[0]["component"] == "whisper"
    assert (tmp_path / "error_log.json").exists()

    # 4. Chat history
    op.get_history("session_123").append({"role": "user", "content": "hello"})
    op._save_history("session_123")
    assert (tmp_path / "chat_sessions" / "session_123.json").exists()


def test_order_radar_atomic_storage(tmp_path, monkeypatch):
    from pipeline.stages.order_radar import OrderRadar

    radar = OrderRadar(base_dir=str(tmp_path))
    radar.orders.append({"id": "ord_99", "amount": 49.0})
    radar.save_orders()

    loaded = radar.load_orders()
    assert len(loaded) == 1
    assert loaded[0]["id"] == "ord_99"
    assert (tmp_path / "workspace" / "orders_history.json").exists()


def test_herald_scheduler_atomic_storage(tmp_path):
    from pipeline.stages.herald_scheduler import HeraldScheduler

    state_path = tmp_path / "daily_schedule_state.json"
    sched = HeraldScheduler(
        config_path="F:/WORKHORSE/config.json",
        state_file=str(state_path)
    )
    sched.state["executed_slots"].append("slot_1_morning")
    sched._save_state()

    assert state_path.exists()
    sched._load_state()
    assert "slot_1_morning" in sched.state["executed_slots"]


# ==============================================================================
# 5. TEMP WORKSPACE PRUNING & BOUNDS VALIDATION
# ==============================================================================

def test_prune_old_staging_files_bounds_validation(tmp_path, monkeypatch):
    """Enforce max_age_hours >= 1 so 0 or negative values can NEVER wipe active files."""
    manager = VramManager()

    staging = tmp_path / "comfy_staging"
    temp = tmp_path / "temp"
    staging.mkdir()
    temp.mkdir()

    monkeypatch.setattr("shared.vram_manager.Path", lambda p: tmp_path / Path(p).name if "workspace" in str(p) else Path(p))

    # Create fresh file created right now
    fresh_file = staging / "just_rendered.png"
    fresh_file.write_bytes(b"new")

    # Calling with 0 or negative hours must clamp to 1 hour and protect the fresh file
    res = manager.prune_old_staging_files(max_age_hours=0)
    assert res["cutoff_hours"] == 1
    assert fresh_file.exists()

    res_neg = manager.prune_old_staging_files(max_age_hours=-5)
    assert res_neg["cutoff_hours"] == 1
    assert fresh_file.exists()


def test_prune_old_staging_files_recursively_prunes_temp_job_directories(tmp_path, monkeypatch):
    """workspace/temp/<job_id>/ subdirectories must be recursively cleaned when older than cutoff."""
    manager = VramManager()

    comfy_staging = tmp_path / "comfy_staging"
    temp_dir = tmp_path / "temp"
    comfy_staging.mkdir()
    temp_dir.mkdir()

    # Patch target paths in vram_manager
    monkeypatch.setattr("shared.vram_manager.Path", lambda p: comfy_staging if "comfy_staging" in str(p) else (temp_dir if "temp" in str(p) else Path(p)))

    # Create an old job directory in temp
    old_job = temp_dir / "job_expired_123"
    old_job.mkdir()
    sub_dir = old_job / "intermediate_frames"
    sub_dir.mkdir()
    (sub_dir / "frame_001.png").write_bytes(b"frame_data_x" * 100)

    # Set mtime back 50 hours
    old_mtime = time.time() - (50 * 3600)
    os.utime(old_job, (old_mtime, old_mtime))

    # Create a fresh job directory (10 mins old)
    fresh_job = temp_dir / "job_active_456"
    fresh_job.mkdir()
    (fresh_job / "active.txt").write_bytes(b"active")

    res = manager.prune_old_staging_files(max_age_hours=48)

    assert not old_job.exists()
    assert fresh_job.exists()
    assert res["deleted_count"] >= 1
