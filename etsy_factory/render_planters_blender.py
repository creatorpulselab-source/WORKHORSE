"""High-End Blender Cycles OptiX GPU Renderer for Geometric Planters & Saucers.
Renders 8 faceted planter designs with matching saucers with:
- GPU-accelerated Cycles OptiX on RTX 3060 (device = 'GPU', CPU disabled)
- Authentic matte PLA filament shaders (Terracotta, sage green, sand almond, charcoal, denim blue)
- Procedural soil & succulent plant detail inside each planter
- Micro layer-line texture for authentic FDM print look
- Studio lighting with warm key light, soft fill, and crisp rim accent
- Transparent PNG exports with anchored ground planes for zero-floating composition
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import trimesh

sys.path.insert(0, r"F:\WORKHORSE")
from etsy_factory import shapes3d as s3

BLENDER_EXE = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
LISTING_DIR = Path(r"F:\WORKHORSE\workspace\etsy_listings\geometric_planters_stl_3mf_glb")
FILES_DIR = LISTING_DIR / "files"
STL_DIR = FILES_DIR / "STL"
MF_DIR = FILES_DIR / "3MF"
GLB_DIR = FILES_DIR / "GLB"
RENDERS_DIR = LISTING_DIR / "work_renders"

# 8 Sophisticated Matte PLA / PETG Colors
PLANTER_PALETTE = [
    (0.78, 0.36, 0.18),  # Terracotta Warm Clay
    (0.24, 0.38, 0.28),  # Forest Sage Moss Green
    (0.86, 0.82, 0.72),  # Desert Almond / Warm Sand
    (0.14, 0.15, 0.18),  # Stealth Charcoal / Graphite
    (0.28, 0.44, 0.56),  # Denim Slate Blue
    (0.82, 0.60, 0.16),  # Warm Ochre Honey
    (0.74, 0.46, 0.48),  # Dusty Rose Clay
    (0.92, 0.90, 0.84),  # Bone White / Silk Ivory
]

BLENDER_SCRIPT = r'''
import bpy, sys, math, mathutils, os

args = sys.argv[sys.argv.index('--') + 1:]
stl_dir = args[0]
out_dir = args[1]
res = int(args[2]) if len(args) > 2 else 1800

os.makedirs(out_dir, exist_ok=True)

PALETTE = [
    (0.78, 0.36, 0.18),  # Terracotta Warm Clay
    (0.24, 0.38, 0.28),  # Forest Sage Moss Green
    (0.86, 0.82, 0.72),  # Desert Almond / Warm Sand
    (0.14, 0.15, 0.18),  # Stealth Charcoal / Graphite
    (0.28, 0.44, 0.56),  # Denim Slate Blue
    (0.82, 0.60, 0.16),  # Warm Ochre Honey
    (0.74, 0.46, 0.48),  # Dusty Rose Clay
    (0.92, 0.90, 0.84),  # Bone White / Silk Ivory
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
    if 'Coat Weight' in b.inputs: b.inputs['Coat Weight'].default_value = 0.05
    elif 'Clearcoat' in b.inputs: b.inputs['Clearcoat'].default_value = 0.05

    # Subtle micro-layer bump
    tex = nt.nodes.new('ShaderNodeTexWave')
    tex.wave_type = 'BANDS'
    tex.bands_direction = 'Z'
    tex.inputs['Scale'].default_value = 110.0
    tex.inputs['Distortion'].default_value = 0.12

    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.05
    nt.links.new(tex.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m

def make_succulent_material():
    m = bpy.data.materials.new('M_Succulent')
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    # Soft sage green succulent tone with subtle warmth
    b.inputs['Base Color'].default_value = (0.28, 0.48, 0.32, 1.0)
    b.inputs['Roughness'].default_value = 0.40
    if 'Subsurface Weight' in b.inputs:
        b.inputs['Subsurface Weight'].default_value = 0.15
        b.inputs['Subsurface Radius'].default_value = (0.4, 0.8, 0.3)
    return m

def make_soil_material():
    m = bpy.data.materials.new('M_Soil')
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (0.12, 0.09, 0.07, 1.0)
    b.inputs['Roughness'].default_value = 0.90
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
    k_data.energy = 3.6
    k_data.angle = math.radians(12)
    k_data.color = (1.0, 0.97, 0.92)
    k_ob = bpy.data.objects.new('KeySun', k_data)
    scene.collection.objects.link(k_ob)
    k_ob.rotation_euler = (math.radians(45), math.radians(15), math.radians(35))

    # Fill light: Cool ambient
    f_data = bpy.data.lights.new('FillSun', 'SUN')
    f_data.energy = 1.4
    f_data.angle = math.radians(28)
    f_data.color = (0.92, 0.95, 1.0)
    f_ob = bpy.data.objects.new('FillSun', f_data)
    scene.collection.objects.link(f_ob)
    f_ob.rotation_euler = (math.radians(55), math.radians(-10), math.radians(-120))

    # Rim light
    r_data = bpy.data.lights.new('RimSun', 'SUN')
    r_data.energy = 2.4
    r_data.angle = math.radians(8)
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

def add_succulent_plant(scene, z_top, pot_r):
    """Add a stylized procedural succulent rosette and soil disk inside the pot."""
    # Soil bed
    bpy.ops.mesh.primitive_cylinder_add(
        radius=pot_r * 0.88, depth=0.8,
        location=(0, 0, z_top - 0.4), vertices=32
    )
    soil = bpy.context.active_object
    soil.data.materials.append(make_soil_material())

    # Succulent rosette: layered petals
    mat_succ = make_succulent_material()
    layers = [
        (pot_r * 0.70, 0.75, 8, z_top + 0.2),
        (pot_r * 0.52, 0.60, 7, z_top + 0.65),
        (pot_r * 0.35, 0.45, 6, z_top + 1.05),
        (pot_r * 0.18, 0.30, 4, z_top + 1.35),
    ]
    for r_petal, len_petal, n_petals, z_layer in layers:
        for p in range(n_petals):
            angle = (2 * math.pi * p / n_petals) + (0.35 if (n_petals % 2 == 0) else 0)
            px = (r_petal * 0.45) * math.cos(angle)
            py = (r_petal * 0.45) * math.sin(angle)
            bpy.ops.mesh.primitive_ico_sphere_add(
                subdivisions=2, radius=len_petal * 0.5,
                location=(px, py, z_layer)
            )
            petal = bpy.context.active_object
            petal.scale = (0.55, 1.25, 0.45)
            petal.rotation_euler = (math.radians(25) * math.sin(angle), -math.radians(25) * math.cos(angle), angle)
            petal.data.materials.append(mat_succ)

PLANTER_NAMES = [
    "Hex Taper", "Octagon Taper", "Twisted Hex", "Twisted Square",
    "Twisted Triangle", "Faceted Round", "Tall Hex Vase", "Wide Bowl"
]

# Render all 8 single planters (nested with their matching saucer)
planter_stls = [f'{i+1:02d}_{name.replace(" ", "_")}_Planter.stl' for i, name in enumerate(PLANTER_NAMES)]
saucer_stls = [f'{i+9:02d}_{name.replace(" ", "_")}_Saucer.stl' for i, name in enumerate(PLANTER_NAMES)]

print(f'Rendering {len(planter_stls)} single planter sets...')
for i, (p_name, s_name) in enumerate(zip(planter_stls, saucer_stls)):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    setup_gpu_cycles(scene)
    setup_lighting(scene)

    sau_path = os.path.join(stl_dir, s_name)
    pot_path = os.path.join(stl_dir, p_name)

    # 1. Saucer at bottom
    sau_ob = import_and_center_stl(sau_path)
    sau_ob.location = (0, 0, 0)
    sau_col = PALETTE[(i + 2) % len(PALETTE)]
    sau_ob.data.materials.append(make_matte_pla_material(f'Sau_{i}', sau_col))

    # 2. Planter resting inside saucer (lifted by saucer floor ~0.3 cm)
    pot_ob = import_and_center_stl(pot_path)
    pot_ob.location = (0, 0, 0.30)
    pot_col = PALETTE[i % len(PALETTE)]
    pot_ob.data.materials.append(make_matte_pla_material(f'Pot_{i}', pot_col))

    # Measure pot height
    zs = [v.co.z for v in pot_ob.data.vertices]
    pot_h = (max(zs) - min(zs))
    xs = [v.co.x for v in pot_ob.data.vertices]
    pot_r = (max(xs) - min(xs)) / 2.0

    # Add procedural botanical succulent
    add_succulent_plant(scene, z_top=0.30 + pot_h, pot_r=pot_r)

    # Camera framing
    max_dim = max(pot_r * 2.4, pot_h * 1.5)
    center_z = (pot_h + 0.3) * 0.45

    cam_dist = max_dim * 2.3
    el = math.radians(28)
    az = math.radians(24)
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
    print(f'Rendering Planter {i+1} -> {out_file}...')
    bpy.ops.render.render(write_still=True)

# Render Hero Cluster: 3 complementary planters (Hex Taper, Twisted Hex, Wide Bowl)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
setup_gpu_cycles(scene, samples=64)
setup_lighting(scene)

# Planter 1: Hex Taper in Terracotta
pot1 = import_and_center_stl(os.path.join(stl_dir, planter_stls[0]))
pot1.location = (0, 0, 0.3)
pot1.data.materials.append(make_matte_pla_material('Pot1Mat', PALETTE[0])) # Terracotta
sau1 = import_and_center_stl(os.path.join(stl_dir, saucer_stls[0]))
sau1.location = (0, 0, 0)
sau1.data.materials.append(make_matte_pla_material('Sau1Mat', PALETTE[2])) # Almond
add_succulent_plant(scene, z_top=0.3 + 7.0, pot_r=4.6)

# Planter 2: Twisted Hex in Forest Sage (left)
pot2 = import_and_center_stl(os.path.join(stl_dir, planter_stls[2]))
pot2.location = (-9.5, -1.5, 0.3)
pot2.rotation_euler = (0, 0, math.radians(15))
pot2.data.materials.append(make_matte_pla_material('Pot2Mat', PALETTE[1])) # Forest Sage
sau2 = import_and_center_stl(os.path.join(stl_dir, saucer_stls[2]))
sau2.location = (-9.5, -1.5, 0)
sau2.data.materials.append(make_matte_pla_material('Sau2Mat', PALETTE[3])) # Charcoal
# Add succulent at (-9.5, -1.5)
bpy.ops.mesh.primitive_cylinder_add(radius=4.0 * 0.88, depth=0.8, location=(-9.5, -1.5, 0.3 + 7.6 - 0.4), vertices=32)
bpy.context.active_object.data.materials.append(make_soil_material())
mat_succ = make_succulent_material()
for p in range(7):
    a = 2 * math.pi * p / 7
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.6, location=(-9.5 + 1.2*math.cos(a), -1.5 + 1.2*math.sin(a), 0.3 + 7.6 + 0.3))
    b = bpy.context.active_object
    b.scale = (0.55, 1.25, 0.45)
    b.data.materials.append(mat_succ)

# Planter 3: Wide Bowl in Desert Sand (right)
pot3 = import_and_center_stl(os.path.join(stl_dir, planter_stls[7]))
pot3.location = (10.0, -2.0, 0.3)
pot3.rotation_euler = (0, 0, math.radians(-10))
pot3.data.materials.append(make_matte_pla_material('Pot3Mat', PALETTE[2])) # Almond
sau3 = import_and_center_stl(os.path.join(stl_dir, saucer_stls[7]))
sau3.location = (10.0, -2.0, 0)
sau3.data.materials.append(make_matte_pla_material('Sau3Mat', PALETTE[0])) # Terracotta
bpy.ops.mesh.primitive_cylinder_add(radius=5.5 * 0.88, depth=0.8, location=(10.0, -2.0, 0.3 + 4.8 - 0.4), vertices=32)
bpy.context.active_object.data.materials.append(make_soil_material())
for p in range(8):
    a = 2 * math.pi * p / 8
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.6, location=(10.0 + 1.5*math.cos(a), -2.0 + 1.5*math.sin(a), 0.3 + 4.8 + 0.3))
    b = bpy.context.active_object
    b.scale = (0.55, 1.25, 0.45)
    b.data.materials.append(mat_succ)

# Camera framing for Hero Cluster
cam_data = bpy.data.cameras.new('CamHero')
cam_data.lens = 48
cam_ob = bpy.data.objects.new('CamHero', cam_data)
scene.collection.objects.link(cam_ob)
scene.camera = cam_ob
cam_ob.location = (0.0, -36.0, 18.0)
dir_vec = mathutils.Vector((0, -1.0, 4.0)) - cam_ob.location
cam_ob.rotation_euler = dir_vec.to_track_quat('-Z', 'Y').to_euler()

out_hero = os.path.join(out_dir, 'cluster_hero.png')
scene.render.filepath = out_hero
print(f'Rendering Planter Hero Cluster -> {out_hero}...')
bpy.ops.render.render(write_still=True)

print('BLENDER_PLANTERS_RENDER_ALL_DONE')
'''


def export_all_models():
    """Build all 16 STLs, 8 3MFs, and 8 GLBs with realistic matte colors."""
    STL_DIR.mkdir(parents=True, exist_ok=True)
    MF_DIR.mkdir(parents=True, exist_ok=True)
    GLB_DIR.mkdir(parents=True, exist_ok=True)

    for d in (STL_DIR, MF_DIR, GLB_DIR):
        for old in d.glob("*"):
            if old.is_file():
                old.unlink()

    designs = s3.PLANTER_SPECS
    catalog = []
    print(f"Exporting {len(designs) * 2} STL files, {len(designs)} 3MFs, and {len(designs)} GLBs...")

    # Export Planters
    for i, p in enumerate(designs):
        pot = s3.planter(p)
        idx = i + 1
        fname = f"{idx:02d}_{p['name'].replace(' ', '_')}_Planter.stl"
        out_p = STL_DIR / fname
        pot.export(out_p)
        catalog.append({
            "index": idx,
            "name": f"{p['name']} Planter",
            "file": fname,
            "size_mm": [round(float(x), 1) for x in pot.extents],
            "volume_cm3": round(float(pot.volume) / 1000.0, 1),
            "faces": len(pot.faces),
        })

    # Export Saucers
    for i, p in enumerate(designs):
        sau = s3.saucer(p)
        idx = i + 9
        fname = f"{idx:02d}_{p['name'].replace(' ', '_')}_Saucer.stl"
        out_p = STL_DIR / fname
        sau.export(out_p)
        catalog.append({
            "index": idx,
            "name": f"{p['name']} Saucer",
            "file": fname,
            "size_mm": [round(float(x), 1) for x in sau.extents],
            "volume_cm3": round(float(sau.volume) / 1000.0, 1),
            "faces": len(sau.faces),
        })

    # Export 3MF & GLB with realistic matte palette
    for i, p in enumerate(designs):
        pot = s3.planter(p)
        sau = s3.saucer(p)
        tag = f"{i + 1:02d}_{p['name'].replace(' ', '_')}"

        # 3MF plate (side by side)
        plate = trimesh.Scene()
        a, b = pot.copy(), sau.copy()
        b.apply_translation((a.extents[0] / 2 + b.extents[0] / 2 + 10, 0, 0))
        plate.add_geometry(a, node_name="planter")
        plate.add_geometry(b, node_name="saucer")
        plate.export(MF_DIR / f"{tag}_Planter_and_Saucer.3mf")

        # GLB with realistic PBR material
        col = PLANTER_PALETTE[i % len(PLANTER_PALETTE)]
        scene = trimesh.Scene()
        for nm, m, c in (("planter", pot, col), ("saucer", sau, PLANTER_PALETTE[(i + 2) % len(PLANTER_PALETTE)])):
            m2 = m.copy()
            m2.visual = trimesh.visual.TextureVisuals(
                material=trimesh.visual.material.PBRMaterial(
                    baseColorFactor=[c[0], c[1], c[2], 1.0],
                    metallicFactor=0.0,
                    roughnessFactor=0.55,
                    name=f"{nm}_matte_pla"
                )
            )
            scene.add_geometry(m2, node_name=nm)
        scene.apply_transform(trimesh.transformations.rotation_matrix(-math.pi / 2, (1, 0, 0)))
        scene.export(GLB_DIR / f"{tag}.glb")

    with open(LISTING_DIR / "catalog.json", "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)
    print("All models exported successfully!")
    return catalog


def run_blender_render():
    RENDERS_DIR.mkdir(parents=True, exist_ok=True)
    script_path = RENDERS_DIR / "_render_planters.py"
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
    print("Launching Blender Cycles GPU render for Planters...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.time() - t0
    print(f"Blender finished in {dt:.1f}s")
    for line in res.stdout.splitlines():
        if "Rendering" in line or "BLENDER" in line or "Saved" in line:
            print("  ", line)
    if res.returncode != 0:
        print("Blender STDERR:\n", res.stderr)
        raise RuntimeError("Blender rendering failed")


if __name__ == "__main__":
    export_all_models()
    run_blender_render()
