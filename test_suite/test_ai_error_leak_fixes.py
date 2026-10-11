"""Regression tests for the "AI provider error strings leaking into deliverables" bug
(2026-10-10): shared/ai_providers.py's call_ollama_text()/call_ollama_vision() never
raise on a connection/HTTP failure - they return a plain error string instead (e.g.
"Ollama connection error: ..."). Several callers had no check for this, so a real
infra failure was silently treated as if it were genuine generated content:

1. prompt_synthesizer.py: an error string became the literal FLUX image-generation
   prompt fed to ComfyUI, the WAN video-motion prompt, and/or produced zero pose
   variations with no indication anything had failed.
2. vision_agent.py: an error string became a client-visible "visual_summary" or
   "scene_description" (the latter then compounds directly into Muse's prompts too).
3. audio_agent.py: a mid-transcription failure appended "[Transcription error: ...]"
   directly onto the end of already-successfully-transcribed real dialogue, making it
   look like part of the actual spoken transcript rather than a failure notice.

copy_synthesizer.py is NOT covered here because it already requires valid JSON and
falls back to static content otherwise - an error string is never valid JSON, so it
was never vulnerable to this in the first place (confirmed, not assumed).
"""
from unittest.mock import patch

import pytest

from shared.ai_providers import is_ai_error_response


# --------------------------------------------------------------------------
# shared/ai_providers.py: is_ai_error_response()
# --------------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "Ollama connection error: HTTPConnectionPool(host='127.0.0.1', port=11434): Max retries exceeded",
    "Error from Local Ollama: HTTP 500 - Internal Server Error",
    "Ollama Vision error: Connection refused",
    '{"passed": false, "error": "Vision QC timed out (>60s) and was aborted to release GPU."}',
])
def test_is_ai_error_response_detects_every_known_failure_prefix(text):
    assert is_ai_error_response(text) is True


@pytest.mark.parametrize("text", [
    "A photorealistic portrait of a woman in golden hour lighting, 8k uhd, RAW photo",
    "1. A confident standing pose.\n2. A seated profile shot.",
    "",
    None,
])
def test_is_ai_error_response_does_not_flag_real_content(text):
    assert is_ai_error_response(text) is False


# --------------------------------------------------------------------------
# prompt_synthesizer.py
# --------------------------------------------------------------------------

@pytest.fixture
def synthesizer():
    from pipeline.stages.prompt_synthesizer import PromptSynthesizer
    return PromptSynthesizer()


def test_generate_prompt_kit_fails_clearly_instead_of_using_error_text_as_prompt(synthesizer):
    with patch.object(
        synthesizer.ai, "call_ollama_text",
        return_value="Ollama connection error: Connection refused"
    ):
        result = synthesizer.generate_prompt_kit(scene_description="A woman in a red dress.")

    assert result["status"] == "error"
    assert "Connection refused" in result["error"]
    # The raw infra error must never be used as the literal generation prompt.
    assert "Ollama connection error" not in result["flux_image_prompt"]
    assert "Ollama connection error" not in result["wan_video_prompt"]
    assert result["pose_series"] == []


def test_generate_prompt_kit_succeeds_normally_when_ai_calls_are_healthy(synthesizer):
    with patch.object(synthesizer.ai, "call_ollama_text", return_value="A beautiful studio portrait, 8k uhd, RAW photo"):
        result = synthesizer.generate_prompt_kit(scene_description="A woman in a red dress.")

    assert result["status"] == "ok"
    assert result["flux_image_prompt"] == "A beautiful studio portrait, 8k uhd, RAW photo"


# --------------------------------------------------------------------------
# vision_agent.py
# --------------------------------------------------------------------------

@pytest.fixture
def vision_agent():
    from pipeline.stages.vision_agent import VisionAgent
    return VisionAgent()


def test_analyze_poses_does_not_present_infra_error_as_visual_summary(vision_agent, tmp_path):
    fake_image = tmp_path / "pose1.jpg"
    fake_image.write_bytes(b"x")

    with patch.object(vision_agent.ai, "call_ollama_vision", return_value="Ollama Vision error: Connection refused"):
        result = vision_agent.analyze_poses([fake_image])

    assert "Ollama Vision error" not in result["visual_summary"]
    assert result["error"] == "Ollama Vision error: Connection refused"


def test_extract_forensic_scene_does_not_leak_into_muse_prompt_inputs(vision_agent, tmp_path):
    """The real-world compounding risk: scene_description feeds directly into
    prompt_synthesizer.py as the 'ground-truth scene description'."""
    fake_image = tmp_path / "pose1.jpg"
    fake_image.write_bytes(b"x")

    with patch.object(vision_agent.ai, "call_ollama_vision", return_value="Ollama Vision error: timed out"):
        result = vision_agent.extract_forensic_scene([fake_image])

    assert "Ollama Vision error" not in result["scene_description"]
    assert result["error"] == "Ollama Vision error: timed out"


def test_extract_forensic_scene_succeeds_normally_when_healthy(vision_agent, tmp_path):
    fake_image = tmp_path / "pose1.jpg"
    fake_image.write_bytes(b"x")

    with patch.object(vision_agent.ai, "call_ollama_vision", return_value="1. SUBJECT: Brown hair, athletic build."):
        result = vision_agent.extract_forensic_scene([fake_image])

    assert result["scene_description"] == "1. SUBJECT: Brown hair, athletic build."
    assert "error" not in result


# --------------------------------------------------------------------------
# audio_agent.py
# --------------------------------------------------------------------------

def test_transcription_failure_does_not_append_error_text_onto_real_transcript(tmp_path, monkeypatch):
    from pipeline.stages import audio_agent as audio_module

    monkeypatch.setattr(audio_module.gpu1_arbiter, "acquire", lambda *a, **k: True)
    monkeypatch.setattr(audio_module.gpu1_arbiter, "release", lambda *a, **k: None)

    agent = audio_module.AudioAgent()
    agent.auto_unload = False
    monkeypatch.setattr(agent, "extract_audio", lambda video_path, wav_path: True)
    monkeypatch.setattr(agent, "_ensure_model", lambda: None)

    class _Segment:
        def __init__(self, start, end, text):
            self.start, self.end, self.text = start, end, text

    def fake_transcribe(*args, **kwargs):
        def segment_generator():
            yield _Segment(0.0, 2.0, "Hey guys, welcome back to my channel.")
            raise RuntimeError("CUDA out of memory")
        return segment_generator(), {}

    agent.model = type("FakeModel", (), {"transcribe": staticmethod(fake_transcribe)})()

    result = agent._execute_transcribe(tmp_path / "video.mp4", tmp_path / "out")

    # The real, successfully-transcribed dialogue must survive, clean, with no
    # bracketed error text appended onto the end of it.
    assert result["full_text"] == "Hey guys, welcome back to my channel."
    assert "Transcription error" not in result["full_text"]
    assert "CUDA out of memory" in result["transcription_error"]
