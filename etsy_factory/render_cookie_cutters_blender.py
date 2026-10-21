"""High-End Blender Cycles OptiX GPU Renderer for Christmas Cookie Cutters.
Renders all 10 designs with authentic festive Matte PLA filament shaders:
- GPU-accelerated Cycles OptiX on RTX (device = 'GPU')
- Festive holiday palette: Crimson Red, Pine Green, Warm Gold, Frosted Snow White, Festive Teal
- Subtle FDM micro layer-line texture
- Transparent PNG exports for zero-floating composition in build_3d_listing_deck.py
"""
import bpy, sys, math, mathutils, os
from pathlib import Path

LISTING_DIR = Path(r"F:\WORKHORSE\workspace\etsy_listings\christmas_cookie_cutters_stl")
STL_DIR = LISTING_DIR / "files" / "STL"
OUT_DIR = LISTING_DIR / "work_renders"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RES = 1600

# Festive Holiday Matte PLA Palette
PALETTE = [
    (0.80, 0.12, 0.16),  # 01 Tree: Vibrant Crimson Holiday Red
    (0.88, 0.68, 0.15),  # 02 Star: Warm Golden Star Yellow
    (0.92, 0.94, 0.96),  # 03 Snowflake: Frosted Glacier White
    (0.68, 0.42, 0.22),  # 04 Gingerbread: Rich Warm Gingerbread Brown
    (0.82, 0.14, 0.18),  # 05 Candy Cane: Peppermint Red
    (0.12, 0.46, 0.24),  # 06 Ornament: Forest Pine Green
    (0.18, 0.52, 0.56),  # 07 Mitten: Winter Frost Teal
    (0.80, 0.12, 0.16),  # 08 Stocking: Holiday Red
    (0.86, 0.66, 0.18),  # 09 Bell: Polished Brass Gold
    (0.92, 0.94, 0.96),  # 10 Snowman: Pure Snow White
]

ITEMS = [
    ("single_01", "01_Christmas_Tree_Cutter_80mm.stl", "01_Christmas_Tree_Press_Plate_80mm.stl"),
    ("single_02", "02_Star_Cutter_80mm.stl", "02_Star_Press_Plate_80mm.stl"),
    ("single_03", "03_Snowflake_Cutter_80mm.stl", "03_Snowflake_Press_Plate_80mm.stl"),
    ("single_04", "04_Gingerbread_Man_Cutter_80mm.stl", "04_Gingerbread_Man_Press_Plate_80mm.stl"),
    ("single_05", "05_Candy_Cane_Cutter_80mm.stl", "05_Candy_Cane_Press_Plate_80mm.stl"),
    ("single_06", "06_Bauble_Ornament_Cutter_80mm.stl", "06_Bauble_Ornament_Press_Plate_80mm.stl"),
    ("single_07", "07_Mitten_Cutter_80mm.stl", "07_Mitten_Press_Plate_80mm.stl"),
    ("single_08", "08_Stocking_Cutter_80mm.stl", "08_Stocking_Press_Plate_80mm.stl"),
    ("single_09", "09_Jingle_Bell_Cutter_80mm.stl", "09_Jingle_Bell_Press_Plate_80mm.stl"),
    ("single_10", "10_Snowman_Cutter_80mm.stl", "10_Snowman_Press_Plate_80mm.stl"),
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
    if 'Coat Weight' in b.inputs: b.inputs['Coat Weight'].default_value = 0.06
    elif 'Clearcoat' in b.inputs: b.inputs['Clearcoat'].default_value = 0.06

    # Micro layer lines
    tex = nt.nodes.new('ShaderNodeTexWave')
    tex.wave_type = 'BANDS'
    tex.bands_direction = 'Z'
    tex.inputs['Scale'].default_value = 140.0
    tex.inputs['Distortion'].default_value = 0.08
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.04
    nt.links.new(tex.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m

def setup_cycles(scene):
    scene.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    for d in prefs.devices:
        d.use = (d.type == 'OPTIX')
    scene.cycles.device = 'GPU'
    scene.cycles.samples = 36
    scene.cycles.use_denoising = True
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.resolution_x = RES
    scene.render.resolution_y = RES

def setup_lighting(scene):
    if scene.world is None:
        scene.world = bpy.data.worlds.new('World')
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get('Background')
    if bg is None:
        bg = scene.world.node_tree.nodes.new('ShaderNodeBackground')
    bg.inputs['Color'].default_value = (0.96, 0.95, 0.94, 1.0)
    bg.inputs['Strength'].default_value = 0.9

    k_data = bpy.data.lights.new('KeySun', 'SUN')
    k_data.energy = 3.6
    k_data.angle = math.radians(12)
    k_data.color = (1.0, 0.96, 0.90)
    k_ob = bpy.data.objects.new('KeySun', k_data)
    scene.collection.objects.link(k_ob)
    k_ob.rotation_euler = (math.radians(45), math.radians(15), math.radians(35))

    f_data = bpy.data.lights.new('FillSun', 'SUN')
    f_data.energy = 1.4
    f_data.angle = math.radians(30)
    f_data.color = (0.90, 0.94, 1.0)
    f_ob = bpy.data.objects.new('FillSun', f_data)
    scene.collection.objects.link(f_ob)
    f_ob.rotation_euler = (math.radians(55), math.radians(-10), math.radians(-120))

    r_data = bpy.data.lights.new('RimSun', 'SUN')
    r_data.energy = 2.4
    r_data.angle = math.radians(15)
    r_data.color = (1.0, 0.98, 0.92)
    r_ob = bpy.data.objects.new('RimSun', r_data)
    scene.collection.objects.link(r_ob)
    r_ob.rotation_euler = (math.radians(-35), math.radians(20), math.radians(150))

def render_single_item(out_name, cutter_stl, press_stl, color, idx):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    setup_cycles(scene)
    setup_lighting(scene)

    mat_cutter = make_matte_pla_material(f"cutter_{idx}", color)
    press_color = (0.95, 0.95, 0.96) if color[0] < 0.8 else (0.15, 0.45, 0.25)
    mat_press = make_matte_pla_material(f"press_{idx}", press_color)

    # 1. Import Cutter
    p_cutter = STL_DIR / cutter_stl
    bpy.ops.wm.stl_import(filepath=str(p_cutter))
    ob_cutter = bpy.context.active_object
    ob_cutter.data.materials.append(mat_cutter)

    # Center cutter
    zs = [v.co.z for v in ob_cutter.data.vertices]
    xs = [v.co.x for v in ob_cutter.data.vertices]
    ys = [v.co.y for v in ob_cutter.data.vertices]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    cz = min(zs)
    ob_cutter.data.transform(mathutils.Matrix.Translation((-cx, -cy, -cz)))

    # 2. Import Press Plate
    p_press = STL_DIR / press_stl
    if p_press.exists():
        bpy.ops.wm.stl_import(filepath=str(p_press))
        ob_press = bpy.context.active_object
        ob_press.data.materials.append(mat_press)
        p_zs = [v.co.z for v in ob_press.data.vertices]
        p_xs = [v.co.x for v in ob_press.data.vertices]
        p_ys = [v.co.y for v in ob_press.data.vertices]
        p_cx = (min(p_xs) + max(p_xs)) / 2
        p_cy = (min(p_ys) + max(p_ys)) / 2
        p_cz = min(p_zs)
        ob_press.data.transform(mathutils.Matrix.Translation((-p_cx, -p_cy, -p_cz)))

        # Position press plate slightly to the right & back, tilted up slightly
        cutter_w = max(xs) - min(xs)
        ob_press.location = (cutter_w * 0.65, cutter_w * 0.15, 0)
        ob_press.rotation_euler = (math.radians(-8), math.radians(6), math.radians(-15))

    # Overall bounding box
    all_verts = []
    for o in scene.objects:
        if o.type == 'MESH':
            all_verts.extend([o.matrix_world @ v.co for v in o.data.vertices])

    xs_all = [v.x for v in all_verts]
    ys_all = [v.y for v in all_verts]
    zs_all = [v.z for v in all_verts]
    center = mathutils.Vector(((min(xs_all)+max(xs_all))/2, (min(ys_all)+max(ys_all))/2, (min(zs_all)+max(zs_all))/2))
    dim_max = max(max(xs_all)-min(xs_all), max(ys_all)-min(ys_all), max(zs_all)-min(zs_all))

    # Camera setup (Hero 3/4 isometric perspective)
    cam_data = bpy.data.cameras.new('Camera')
    cam_data.lens = 72
    cam_ob = bpy.data.objects.new('Camera', cam_data)
    scene.collection.objects.link(cam_ob)
    scene.camera = cam_ob

    elev = math.radians(48)
    azim = math.radians(-42)
    dist = dim_max * 2.25

    cam_ob.location = (
        center.x + dist * math.cos(elev) * math.sin(azim),
        center.y - dist * math.cos(elev) * math.cos(azim),
        center.z + dist * math.sin(elev)
    )

    direction = center - cam_ob.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_ob.rotation_euler = rot_quat.to_euler()

    dest = OUT_DIR / f"{out_name}.png"
    scene.render.filepath = str(dest)
    bpy.ops.render.render(write_still=True)
    print(f"  [OK] Rendered {dest.name}")

def render_all():
    print(f"Rendering all {len(ITEMS)} Christmas Cookie Cutter designs...")
    for idx, (out_name, cutter_stl, press_stl) in enumerate(ITEMS):
        color = PALETTE[idx % len(PALETTE)]
        render_single_item(out_name, cutter_stl, press_stl, color, idx)

    # 11. Render Hero Cluster
    print("Rendering Hero Cluster...")
    render_hero_cluster()

def render_hero_cluster():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    setup_cycles(scene)
    setup_lighting(scene)

    # Place 5 showcase cutters in a dynamic semi-circle
    showcase = [0, 1, 2, 3, 5]  # Tree, Star, Snowflake, Gingerbread, Ornament
    offsets = [(-80, -20), (-25, 40), (40, 25), (85, -20), (0, -60)]
    rots = [-15, 8, -6, 18, 0]

    for i, s_idx in enumerate(showcase):
        cutter_stl = ITEMS[s_idx][1]
        color = PALETTE[s_idx % len(PALETTE)]
        mat = make_matte_pla_material(f"cluster_{i}", color)
        p = STL_DIR / cutter_stl
        bpy.ops.wm.stl_import(filepath=str(p))
        ob = bpy.context.active_object
        ob.data.materials.append(mat)
        
        # Center
        zs = [v.co.z for v in ob.data.vertices]
        xs = [v.co.x for v in ob.data.vertices]
        ys = [v.co.y for v in ob.data.vertices]
        ob.data.transform(mathutils.Matrix.Translation((-(min(xs)+max(xs))/2, -(min(ys)+max(ys))/2, -min(zs))))
        ox, oy = offsets[i]
        ob.location = (ox, oy, 0)
        ob.rotation_euler = (0, 0, math.radians(rots[i]))

    all_verts = []
    for o in scene.objects:
        if o.type == 'MESH':
            all_verts.extend([o.matrix_world @ v.co for v in o.data.vertices])

    xs_all = [v.x for v in all_verts]
    ys_all = [v.y for v in all_verts]
    zs_all = [v.z for v in all_verts]
    center = mathutils.Vector(((min(xs_all)+max(xs_all))/2, (min(ys_all)+max(ys_all))/2, (min(zs_all)+max(zs_all))/2))
    dim_max = max(max(xs_all)-min(xs_all), max(ys_all)-min(ys_all), max(zs_all)-min(zs_all))

    cam_data = bpy.data.cameras.new('Camera')
    cam_data.lens = 65
    cam_ob = bpy.data.objects.new('Camera', cam_data)
    scene.collection.objects.link(cam_ob)
    scene.camera = cam_ob

    elev = math.radians(52)
    azim = math.radians(-38)
    dist = dim_max * 2.1

    cam_ob.location = (
        center.x + dist * math.cos(elev) * math.sin(azim),
        center.y - dist * math.cos(elev) * math.cos(azim),
        center.z + dist * math.sin(elev)
    )

    direction = center - cam_ob.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_ob.rotation_euler = rot_quat.to_euler()

    dest = OUT_DIR / "cluster_hero.png"
    scene.render.filepath = str(dest)
    bpy.ops.render.render(write_still=True)
    print(f"  [OK] Rendered {dest.name}")

if __name__ == '__main__':
    render_all()
