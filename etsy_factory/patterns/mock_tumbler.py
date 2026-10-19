"""Headless Blender render of sublimation tumblers wearing a wrap PNG (20 oz skinny, 9.3 x 8.2 in wrap).

Each scene = a list of tumblers (wrap image + lid/straw colour) on a seamless cream backdrop with strip-light reflections.
Runs `blender --background --factory-startup` (never touches a Blender window you have open). Units: 1 Blender unit = 1 cm.
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List

BLENDER_EXE = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")

_BPY = r'''
import bpy, sys, json, math, mathutils

cfg = json.load(open(sys.argv[sys.argv.index("--") + 1], encoding="utf-8"))

def set_in(node, names, value):
    for n in names:
        if n in node.inputs:
            try:
                node.inputs[n].default_value = value
                return True
            except Exception:
                pass
    return False

def mat_plain(name, rgb, rough=0.4, metal=0.0, coat=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    set_in(b, ["Base Color"], (rgb[0], rgb[1], rgb[2], 1)); set_in(b, ["Roughness"], rough); set_in(b, ["Metallic"], metal)
    if coat:
        set_in(b, ["Coat Weight", "Clearcoat"], coat); set_in(b, ["Coat Roughness", "Clearcoat Roughness"], 0.05)
    return m

def mat_wrap(path):
    m = bpy.data.materials.new("Wrap"); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes.get("Principled BSDF")
    img = bpy.data.images.load(path)
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img; tex.extension = "REPEAT"; tex.interpolation = "Cubic"
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    set_in(b, ["Roughness"], 0.16); set_in(b, ["Metallic"], 0.0)
    set_in(b, ["Specular IOR Level", "Specular"], 0.6)
    set_in(b, ["Coat Weight", "Clearcoat"], 0.7); set_in(b, ["Coat Roughness", "Clearcoat Roughness"], 0.03)
    return m

def smooth(ob):
    bpy.context.view_layer.objects.active = ob
    for p in ob.data.polygons:
        p.use_smooth = True

def tumbler(x, wrap, lid_rgb, straw_rgb, rot_z, tilt=0.0):
    H, r0, r1 = 20.8, 3.35, 3.76
    base_z = 0.55
    bpy.ops.mesh.primitive_cone_add(vertices=192, radius1=r0, radius2=r1, depth=H, end_fill_type="NOTHING", calc_uvs=True,
                                    location=(x, 0, base_z + H / 2))
    body = bpy.context.active_object; smooth(body)
    body.rotation_euler[2] = math.radians(rot_z)
    body.data.materials.append(mat_wrap(wrap))
    # steel foot
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=r0 + 0.04, depth=0.7, location=(x, 0, 0.35))
    foot = bpy.context.active_object; smooth(foot); foot.data.materials.append(mat_plain("Steel", (0.62, 0.63, 0.66), 0.28, 1.0))
    # bottom cap so the body is closed
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=r0, depth=0.1, location=(x, 0, base_z + 0.02))
    cap = bpy.context.active_object; cap.data.materials.append(mat_plain("CapSteel", (0.55, 0.56, 0.6), 0.3, 1.0))
    # lid
    lid_z = base_z + H + 0.85
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=r1 + 0.12, depth=1.7, location=(x, 0, lid_z))
    lid = bpy.context.active_object; smooth(lid); lid.data.materials.append(mat_plain("Lid", lid_rgb, 0.32, 0.0, 0.2))
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=r1 - 0.35, depth=0.12, location=(x, 0, lid_z + 0.88))
    top = bpy.context.active_object; top.data.materials.append(mat_plain("LidTop", (lid_rgb[0] * 0.8, lid_rgb[1] * 0.8, lid_rgb[2] * 0.8), 0.4))
    # straw
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.33, depth=17.0, location=(x + 1.2, 0.2, lid_z + 7.4))
    st = bpy.context.active_object; smooth(st); st.rotation_euler[1] = math.radians(-7)
    st.data.materials.append(mat_plain("Straw", straw_rgb, 0.25, 0.0, 0.5))
    return body

for sc in cfg:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = sc.get("samples", 96)
    try: scene.cycles.use_denoising = True
    except Exception: pass
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for dev in ("OPTIX", "CUDA"):
            try:
                prefs.compute_device_type = dev; prefs.get_devices()
                if any(d.type == dev for d in prefs.devices):
                    for d in prefs.devices: d.use = (d.type == dev)
                    scene.cycles.device = "GPU"; print("CYCLES_GPU", dev); break
            except Exception as ex:
                print("DEV_FAIL", dev, ex)
    except Exception as ex:
        print("PREFS_FAIL", ex)
    scene.render.resolution_x, scene.render.resolution_y = sc.get("res", [2000, 2000])
    scene.render.image_settings.file_format = "PNG"
    try: scene.view_settings.view_transform = "Standard"
    except Exception: pass

    bgc = sc.get("bg", [0.93, 0.90, 0.85])
    w = bpy.data.worlds.new("W"); scene.world = w; w.use_nodes = True
    wb = w.node_tree.nodes.get("Background"); wb.inputs["Color"].default_value = (bgc[0], bgc[1], bgc[2], 1); wb.inputs["Strength"].default_value = sc.get("world", 1.1)

    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
    ground = bpy.context.active_object; ground.scale = (400, 400, 1)
    ground.data.materials.append(mat_plain("Ground", bgc, 0.55))

    for t in sc["tumblers"]:
        tumbler(t["x"], t["wrap"], t.get("lid", [0.96, 0.95, 0.93]), t.get("straw", [0.9, 0.5, 0.55]), t.get("rot", 90), t.get("tilt", 0))

    def area(name, loc, size, energy, target=(0, 0, 11), visible_cam=False, color=(1, 1, 1)):
        ld = bpy.data.lights.new(name, "AREA"); ld.energy = energy; ld.size = size[0]; ld.size_y = size[1]; ld.shape = "RECTANGLE"
        ld.color = color
        lo = bpy.data.objects.new(name, ld); scene.collection.objects.link(lo); lo.location = loc
        d = mathutils.Vector(target) - mathutils.Vector(loc)
        lo.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        lo.visible_camera = visible_cam
    spread = sc.get("spread", 0)
    area("Key", (-55, -70, 70), (60, 60), sc.get("key", 9000), target=(spread / 2, 0, 12))
    area("Fill", (70, -60, 40), (80, 60), sc.get("fill", 3500), target=(spread / 2, 0, 12))
    area("RimL", (-48, 22, 40), (14, 60), sc.get("rim", 6000), target=(-spread / 2, 0, 12))
    area("RimR", (48, 22, 40), (14, 60), sc.get("rim", 6000), target=(spread / 2, 0, 12))
    # strip reflector cards (only visible in reflections)
    for nm, loc, sz in (("StripL", (-34, -52, 20), (7, 40)), ("StripR", (34, -52, 20), (7, 40))):
        area(nm, loc, sz, 2600, target=(0, 0, 12))

    cam = sc["camera"]
    tgt = mathutils.Vector(cam.get("target", [0, 0, 12])); az = math.radians(cam.get("az", 0)); el = math.radians(cam.get("el", 8)); dist = cam["dist"]
    pos = tgt + mathutils.Vector((dist * math.cos(el) * math.sin(az), -dist * math.cos(el) * math.cos(az), dist * math.sin(el)))
    cd = bpy.data.cameras.new("Cam"); cd.lens = cam.get("lens", 85)
    co = bpy.data.objects.new("Cam", cd); scene.collection.objects.link(co); scene.camera = co; co.location = pos
    co.rotation_euler = (tgt - pos).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = sc["out"]
    bpy.ops.render.render(write_still=True)
    print("RENDERED", sc["out"])
print("TUMBLER_RENDER_DONE")
'''


def render(scenes: List[Dict[str, Any]], work_dir: Path, timeout: int = 2400) -> Dict[str, Any]:
    work_dir.mkdir(parents=True, exist_ok=True)
    script, cfg = work_dir / "_tumbler.py", work_dir / "_tumbler.json"
    script.write_text(_BPY, encoding="utf-8")
    cfg.write_text(json.dumps(scenes), encoding="utf-8")
    t = time.time()
    proc = subprocess.run([str(BLENDER_EXE), "--background", "--factory-startup", "--python", str(script), "--", str(cfg)],
                          capture_output=True, text=True, timeout=timeout)
    made = [s["out"] for s in scenes if Path(s["out"]).exists() and Path(s["out"]).stat().st_size > 20_000]
    return {"seconds": round(time.time() - t, 1), "returncode": proc.returncode, "rendered": len(made), "expected": len(scenes),
            "missing": [s["out"] for s in scenes if s["out"] not in made], "stdout_tail": proc.stdout[-700:], "stderr_tail": proc.stderr[-900:]}
