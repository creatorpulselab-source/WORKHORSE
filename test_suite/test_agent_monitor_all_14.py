import pytest
import time
from shared.agent_roster import AGENT_ROSTER
from pipeline.stages.ai_operator import active_task_tracker, ai_operator

def test_all_14_agents_in_roster():
    assert len(AGENT_ROSTER) == 14
    expected_agents = {
        "synapse", "vanguard", "iris", "forge", "echo",
        "aura", "muse", "scribe", "mercury", "herald",
        "cipher", "apex", "radar", "scrubber"
    }
    assert set(AGENT_ROSTER.keys()) == expected_agents

def test_tool_agent_map_covers_all_agents():
    mapped_agents = {agent_id for agent_id, _ in ai_operator.TOOL_AGENT_MAP.values()}
    # All core and specialist agents should have assigned tools
    for agent in ["synapse", "vanguard", "iris", "forge", "echo", "aura", "muse", "scribe", "mercury", "herald", "cipher", "apex", "radar", "scrubber"]:
        assert agent in mapped_agents, f"Agent '{agent}' is missing from TOOL_AGENT_MAP!"

def test_active_task_tracker_multi_agent_concurrency():
    # Clear any leftover tasks
    active_task_tracker.cancel_current_task()

    # Start tasks for 3 different agents concurrently
    active_task_tracker.start_task(agent="synapse", task_desc="Synapse mastermind task", task_id="task_synapse")
    active_task_tracker.start_task(agent="aura", task_desc="Aura retouching photos", task_id="task_aura")
    active_task_tracker.start_task(agent="cipher", task_desc="Cipher trend sweep", task_id="task_cipher")

    all_tasks = active_task_tracker.get_all_active_tasks()
    assert len(all_tasks) == 3

    task_agents = {t["agent"] for t in all_tasks}
    assert task_agents == {"synapse", "aura", "cipher"}

    # Update one task with a sub-agent
    active_task_tracker.update_task("Forge rendering video", progress=60, sub_agent="forge", task_id="task_synapse")
    updated = active_task_tracker.get_all_active_tasks()
    synapse_task = next(t for t in updated if t["task_id"] == "task_synapse")
    assert synapse_task["sub_agent"] == "forge"
    assert synapse_task["progress"] == 60

    # Finish one task
    active_task_tracker.finish_task("task_aura")
    remaining = active_task_tracker.get_all_active_tasks()
    assert len(remaining) == 2
    assert "aura" not in {t["agent"] for t in remaining}

    # Clean up
    active_task_tracker.cancel_current_task()
    assert len(active_task_tracker.get_all_active_tasks()) == 0

def test_server_monitor_endpoint_reflects_all_active_agents():
    import asyncio
    from dashboard.server import get_active_agents_monitor

    active_task_tracker.cancel_current_task()

    # Simulate Echo [26 Fe] and Iris [77 Ir] working concurrently
    active_task_tracker.start_task(
        agent="echo",
        task_desc="Echo [26 Fe]: Faster-Whisper vocal extraction on GPU 1",
        task_id="test_echo"
    )
    active_task_tracker.start_task(
        agent="iris",
        task_desc="Iris [77 Ir]: Forensic QC audit on GPU 0",
        task_id="test_iris"
    )

    monitor = asyncio.run(get_active_agents_monitor())
    assert monitor["has_active"] is True
    assert monitor["active_count"] >= 2

    agent_status_map = {a["id"]: a for a in monitor["agents"]}
    assert agent_status_map["echo"]["state"] == "active"
    assert "Faster-Whisper" in agent_status_map["echo"]["current_task"]
    assert agent_status_map["iris"]["state"] == "active"
    assert "Forensic QC" in agent_status_map["iris"]["current_task"]

    # Verify idle agent remains idle
    assert agent_status_map["radar"]["state"] == "idle"

    # Finish both
    active_task_tracker.finish_task("test_echo")
    active_task_tracker.finish_task("test_iris")

    monitor_idle = asyncio.run(get_active_agents_monitor())
    agent_status_map_idle = {a["id"]: a for a in monitor_idle["agents"]}
    assert agent_status_map_idle["echo"]["state"] == "idle"
    assert agent_status_map_idle["iris"]["state"] == "idle"
