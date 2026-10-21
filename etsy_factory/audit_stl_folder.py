import bpy
import bmesh
import sys
from pathlib import Path

folder = Path(sys.argv[-1])
print(f"--- AUDITING STLS IN: {folder} ---")
all_passed = True
for f in sorted(folder.glob("*.stl")):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.stl_import(filepath=str(f))
    obj = bpy.context.selected_objects[0]
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    non_man = sum(1 for e in bm.edges if not e.is_manifold)
    boundary = sum(1 for e in bm.edges if e.is_boundary)
    bm.free()
    ok = (non_man == 0 and boundary == 0)
    if not ok:
        all_passed = False
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {f.name}: faces={len(me.polygons)}, non_manifold={non_man}, boundary={boundary}")

print(f"--- AUDIT RESULT: {'ALL PASSED' if all_passed else 'FAILURES DETECTED'} ---")
