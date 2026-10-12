"""Regression tests for the 2026-10-11 WORKHORSE outage: the process stayed alive
(no OS-level crash) but stopped accepting new HTTP/WebSocket connections on port 8800
for hours, with no traceback anywhere. The leading hypothesis, verified in code: the
VRAM circuit breaker's `taskkill /F /IM llama-server.exe` call ran synchronously, every
5s, directly on the asyncio event loop thread, with NO subprocess timeout at all -
force-killing a process with active GPU/CUDA work in flight can itself hang on Windows
waiting for driver-level termination, which would block that single thread (and thus
the entire server) forever.

Two fixes, both covered here:
1. `check_and_trip_circuit_breaker()`'s taskkill call now has an explicit timeout and
   degrades to a clearly logged no-op instead of hanging past it.
2. `run_watchdog_loop()` now runs the whole check via `asyncio.to_thread()` instead of
   inline, so even an unforeseen future blocking call in that path can never again
   freeze the event loop that serves real requests.
"""
import subprocess
import time
from unittest.mock import Mock, patch

import pytest

from shared.vram_manager import VramManager


@pytest.fixture
def manager():
    return VramManager(idle_timeout_seconds=300)


def _nvidia_smi_result(util: int) -> Mock:
    return Mock(returncode=0, stdout=f"0, {util}\n1, 5\n")


def test_taskkill_call_always_specifies_an_explicit_timeout(manager):
    """The core bug: a bare `subprocess.run(..., shell=True, capture_output=True)` with
    no timeout= can block its calling thread forever if taskkill itself hangs. Assert
    every subprocess.run call made while tripping the breaker passes a timeout."""
    manager._high_util_start = time.time() - 46

    calls = []

    def recording_run(*args, **kwargs):
        calls.append((args, kwargs))
        if args and isinstance(args[0], list):
            return _nvidia_smi_result(90)
        return Mock(returncode=0)

    with patch("subprocess.run", side_effect=recording_run), \
         patch.object(manager, "purge_vram", return_value={"status": "ok"}):
        manager.check_and_trip_circuit_breaker()

    assert len(calls) >= 2  # nvidia-smi query + taskkill
    for args, kwargs in calls:
        assert "timeout" in kwargs, f"subprocess.run called without a timeout: {args!r}"
        assert kwargs["timeout"] is not None


def test_a_hanging_taskkill_is_bounded_not_fatal(manager):
    """Directly proves the fix: if taskkill ever exceeds its timeout (simulating the
    real-world GPU-driver-hang scenario), check_and_trip_circuit_breaker() must return
    promptly with a clear log instead of propagating an unhandled block/exception."""
    manager._high_util_start = time.time() - 46

    def fake_run(cmd, *args, **kwargs):
        if isinstance(cmd, list):  # the nvidia-smi query
            return _nvidia_smi_result(90)
        # the taskkill call: simulate it blowing past its own timeout
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs.get("timeout"))

    with patch("subprocess.run", side_effect=fake_run), \
         patch.object(manager, "purge_vram", return_value={"status": "ok"}) as purge_mock:
        start = time.time()
        result = manager.check_and_trip_circuit_breaker()
        elapsed = time.time() - start

    assert result is True
    assert elapsed < 1.0  # the fake TimeoutExpired raises instantly; real code must not retry/loop
    purge_mock.assert_called_once_with(reason="circuit_breaker_runaway_inference")
    # Breaker state must still reset so the next genuinely-idle reading isn't stuck "tripped".
    assert manager._high_util_start is None


def test_breaker_does_not_trip_below_45s_or_below_80_percent(manager):
    with patch("subprocess.run", return_value=_nvidia_smi_result(50)), \
         patch.object(manager, "purge_vram") as purge_mock:
        assert manager.check_and_trip_circuit_breaker() is False
        purge_mock.assert_not_called()

    manager._high_util_start = time.time() - 10  # high but not yet past the 45s threshold
    with patch("subprocess.run", return_value=_nvidia_smi_result(95)), \
         patch.object(manager, "purge_vram") as purge_mock:
        assert manager.check_and_trip_circuit_breaker() is False
        purge_mock.assert_not_called()


def test_watchdog_loop_offloads_the_circuit_breaker_check_to_a_worker_thread(manager, monkeypatch):
    """The event-loop-freeze fix: run_watchdog_loop() must never call
    check_and_trip_circuit_breaker() directly on the event loop thread - it has to go
    through asyncio.to_thread so a slow/blocking call inside it can't stall any other
    request being served concurrently."""
    import asyncio
    import threading

    main_thread_id = threading.get_ident()
    seen_thread_ids = []
    call_count = 0

    def fake_check():
        nonlocal call_count
        call_count += 1
        seen_thread_ids.append(threading.get_ident())
        if call_count >= 2:
            raise asyncio.CancelledError()  # stop the infinite watchdog loop cleanly
        return False

    monkeypatch.setattr(manager, "check_and_trip_circuit_breaker", fake_check)
    monkeypatch.setattr(manager, "get_idle_seconds", lambda: 0.0)

    # Speed the loop's internal sleep(5) up so the test doesn't actually wait 5s+.
    async def fast_sleep(_seconds):
        return None
    monkeypatch.setattr("shared.vram_manager.asyncio.sleep", fast_sleep)

    asyncio.run(manager.run_watchdog_loop())

    assert call_count >= 1
    assert all(tid != main_thread_id for tid in seen_thread_ids), (
        "check_and_trip_circuit_breaker() ran on the event loop thread instead of a "
        "worker thread - the freeze-prevention fix is not actually in effect."
    )
