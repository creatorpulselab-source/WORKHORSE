import bpy
import bmesh
from pathlib import Path

stl_path = Path(r"F:\WORKHORSE\workspace\etsy_listings\can_holders_stl\files\STL\01_QuadGrip_4-Cup_Drink_Caddy.stl")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.stl_import(filepath=str(stl_path))
obj = bpy.context.selected_objects[0]
bpy.context.view_layer.objects.active = obj

print(f"Original: {len(obj.data.polygons)} faces")

# Check interior faces
bm = bmesh.new()
bm.from_mesh(obj.data)
non_man_edges = [e for e in bm.edges if not e.is_manifold]
print(f"Non-manifold edges: {len(non_man_edges)}")

# Let's see: what if we do Remesh VOXEL at 0.6mm (0.06 in Blender units if scaled)
# Wait, what are the dimensions of obj?
print(f"Dimensions: {obj.dimensions}")

# If dimensions are ~189 x 189 x 165 mm:
# In Blender, 189 means 189 meters unless unit is mm!
# Let's check obj.dimensions
dim = obj.dimensions
print(f"Dimensions: x={dim.x:.2f}, y={dim.y:.2f}, z={dim.z:.2f}")

bm.free()
