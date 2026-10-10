"""Shared pytest fixtures and test-session safety infrastructure for the WORKHORSE
test suite.

Several production modules create module-level singletons (order_radar,
herald_scheduler, newsletter_mgr, ...) with real file-system side effects - and real
network calls (Twitter, SMTP, Twilio, IMAP, Stripe, Ollama, ComfyUI, DuckDuckGo/Google
News) are reachable from plain Python calls with no test-mode flag. Without this file,
simply running `pytest` could:
  - read/rewrite the real F:/WORKHORSE/config/order_radar_config.json (which has held
    a live Gmail app password and will hold the Stripe webhook secret once configured)
  - mutate the real workspace/orders_history.json, daily_schedule_state.json, or
    newsletter subscriber list
  - send a real tweet/SMS/email, or hit a real external API, from an automated test run

This module runs ONCE, before any test file in this directory is collected/imported
(pytest guarantees conftest.py loads first), and:
  1. Blocks all real outbound network connections for the rest of the test process.
  2. Redirects the known file-I/O-at-import singletons to a throwaway temp directory
     instead of the real F:/WORKHORSE workspace.
Individual tests remain free to construct their OWN fresh instances pointed at a
pytest `tmp_path` (the preferred, most explicit pattern - see test_tier0_security_fixes.py
and test_client_retouch_pipeline.py for examples) for anything that needs its own
isolated state within a single test.
"""
import os
import socket
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# --------------------------------------------------------------------------
# 1. Block real outbound network connections for the whole test process.
#
# FastAPI's TestClient (used throughout this suite) talks to the app in-process via
# an ASGI transport and never opens a real socket, so this does not affect any
# existing test. Anything that DOES try to open a real connection (a missed mock,
# an accidentally-exercised Twitter/SMTP/Twilio/IMAP/Stripe/Ollama/ComfyUI/search
# call) now fails immediately with a clear error instead of silently succeeding
# against a real external service or hanging on a real-world timeout.
# --------------------------------------------------------------------------
_real_connect = socket.socket.connect
_real_connect_ex = socket.socket.connect_ex

# Windows' asyncio ProactorEventLoop implements its internal wakeup self-pipe via a
# loopback socketpair fallback (bind to an OS-assigned ephemeral port, then connect to
# it) - this is pure in-process IPC plumbing required for ANY async event loop to exist
# at all (including the one FastAPI's TestClient spins up), not a real network call, so
# it must stay allowed. It's reliably distinguishable from a real external/local-service
# connection (Ollama :11434, ComfyUI :8188, WORKHORSE itself :8800, SMTP/IMAP, etc.) by
# port range: the OS only hands out ephemeral ports from a high range, while every real
# service above uses a well-known/registered low port.
_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
_EPHEMERAL_PORT_MIN = 49152


def _is_internal_loopback_plumbing(address) -> bool:
    if not isinstance(address, tuple) or len(address) < 2:
        return False
    host, port = address[0], address[1]
    return host in _LOOPBACK_HOSTS and isinstance(port, int) and port >= _EPHEMERAL_PORT_MIN


def _blocked_connect(self, address, *args, **kwargs):
    if _is_internal_loopback_plumbing(address):
        return _real_connect(self, address, *args, **kwargs)
    raise RuntimeError(
        f"WORKHORSE test suite: blocked a real network connection attempt to "
        f"{address!r}. Tests must mock external calls (Twitter/SMTP/Twilio/IMAP/"
        f"Stripe/Ollama/ComfyUI/web search/etc.) instead of reaching real services. "
        f"If this is a genuine, intentional in-process need, add an explicit "
        f"allowlist entry in test_suite/conftest.py."
    )


def _blocked_connect_ex(self, address, *args, **kwargs):
    if _is_internal_loopback_plumbing(address):
        return _real_connect_ex(self, address, *args, **kwargs)
    raise RuntimeError(
        f"WORKHORSE test suite: blocked a real network connection attempt to {address!r}."
    )


socket.socket.connect = _blocked_connect
socket.socket.connect_ex = _blocked_connect_ex

# --------------------------------------------------------------------------
# 2. Redirect known import-time-singleton file I/O away from the real workspace.
# --------------------------------------------------------------------------
TEST_WORKSPACE_ROOT = Path(tempfile.mkdtemp(prefix="workhorse-pytest-"))
os.environ["WORKHORSE_TEST_BASE_DIR"] = str(TEST_WORKSPACE_ROOT)

# The exact fallback GPU record shared/system_monitor.py returns when `nvidia-smi`
# fails or isn't present - exposed here so a test can assert against this specific
# signature instead of accidentally treating simulated data as a real GPU reading.
MOCK_GPU_FALLBACK_NAME = "NVIDIA GeForce RTX 3060 (Dual Mode)"
MOCK_GPU_FALLBACK_MEMORY_TOTAL_MB = 12288


def _redirect_order_radar_singleton() -> None:
    """order_radar.py's module-level singleton reads/writes the real
    config/order_radar_config.json (which holds the real IMAP app password and, once
    configured, the real Stripe webhook secret) the moment it is first imported by
    ANY test file. Re-point it at the temp workspace and reload, which also flushes
    the real secret this one-time import read out of memory."""
    from pipeline.stages import order_radar as order_radar_module
    radar = order_radar_module.order_radar
    radar.base_dir = TEST_WORKSPACE_ROOT
    radar.config_file = TEST_WORKSPACE_ROOT / "config" / "order_radar_config.json"
    radar.orders_file = TEST_WORKSPACE_ROOT / "workspace" / "orders_history.json"
    radar.tokens_file = TEST_WORKSPACE_ROOT / "workspace" / "order_download_tokens.json"
    radar.config_file.parent.mkdir(parents=True, exist_ok=True)
    radar.orders_file.parent.mkdir(parents=True, exist_ok=True)
    radar.load_config()
    radar.load_orders()
    radar.load_download_tokens()


def _redirect_herald_scheduler_singleton() -> None:
    """herald_scheduler.py's module-level STATE_FILE/LOGS_DIR constants and its
    singleton's internal NewsletterManager previously had no per-instance override at
    all - any import touched the real daily_schedule_state.json and newsletter_logs/.
    HeraldScheduler now accepts state_file/newsletter_workspace_base overrides
    specifically to support this."""
    from pipeline.stages import herald_scheduler as herald_module
    test_workspace = TEST_WORKSPACE_ROOT / "workspace"
    test_workspace.mkdir(parents=True, exist_ok=True)
    herald_module.STATE_FILE = test_workspace / "daily_schedule_state.json"
    herald_module.LOGS_DIR = test_workspace / "newsletter_logs"
    herald_module.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    sched = herald_module.herald_scheduler
    sched.state_file = herald_module.STATE_FILE
    sched.newsletter = herald_module.NewsletterManager(workspace_base=str(test_workspace))
    sched._load_state()


def _redirect_newsletter_mgr_singleton() -> None:
    """newsletter_manager.py's own module-level singleton - redirected in case any
    test imports/uses it directly rather than going through herald_scheduler or a
    freshly-constructed instance."""
    from pipeline.stages import newsletter_manager as newsletter_module
    test_workspace = TEST_WORKSPACE_ROOT / "workspace"
    newsletter_module.newsletter_mgr = newsletter_module.NewsletterManager(
        workspace_base=str(test_workspace)
    )


_redirect_order_radar_singleton()
_redirect_herald_scheduler_singleton()
_redirect_newsletter_mgr_singleton()
