"""Unit tests for client-file isolation & marketing-source resolution in ai_operator.py.

Covers two distinct safety fixes:
1. Upload-batch isolation: each file-drop gets its own client_inbox/batch_.../ folder
   (via create_client_batch/get_latest_client_batch_dir/tag_client_batch), so one
   client's/session's files are never mixed with another's just because they land in
   the same flat folder.
2. Marketing-source resolution lockdown: tools that produce POSTABLE content
   (image-to-video, background swap, subject swap) must NEVER implicitly resolve a
   bare filename against client_inbox, even when a same-named file exists there -
   only brand_assets/comfy_renders (or an explicit absolute path) is ever used.
"""
import json
import shutil
import uuid
from pathlib import Path

import pytest

from pipeline.stages.ai_operator import (
    AIOperatorEngine,
    CLIENT_INBOX_DIR,
    CLIENT_BATCHES_FILE,
    create_client_batch,
    get_latest_client_batch_dir,
    tag_client_batch,
    register_batch_files,
)


@pytest.fixture
def isolated_batches_file(tmp_path, monkeypatch):
    """Points the client_batches registry at a throwaway file for this test only."""
    fake_registry = tmp_path / "client_batches.json"
    monkeypatch.setattr("pipeline.stages.ai_operator.CLIENT_BATCHES_FILE", fake_registry)
    yield fake_registry


def test_create_client_batch_makes_isolated_folder(isolated_batches_file):
    batch_dir = create_client_batch(session_id="session-A")
    try:
        assert batch_dir.exists()
        assert batch_dir.parent == CLIENT_INBOX_DIR
        assert batch_dir.name.startswith("batch_")
    finally:
        shutil.rmtree(batch_dir, ignore_errors=True)


def test_two_sessions_get_different_batches_and_latest_is_session_scoped(isolated_batches_file):
    batch_a = create_client_batch(session_id="session-A")
    batch_b = create_client_batch(session_id="session-B")
    try:
        assert batch_a != batch_b
        # Each session's "latest batch" must resolve to its OWN batch, never the
        # other session's, even though session-B's batch was created more recently.
        assert get_latest_client_batch_dir("session-A") == batch_a
        assert get_latest_client_batch_dir("session-B") == batch_b
    finally:
        shutil.rmtree(batch_a, ignore_errors=True)
        shutil.rmtree(batch_b, ignore_errors=True)


def test_register_and_tag_batch_files(isolated_batches_file):
    batch_dir = create_client_batch(session_id="session-C")
    try:
        register_batch_files(batch_dir, ["photo1.jpg", "photo2.jpg"])
        assert tag_client_batch(batch_dir, "Acme Client") is True

        data = json.loads(isolated_batches_file.read_text(encoding="utf-8"))
        entry = next(b for b in data["batches"] if b["folder"] == str(batch_dir))
        assert entry["client_name"] == "Acme Client"
        assert set(entry["files"]) == {"photo1.jpg", "photo2.jpg"}
    finally:
        shutil.rmtree(batch_dir, ignore_errors=True)


def test_resolve_marketing_source_image_ignores_client_inbox_namesake():
    """The core safety assertion: even when a file of the SAME NAME exists directly in
    client_inbox, tools that produce postable marketing content must resolve the bare
    filename against brand_assets/comfy_renders only - never silently pick up the
    client's file."""
    unique_name = f"IMG_{uuid.uuid4().hex[:8]}.jpg"
    client_copy = CLIENT_INBOX_DIR / unique_name
    CLIENT_INBOX_DIR.mkdir(parents=True, exist_ok=True)
    client_copy.write_bytes(b"client-private-bytes")
    try:
        resolved = AIOperatorEngine._resolve_marketing_source_image(unique_name)
        assert resolved != client_copy
        assert "brand_assets" in str(resolved)
        assert "client_inbox" not in str(resolved)
    finally:
        client_copy.unlink(missing_ok=True)


def test_resolve_marketing_source_image_honors_explicit_absolute_path():
    """An absolute path is still honored unchanged - so a deliberate, explicit choice
    to use a client_inbox file is possible, just never an implicit filename guess."""
    explicit_path = CLIENT_INBOX_DIR / "deliberately_chosen.jpg"
    resolved = AIOperatorEngine._resolve_marketing_source_image(str(explicit_path))
    assert resolved == explicit_path
