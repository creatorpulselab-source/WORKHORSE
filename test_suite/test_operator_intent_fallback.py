import pytest
import re
from pathlib import Path
from pipeline.stages.ai_operator import ai_operator, extract_tool_calls

def test_resolve_marketing_source_image_in_client_batch():
    batch_dir = Path("F:/WORKHORSE/workspace/client_inbox/batch_20261014_062742_84d8a4")
    resolved = ai_operator._resolve_marketing_source_image("JT2A9258WEB.jpg", batch_dir=batch_dir)
    assert resolved.exists(), f"Failed to resolve JT2A9258WEB.jpg: {resolved}"
    assert "JT2A9258WEB.jpg" in str(resolved)

def test_intent_fallback_image_to_video():
    test_msg = "Give this image motion using comfyui"
    test_reply = (
        "Commander, motion is now active. I have queued your still photo for cinematic animation "
        "using the LTX-2.3 Video Engine on the RTX 5070 Ti.\n\n"
        "Render Specs:\n"
        "- Input: JT2A9258WEB.jpg\n"
        "- Motion Prompt: *\"A slow, elegant dolly-in tracking shot as the subject turns\"*\n\n"
        "The job is now active in ComfyUI's render queue."
    )
    extracted_tools, cleaned_reply, tool_parse_errors = extract_tool_calls(test_reply)
    assert len(extracted_tools) == 0

    msg_lower = test_msg.lower()
    reply_lower = test_reply.lower()

    motion_keywords = ["motion", "animate", "move", "animation", "make this image move", "give this image motion"]
    hallucinated_motion = any(h in reply_lower for h in ["motion is now active", "queued your still photo", "active in comfyui"])
    user_requested_motion = any(k in msg_lower for k in motion_keywords)
    assert user_requested_motion and hallucinated_motion

    m_img = re.search(r'[\w\-.]+\.(?:jpg|jpeg|png|webp|bmp)', test_msg + " " + test_reply, re.I)
    assert m_img and m_img.group(0) == "JT2A9258WEB.jpg"
