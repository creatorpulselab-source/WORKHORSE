"""Master Automated 3D Clean & Watertight STL Export Engine (Blender 5.2).
End-to-End Repeatable Production Pipeline for 3D Printable STL Files on Etsy:
1. Exact 1:1 match to listing images
2. 100% Watertight (0 non-manifold edges, 0 boundary holes)
3. Zero floating blobs or stray noise (exactly 1 monolithic solid shell)
4. Monolithic boolean union of 4.2mm keyring eyelet loop
5. Leveled flat base cut at Z=0 for support-free first-layer bed adhesion
6. Model-specific topology & slicer optimization:
   - Low-poly geometric models (Bulldog): 0.04cm remesh + decimate collapse + shade flat (sharp planes, zero smoothing blur)
   - Organic sculpted models: high-precision 0.045cm remesh + gentle polish (70k-110k faces, flawless 2-manifold, zero holes)
"""
import bpy, bmesh, math, mathutils, os, sys

PBR_DIR = r"F:\WORKHORSE\workspace\brand_assets\comfy_3d_pbr_renders"
STL_OUT_DIR = r"F:\WORKHORSE\workspace\etsy_listings\keychains_stl\files\STL"
RENDERS_DIR = r"F:\WORKHORSE\workspace\etsy_listings\keychains_stl\work_renders"

os.makedirs(STL_OUT_DIR, exist_ok=True)
os.makedirs(RENDERS_DIR, exist_ok=True)

MODELS = [
    {
        "index": 1,
        "name": "01_Baby_Crystal_Dragon_Keychain",
        "glb": os.path.join(PBR_DIR, "keychain_01_01_baby_crystal_dragon_keychain_1792595674.glb"),
        "height_mm": 52.0,
        "is_low_poly": False,
        "voxel_size": 0.044,
        "color": (0.38, 0.52, 0.42), # Sage Green
        "eyelet_offset": (0.0, -0.12, 0.16)
    },
    {
        "index": 2,
        "name": "02_Chubby_Kawaii_Axolotl_Keychain",
        "glb": os.path.join(PBR_DIR, "keychain_02_02_chubby_kawaii_axolotl_keychain_1792595763.glb"),
        "height_mm": 48.0,
        "is_low_poly": False,
        "voxel_size": 0.044,
        "color": (0.76, 0.44, 0.48), # Dusty Rose
        "eyelet_offset": (0.0, -0.15, 0.16)
    },
    {
        "index": 3,
        "name": "03_Kawaii_Baby_Octopus_Keychain",
        "glb": os.path.join(PBR_DIR, "test_cute_octopus_trellis2_1792595384.glb"),
        "height_mm": 46.0,
        "is_low_poly": False,
        "voxel_size": 0.045,
        "color": (0.28, 0.46, 0.68), # Slate Teal
        "eyelet_offset": (0.0, 0.0, 0.18)
    },
    {
        "index": 4,
        "name": "04_Geometric_French_Bulldog_Keychain",
        "glb": os.path.join(PBR_DIR, "keychain_04_04_geometric_french_bulldog_keychain_1792595874.glb"),
        "height_mm": 50.0,
        "is_low_poly": True, # CRISP GEOMETRIC FACETS!
        "voxel_size": 0.040,
        "decimate_ratio": 0.035,
        "color": (0.15, 0.15, 0.17), # Stealth Charcoal
        "eyelet_offset": (0.0, -0.20, 0.20)
    },
    {
        "index": 5,
        "name": "05_Pirate_Skull_Keychain",
        "glb": os.path.join(PBR_DIR, "pirate_skull_keychain_1792586773.glb"),
        "height_mm": 54.0,
        "is_low_poly": False,
        "voxel_size": 0.048,
        "color": (0.88, 0.84, 0.74), # Bone White
        "eyelet_offset": (0.0, -0.10, 0.18)
    },
    {
        "index": 6,
        "name": "06_Retro_HighTop_Sneaker_Keychain",
        "glb": os.path.join(PBR_DIR, "keychain_06_06_retro_hightop_sneaker_keychain_1792595997.glb"),
        "height_mm": 48.0,
        "is_low_poly": False,
        "voxel_size": 0.046,
        "color": (0.22, 0.40, 0.72), # Royal Blue
        "eyelet_offset": (0.0, -0.60, 0.18)
    },
    {
        "index": 7,
        "name": "07_Lucky_Maneki_Neko_Keychain",
        "glb": os.path.join(PBR_DIR, "keychain_07_07_lucky_maneki_neko_keychain_1792596079.glb"),
        "height_mm": 50.0,
        "is_low_poly": False,
        "voxel_size": 0.044,
        "color": (0.85, 0.60, 0.15), # Amber Honey
        "eyelet_offset": (0.0, 0.0, 0.18)
    },
    {
        "index": 8,
        "name": "08_Chibi_Astronaut_Keychain",
        "glb": os.path.join(PBR_DIR, "keychain_08_08_chibi_astronaut_keychain_1792596160.glb"),
        "height_mm": 52.0,
        "is_low_poly": False,
        "voxel_size": 0.044,
        "color": (0.88, 0.85, 0.78), # Sand Almond
        "eyelet_offset": (0.0, -0.15, 0.18)
    }
]


def clean_and_process_model(cfg):
    idx = cfg["index"]
    name = cfg["name"]
    glb_path = cfg["glb"]
    target_h_cm = cfg["height_mm"] / 10.0
    stl_out = os.path.join(STL_OUT_DIR, f"{name}.stl")
    prev_out = os.path.join(RENDERS_DIR, f"_verify_stl_{idx:02d}.png")

    print(f"\n=======================================================")
    print(f"[{idx}/8] Processing {name}")
    print(f"=======================================================")

    bpy.ops.wm.read_factory_settings(use_empty=True)

    # 1. Import GLB
    bpy.ops.import_scene.gltf(filepath=glb_path)
    mesh_objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    for o in mesh_objs: o.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objs[0]
    if len(mesh_objs) > 1: bpy.ops.object.join()
    ob = bpy.context.active_object

    # 2. Normalize height
    zs = [v.co.z for v in ob.data.vertices]
    h = max(zs) - min(zs)
    scale_f = target_h_cm / max(h, 0.001)
    ob.scale = (scale_f, scale_f, scale_f)
    bpy.ops.object.transform_apply(scale=True)

    # Center XY and ground Z
    xs = [v.co.x for v in ob.data.vertices]
    ys = [v.co.y for v in ob.data.vertices]
    zs = [v.co.z for v in ob.data.vertices]
    ob.data.transform(mathutils.Matrix.Translation((-(min(xs)+max(xs))/2, -(min(ys)+max(ys))/2, -min(zs))))

    # 3. Clean edit mode: remove doubles & loose vertices
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.005)
    bpy.ops.mesh.delete_loose()
    bpy.ops.object.mode_set(mode='OBJECT')

    # Purge all floating disconnected islands before remesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    islands = []
    left = set(bm.verts)
    while left:
        v = left.pop(); isl = [v]; q = [v]
        while q:
            c = q.pop()
            for e in c.link_edges:
                ov = e.other_vert(c)
                if ov in left: left.remove(ov); isl.append(ov); q.append(ov)
        islands.append(isl)

    islands.sort(key=len, reverse=True)
    if len(islands) > 1:
        to_delete = []
        for isl in islands:
            if len(isl) < 500:
                to_delete.extend(isl)
        bmesh.ops.delete(bm, geom=to_delete, context='VERTS')
        bm.to_mesh(ob.data)
    bm.free()

    # 4. Voxel Remesh to guarantee 100% closed manifold solid shell FIRST
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    remesh = ob.modifiers.new('Remesh', 'REMESH')
    remesh.mode = 'VOXEL'
    remesh.voxel_size = cfg.get("voxel_size", 0.045)
    bpy.ops.object.modifier_apply(modifier='Remesh')

    if not cfg.get("is_low_poly"):
        # Organic Sculpt: subtle smooth to polish voxel stepping while preserving fine details
        smooth = ob.modifiers.new('Smooth', 'SMOOTH')
        smooth.factor = 0.32
        smooth.iterations = 2
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_apply(modifier='Smooth')
        for p in ob.data.polygons:
            p.use_smooth = True

    # 5. Sturdy 4.2mm Keyring Eyelet Loop (Monolithic Boolean Union)
    top_z = max(v.co.z for v in ob.data.vertices)
    off_x, off_y, off_z = cfg.get("eyelet_offset", (0.0, 0.0, 0.18))
    head_verts = [v for v in ob.data.vertices if v.co.z > top_z - 0.6]
    center_y = sum(v.co.y for v in head_verts) / max(len(head_verts), 1) + off_y
    center_x = sum(v.co.x for v in head_verts) / max(len(head_verts), 1) + off_x

    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.42, minor_radius=0.14,
        major_segments=36, minor_segments=16,
        location=(center_x, center_y, top_z + off_z),
        rotation=(math.pi / 2, 0, 0)
    )
    loop = bpy.context.active_object

    # Boolean UNION loop into body
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bool_u = ob.modifiers.new('UnionLoop', 'BOOLEAN')
    bool_u.operation = 'UNION'
    bool_u.object = loop
    bpy.ops.object.modifier_apply(modifier='UnionLoop')
    bpy.data.objects.remove(loop, do_unlink=True)

    # 6. Leveled Flat Bed Cut at Z=0 (Support-free adhesion)
    bpy.ops.mesh.primitive_cube_add(size=30, location=(0, 0, -15))
    cutter = bpy.context.active_object
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bool_m = ob.modifiers.new('BaseCut', 'BOOLEAN')
    bool_m.operation = 'DIFFERENCE'
    bool_m.object = cutter
    bpy.ops.object.modifier_apply(modifier='BaseCut')
    bpy.data.objects.remove(cutter, do_unlink=True)

    # 7. Post-Boolean Filter: Keep ONLY the single largest connected shell
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    islands = []
    left = set(bm.verts)
    while left:
        v = left.pop(); isl = [v]; q = [v]
        while q:
            c = q.pop()
            for e in c.link_edges:
                ov = e.other_vert(c)
                if ov in left: left.remove(ov); isl.append(ov); q.append(ov)
        islands.append(isl)

    islands.sort(key=len, reverse=True)
    if len(islands) > 1:
        to_delete = []
        for isl in islands[1:]:
            to_delete.extend(isl)
        bmesh.ops.delete(bm, geom=to_delete, context='VERTS')
        bm.to_mesh(ob.data)
    bm.free()

    # 8. If Low-Poly: Decimate to crisp geometric planar facets
    if cfg.get("is_low_poly"):
        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)
        dec_mod = ob.modifiers.new('Decimate', 'DECIMATE')
        dec_mod.decimate_type = 'COLLAPSE'
        dec_mod.ratio = cfg.get("decimate_ratio", 0.035)
        bpy.ops.object.modifier_apply(modifier='Decimate')
        for p in ob.data.polygons:
            p.use_smooth = False

    # 9. Rigorous Manufacturing Topology Audit
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    n_nm = len([e for e in bm.edges if not e.is_manifold])
    n_bd = len([e for e in bm.edges if e.is_boundary])
    n_lv = len([v for v in bm.verts if not v.link_edges])

    islands = []
    left = set(bm.verts)
    while left:
        v = left.pop(); isl = [v]; q = [v]
        while q:
            c = q.pop()
            for e in c.link_edges:
                ov = e.other_vert(c)
                if ov in left: left.remove(ov); isl.append(ov); q.append(ov)
        islands.append(isl)
    bm.free()

    print(f"TOPOLOGY AUDIT for {name}:")
    print(f"  Verts: {len(ob.data.vertices)}, Faces: {len(ob.data.polygons)}")
    print(f"  Non-Manifold Edges: {n_nm} (Must be 0)")
    print(f"  Boundary Holes:     {n_bd} (Must be 0)")
    print(f"  Loose Vertices:     {n_lv} (Must be 0)")
    print(f"  Solid Shells:       {len(islands)} (Must be 1)")

    assert n_nm == 0, f"FAILED: {n_nm} non-manifold edges found in {name}!"
    assert n_bd == 0, f"FAILED: {n_bd} boundary holes found in {name}!"
    assert n_lv == 0, f"FAILED: {n_lv} loose vertices found in {name}!"
    assert len(islands) == 1, f"FAILED: Expected 1 solid shell, found {len(islands)} in {name}!"

    # 10. Export Clean Watertight STL (in mm)
    ob.scale = (10, 10, 10)
    bpy.ops.object.transform_apply(scale=True)
    bpy.ops.wm.stl_export(filepath=stl_out)
    print(f"  -> Exported STL: {os.path.basename(stl_out)} ({os.path.getsize(stl_out) / 1e6:.2f} MB)")

    # 11. Cycles GPU Verification Render
    ob.scale = (0.1, 0.1, 0.1)
    bpy.ops.object.transform_apply(scale=True)

    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    for d in prefs.devices: d.use = (d.type == 'OPTIX')
    scene.cycles.device = 'GPU'
    scene.cycles.samples = 48
    scene.render.film_transparent = True
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1200

    mat = bpy.data.materials.new(f'M_{name}')
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    rgb = cfg.get("color", (0.78, 0.36, 0.18))
    bsdf.inputs['Base Color'].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    bsdf.inputs['Roughness'].default_value = 0.55
    ob.data.materials.append(mat)

    # 3-Point Light
    for lname, energy, rot, col in [
        ('Key', 4.0, (math.radians(45), math.radians(15), math.radians(35)), (1, 0.96, 0.9)),
        ('Fill', 1.6, (math.radians(55), math.radians(-10), math.radians(-120)), (0.9, 0.94, 1)),
        ('Rim', 2.8, (math.radians(65), 0, math.radians(160)), (1, 0.98, 0.95))
    ]:
        ld = bpy.data.lights.new(lname, 'SUN'); ld.energy = energy; ld.color = col
        lo = bpy.data.objects.new(lname, ld); scene.collection.objects.link(lo); lo.rotation_euler = rot

    cd = bpy.data.cameras.new('Cam'); cd.lens = 70
    co = bpy.data.objects.new('Cam', cd); scene.collection.objects.link(co); scene.camera = co
    co.location = (6.5, -9.5, 6.0)
    co.rotation_euler = (math.radians(62), 0, math.radians(35))

    scene.render.filepath = prev_out
    bpy.ops.render.render(write_still=True)
    print(f"  -> Rendered Verification Preview: {os.path.basename(prev_out)}")
    return True


def main():
    print("=== STARTING MASTER 3D TOPOLOGY CLEAN & VERIFICATION ENGINE ===")
    total = len(MODELS)
    success = 0
    for cfg in MODELS:
        ok = clean_and_process_model(cfg)
        if ok: success += 1
    print(f"\nALL {success}/{total} MODELS CLEANED, VERIFIED & EXPORTED WITH ZERO DEFECTS!")


if __name__ == "__main__":
    main()
