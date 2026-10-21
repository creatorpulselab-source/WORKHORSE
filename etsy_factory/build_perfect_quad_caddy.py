import bpy
import bmesh
import math
from pathlib import Path

bpy.ops.wm.read_factory_settings(use_empty=True)

# Parameters from shapes_can_holders_original.py
r_well = 41.0
r_out = 44.5
pitch = 94.0
well_h = 68.0
FLOOR = 4.0
DRAIN_R = 3.5

# 1. Base plate
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, FLOOR / 2.0))
base_plate = bpy.context.active_object
base_plate.scale = (pitch + r_out * 2 + 6.0, pitch + r_out * 2 + 6.0, FLOOR)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# 2. Four outer cylinder wells
offsets = [(-pitch / 2, -pitch / 2), (pitch / 2, -pitch / 2),
           (-pitch / 2, pitch / 2), (pitch / 2, pitch / 2)]

caddy = base_plate
bpy.context.view_layer.objects.active = caddy

for i, (ox, oy) in enumerate(offsets):
    bpy.ops.mesh.primitive_cylinder_add(radius=r_out, depth=well_h, vertices=64, location=(ox, oy, well_h / 2.0))
    cyl = bpy.context.active_object
    bpy.context.view_layer.objects.active = caddy
    mod = caddy.modifiers.new(name=f"Union_Well_{i}", type='BOOLEAN')
    mod.operation = 'UNION'
    mod.solver = 'EXACT'
    mod.object = cyl
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cyl, do_unlink=True)

# 3. Handle
handle_h = 165.0
handle_w = pitch * 1.15
handle_thick = 14.0

bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, handle_h / 2.0))
handle = bpy.context.active_object
handle.scale = (handle_w, handle_thick, handle_h)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Grip cutout
bpy.ops.mesh.primitive_cylinder_add(radius=16.0, depth=handle_thick * 3, vertices=48, 
                                    location=(0, 0, handle_h - 26.0),
                                    rotation=(math.pi / 2, 0, 0))
grip = bpy.context.active_object
bpy.context.view_layer.objects.active = handle
mod = handle.modifiers.new("Cut_Grip", 'BOOLEAN')
mod.operation = 'DIFFERENCE'
mod.solver = 'EXACT'
mod.object = grip
bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.data.objects.remove(grip, do_unlink=True)

# Diamond cutout
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, handle_h / 2.0 - 15.0), rotation=(0, math.pi / 4, 0))
diamond = bpy.context.active_object
diamond.scale = (44.0, handle_thick * 3, 44.0)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.context.view_layer.objects.active = handle
mod = handle.modifiers.new("Cut_Diamond", 'BOOLEAN')
mod.operation = 'DIFFERENCE'
mod.solver = 'EXACT'
mod.object = diamond
bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.data.objects.remove(diamond, do_unlink=True)

# Union handle to caddy
bpy.context.view_layer.objects.active = caddy
mod = caddy.modifiers.new("Union_Handle", 'BOOLEAN')
mod.operation = 'UNION'
mod.solver = 'EXACT'
mod.object = handle
bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.data.objects.remove(handle, do_unlink=True)

# 4. Hollow out 4 wells
for i, (ox, oy) in enumerate(offsets):
    bpy.ops.mesh.primitive_cylinder_add(radius=r_well, depth=well_h * 2, vertices=64, 
                                        location=(ox, oy, FLOOR + well_h))
    cav = bpy.context.active_object
    bpy.context.view_layer.objects.active = caddy
    mod = caddy.modifiers.new(f"Cut_Cavity_{i}", 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cav
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cav, do_unlink=True)

    # Drain hole
    bpy.ops.mesh.primitive_cylinder_add(radius=DRAIN_R, depth=FLOOR * 4, vertices=32,
                                        location=(ox, oy, 0))
    dr = bpy.context.active_object
    bpy.context.view_layer.objects.active = caddy
    mod = caddy.modifiers.new(f"Cut_Drain_{i}", 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = dr
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(dr, do_unlink=True)

# Audit topology
bm = bmesh.new()
bm.from_mesh(caddy.data)
non_man = sum(1 for e in bm.edges if not e.is_manifold)
boundary = sum(1 for e in bm.edges if e.is_boundary)
bm.free()

print(f"BLENDER GENERATED CAD CADDY: faces={len(caddy.data.polygons)}, non_manifold={non_man}, boundary={boundary}, dims={caddy.dimensions}")

# Export to clean STL
out_stl = Path(r"F:\WORKHORSE\workspace\etsy_listings\can_holders_stl\files\STL\01_QuadGrip_4-Cup_Drink_Caddy.stl")
bpy.ops.wm.stl_export(filepath=str(out_stl))
print(f"Saved: {out_stl}")
