"""High-End Blender Cycles OptiX GPU Renderer for Desk Organizers STL Bundle.
Renders 100% original, functional desk organizers with:
- GPU-accelerated Cycles OptiX on RTX GPU
- Sophisticated matte PLA filament shaders (Almond Sand, Forest Green, Terracotta, Charcoal, Slate Blue, Honey Ochre, Dusty Rose, Teal)
- Micro layer-line texture for authentic FDM 3D print look
- Studio 3-point lighting (warm key, soft fill, crisp rim)
- Transparent PNG exports for zero-floating grounded composition
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

BLENDER_EXE = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
LISTING_DIR = Path(r"F:\WORKHORSE\workspace\etsy_listings\desk_organizers_stl")
STL_DIR = LISTING_DIR / "files" / "STL"
RENDERS_DIR = LISTING_DIR / "work_renders"

BLENDER_SCRIPT = r'''
import bpy, sys, math, mathutils, os

args = sys.argv[sys.argv.index('--') + 1:]
stl_dir = args[0]
out_dir = args[1]
res = int(args[2]) if len(args) > 2 else 1800

os.makedirs(out_dir, exist_ok=True)

# 10 Sophisticated Matte PLA Colors for modern desk aesthetics
PALETTE = [
    (0.86, 0.82, 0.72),  # 01 Desert Almond / Sand (Warm Neutral)
    (0.24, 0.38, 0.28),  # 02 Forest Moss Green (Earthy Organic)
    (0.78, 0.36, 0.18),  # 03 Terracotta Clay (Warm Terracotta)
    (0.14, 0.15, 0.18),  # 04 Stealth Matte Charcoal (Sleek Tech)
    (0.32, 0.44, 0.56),  # 05 Denim Slate Blue (Nordic Blue)
    (0.82, 0.60, 0.16),  # 06 Amber Honey Ochre (Warm Accent)
    (0.74, 0.44, 0.48),  # 07 Dusty Rose Clay (Subtle Warm)
    (0.18, 0.45, 0.48),  # 08 Ocean Slate Teal (Calm Teal)
    (0.48, 0.52, 0.46),  # 09 Sage Grey Green (Muted Studio)
    (0.68, 0.62, 0.54),  # 10 Warm Stone Clay (Minimalist Warm)
]

def make_matte_pla_material(name, rgb, rough=0.55):
    m = bpy.data.materials.new(f'M_{name}')
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    b.inputs['Roughness'].default_value = rough
    if 'Metallic' in b.inputs: b.inputs['Metallic'].default_value = 0.0
    if 'Specular IOR Level' in b.inputs: b.inputs['Specular IOR Level'].default_value = 0.32
    elif 'Specular' in b.inputs: b.inputs['Specular'].default_value = 0.32
    if 'Coat Weight' in b.inputs: b.inputs['Coat Weight'].default_value = 0.04
    elif 'Clearcoat' in b.inputs: b.inputs['Clearcoat'].default_value = 0.04

    # Subtle micro-layer line bump
    tex = nt.nodes.new('ShaderNodeTexWave')
    tex.wave_type = 'BANDS'
    tex.bands_direction = 'Z'
    tex.inputs['Scale'].default_value = 120.0
    tex.inputs['Distortion'].default_value = 0.12

    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.05
    nt.links.new(tex.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m

def setup_gpu_cycles(scene, samples=48):
    scene.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    for d in prefs.devices:
        d.use = (d.type == 'OPTIX')
    scene.cycles.device = 'GPU'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.resolution_x = res
    scene.render.resolution_y = res

def setup_lighting(scene):
    if scene.world is None:
        scene.world = bpy.data.worlds.new('World')
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get('Background')
    if bg is None:
        bg = scene.world.node_tree.nodes.new('ShaderNodeBackground')
    bg.inputs['Color'].default_value = (0.95, 0.94, 0.92, 1.0)
    bg.inputs['Strength'].default_value = 0.85

    # Key light: Warm sun at 45 deg
    k_data = bpy.data.lights.new('KeySun', 'SUN')
    k_data.energy = 3.8
    k_data.angle = math.radians(12)
    k_data.color = (1.0, 0.96, 0.90)
    k_ob = bpy.data.objects.new('KeySun', k_data)
    scene.collection.objects.link(k_ob)
    k_ob.rotation_euler = (math.radians(45), math.radians(15), math.radians(35))

    # Fill light: Soft cool ambient
    f_data = bpy.data.lights.new('FillSun', 'SUN')
    f_data.energy = 1.5
    f_data.angle = math.radians(30)
    f_data.color = (0.90, 0.94, 1.0)
    f_ob = bpy.data.objects.new('FillSun', f_data)
    scene.collection.objects.link(f_ob)
    f_ob.rotation_euler = (math.radians(55), math.radians(-10), math.radians(-120))

    # Rim light: Crisp contour accent
    r_data = bpy.data.lights.new('RimSun', 'SUN')
    r_data.energy = 2.5
    r_data.angle = math.radians(8)
    r_data.color = (1.0, 0.98, 0.95)
    r_ob = bpy.data.objects.new('RimSun', r_data)
    scene.collection.objects.link(r_ob)
    r_ob.rotation_euler = (math.radians(65), 0, math.radians(160))

def import_and_center_stl(path):
    before = set(bpy.data.objects.keys())
    bpy.ops.wm.stl_import(filepath=path)
    new = [bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in before]
    ob = new[0]
    ob.scale = (0.1, 0.1, 0.1) # mm -> cm
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.transform_apply(scale=True)

    xs = [v.co.x for v in ob.data.vertices]
    ys = [v.co.y for v in ob.data.vertices]
    zs = [v.co.z for v in ob.data.vertices]
    cx = (min(xs) + max(xs)) / 2.0
    cy = (min(ys) + max(ys)) / 2.0
    cz = min(zs)
    ob.data.transform(mathutils.Matrix.Translation((-cx, -cy, -cz)))
    return ob

# 1. Render all 10 single items
stls = sorted([f for f in os.listdir(stl_dir) if f.endswith('.stl')])
print(f'Found {len(stls)} STLs to render in {stl_dir}')

for i, stl_name in enumerate(stls):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    setup_gpu_cycles(scene)
    setup_lighting(scene)

    ob = import_and_center_stl(os.path.join(stl_dir, stl_name))
    color = PALETTE[i % len(PALETTE)]
    mat = make_matte_pla_material(f'Mat_{i}', color)
    ob.data.materials.append(mat)

    xs = [v.co.x for v in ob.data.vertices]
    ys = [v.co.y for v in ob.data.vertices]
    zs = [v.co.z for v in ob.data.vertices]
    max_dim = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
    center_z = (max(zs) - min(zs)) * 0.45

    cam_dist = max_dim * 2.35
    el = math.radians(28)
    az = math.radians(25)
    cam_x = cam_dist * math.cos(el) * math.sin(az)
    cam_y = -cam_dist * math.cos(el) * math.cos(az)
    cam_z = center_z + cam_dist * math.sin(el)

    cam_data = bpy.data.cameras.new('Cam')
    cam_data.lens = 65
    cam_ob = bpy.data.objects.new('Cam', cam_data)
    scene.collection.objects.link(cam_ob)
    scene.camera = cam_ob
    cam_ob.location = (cam_x, cam_y, cam_z)

    dir_vec = mathutils.Vector((0, 0, center_z)) - cam_ob.location
    cam_ob.rotation_euler = dir_vec.to_track_quat('-Z', 'Y').to_euler()

    out_file = os.path.join(out_dir, f'single_{i+1:02d}.png')
    scene.render.filepath = out_file
    print(f'Rendering {stl_name} -> {out_file}...')
    bpy.ops.render.render(write_still=True)

# 2. Render Hero Desk Setup Cluster (Phone stand + Pen cups + Trays + Cable clips)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
setup_gpu_cycles(scene, samples=64)
setup_lighting(scene)

# Layout key items in an organic, harmonious desk arrangement
# 04 Phone stand in center-left
phone_ob = import_and_center_stl(os.path.join(stl_dir, stls[3]))
phone_ob.location = (-6.5, 4.0, 0)
phone_ob.rotation_euler = (0, 0, math.radians(-10))
phone_ob.data.materials.append(make_matte_pla_material('PhoneMat', PALETTE[3])) # Charcoal

# 08 4-Compartment Desk Tray in center-right
tray_ob = import_and_center_stl(os.path.join(stl_dir, stls[7]))
tray_ob.location = (9.5, 5.0, 0)
tray_ob.rotation_euler = (0, 0, math.radians(5))
tray_ob.data.materials.append(make_matte_pla_material('TrayMat', PALETTE[0])) # Almond Sand

# 02 Hex Pen Cup left background
hex_ob = import_and_center_stl(os.path.join(stl_dir, stls[1]))
hex_ob.location = (-16.0, 10.0, 0)
hex_ob.rotation_euler = (0, 0, math.radians(15))
hex_ob.data.materials.append(make_matte_pla_material('HexMat', PALETTE[1])) # Forest Green

# 01 Round Pen Cup right background
round_ob = import_and_center_stl(os.path.join(stl_dir, stls[0]))
round_ob.location = (18.5, 12.0, 0)
round_ob.rotation_euler = (0, 0, math.radians(-12))
round_ob.data.materials.append(make_matte_pla_material('RoundMat', PALETTE[2])) # Terracotta

# 07 Sticky Note Tray in foreground center
note_ob = import_and_center_stl(os.path.join(stl_dir, stls[6]))
note_ob.location = (-3.0, -8.0, 0)
note_ob.rotation_euler = (0, 0, math.radians(-6))
note_ob.data.materials.append(make_matte_pla_material('NoteMat', PALETTE[5])) # Amber Honey

# 06 Business Card Holder foreground right
card_ob = import_and_center_stl(os.path.join(stl_dir, stls[5]))
card_ob.location = (8.5, -9.0, 0)
card_ob.rotation_euler = (0, 0, math.radians(12))
card_ob.data.materials.append(make_matte_pla_material('CardMat', PALETTE[4])) # Slate Blue

# 05 Cable clips in foreground left
clip_ob = import_and_center_stl(os.path.join(stl_dir, stls[4]))
clip_ob.location = (-15.5, -7.0, 0)
clip_ob.rotation_euler = (0, 0, math.radians(-18))
clip_ob.data.materials.append(make_matte_pla_material('ClipMat', PALETTE[7])) # Teal

# Camera for Hero Cluster
cam_data = bpy.data.cameras.new('CamHero')
cam_data.lens = 45
cam_ob = bpy.data.objects.new('CamHero', cam_data)
scene.collection.objects.link(cam_ob)
scene.camera = cam_ob
cam_ob.location = (0.0, -56.0, 36.0)
dir_vec = mathutils.Vector((0, 2.0, 4.0)) - cam_ob.location
cam_ob.rotation_euler = dir_vec.to_track_quat('-Z', 'Y').to_euler()

out_hero = os.path.join(out_dir, 'cluster_hero.png')
scene.render.filepath = out_hero
print(f'Rendering Hero Desk Cluster -> {out_hero}...')
bpy.ops.render.render(write_still=True)

print('BLENDER_DESK_ORGANIZERS_RENDER_ALL_DONE')
'''


def run_blender_render():
    RENDERS_DIR.mkdir(parents=True, exist_ok=True)
    script_path = RENDERS_DIR / "_render_desk_organizers.py"
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(BLENDER_SCRIPT)

    cmd = [
        str(BLENDER_EXE),
        "--background",
        "--python",
        str(script_path),
        "--",
        str(STL_DIR),
        str(RENDERS_DIR),
        "1800",
    ]
    t0 = time.time()
    print("Launching Blender Cycles OptiX GPU render for Desk Organizers...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.time() - t0
    print(f"Render completed in {dt:.1f}s (Exit code: {res.returncode})")
    if "BLENDER_DESK_ORGANIZERS_RENDER_ALL_DONE" in res.stdout:
        print("[SUCCESS] All 10 single renders + Hero Cluster completed!")
    else:
        print(f"Blender output:\n{res.stdout}\n{res.stderr}")


if __name__ == "__main__":
    run_blender_render()
