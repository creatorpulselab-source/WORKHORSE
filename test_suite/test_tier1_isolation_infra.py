"""Regression tests for the Tier 1 test-safety infrastructure added to conftest.py
(2026-10-10): real network connections are blocked by default during the test suite,
the known file-I/O-at-import singletons are redirected away from the real
F:/WORKHORSE workspace, and dashboard/server.py no longer double-imports itself.

These tests exist so the safety net itself has coverage - if a future change
accidentally weakens or removes it, a test should fail rather than the gap going
unnoticed until a real secret/network call slips through during a test run.
"""
import socket
import socketserver
import threading

import pytest


def test_real_external_connection_attempt_is_blocked():
    with pytest.raises(RuntimeError, match="blocked a real network connection"):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(("8.8.8.8", 443))
        finally:
            sock.close()


@pytest.mark.parametrize("port", [11434, 8188, 8800, 993, 587])
def test_well_known_local_service_ports_are_still_blocked_on_loopback(port):
    """Ollama (11434), ComfyUI (8188), WORKHORSE itself (8800), IMAP (993), and SMTP
    (587) all run on well-known ports on this very machine - the loopback allowlist
    must not accidentally let a test reach any of them for real."""
    with pytest.raises(RuntimeError, match="blocked a real network connection"):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(("127.0.0.1", port))
        finally:
            sock.close()


def test_loopback_ephemeral_port_connections_still_work():
    """Proves the allowlist genuinely distinguishes ephemeral-range loopback IPC
    (what asyncio's Windows self-pipe and FastAPI's TestClient need) from a real
    service connection, rather than merely happening to pass because every other
    test in this suite uses TestClient (which could mask a narrower regression)."""
    server = socketserver.TCPServer(("127.0.0.1", 0), socketserver.BaseRequestHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert port >= 49152, "test setup assumption: OS should hand out an ephemeral port"
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(("127.0.0.1", port))  # must NOT raise
        finally:
            sock.close()
    finally:
        server.shutdown()
        server.server_close()


def test_order_radar_singleton_is_redirected_away_from_real_workspace():
    from pipeline.stages.order_radar import order_radar
    assert "workhorse-pytest-" in str(order_radar.base_dir)
    assert "F:\\WORKHORSE" not in str(order_radar.config_file)
    assert "F:/WORKHORSE" not in str(order_radar.config_file)


def test_herald_scheduler_singleton_is_redirected_away_from_real_workspace():
    from pipeline.stages.herald_scheduler import herald_scheduler
    assert "workhorse-pytest-" in str(herald_scheduler.state_file)
    assert "workhorse-pytest-" in str(herald_scheduler.newsletter.workspace)


def test_newsletter_mgr_singleton_is_redirected_away_from_real_workspace():
    from pipeline.stages.newsletter_manager import newsletter_mgr
    assert "workhorse-pytest-" in str(newsletter_mgr.workspace)


def test_server_entry_point_does_not_reimport_itself_by_string():
    """Locks in the dashboard/server.py fix: uvicorn.run() must be given the already-
    constructed `app` object, not the string "dashboard.server:app", which previously
    forced a second full module (re-)import and duplicated every singleton
    construction/file I/O on every `python dashboard/server.py` launch."""
    source = (__import__("pathlib").Path(__file__).resolve().parents[1] / "dashboard" / "server.py").read_text(encoding="utf-8")
    assert 'uvicorn.run("dashboard.server:app"' not in source
    assert "uvicorn.run(app," in source
