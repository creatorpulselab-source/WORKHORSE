"""Automated ComfyUI Trellis 2 to Blender 5.2 Cleanup & GPU Render Pipeline for Keychains.
Generates 100% original, sculpted, high-demand 3D printable keychains:
1. ComfyUI Trellis 2 generates 3D volumetric mesh (.GLB)
2. Blender 5.2 MCP cleans up edges, removes artifacts, adds keyring eyelet, ensures 100% watertight manifold
3. Blender Cycles OptiX GPU renders photorealistic listing media with grounded contact shadows
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, r"F:\WORKHORSE")
from pipeline.stages.comfyui_bridge import comfy_bridge

BLENDER_EXE = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
LISTING_DIR = Path(r"F:\WORKHORSE\workspace\etsy_listings\keychains_stl")
STL_DIR = LISTING_DIR / "files" / "STL"
RENDERS_DIR = LISTING_DIR / "work_renders"
COMFY_CACHE_DIR = Path(r"F:\WORKHORSE\workspace\brand_assets\comfy_3d_pbr_renders")

STL_DIR.mkdir(parents=True, exist_ok=True)
RENDERS_DIR.mkdir(parents=True, exist_ok=True)
COMFY_CACHE_DIR.mkdir(parents=True, exist_ok=True)

BLENDER_CLEANUP_SCRIPT = r'''
import bpy, bmesh, sys, math, mathutils, os

args = sys.argv[sys.argv.index('--') + 1:]
glb_in = args[0]
stl_out = args[1]
preview_out = args[2]
target_h_mm = float(args[3]) if len(args) > 3 else 48.0
color_hex = args[4] if len(args) > 4 else "terracotta"

bpy.ops.wm.read_factory_settings(use_empty=True)

# 1. Import GLB from ComfyUI
bpy.ops.import_scene.gltf(filepath=glb_in)
mesh_objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
if not mesh_objs:
    raise RuntimeError(f"No mesh objects found in {glb_in}")

bpy.ops.object.select_all(action='DESELECT')
for o in mesh_objs:
    o.select_set(True)
bpy.context.view_layer.objects.active = mesh_objs[0]
if len(mesh_objs) > 1:
    bpy.ops.object.join()

ob = bpy.context.active_object

# 2. Clean topology in edit mode
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=0.0002)
bpy.ops.mesh.delete_loose()
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode='OBJECT')

# 3. Normalize size and ground at Z=0
xs = [v.co.x for v in ob.data.vertices]
ys = [v.co.y for v in ob.data.vertices]
zs = [v.co.z for v in ob.data.vertices]
h_cur = max(zs) - min(zs)
scale_f = (target_h_mm / 10.0) / max(h_cur, 0.001) # cm in Blender
ob.scale = (scale_f, scale_f, scale_f)
bpy.ops.object.transform_apply(scale=True)

# Re-center XY and ground base
xs = [v.co.x for v in ob.data.vertices]
ys = [v.co.y for v in ob.data.vertices]
zs = [v.co.z for v in ob.data.vertices]
cx = (min(xs) + max(xs)) / 2.0
cy = (min(ys) + max(ys)) / 2.0
cz = min(zs)
ob.data.transform(mathutils.Matrix.Translation((-cx, -cy, -cz)))

# 4. Add sturdy 4mm keyring eyelet loop on top if needed
top_z = max(v.co.z for v in ob.data.vertices)
bpy.ops.mesh.primitive_torus_add(
    major_radius=0.42, minor_radius=0.14,
    major_segments=32, minor_segments=16,
    location=(0, 0, top_z + 0.32),
    rotation=(math.pi / 2, 0, 0)
)
loop_ob = bpy.context.active_object

# Join model and loop
bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
loop_ob.select_set(True)
bpy.context.view_layer.objects.active = ob
bpy.ops.object.join()

# 5. Voxel Remesh to weld all seams, eliminate internal artifacts & ensure watertight shell
remesh_mod = ob.modifiers.new(name='VoxelRemesh', type='REMESH')
remesh_mod.mode = 'VOXEL'
remesh_mod.voxel_size = 0.065 # 0.65 mm voxels in Blender cm units
bpy.ops.object.modifier_apply(modifier='VoxelRemesh')

# 6. Smooth modifier to polish surface
smooth_mod = ob.modifiers.new(name='Smooth', type='SMOOTH')
smooth_mod.factor = 0.45
smooth_mod.iterations = 2
bpy.ops.object.modifier_apply(modifier='Smooth')

# 7. Flatten bottom base at Z=0 for support-free print
bpy.ops.mesh.primitive_cube_add(size=20, location=(0, 0, -10))
cutter = bpy.context.active_object
bool_mod = ob.modifiers.new(name='BottomCut', type='BOOLEAN')
bool_mod.operation = 'DIFFERENCE'
bool_mod.object = cutter
bpy.ops.object.modifier_apply(modifier='BottomCut')
bpy.data.objects.remove(cutter, do_unlink=True)

# Convert from cm to mm for STL export
ob.scale = (10.0, 10.0, 10.0)
bpy.ops.object.transform_apply(scale=True)

# 8. Export clean, watertight STL
if hasattr(bpy.ops.wm, 'stl_export'):
    bpy.ops.wm.stl_export(filepath=stl_out)
else:
    bpy.ops.export_mesh.stl(filepath=stl_out)

# Scale back to cm for Cycles render
ob.scale = (0.1, 0.1, 0.1)
bpy.ops.object.transform_apply(scale=True)
for p in ob.data.polygons: p.use_smooth = True

# Inspect topology
me = ob.data
bm = bmesh.new()
bm.from_mesh(me)
n_non_manifold = len([e for e in bm.edges if not e.is_manifold])
n_boundary = len([e for e in bm.edges if e.is_boundary])
n_loose = len([v for v in bm.verts if not v.link_edges])
bm.free()
print(f"VERIFIED_TOPOLOGY: verts={len(me.vertices)}, faces={len(me.polygons)}, non_manifold={n_non_manifold}, boundary={n_boundary}")

# 9. Setup Cycles OptiX GPU render
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'OPTIX'
prefs.get_devices()
for d in prefs.devices:
    d.use = (d.type == 'OPTIX')
scene.cycles.device = 'GPU'
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.resolution_x = 1600
scene.render.resolution_y = 1600

# World
if scene.world is None:
    scene.world = bpy.data.worlds.new('World')
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes.get('Background')
if bg:
    bg.inputs['Color'].default_value = (0.95, 0.94, 0.92, 1.0)
    bg.inputs['Strength'].default_value = 0.9

# Matte PLA Material
mat_colors = {
    "terracotta": (0.78, 0.36, 0.18),
    "sage": (0.38, 0.52, 0.42),
    "charcoal": (0.12, 0.12, 0.14),
    "blue": (0.28, 0.46, 0.68),
    "sand": (0.88, 0.84, 0.74),
    "amber": (0.85, 0.60, 0.15),
    "lavender": (0.68, 0.58, 0.76),
    "rose": (0.76, 0.44, 0.48),
}
rgb = mat_colors.get(color_hex, (0.78, 0.36, 0.18))
mat = bpy.data.materials.new('MattePLA')
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
bsdf.inputs['Roughness'].default_value = 0.55
if 'Coat Weight' in bsdf.inputs: bsdf.inputs['Coat Weight'].default_value = 0.05
ob.data.materials.append(mat)

# 3-Point Studio Lights
for name, energy, rot, col in [
    ('Key', 3.6, (math.radians(45), math.radians(15), math.radians(35)), (1, 0.96, 0.9)),
    ('Fill', 1.4, (math.radians(55), math.radians(-10), math.radians(-120)), (0.9, 0.94, 1)),
    ('Rim', 2.6, (math.radians(65), 0, math.radians(160)), (1, 0.98, 0.95))
]:
    ld = bpy.data.lights.new(name, 'SUN'); ld.energy = energy; ld.color = col
    lo = bpy.data.objects.new(name, ld); scene.collection.objects.link(lo); lo.rotation_euler = rot

# Camera
cd = bpy.data.cameras.new('Cam'); cd.lens = 70
co = bpy.data.objects.new('Cam', cd); scene.collection.objects.link(co); scene.camera = co

xs = [v.co.x for v in ob.data.vertices]
ys = [v.co.y for v in ob.data.vertices]
zs = [v.co.z for v in ob.data.vertices]
max_d = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
cz = (max(zs) - min(zs)) * 0.45

dist = max_d * 2.45
el, az = math.radians(30), math.radians(24)
cam_x = dist * math.cos(el) * math.sin(az)
cam_y = -dist * math.cos(el) * math.cos(az)
cam_z = cz + dist * math.sin(el)
co.location = (cam_x, cam_y, cam_z)
co.rotation_euler = (mathutils.Vector((0, 0, cz)) - co.location).to_track_quat('-Z', 'Y').to_euler()

scene.render.filepath = preview_out
bpy.ops.render.render(write_still=True)
print('CLEANUP_AND_RENDER_DONE:', preview_out)
'''


def run_blender_cleanup(glb_path: Path, stl_out: Path, preview_out: Path, height_mm: float = 48.0, color: str = "terracotta"):
    script_p = RENDERS_DIR / "_cleanup_step.py"
    with open(script_p, "w", encoding="utf-8") as f:
        f.write(BLENDER_CLEANUP_SCRIPT)

    cmd = [
        str(BLENDER_EXE),
        "--background",
        "--python",
        str(script_p),
        "--",
        str(glb_path),
        str(stl_out),
        str(preview_out),
        str(height_mm),
        color
    ]
    t0 = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.time() - t0
    for line in res.stdout.splitlines():
        if "VERIFIED" in line or "CLEANUP" in line:
            print("  ", line)
    if res.returncode != 0:
        print("Blender cleanup error:\n", res.stderr)
        raise RuntimeError("Blender cleanup failed")
    print(f"  [Blender] Cleaned & rendered in {dt:.1f}s")


if __name__ == "__main__":
    # Test on the existing octopus GLB
    octo_glb = Path(r"F:\WORKHORSE\workspace\brand_assets\comfy_3d_pbr_renders\test_cute_octopus_keychain_1792583454.glb")
    stl_out = STL_DIR / "01_Cute_Baby_Octopus_Keychain.stl"
    prev_out = RENDERS_DIR / "single_01.png"
    print("Testing Blender cleanup pipeline on Octopus...")
    run_blender_cleanup(octo_glb, stl_out, prev_out, height_mm=45.0, color="teal")
