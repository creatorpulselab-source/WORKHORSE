"""Fix Axolotl 3D STL to have prominent, sculpted, 3-tiered external gill frills.
Eliminates any pig-like appearance by adding unmistakable axolotl branchial stalks with ruffles.
Voxel remeshes at 0.65mm in Blender 5.2 to ensure 100% watertight manifold solid geometry.
"""
import bpy
import bmesh
import math
import mathutils
import os
import sys

STL_IN = r"F:\WORKHORSE\workspace\etsy_listings\keychains_stl\files\STL\02_Chubby_Kawaii_Axolotl_Keychain.stl"
STL_OUT = r"F:\WORKHORSE\workspace\etsy_listings\keychains_stl\files\STL\02_Chubby_Kawaii_Axolotl_Keychain.stl"
PREVIEW_OUT = r"F:\WORKHORSE\workspace\etsy_listings\keychains_stl\work_renders\_axolotl_fixed_gills.png"

bpy.ops.wm.read_factory_settings(use_empty=True)

# 1. Import existing STL
bpy.ops.wm.stl_import(filepath=STL_IN)
body = bpy.context.active_object
body.name = "Axolotl_Body"

# Create a collection for gill parts
gill_objs = []

def make_gill_frill(start_pt, end_pt, frill_offsets, radius_start=3.2, radius_end=1.8):
    """Creates a tapered curved stalk with frill bulbs along its length."""
    parts = []
    
    # Main stalk using cylinder segments or skin/icospheres along path
    p0 = mathutils.Vector(start_pt)
    p1 = mathutils.Vector(end_pt)
    steps = 8
    stalk_spheres = []
    for s in range(steps + 1):
        t = s / steps
        # Add slight backward curve
        pt = p0.lerp(p1, t)
        curve_lift = math.sin(t * math.pi) * 2.5
        pt.z += curve_lift
        r = radius_start * (1.0 - t) + radius_end * t
        
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=r, location=pt)
        sp = bpy.context.active_object
        stalk_spheres.append(sp)
    
    # Frill ruffles / feathery lobes
    for t_frill, offset_vec, r_frill in frill_offsets:
        base_pt = p0.lerp(p1, t_frill)
        base_pt.z += math.sin(t_frill * math.pi) * 2.5
        f_pos = base_pt + mathutils.Vector(offset_vec)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=r_frill, location=f_pos)
        stalk_spheres.append(bpy.context.active_object)
        
    # Join stalk parts
    bpy.ops.object.select_all(action='DESELECT')
    for sp in stalk_spheres:
        sp.select_set(True)
    bpy.context.view_layer.objects.active = stalk_spheres[0]
    bpy.ops.object.join()
    return bpy.context.active_object

# Define 3 gills per side with frills
# Coordinates tuned for head around X: 18-22, Y: 4-14, Z: 24-38
gill_specs = [
    # Top gill: long, arches upward and back
    {
        "start": (18.0, 5.0, 36.0),
        "end": (38.0, -6.0, 48.0),
        "r_start": 3.8, "r_end": 2.2,
        "frills": [
            (0.35, (1.5, -3.0, 3.5), 2.8),
            (0.65, (1.8, -4.0, 4.0), 3.0),
            (0.90, (1.2, -3.5, 3.2), 2.6),
            (0.50, (2.0, 2.5, 2.5), 2.5),
        ]
    },
    # Middle gill: arches outward and back horizontally
    {
        "start": (20.0, 7.0, 29.0),
        "end": (41.0, -2.0, 32.0),
        "r_start": 3.6, "r_end": 2.0,
        "frills": [
            (0.35, (1.5, -3.5, 1.5), 2.8),
            (0.65, (2.0, -4.0, 2.0), 2.9),
            (0.88, (1.5, -3.0, 1.8), 2.5),
            (0.50, (1.0, 2.0, -2.0), 2.4),
        ]
    },
    # Bottom gill: arches outward and slightly down/back
    {
        "start": (19.0, 9.0, 22.0),
        "end": (36.0, 2.0, 20.0),
        "r_start": 3.4, "r_end": 1.8,
        "frills": [
            (0.35, (1.2, -3.0, -1.5), 2.6),
            (0.65, (1.6, -3.5, -1.8), 2.7),
            (0.85, (1.2, -2.5, -1.2), 2.4),
            (0.50, (1.0, 2.0, 1.5), 2.3),
        ]
    }
]

created_gills = []
for spec in gill_specs:
    # Right side gill (+X)
    g_right = make_gill_frill(spec["start"], spec["end"], spec["frills"], spec["r_start"], spec["r_end"])
    created_gills.append(g_right)
    
    # Left side gill (-X, mirrored)
    start_m = (-spec["start"][0], spec["start"][1], spec["start"][2])
    end_m = (-spec["end"][0], spec["end"][1], spec["end"][2])
    frills_m = [(t, (-off[0], off[1], off[2]), r) for t, off, r in spec["frills"]]
    g_left = make_gill_frill(start_m, end_m, frills_m, spec["r_start"], spec["r_end"])
    created_gills.append(g_left)

# Join all gills and body
bpy.ops.object.select_all(action='DESELECT')
body.select_set(True)
for g in created_gills:
    g.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()

ob = bpy.context.active_object

# Apply Voxel Remesh to weld all seams seamlessly into a single solid watertight volume
mod = ob.modifiers.new(name="VoxelRemesh", type='REMESH')
mod.mode = 'VOXEL'
mod.voxel_size = 0.65 # mm
bpy.ops.object.modifier_apply(modifier=mod.name)

# Apply gentle Laplacian smooth to polish voxel stepping
mod_sm = ob.modifiers.new(name="Smooth", type='SMOOTH')
mod_sm.factor = 0.40
mod_sm.iterations = 2
bpy.ops.object.modifier_apply(modifier=mod_sm.name)

# Flat ground cut at Z=0 for flawless bed contact
cut_box = bpy.ops.mesh.primitive_cube_add(size=300.0, location=(0, 0, -150.0))
cutter = bpy.context.active_object
mod_cut = ob.modifiers.new(name="GroundCut", type='BOOLEAN')
mod_cut.operation = 'DIFFERENCE'
mod_cut.object = cutter
mod_cut.solver = 'EXACT'
bpy.ops.object.modifier_apply(modifier=mod_cut.name)
bpy.data.objects.remove(cutter, do_unlink=True)
bpy.context.view_layer.objects.active = ob
ob.select_set(True)

# Clean up loose geometry in Edit mode
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=0.0002)
bpy.ops.mesh.delete_loose()
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode='OBJECT')

# Verify topology
bm = bmesh.new()
bm.from_mesh(ob.data)
n_non_manifold = len([e for e in bm.edges if not e.is_manifold])
n_boundary = len([e for e in bm.edges if e.is_boundary])
n_loose = len([v for v in bm.verts if not v.link_edges])
bm.free()

print(f"VERIFIED AXOLOTL TOPOLOGY: verts={len(ob.data.vertices)}, faces={len(ob.data.polygons)}, non_manifold={n_non_manifold}, boundary={n_boundary}")
assert n_non_manifold == 0, f"Error: {n_non_manifold} non-manifold edges!"
assert n_boundary == 0, f"Error: {n_boundary} boundary edges!"

# Export STL
if hasattr(bpy.ops.wm, 'stl_export'):
    bpy.ops.wm.stl_export(filepath=STL_OUT)
else:
    bpy.ops.export_mesh.stl(filepath=STL_OUT)
print(f"Exported watertight STL to {STL_OUT} ({os.path.getsize(STL_OUT) / (1024*1024):.2f} MB)")

# Render diagnostic preview
cam_d = bpy.data.cameras.new('Cam')
cam = bpy.data.objects.new('Cam', cam_d)
bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera = cam
cam.location = (0, -120, 75)
cam.rotation_euler = (math.radians(65), 0, 0)
bpy.context.scene.render.resolution_x = 800
bpy.context.scene.render.resolution_y = 800
bpy.context.scene.render.filepath = PREVIEW_OUT
bpy.ops.render.render(write_still=True)
print(f"Diagnostic preview saved to {PREVIEW_OUT}")
