"""High-End Blender Cycles OptiX Renderer for Cute Animal Pencil Cups (Pack 2).
Generates photorealistic product renders with:
- Multi-tone Matte PLA filament shaders with procedural relief feature coloring & black pupils
- Ambient Occlusion crevice shading for crisp embossed facial details
- Pencils, pens, markers, scissors, and makeup brushes inside cups (authentic product-in-use)
- Perfect Z-offsets: zero mesh clipping at the bottom of the cups
- Transparent background rendering for clean card composition
- Rich warm lighting with natural directional key light and rim accents
"""
from __future__ import annotations

import math
import os
import subprocess
import sys
import time
from pathlib import Path

BLENDER_EXE = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")

BLENDER_SCRIPT = r'''
import bpy, sys, math, mathutils, os, random

args = sys.argv[sys.argv.index('--') + 1:]
stl_dir = args[0]
out_dir = args[1]
res = int(args[2]) if len(args) > 2 else 1600

os.makedirs(out_dir, exist_ok=True)

# 8 Animals Palette: (body_rgb, feat1_rgb, feat2_rgb)
# feat1: face layer 1 (snout, whiskers, eye rings, inner ears)
# feat2: face layer 2 (pupils, nostrils, beak highlights)
PALETTE = {
    'Cat':   ((0.86, 0.36, 0.12), (0.95, 0.94, 0.90), (0.10, 0.08, 0.08)),  # Terracotta, Cream, Black
    'Bear':  ((0.72, 0.42, 0.16), (0.92, 0.88, 0.78), (0.10, 0.08, 0.08)),  # Honey Caramel, Sand, Black
    'Bunny': ((0.92, 0.38, 0.52), (0.96, 0.94, 0.92), (0.10, 0.08, 0.08)),  # Rose Pink, Ivory, Black
    'Panda': ((0.94, 0.94, 0.92), (0.12, 0.12, 0.14), (0.05, 0.05, 0.05)),  # Silk Ivory, Slate Black, Deep Black
    'Pig':   ((0.94, 0.48, 0.60), (0.85, 0.28, 0.42), (0.10, 0.08, 0.08)),  # Blossom Pink, Strawberry, Black
    'Owl':   ((0.38, 0.50, 0.64), (0.94, 0.92, 0.86), (0.96, 0.65, 0.10)),  # Denim Blue, Ivory, Marigold
    'Chick': ((0.96, 0.76, 0.12), (0.96, 0.94, 0.90), (0.95, 0.45, 0.08)),  # Dandelion Yellow, Ivory, Pumpkin
    'Dino':  ((0.20, 0.62, 0.38), (0.92, 0.90, 0.78), (0.92, 0.48, 0.15)),  # Forest Mint, Butter, Amber
}

def make_animal_mat(name, rough=0.50):
    body_col, feat1_col, feat2_col = PALETTE.get(name, ((0.8, 0.5, 0.3), (0.95, 0.95, 0.95), (0.1, 0.1, 0.1)))
    m = bpy.data.materials.new(f'M_{name}')
    nt = m.node_tree
    b = nt.nodes.get('Principled BSDF')

    co = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(co.outputs['Object'], sep.inputs['Vector'])

    # Step 1: Face features layer 1 (Y < -25.2 in unscaled mesh coords)
    step1 = nt.nodes.new('ShaderNodeMath')
    step1.operation = 'LESS_THAN'
    step1.inputs[1].default_value = -25.2
    nt.links.new(sep.outputs['Y'], step1.inputs[0])

    # Step 2: Pupils / highlights layer 2 (Y < -26.7 in unscaled mesh coords)
    step2 = nt.nodes.new('ShaderNodeMath')
    step2.operation = 'LESS_THAN'
    step2.inputs[1].default_value = -26.7
    nt.links.new(sep.outputs['Y'], step2.inputs[0])

    # Mix 1: Body vs Face layer 1
    mix1 = nt.nodes.new('ShaderNodeMix')
    mix1.data_type = 'RGBA'
    nt.links.new(step1.outputs['Value'], mix1.inputs['Factor'])
    mix1.inputs[6].default_value = (body_col[0], body_col[1], body_col[2], 1.0)
    mix1.inputs[7].default_value = (feat1_col[0], feat1_col[1], feat1_col[2], 1.0)

    # Mix 2: Mix1 vs Face layer 2
    mix2 = nt.nodes.new('ShaderNodeMix')
    mix2.data_type = 'RGBA'
    nt.links.new(step2.outputs['Value'], mix2.inputs['Factor'])
    nt.links.new(mix1.outputs['Result'], mix2.inputs[6])
    mix2.inputs[7].default_value = (feat2_col[0], feat2_col[1], feat2_col[2], 1.0)

    # Ambient Occlusion for crevice contrast
    ao = nt.nodes.new('ShaderNodeAmbientOcclusion')
    ao.samples = 16
    ao.inputs['Distance'].default_value = 2.2
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.35, 0.35, 0.35, 1.0)
    ramp.color_ramp.elements[1].position = 0.85
    ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    nt.links.new(ao.outputs['Color'], ramp.inputs['Fac'])

    ao_mult = nt.nodes.new('ShaderNodeMix')
    ao_mult.data_type = 'RGBA'
    ao_mult.blend_type = 'MULTIPLY'
    ao_mult.inputs['Factor'].default_value = 1.0
    nt.links.new(mix2.outputs['Result'], ao_mult.inputs[6])
    nt.links.new(ramp.outputs['Color'], ao_mult.inputs[7])

    nt.links.new(ao_mult.outputs['Result'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough
    b.inputs['Specular IOR Level'].default_value = 0.45
    return m

def make_pla_simple(name, col, rough=0.45):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    b = nt.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (col[0], col[1], col[2], 1.0)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Specular IOR Level'].default_value = 0.40
    return m

def init_scene(samples=32, transparent=True):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.resolution_x = res
    scene.render.resolution_y = res
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.film_transparent = transparent

    prefs = bpy.context.preferences.addons['cycles'].preferences
    for dt in ('OPTIX', 'CUDA'):
        try:
            prefs.compute_device_type = dt
            prefs.get_devices()
            if any(d.type == dt for d in prefs.devices):
                for d in prefs.devices: d.use = (d.type == dt)
                scene.cycles.device = 'GPU'
                break
        except Exception:
            pass

    # Key sun (warm sunlight)
    sun_d = bpy.data.lights.new('KeySun', 'SUN')
    sun_d.energy = 4.2
    sun_d.color = (1.0, 0.96, 0.92)
    sun = bpy.data.objects.new('KeySun', sun_d)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(45), math.radians(15), math.radians(35))

    # Fill sun (cool sky fill)
    fill_d = bpy.data.lights.new('FillSun', 'SUN')
    fill_d.energy = 1.2
    fill_d.color = (0.80, 0.88, 1.0)
    fill = bpy.data.objects.new('FillSun', fill_d)
    scene.collection.objects.link(fill)
    fill.rotation_euler = (math.radians(50), 0, math.radians(-115))

    # Rim light (silhouette highlight)
    rim_d = bpy.data.lights.new('RimSun', 'SUN')
    rim_d.energy = 3.6
    rim_d.color = (1.0, 0.96, 0.90)
    rim = bpy.data.objects.new('RimSun', rim_d)
    scene.collection.objects.link(rim)
    rim.rotation_euler = (math.radians(70), 0, math.radians(165))

    return scene

def load_cup(name, loc=(0,0,0), rot_z=0):
    candidates = [f for f in os.listdir(stl_dir) if name.lower() in f.lower() and f.endswith('.stl')]
    if not candidates:
        raise FileNotFoundError(f"Cup {name} not found in {stl_dir}")
    path = os.path.join(stl_dir, candidates[0])
    before = set(bpy.data.objects.keys())
    if hasattr(bpy.ops.wm, 'stl_import'): bpy.ops.wm.stl_import(filepath=path)
    else: bpy.ops.import_mesh.stl(filepath=path)
    ob = [bpy.data.objects[k] for k in bpy.data.objects.keys() if k not in before][0]
    ob.scale = (0.1, 0.1, 0.1)
    xs = [v.co.x for v in ob.data.vertices]; ys = [v.co.y for v in ob.data.vertices]; zs = [v.co.z for v in ob.data.vertices]
    cx, cy, cz = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2, min(zs)
    ob.data.transform(mathutils.Matrix.Translation((-cx, -cy, -cz)))
    ob.location = loc
    ob.rotation_euler = (0, 0, math.radians(rot_z))
    ob.data.materials.append(make_animal_mat(name))
    return ob

def add_pencils(cup_loc, count=6, seed=42, has_scissors=False):
    random.seed(seed)
    palette = [
        (0.85, 0.22, 0.20), (0.22, 0.45, 0.82), (0.88, 0.72, 0.18),
        (0.28, 0.65, 0.38), (0.58, 0.32, 0.68), (0.92, 0.52, 0.22),
        (0.18, 0.72, 0.70), (0.15, 0.15, 0.18), (0.92, 0.42, 0.55)
    ]
    wood_mat = make_pla_simple('PencilWood', (0.86, 0.76, 0.60), rough=0.85)

    if has_scissors:
        # Craft scissors sitting naturally inside the cup (loops at rim level)
        scis_mat = make_pla_simple(f'ScisMat_{seed}', (0.18, 0.48, 0.85), rough=0.35)
        metal_mat = make_pla_simple(f'MetalMat_{seed}', (0.85, 0.86, 0.88), rough=0.20)
        
        # Scissors assembly centered at local z=0 at the bottom tip
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 3.8))
        blade = bpy.context.active_object
        blade.scale = (0.35, 0.12, 6.5)
        blade.data.materials.append(metal_mat)

        bpy.ops.mesh.primitive_torus_add(major_radius=0.72, minor_radius=0.18, location=(-0.58, 0.05, 7.8))
        l_loop = bpy.context.active_object
        l_loop.rotation_euler = (math.radians(12), math.radians(-10), 0)
        l_loop.data.materials.append(scis_mat)

        bpy.ops.mesh.primitive_torus_add(major_radius=0.72, minor_radius=0.18, location=(0.58, 0.05, 7.8))
        r_loop = bpy.context.active_object
        r_loop.rotation_euler = (math.radians(12), math.radians(10), 0)
        r_loop.data.materials.append(scis_mat)

        bpy.context.view_layer.objects.active = blade
        l_loop.select_set(True); r_loop.select_set(True); blade.select_set(True)
        bpy.ops.object.join()
        scis = blade
        scis.location = (cup_loc[0] - 0.2, cup_loc[1] + 0.3, cup_loc[2] + 0.6)
        scis.rotation_euler = (math.radians(-6), math.radians(4), math.radians(15))
        count = max(count - 1, 3)

    for i in range(count):
        col = palette[(i + seed) % len(palette)]
        plen = 10.5 + (i % 3) * 1.0

        # Cylinder with local origin at bottom (z=0 to z=plen)
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.34, depth=plen, location=(0, 0, 0))
        barrel = bpy.context.active_object
        barrel.data.transform(mathutils.Matrix.Translation((0, 0, plen / 2)))
        barrel.data.materials.append(make_pla_simple(f'PCol_{seed}_{i}', col, rough=0.38))

        bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.34, radius2=0, depth=1.1, location=(0, 0, plen + 0.55))
        tip = bpy.context.active_object
        tip.data.materials.append(wood_mat)

        bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=0.13, radius2=0, depth=0.4, location=(0, 0, plen + 1.1 - 0.2))
        lead = bpy.context.active_object
        lead.data.materials.append(make_pla_simple(f'Lead_{seed}_{i}', col, rough=0.3))

        bpy.context.view_layer.objects.active = barrel
        tip.select_set(True); lead.select_set(True); barrel.select_set(True)
        bpy.ops.object.join()

        ang = i * (2 * math.pi / count) + 0.3 + (random.random() * 0.12)
        r = 0.72 + (random.random() * 0.10)
        px = cup_loc[0] + r * math.cos(ang)
        py = cup_loc[1] + r * math.sin(ang)
        pz = cup_loc[2] + 0.6  # cup floor is at 0.4

        tilt_axis = mathutils.Vector((-math.sin(ang), math.cos(ang), 0))
        tilt_deg = 6.2 + (i % 2) * 1.8
        tilt_rot = mathutils.Matrix.Rotation(math.radians(tilt_deg), 4, tilt_axis)
        barrel.matrix_world = mathutils.Matrix.Translation((px, py, pz)) @ tilt_rot

def add_brushes(cup_loc, count=5, seed=77):
    """Adds beauty/makeup brushes (inspired by reference image 5b2bd70fd3c16013.webp)."""
    random.seed(seed)
    wood_handle = make_pla_simple('BrushWood', (0.75, 0.55, 0.35), rough=0.4)
    ferrule_mat = make_pla_simple('BrushFerrule', (0.15, 0.15, 0.16), rough=0.25)
    bristle_dark = make_pla_simple('BristleDark', (0.12, 0.10, 0.10), rough=0.9)
    bristle_tip = make_pla_simple('BristleTip', (0.88, 0.82, 0.72), rough=0.85)

    for i in range(count):
        hlen = 9.5 + (i % 2) * 1.5

        # Handle with origin at bottom (z=0 to hlen)
        bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.35, depth=hlen, location=(0, 0, 0))
        handle = bpy.context.active_object
        handle.data.transform(mathutils.Matrix.Translation((0, 0, hlen / 2)))
        handle.data.materials.append(wood_handle)

        # Black ferrule
        bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.42, depth=2.5, location=(0, 0, hlen + 1.25))
        ferrule = bpy.context.active_object
        ferrule.data.materials.append(ferrule_mat)

        # Fluffy bristle head
        br_rad = 0.85 if i == 0 else 0.55
        bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.42, radius2=br_rad, depth=3.0, location=(0, 0, hlen + 2.5 + 1.5))
        bristles = bpy.context.active_object
        bristles.data.materials.append(bristle_tip if i == 0 else bristle_dark)

        bpy.context.view_layer.objects.active = handle
        ferrule.select_set(True); bristles.select_set(True); handle.select_set(True)
        bpy.ops.object.join()

        ang = i * (2 * math.pi / count) + 0.4
        r = 0.65
        px = cup_loc[0] + r * math.cos(ang)
        py = cup_loc[1] + r * math.sin(ang)
        pz = cup_loc[2] + 0.6

        tilt_axis = mathutils.Vector((-math.sin(ang), math.cos(ang), 0))
        tilt_deg = 6.5 + (i % 2) * 2.0
        tilt_rot = mathutils.Matrix.Rotation(math.radians(tilt_deg), 4, tilt_axis)
        handle.matrix_world = mathutils.Matrix.Translation((px, py, pz)) @ tilt_rot

def add_camera(target=(0, 0, 4.5), dist=28.0, el=24.0, az=0.0, lens=52):
    cam_d = bpy.data.cameras.new('Cam')
    cam = bpy.data.objects.new('Cam', cam_d)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam_d.lens = lens

    tgt = mathutils.Vector(target)
    el_r, az_r = math.radians(el), math.radians(az)
    pos = tgt + mathutils.Vector((dist * math.cos(el_r) * math.sin(az_r),
                                  -dist * math.cos(el_r) * math.cos(az_r),
                                  dist * math.sin(el_r)))
    cam.location = pos
    cam.rotation_euler = (tgt - pos).to_track_quat('-Z', 'Y').to_euler()
    return cam

# =============================================================================
# BATCH 1: 8 INDIVIDUAL SINGLE CUP RENDERS (Transparent PNG for Card Grids)
# =============================================================================
all_animals = ['Cat', 'Bear', 'Bunny', 'Panda', 'Pig', 'Owl', 'Chick', 'Dino']

for idx, name in enumerate(all_animals):
    print(f"--- RENDERING SINGLE: {name} ---")
    scene = init_scene(samples=32, transparent=True)
    load_cup(name, (0, 0, 0), rot_z=8.0 if idx % 2 == 0 else -8.0)
    has_scis = (name in ('Owl', 'Cat'))
    add_pencils((0, 0, 0), count=6, seed=500 + idx, has_scissors=has_scis)
    add_camera(target=(0, 0, 4.5), dist=28.0, el=24.0, az=0.0, lens=52)
    scene.render.filepath = os.path.join(out_dir, f'single_{name.lower()}.png')
    bpy.ops.render.render(write_still=True)
    print(f"Saved single_{name.lower()}.png")

# =============================================================================
# BATCH 2: MAKEUP BRUSHES VARIANT (Owl Vanity Setup)
# =============================================================================
print("--- RENDERING MAKEUP BRUSHES: Owl ---")
scene = init_scene(samples=32, transparent=True)
load_cup('Owl', (0, 0, 0), rot_z=5.0)
add_brushes((0, 0, 0), count=5, seed=888)
add_camera(target=(0, 0, 4.5), dist=28.0, el=24.0, az=0.0, lens=52)
scene.render.filepath = os.path.join(out_dir, 'feature_owl_brushes.png')
bpy.ops.render.render(write_still=True)
print("Saved feature_owl_brushes.png")

# =============================================================================
# BATCH 3: LIFESTYLE TRIO (Cat, Panda, Dino) - Transparent RGBA with ground
# =============================================================================
print("--- RENDERING TRIO: Cat, Panda, Dino ---")
scene = init_scene(samples=40, transparent=True)
trio = [('Cat', -9.5, 0.0, 10), ('Panda', 0.0, -1.8, 0), ('Dino', 9.5, 0.0, -10)]
for idx, (name, x, y, rz) in enumerate(trio):
    loc = (x, y, 0)
    load_cup(name, loc, rz)
    add_pencils(loc, count=6, seed=200 + idx, has_scissors=(name == 'Cat'))

add_camera(target=(0, 0, 4.5), dist=38.0, el=25.0, az=0.0, lens=52)
scene.render.filepath = os.path.join(out_dir, 'trio_lifestyle_trans.png')
bpy.ops.render.render(write_still=True)
print("Saved trio_lifestyle_trans.png")

# =============================================================================
# BATCH 4: ALL 8 HERO LINEUP (Transparent for Cover & Overview)
# =============================================================================
print("--- RENDERING ALL 8 CUPS HERO ---")
scene = init_scene(samples=40, transparent=True)
cups_back = [('Bear', -16.5, 7.0, 10), ('Pig', -5.5, 7.5, 3), ('Owl', 5.5, 7.5, -3), ('Chick', 16.5, 7.0, -10)]
cups_front = [('Cat', -14.5, -3.5, 12), ('Panda', -5.0, -4.5, 3), ('Bunny', 5.0, -4.5, -3), ('Dino', 14.5, -3.5, -12)]

for idx, (name, x, y, rz) in enumerate(cups_front + cups_back):
    loc = (x, y, 0)
    load_cup(name, loc, rz)
    add_pencils(loc, count=5, seed=100 + idx, has_scissors=(name in ('Owl', 'Cat')))

add_camera(target=(0, 1.5, 4.5), dist=56.0, el=27.0, az=0.0, lens=50)
scene.render.filepath = os.path.join(out_dir, 'all_8_cups_trans.png')
bpy.ops.render.render(write_still=True)
print("Saved all_8_cups_trans.png")

print("ALL_BLENDER_RENDERS_FINISHED_SUCCESSFULLY")
'''

def run_blender_renders(stl_dir: Path, out_dir: Path, res: int = 1600) -> bool:
    out_dir.mkdir(parents=True, exist_ok=True)
    script_path = out_dir / "_run_render_v3.py"
    script_path.write_text(BLENDER_SCRIPT, encoding="utf-8")

    cmd = [
        str(BLENDER_EXE),
        "--background",
        "--factory-startup",
        "--python", str(script_path),
        "--",
        str(stl_dir),
        str(out_dir),
        str(res),
    ]
    t0 = time.time()
    print(f"Starting Blender Cycles renders at {res}x{res}...")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0
    print(f"Blender finished in {elapsed:.1f}s, returncode={proc.returncode}")
    if proc.returncode != 0:
        print("STDERR tail:\n", proc.stderr[-1000:])
        return False
    return True

if __name__ == "__main__":
    stl_path = Path(r"F:\WORKHORSE\workspace\etsy_listings\cute_animal_pencil_cups_stl_3mf_glb\files\STL")
    work_out = Path(r"F:\WORKHORSE\workspace\etsy_listings\cute_animal_pencil_cups_stl_3mf_glb\work_renders")
    run_blender_renders(stl_path, work_out, 1600)
