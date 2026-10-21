import subprocess
from pathlib import Path

p = Path(r"F:\WORKHORSE\workspace\etsy_listings\keychains_stl\files\STL\07_Lucky_Medallion_Charm.stl")
blender_script = f"""
import bpy
bpy.ops.wm.stl_import(filepath=r"{p}")
ob = bpy.context.active_object
mod = ob.modifiers.new('Dec', 'DECIMATE')
mod.ratio = 0.04
bpy.ops.object.modifier_apply(modifier='Dec')
bpy.ops.wm.stl_export(filepath=r"{p}")
print("DECIMATE_DONE")
"""

tmp = Path(r"F:\WORKHORSE\workspace\etsy_listings\keychains_stl\work_renders\_decimate.py")
tmp.write_text(blender_script, encoding="utf-8")
res = subprocess.run([
    r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe",
    "--background",
    "--python",
    str(tmp)
], capture_output=True, text=True)

print("Decimation result:")
for line in res.stdout.splitlines():
    if "DECIMATE" in line or "Saved" in line:
        print(" ", line)
print(f"New size: {p.stat().st_size / 1e6:.2f} MB")
