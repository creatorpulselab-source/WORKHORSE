"""
Regression test: Synapse's system diagnostics probed Blender/DaVinci via methods that did not exist
(`BlenderBridge.check_status`, a `davinci_resolve_bridge` singleton), so both always reported
'standby' with an AttributeError/ImportError. Found 2026-10-18 while verifying the Blender integration.
"""
from unittest.mock import patch

from pipeline.stages.blender_bridge import BlenderBridge, blender_bridge
from pipeline.stages.davinci_resolve_bridge import DaVinciResolveBridge, davinci_resolve_bridge


def test_blender_check_status_reports_socket_and_cli_independently():
    b = BlenderBridge()
    with patch.object(b, "check_connection", return_value={"mcp_online": False, "blender_exe_exists": True,
                                                            "blender_exe": "x", "host": "localhost", "port": 9876, "handshake": {}}):
        s = b.check_status()
    assert s["mcp_socket_online"] is False and s["cli_available"] is True       # fallback path is healthy
    assert {"blender_exe", "host", "port"} <= set(s)


def test_davinci_check_status_has_the_keys_the_diagnostics_probe_reads(tmp_path):
    exe, mcp, mod = tmp_path / "Resolve.exe", tmp_path / "ResolveMCP.exe", tmp_path / "DaVinciResolveScript.py"
    exe.write_text("x"); mcp.write_text("x")
    d = DaVinciResolveBridge(resolve_exe=exe, script_module_path=mod, lut_dir=tmp_path)
    d.resolve_mcp_exe = mcp
    with patch("pipeline.stages.davinci_resolve_bridge.subprocess.run") as run:
        run.return_value.stdout = "Resolve.exe    1234 Console"
        s = d.check_status()
    assert s == {"resolve_installed": True, "mcp_binary_exists": True, "scripting_module_exists": False, "resolve_running": True}


def test_singletons_exist():
    assert isinstance(blender_bridge, BlenderBridge) and isinstance(davinci_resolve_bridge, DaVinciResolveBridge)


def test_system_diagnostics_no_longer_reports_attribute_or_import_errors_for_blender_and_davinci():
    from pipeline.stages import ai_operator as op
    with patch.object(blender_bridge, "check_status", return_value={"mcp_socket_online": False, "cli_available": True}), \
         patch.object(davinci_resolve_bridge, "check_status", return_value={"resolve_installed": True, "mcp_binary_exists": True}):
        report = op.AIOperatorEngine().run_system_diagnostics()
    blender, resolve = report["components"]["blender"], report["components"]["davinci_resolve"]
    assert blender["status"] == "ok" and "error" not in blender and blender["cli_available"] is True
    assert resolve["status"] == "ok" and "error" not in resolve
