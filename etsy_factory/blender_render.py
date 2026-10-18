"""Headless Blender product renders for Etsy listing photos.

Runs `blender --background` directly (NOT through the live MCP session) because each scene starts from factory
settings - that must never touch a Blender window the Commander has open.
Units: STL files are millimetres; the scene uses 1 Blender unit = 1 cm (scale 0.1).
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List

BLENDER_EXE = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")

_BPY_SCRIPT = r'''
import bpy, sys, json, math, mathutils, os

cfg_path = sys.argv[sys.argv.index("--") + 1]
scenes = json.load(open(cfg_path, encoding="utf-8"))

def pick_engine(scene):
    engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    for cand in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        if cand in engines:
            scene.render.engine = cand
            return cand

def set_in(node, names, value):
    for n in names:
        if n in node.inputs:
            try:
                node.inputs[n].default_value = value
                return True
            except Exception:
                pass
    return False

def material(name, kind, color=(0.8, 0.1, 0.1)):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    rgba = (color[0], color[1], color[2], 1.0)
    if kind == "pla":
        set_in(b, ["Base Color"], rgba); set_in(b, ["Roughness"], 0.38); set_in(b, ["Metallic"], 0.0)
        set_in(b, ["Coat Weight", "Clearcoat"], 0.25); set_in(b, ["Coat Roughness", "Clearcoat Roughness"], 0.3)
        # faint layer-line bump so it reads as a real FDM print
        tex = nt.nodes.new("ShaderNodeTexWave"); tex.wave_type = "BANDS"; tex.bands_direction = "Z"
        tex.inputs["Scale"].default_value = 90.0; tex.inputs["Distortion"].default_value = 0.2
        mp = nt.nodes.new("ShaderNodeMapping"); co = nt.nodes.new("ShaderNodeTexCoord")
        nt.links.new(co.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
        bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.08
        nt.links.new(tex.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    elif kind == "dough":
        set_in(b, ["Base Color"], (0.93, 0.78, 0.55, 1.0)); set_in(b, ["Roughness"], 0.9)
        set_in(b, ["Subsurface Weight", "Subsurface"], 0.12); set_in(b, ["Subsurface Radius"], (0.9, 0.6, 0.35))
        noise = nt.nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 140.0
        bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.25
        nt.links.new(noise.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    elif kind == "wood":
        co = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (9.0, 0.8, 9.0)
        nt.links.new(co.outputs["Object"], mp.inputs["Vector"])
        wave = nt.nodes.new("ShaderNodeTexWave"); wave.wave_type = "BANDS"; wave.bands_direction = "X"
        wave.inputs["Scale"].default_value = 1.0; wave.inputs["Distortion"].default_value = 6.0
        wave.inputs["Detail"].default_value = 3.0; wave.inputs["Detail Scale"].default_value = 1.2
        nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (0.16, 0.08, 0.035, 1); ramp.color_ramp.elements[1].color = (0.36, 0.20, 0.10, 1)
        nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"]); nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
        set_in(b, ["Roughness"], 0.55)
    elif kind in ("sage", "slate", "blush"):
        col = {"sage": (0.30, 0.40, 0.33), "slate": (0.10, 0.13, 0.18), "blush": (0.62, 0.42, 0.40)}[kind]
        set_in(b, ["Base Color"], (col[0], col[1], col[2], 1.0)); set_in(b, ["Roughness"], 0.8)
    elif kind == "cream":
        set_in(b, ["Base Color"], (0.96, 0.93, 0.86, 1.0)); set_in(b, ["Roughness"], 0.85)
    elif kind == "marble":
        set_in(b, ["Base Color"], (0.9, 0.9, 0.92, 1.0)); set_in(b, ["Roughness"], 0.25)
    elif kind == "dark":
        set_in(b, ["Base Color"], (0.05, 0.055, 0.07, 1.0)); set_in(b, ["Roughness"], 0.6)
    elif kind == "flour":
        set_in(b, ["Base Color"], (0.98, 0.97, 0.94, 1.0)); set_in(b, ["Roughness"], 1.0)
    return m

def import_stl(path):
    before = set(bpy.data.objects.keys())
    if hasattr(bpy.ops.wm, "stl_import"):
        bpy.ops.wm.stl_import(filepath=path)
    else:
        bpy.ops.import_mesh.stl(filepath=path)
    new = [bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in before]
    ob = new[0]
    xs = [v.co.x for v in ob.data.vertices]; ys = [v.co.y for v in ob.data.vertices]; zs = [v.co.z for v in ob.data.vertices]
    cx, cy, cz = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs)
    ob.data.transform(mathutils.Matrix.Translation((-cx, -cy, -cz)))
    return ob

for sc_cfg in scenes:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    engine = pick_engine(scene)
    scene.render.resolution_x, scene.render.resolution_y = sc_cfg.get("res", [2000, 2000])
    scene.render.film_transparent = False
    try:
        scene.view_settings.view_transform = sc_cfg.get("view", "AgX")
    except Exception:
        scene.view_settings.view_transform = "Standard"
    for look in ("AgX - Medium High Contrast", "Medium High Contrast", "None"):
        try:
            scene.view_settings.look = look
            break
        except Exception:
            continue
    scene.view_settings.exposure = sc_cfg.get("exposure", 0.0)
    if engine.startswith("BLENDER_EEVEE"):
        try: scene.eevee.taa_render_samples = sc_cfg.get("samples", 96)
        except Exception: pass
    elif engine == "CYCLES":
        scene.cycles.samples = 48

    world = bpy.data.worlds.new("W"); scene.world = world; world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bgc = sc_cfg.get("world_color", [0.82, 0.84, 0.88]); bg.inputs["Color"].default_value = (bgc[0], bgc[1], bgc[2], 1)
    bg.inputs["Strength"].default_value = sc_cfg.get("world_strength", 0.9)

    S = 0.1  # mm -> cm
    # ground plane
    gk = sc_cfg.get("ground", "cream")
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
    ground = bpy.context.active_object; ground.scale = (200, 200, 1)
    ground.data.materials.append(material("Ground", gk))

    for o in sc_cfg["objects"]:
        ob = import_stl(o["stl"])
        ob.scale = (S * o.get("scale", 1.0),) * 3
        ob.rotation_euler = (math.radians(o.get("rot_x", 0)), math.radians(o.get("rot_y", 0)), math.radians(o.get("rot_z", 0)))
        ob.location = (o["loc"][0] * S, o["loc"][1] * S, o["loc"][2] * S)
        bpy.context.view_layer.objects.active = ob
        for p in ob.data.polygons: p.use_smooth = False
        ob.data.materials.append(material("M_" + os.path.basename(o["stl"]), o.get("material", "pla"), o.get("color", [0.75, 0.1, 0.12])))

    # key sun + soft fill sun (distance independent so exposure is predictable)
    for name, energy, rot in (("Key", sc_cfg.get("key", 2.4), (math.radians(48), 0, math.radians(35))),
                              ("Fill", sc_cfg.get("fill", 0.8), (math.radians(60), 0, math.radians(-120)))):
        ld = bpy.data.lights.new(name, "SUN"); ld.energy = energy; ld.angle = math.radians(6 if name == "Key" else 25)
        lo = bpy.data.objects.new(name, ld); scene.collection.objects.link(lo); lo.rotation_euler = rot

    cam_cfg = sc_cfg["camera"]
    tgt = mathutils.Vector([c * S for c in cam_cfg["target"]])
    az, el, dist = math.radians(cam_cfg.get("azimuth", 0)), math.radians(cam_cfg.get("elevation", 40)), cam_cfg["distance"] * S
    pos = tgt + mathutils.Vector((dist * math.cos(el) * math.sin(az), -dist * math.cos(el) * math.cos(az), dist * math.sin(el)))
    cd = bpy.data.cameras.new("Cam"); cd.lens = cam_cfg.get("lens", 70)
    co = bpy.data.objects.new("Cam", cd); scene.collection.objects.link(co); scene.camera = co; co.location = pos
    co.rotation_euler = (tgt - pos).to_track_quat("-Z", "Y").to_euler()
    if cam_cfg.get("dof", 0):
        cd.dof.use_dof = True; cd.dof.focus_distance = (tgt - pos).length; cd.dof.aperture_fstop = cam_cfg["dof"]

    scene.render.filepath = sc_cfg["out"]
    scene.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    print("RENDERED", sc_cfg["out"], engine)
print("BLENDER_RENDER_DONE")
'''


def render_scenes(scenes: List[Dict[str, Any]], work_dir: Path, timeout: int = 1800) -> Dict[str, Any]:
    """Render every scene in ONE Blender process (amortises startup). Returns timing + which outputs exist."""
    work_dir.mkdir(parents=True, exist_ok=True)
    script = work_dir / "_render_scenes.py"
    cfg = work_dir / "_render_scenes.json"
    script.write_text(_BPY_SCRIPT, encoding="utf-8")
    cfg.write_text(json.dumps(scenes), encoding="utf-8")
    t = time.time()
    proc = subprocess.run(
        [str(BLENDER_EXE), "--background", "--factory-startup", "--python", str(script), "--", str(cfg)],
        capture_output=True, text=True, timeout=timeout,
    )
    made = [s["out"] for s in scenes if Path(s["out"]).exists() and Path(s["out"]).stat().st_size > 20_000]
    return {
        "seconds": round(time.time() - t, 1),
        "returncode": proc.returncode,
        "rendered": len(made),
        "expected": len(scenes),
        "missing": [s["out"] for s in scenes if s["out"] not in made],
        "stdout_tail": proc.stdout[-600:],
        "stderr_tail": proc.stderr[-600:],
    }
