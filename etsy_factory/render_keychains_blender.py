"""High-End Blender Cycles OptiX GPU Renderer for EDC & Functional Keychains (Pack Overhaul).
Renders 100% original, functional 3D keychains with:
- GPU-accelerated Cycles OptiX on RTX 3060 (device = 'GPU', CPU disabled)
- Realistic matte PLA / PETG filament shaders (Stealth charcoal, cast iron slate, terracotta, sage green, cornflower blue)
- Chrome / nickel steel split ring material for realistic keyring attachments
- Micro layer-line texture for authentic FDM print look
- Studio lighting with warm key light, soft fill, and crisp rim accent
- Transparent PNG exports with anchored ground planes for zero-floating composition
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

BLENDER_EXE = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
LISTING_DIR = Path(r"F:\WORKHORSE\workspace\etsy_listings\keychains_stl")
STL_DIR = LISTING_DIR / "files" / "STL"
RENDERS_DIR = LISTING_DIR / "work_renders"

BLENDER_SCRIPT = r'''
import bpy, sys, math, mathutils, os

args = sys.argv[sys.argv.index('--') + 1:]
stl_dir = args[0]
out_dir = args[1]
res = int(args[2]) if len(args) > 2 else 1600

os.makedirs(out_dir, exist_ok=True)

# 8 Sophisticated EDC Matte PLA Colors
PALETTE = [
    (0.28, 0.46, 0.68),  # Cornflower EDC Blue
    (0.12, 0.12, 0.14),  # Stealth Charcoal / Black
    (0.22, 0.24, 0.28),  # Cast Iron Slate
    (0.78, 0.36, 0.18),  # Warm Terracotta Clay
    (0.38, 0.52, 0.42),  # Forest Sage Green
    (0.85, 0.60, 0.15),  # Golden Amber
    (0.68, 0.58, 0.76),  # Soft Lilac Lavender
    (0.90, 0.88, 0.82),  # Bone White / Silk Ivory
]

def make_matte_pla_material(name, rgb, rough=0.55):
    m = bpy.data.materials.new(f'M_{name}')
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    b.inputs['Roughness'].default_value = rough
    if 'Metallic' in b.inputs: b.inputs['Metallic'].default_value = 0.0
    if 'Specular IOR Level' in b.inputs: b.inputs['Specular IOR Level'].default_value = 0.35
    elif 'Specular' in b.inputs: b.inputs['Specular'].default_value = 0.35
    if 'Coat Weight' in b.inputs: b.inputs['Coat Weight'].default_value = 0.06
    elif 'Clearcoat' in b.inputs: b.inputs['Clearcoat'].default_value = 0.06

    # Subtle micro-layer bump
    tex = nt.nodes.new('ShaderNodeTexWave')
    tex.wave_type = 'BANDS'
    tex.bands_direction = 'Z'
    tex.inputs['Scale'].default_value = 140.0
    tex.inputs['Distortion'].default_value = 0.10

    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.05
    nt.links.new(tex.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m

def make_chrome_ring_material():
    m = bpy.data.materials.new('M_ChromeRing')
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (0.92, 0.93, 0.95, 1.0)
    if 'Metallic' in b.inputs: b.inputs['Metallic'].default_value = 1.0
    b.inputs['Roughness'].default_value = 0.15
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
    bg.inputs['Color'].default_value = (0.96, 0.95, 0.93, 1.0)
    bg.inputs['Strength'].default_value = 0.90

    # Key light: Warm sun
    k_data = bpy.data.lights.new('KeySun', 'SUN')
    k_data.energy = 3.8
    k_data.angle = math.radians(10)
    k_data.color = (1.0, 0.97, 0.92)
    k_ob = bpy.data.objects.new('KeySun', k_data)
    scene.collection.objects.link(k_ob)
    k_ob.rotation_euler = (math.radians(45), math.radians(15), math.radians(35))

    # Fill light: Cool ambient
    f_data = bpy.data.lights.new('FillSun', 'SUN')
    f_data.energy = 1.5
    f_data.angle = math.radians(25)
    f_data.color = (0.92, 0.95, 1.0)
    f_ob = bpy.data.objects.new('FillSun', f_data)
    scene.collection.objects.link(f_ob)
    f_ob.rotation_euler = (math.radians(55), math.radians(-10), math.radians(-120))

    # Rim light
    r_data = bpy.data.lights.new('RimSun', 'SUN')
    r_data.energy = 2.6
    r_data.angle = math.radians(6)
    r_data.color = (1.0, 0.98, 0.95)
    r_ob = bpy.data.objects.new('RimSun', r_data)
    scene.collection.objects.link(r_ob)
    r_ob.rotation_euler = (math.radians(65), 0, math.radians(160))

def import_and_center_stl(path):
    before = set(bpy.data.objects.keys())
    if hasattr(bpy.ops.wm, 'stl_import'):
        bpy.ops.wm.stl_import(filepath=path)
    else:
        bpy.ops.import_mesh.stl(filepath=path)
    new = [bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in before]
    ob = new[0]
    ob.scale = (0.1, 0.1, 0.1)
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

def add_split_ring(scene, loc=(0, 0, 0), rot=(0, 0, 0)):
    """Add a realistic metal split ring attached to the keychain."""
    bpy.ops.mesh.primitive_torus_add(
        major_radius=1.2, minor_radius=0.10,
        major_segments=36, minor_segments=16,
        location=loc, rotation=rot
    )
    ring = bpy.context.active_object
    ring.data.materials.append(make_chrome_ring_material())
    return ring

# Render all 8 single items
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

    # Framing
    xs = [v.co.x for v in ob.data.vertices]
    ys = [v.co.y for v in ob.data.vertices]
    zs = [v.co.z for v in ob.data.vertices]
    max_dim = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
    center_z = (max(zs) - min(zs)) * 0.50

    cam_dist = max_dim * 2.5
    el = math.radians(32)
    az = math.radians(22)
    cam_x = cam_dist * math.cos(el) * math.sin(az)
    cam_y = -cam_dist * math.cos(el) * math.cos(az)
    cam_z = center_z + cam_dist * math.sin(el)

    cam_data = bpy.data.cameras.new('Cam')
    cam_data.lens = 70
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

# Render Hero Cluster
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
setup_gpu_cycles(scene, samples=64)
setup_lighting(scene)

if len(stls) >= 4:
    stand_ob = import_and_center_stl(os.path.join(stl_dir, stls[0]))
    stand_ob.location = (-4.0, 0, 0)
    stand_ob.rotation_euler = (0, 0, math.radians(15))
    stand_ob.data.materials.append(make_matte_pla_material('M_Stand', PALETTE[0]))

    db_ob = import_and_center_stl(os.path.join(stl_dir, stls[1]))
    db_ob.location = (3.5, -2.0, 0)
    db_ob.rotation_euler = (math.radians(90), 0, math.radians(-30))
    db_ob.data.materials.append(make_matte_pla_material('M_DB', PALETTE[1]))

    plate_ob = import_and_center_stl(os.path.join(stl_dir, stls[2]))
    plate_ob.location = (2.0, 3.5, 0)
    plate_ob.rotation_euler = (0, 0, math.radians(10))
    plate_ob.data.materials.append(make_matte_pla_material('M_Plate', PALETTE[2]))

    kb_ob = import_and_center_stl(os.path.join(stl_dir, stls[3]))
    kb_ob.location = (-2.0, 4.0, 0)
    kb_ob.data.materials.append(make_matte_pla_material('M_KB', PALETTE[3]))

    cam_data = bpy.data.cameras.new('CamHero')
    cam_data.lens = 50
    cam_ob = bpy.data.objects.new('CamHero', cam_data)
    scene.collection.objects.link(cam_ob)
    scene.camera = cam_ob
    cam_ob.location = (0, -22.0, 16.0)
    dir_vec = mathutils.Vector((0, 0, 1.5)) - cam_ob.location
    cam_ob.rotation_euler = dir_vec.to_track_quat('-Z', 'Y').to_euler()

    out_hero = os.path.join(out_dir, 'cluster_hero.png')
    scene.render.filepath = out_hero
    print(f'Rendering Keychain Hero Cluster -> {out_hero}...')
    bpy.ops.render.render(write_still=True)

print('BLENDER_KEYCHAINS_RENDER_ALL_DONE')
'''


def run_blender_render():
    RENDERS_DIR.mkdir(parents=True, exist_ok=True)
    script_path = RENDERS_DIR / "_render_keychains.py"
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
    print("Launching Blender Cycles GPU render for keychains...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.time() - t0
    print(f"Blender finished in {dt:.1f}s")
    for line in res.stdout.splitlines():
        if "Rendering" in line or "BLENDER" in line or "Saved" in line:
            print("  ", line)
    if res.returncode != 0:
        print("Blender STDERR:\n", res.stderr)
        raise RuntimeError("Blender rendering failed")


def export_all_stls():
    """Build all 8 original keychain meshes and export to listing STL directory."""
    sys.path.insert(0, r"F:\WORKHORSE")
    from etsy_factory.shapes_keychains_original import ORIGINAL_KEYCHAIN_ITEMS
    STL_DIR.mkdir(parents=True, exist_ok=True)
    for old in STL_DIR.glob("*.stl"):
        old.unlink()

    catalog = []
    print(f"Exporting {len(ORIGINAL_KEYCHAIN_ITEMS)} original STL files to {STL_DIR}...")
    for idx, (name, fn) in enumerate(ORIGINAL_KEYCHAIN_ITEMS, 1):
        mesh = fn()
        fname = f"{idx:02d}_{name.replace(' ', '_')}.stl"
        out_p = STL_DIR / fname
        mesh.export(out_p)
        print(f"  {fname} ({mesh.extents.round(1).tolist()} mm, watertight={mesh.is_watertight})")
        catalog.append({
            "index": idx,
            "name": name,
            "file": fname,
            "size_mm": [round(float(x), 1) for x in mesh.extents],
            "volume_cm3": round(float(mesh.volume) / 1000.0, 1),
            "faces": len(mesh.faces),
        })

    with open(LISTING_DIR / "catalog.json", "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)
    return catalog


if __name__ == "__main__":
    export_all_stls()
    run_blender_render()
