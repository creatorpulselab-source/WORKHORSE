"""
WORKHORSE Blender 5.2 + MCP Studio Bridge
==========================================
Integrates Blender 5.2.2 LTS and MCP for Blender (localhost:9876) directly into
the WORKHORSE pipeline for:
  1. Post-processing ComfyUI Trellis 2 / Pixal3D .GLB meshes (UV/PBR material
     refinement, normal smoothing, scale normalization).
  2. Converting 3D meshes into watertight, flat-bottomed, manifold .STL files
     ready for resin/FDM 3D printing (Cura, Bambu Studio, PrusaSlicer, Chitubox).
  3. Converting ComfyUI layered .SVG vector files into 3D extruded relief .STL
     and .GLB models.
  4. Rendering photorealistic 3D studio beauty shots, matte resin clay print
     previews, and wireframe topology turntables via Blender 5.2 EEVEE / Cycles.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional, Union

BLENDER_EXE = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
DEFAULT_MCP_HOST = "localhost"
DEFAULT_MCP_PORT = 9876


class BlenderBridge:
    """High-level WORKHORSE bridge to Blender 5.2 via MCP socket + CLI fallback."""

    def __init__(self, host: str = DEFAULT_MCP_HOST, port: int = DEFAULT_MCP_PORT) -> None:
        self.host = host
        self.port = port
        self.blender_exe = BLENDER_EXE

    def check_connection(self) -> Dict[str, Any]:
        """Checks both the live Blender MCP socket server and local Blender 5.2 binary."""
        mcp_online = False
        handshake_info = {}
        try:
            from blender_mcp.addon_manager import handshake_addon
            from blender_mcp.server import BlenderConnection

            conn = BlenderConnection(self.host, self.port)
            if conn.connect():
                hs = handshake_addon(conn)
                mcp_online = True
                handshake_info = {
                    "up_to_date": hs.up_to_date,
                    "protocol_version": hs.protocol_version,
                    "addon_version": hs.addon_version,
                    "blender_version": hs.blender_version,
                    "capabilities": hs.capabilities,
                }
                conn.disconnect()
        except Exception as e:
            handshake_info = {"error": str(e)}

        return {
            "mcp_online": mcp_online,
            "host": self.host,
            "port": self.port,
            "blender_exe_exists": self.blender_exe.exists(),
            "blender_exe": str(self.blender_exe),
            "handshake": handshake_info,
        }

    def execute_mcp_code(self, code: str, timeout: float = 180.0) -> Dict[str, Any]:
        """Executes a Python `bpy` script inside the live Blender 5.2 MCP session.
        Falls back to headless Blender 5.2 CLI if the MCP socket is not active."""
        try:
            from blender_mcp.server import BlenderConnection

            conn = BlenderConnection(self.host, self.port)
            if conn.connect():
                try:
                    res = conn.send_command("execute_code", {"code": code})
                    return {"success": True, "mode": "mcp_socket", "result": res}
                finally:
                    conn.disconnect()
        except Exception as mcp_err:
            if not self.blender_exe.exists():
                return {"success": False, "error": f"MCP failed ({mcp_err}) and Blender exe not found."}

        # Fallback: Headless Blender 5.2 execution
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tf:
            tf.write(code)
            script_path = tf.name

        try:
            proc = subprocess.run(
                [str(self.blender_exe), "--background", "--python", script_path],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "success": proc.returncode == 0,
                "mode": "headless_cli",
                "stdout": proc.stdout[-2000:],
                "stderr": proc.stderr[-1000:],
            }
        finally:
            try:
                os.unlink(script_path)
            except OSError:
                pass

    def process_glb_to_printable_stl_and_renders(
        self,
        input_glb_path: Union[str, Path],
        output_glb_path: Union[str, Path],
        output_stl_path: Union[str, Path],
        preview_dir: Optional[Union[str, Path]] = None,
        asset_prefix: str = "model",
        add_pedestal_base: bool = True,
        target_height_mm: float = 100.0,
    ) -> Dict[str, Any]:
        """
        Loads a .GLB mesh (e.g. from ComfyUI Trellis 2) into Blender 5.2:
          1. Cleans loose geometry, smooths normals, centers at origin, and exports
             an optimized, studio-grade .GLB.
          2. Generates a 3D-printable .STL version (scaled to `target_height_mm` mm,
             with an optional beveled collector pedestal base for bed adhesion).
          3. Renders 3 studio showcase views in Blender 5.2 (PBR Shaded, Matte Clay
             Print Preview, and Wireframe Topology) if `preview_dir` is provided.
        """
        in_glb = str(Path(input_glb_path).resolve()).replace("\\", "/")
        out_glb = str(Path(output_glb_path).resolve()).replace("\\", "/")
        out_stl = str(Path(output_stl_path).resolve()).replace("\\", "/")
        prev_dir = str(Path(preview_dir).resolve()).replace("\\", "/") if preview_dir else ""

        bpy_script = f"""
import bpy
import bmesh
import math
import mathutils
import os

# 1. Reset scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# 2. Import GLB
bpy.ops.import_scene.gltf(filepath="{in_glb}")

mesh_objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
if not mesh_objs:
    raise RuntimeError("No mesh objects found in imported GLB: {in_glb}")

# Deselect all, select mesh objects and join into one clean master mesh
bpy.ops.object.select_all(action='DESELECT')
for o in mesh_objs:
    o.select_set(True)
bpy.context.view_layer.objects.active = mesh_objs[0]
if len(mesh_objs) > 1:
    bpy.ops.object.join()

obj = bpy.context.active_object
obj.name = "{asset_prefix}_Master"

# Apply all transforms
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Compute bounding box in world space and normalize size to 2.0 Blender units tall
bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
min_x = min(c.x for c in bbox_corners)
max_x = max(c.x for c in bbox_corners)
min_y = min(c.y for c in bbox_corners)
max_y = max(c.y for c in bbox_corners)
min_z = min(c.z for c in bbox_corners)
max_z = max(c.z for c in bbox_corners)

size_x = max(max_x - min_x, 1e-4)
size_y = max(max_y - min_y, 1e-4)
size_z = max(max_z - min_z, 1e-4)
max_dim = max(size_x, size_y, size_z)

scale_factor = 2.0 / max_dim
obj.scale = (scale_factor, scale_factor, scale_factor)
bpy.ops.object.transform_apply(scale=True)

# Re-center XY and place bottom at Z=0
bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
cx = (min(c.x for c in bbox_corners) + max(c.x for c in bbox_corners)) * 0.5
cy = (min(c.y for c in bbox_corners) + max(c.y for c in bbox_corners)) * 0.5
cz_min = min(c.z for c in bbox_corners)
obj.location = (-cx, -cy, -cz_min)
bpy.ops.object.transform_apply(location=True)

# Clean mesh & smooth shading
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=0.0001)
bpy.ops.mesh.delete_loose()
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.shade_smooth()

# Export clean GLB (before adding print pedestal)
os.makedirs(os.path.dirname("{out_glb}"), exist_ok=True)
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.ops.export_scene.gltf(
    filepath="{out_glb}",
    export_format='GLB',
    use_selection=True,
    export_apply=True
)

# 3. Render Studio Previews if preview_dir is requested
prev_dir = "{prev_dir}"
if prev_dir:
    os.makedirs(prev_dir, exist_ok=True)
    scene = bpy.context.scene
    # Use BLENDER_EEVEE_NEXT or BLENDER_EEVEE or CYCLES depending on Blender 5.2 availability
    available_engines = [e.identifier for e in scene.render.bl_rna.properties['engine'].enum_items]
    if 'BLENDER_EEVEE_NEXT' in available_engines:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
    elif 'BLENDER_EEVEE' in available_engines:
        scene.render.engine = 'BLENDER_EEVEE'
    else:
        scene.render.engine = 'CYCLES'

    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1200
    scene.render.film_transparent = False

    # World dark studio background
    world = bpy.data.worlds.new("StudioWorld")
    scene.world = world
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs[0].default_value = (0.055, 0.06, 0.075, 1.0)
        bg_node.inputs[1].default_value = 1.0

    # 3-Point Studio Lighting
    def add_light(name, ltype, loc, rot_deg, energy, color=(1.0, 1.0, 1.0), size=2.5):
        ldata = bpy.data.lights.new(name=name, type=ltype)
        ldata.energy = energy
        ldata.color = color
        if hasattr(ldata, 'size'):
            ldata.size = size
        lobj = bpy.data.objects.new(name=name, object_data=ldata)
        scene.collection.objects.link(lobj)
        lobj.location = loc
        lobj.rotation_euler = [math.radians(a) for a in rot_deg]
        return lobj

    add_light("KeyLight", 'AREA', (2.6, -2.8, 3.2), (48, 0, 42), 180.0, (1.0, 0.96, 0.90), 3.0)
    add_light("FillLight", 'AREA', (-2.8, -2.2, 2.0), (60, 0, -48), 90.0, (0.75, 0.88, 1.0), 3.5)
    add_light("RimLight", 'AREA', (0.0, 3.0, 2.8), (-50, 0, 180), 220.0, (0.4, 0.85, 1.0), 2.5)

    # Camera setup aiming at center of object (Z=1.0)
    cam_data = bpy.data.cameras.new("StudioCam")
    cam_data.lens = 58
    cam_obj = bpy.data.objects.new("StudioCam", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    target = bpy.data.objects.new("CamTarget", None)
    scene.collection.objects.link(target)
    target.location = (0.0, 0.0, 0.95)

    track = cam_obj.constraints.new(type='TRACK_TO')
    track.target = target
    track.track_axis = 'TRACK_NEGATIVE_Z'
    track.up_axis = 'UP_Y'

    cam_obj.location = (0.45, -3.65, 1.45)

    # Render 1: PBR Shaded Beauty Render
    scene.render.filepath = os.path.join(prev_dir, "{asset_prefix}_pbr_shaded.png")
    bpy.ops.render.render(write_still=True)

    # Save original materials
    orig_mats = [slot.material for slot in obj.material_slots]

    # Render 2: Matte Resin Clay 3D Print Preview ( rotated 22 deg )
    clay_mat = bpy.data.materials.new("ResinClayMat")
    clay_mat.use_nodes = True
    bsdf = clay_mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.52, 0.55, 0.60, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.38
        bsdf.inputs["Metallic"].default_value = 0.08

    obj.data.materials.clear()
    obj.data.materials.append(clay_mat)
    obj.rotation_euler = (0, 0, math.radians(-24))
    scene.render.filepath = os.path.join(prev_dir, "{asset_prefix}_clay_print.png")
    bpy.ops.render.render(write_still=True)

    # Render 3: Wireframe Topology Preview (use temporary Decimate modifier so 180k-face mesh shows clean readable topology lines)
    wire_mat = bpy.data.materials.new("WireOverlayMat")
    wire_mat.use_nodes = True
    nodes = wire_mat.node_tree.nodes
    links = wire_mat.node_tree.links
    nodes.clear()
    out_node = nodes.new("ShaderNodeOutputMaterial")
    mix_shader = nodes.new("ShaderNodeMixShader")
    wire_node = nodes.new("ShaderNodeWireframe")
    wire_node.use_pixel_size = True
    wire_node.inputs[0].default_value = 0.65
    base_bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    base_bsdf.inputs["Base Color"].default_value = (0.08, 0.11, 0.16, 1.0)
    base_bsdf.inputs["Roughness"].default_value = 0.45
    emit_node = nodes.new("ShaderNodeEmission")
    emit_node.inputs["Color"].default_value = (0.0, 0.92, 0.78, 1.0)
    emit_node.inputs["Strength"].default_value = 2.0
    links.new(wire_node.outputs[0], mix_shader.inputs[0])
    links.new(base_bsdf.outputs[0], mix_shader.inputs[1])
    links.new(emit_node.outputs[0], mix_shader.inputs[2])
    links.new(mix_shader.outputs[0], out_node.inputs[0])

    dec_mod = obj.modifiers.new(name="WireDecimate", type='DECIMATE')
    if len(obj.data.polygons) > 18000:
        dec_mod.ratio = max(0.04, min(1.0, 14000.0 / float(len(obj.data.polygons))))
    obj.data.materials.clear()
    obj.data.materials.append(wire_mat)
    obj.rotation_euler = (0, 0, math.radians(18))
    scene.render.filepath = os.path.join(prev_dir, "{asset_prefix}_wireframe.png")
    bpy.ops.render.render(write_still=True)

    obj.modifiers.remove(dec_mod)
    # Restore rotation
    obj.rotation_euler = (0, 0, 0)

# 4. Prepare 3D Printable .STL with optional collector pedestal base, Voxel Remesh for 100% watertight manifold shell, and scale to mm
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.context.view_layer.objects.active = obj

if {str(bool(add_pedestal_base))}:
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=64,
        radius=0.82,
        depth=0.14,
        location=(0.0, 0.0, 0.05)
    )
    base_obj = bpy.context.active_object
    base_obj.name = "PrintPedestalBase"
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    base_obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.join()

# Apply Voxel Remesh (adaptivity=0.0 guarantees strict Marching Cubes manifold topology with 0 boundary & 0 non-manifold edges)
bpy.context.view_layer.objects.active = obj
remesh_mod = obj.modifiers.new(name="WatertightVoxelRemesh", type='REMESH')
remesh_mod.mode = 'VOXEL'
remesh_mod.voxel_size = 0.012
remesh_mod.adaptivity = 0.0
remesh_mod.use_smooth_shade = True
bpy.ops.object.modifier_apply(modifier=remesh_mod.name)

# Scale from 2.0 units to target_height_mm (e.g., 100mm) for slicer import
bbox_stl = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
cur_max_dim = max(
    max(c.x for c in bbox_stl) - min(c.x for c in bbox_stl),
    max(c.y for c in bbox_stl) - min(c.y for c in bbox_stl),
    max(c.z for c in bbox_stl) - min(c.z for c in bbox_stl),
    1e-4,
)
stl_scale = {float(target_height_mm)} / cur_max_dim
obj.scale = (stl_scale, stl_scale, stl_scale)
bpy.ops.object.transform_apply(scale=True)

# Re-zero bottom at Z=0.0 in mm space
bbox_mm = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
cx_mm = (min(c.x for c in bbox_mm) + max(c.x for c in bbox_mm)) * 0.5
cy_mm = (min(c.y for c in bbox_mm) + max(c.y for c in bbox_mm)) * 0.5
cz_min_mm = min(c.z for c in bbox_mm)
obj.location = (-cx_mm, -cy_mm, -cz_min_mm)
bpy.ops.object.transform_apply(location=True)

os.makedirs(os.path.dirname("{out_stl}"), exist_ok=True)
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
if hasattr(bpy.ops.wm, "stl_export"):
    bpy.ops.wm.stl_export(filepath="{out_stl}", export_selected_objects=True)
else:
    bpy.ops.export_mesh.stl(filepath="{out_stl}", use_selection=True)

print("BLENDER_PIPELINE_SUCCESS")
"""
        res = self.execute_mcp_code(bpy_script, timeout=240.0)
        stl_p = Path(output_stl_path)
        p3mf_path = None
        if stl_p.exists():
            try:
                from pipeline.stages.bambu_3mf_mockup_engine import bambu_mockup_engine
                m_res = bambu_mockup_engine.export_bambu_3mf_project(
                    stl_or_glb_path=stl_p,
                    model_name=asset_prefix,
                )
                if m_res.get("success"):
                    p3mf_path = m_res.get("project_3mf_path")
            except Exception:
                pass

        return {
            "success": Path(output_glb_path).exists() and Path(output_stl_path).exists(),
            "glb_path": str(output_glb_path),
            "stl_path": str(output_stl_path),
            "project_3mf_path": p3mf_path,
            "preview_dir": str(preview_dir) if preview_dir else None,
            "blender_result": res,
        }

    def extrude_svg_to_3d_stl_and_glb(
        self,
        svg_path: Union[str, Path],
        output_glb_path: Union[str, Path],
        output_stl_path: Union[str, Path],
        preview_png_path: Optional[Union[str, Path]] = None,
        target_diameter_mm: float = 100.0,
    ) -> Dict[str, Any]:
        """
        Imports a 2D .SVG stencil into Blender 5.2, extrudes each curve layer onto a
        collector medallion backing plate with brushed gold PBR materials, exports the
        multi-material .GLB, renders a studio preview PNG, and exports a 100% watertight
        voxel-remeshed 100mm .STL for 3D printing.
        """
        svg_s = str(Path(svg_path).resolve()).replace("\\", "/")
        glb_s = str(Path(output_glb_path).resolve()).replace("\\", "/")
        stl_s = str(Path(output_stl_path).resolve()).replace("\\", "/")
        prev_s = str(Path(preview_png_path).resolve()).replace("\\", "/") if preview_png_path else ""

        code = f"""
import bpy
import math
import mathutils
import os

bpy.ops.wm.read_factory_settings(use_empty=True)

# Create solid circular medallion backing plate
bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=1.15, depth=0.14, location=(0, 0, 0.07))
plate = bpy.context.active_object
plate.name = "Medallion_Base"

mat_base = bpy.data.materials.new("ObsidianBase")
mat_base.use_nodes = True
bsdf_b = mat_base.node_tree.nodes.get("Principled BSDF")
if bsdf_b:
    bsdf_b.inputs["Base Color"].default_value = (0.08, 0.09, 0.12, 1.0)
    bsdf_b.inputs["Metallic"].default_value = 0.85
    bsdf_b.inputs["Roughness"].default_value = 0.28
plate.data.materials.append(mat_base)

# Outer raised rim ring
bpy.ops.mesh.primitive_torus_add(major_radius=1.10, minor_radius=0.055, major_segments=96, minor_segments=24, location=(0, 0, 0.13))
rim = bpy.context.active_object
rim.name = "Medallion_Rim"

mat_gold = bpy.data.materials.new("BrushedGold")
mat_gold.use_nodes = True
bsdf_g = mat_gold.node_tree.nodes.get("Principled BSDF")
if bsdf_g:
    bsdf_g.inputs["Base Color"].default_value = (0.94, 0.74, 0.28, 1.0)
    bsdf_g.inputs["Metallic"].default_value = 0.95
    bsdf_g.inputs["Roughness"].default_value = 0.18
rim.data.materials.append(mat_gold)

# Import SVG curves
bpy.ops.import_curve.svg(filepath="{svg_s}")
curves = [o for o in bpy.context.scene.objects if o.type == 'CURVE']

if len(curves) > 1:
    bpy.data.objects.remove(curves[0], do_unlink=True)
    curves = [o for o in bpy.context.scene.objects if o.type == 'CURVE']

for idx, c in enumerate(curves):
    c.data.extrude = 0.045 + (idx * 0.008)
    c.data.bevel_depth = 0.003
    c.data.bevel_resolution = 2
    bpy.context.view_layer.objects.active = c
    c.select_set(True)
    bpy.ops.object.convert(target='MESH')
    if len(c.data.materials) == 0:
        c.data.materials.append(mat_gold)

mesh_parts = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o not in (plate, rim)]
if mesh_parts:
    bpy.ops.object.select_all(action='DESELECT')
    for m in mesh_parts:
        m.select_set(True)
    bpy.context.view_layer.objects.active = mesh_parts[0]
    if len(mesh_parts) > 1:
        bpy.ops.object.join()
    relief = bpy.context.active_object
    relief.name = "SVG_3D_Relief"
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bbox = [relief.matrix_world @ mathutils.Vector(b) for b in relief.bound_box]
    sx = max(b.x for b in bbox) - min(b.x for b in bbox)
    sy = max(b.y for b in bbox) - min(b.y for b in bbox)
    sc = 1.75 / max(sx, sy, 1e-4)
    relief.scale = (sc, sc, 1.0)
    bpy.ops.object.transform_apply(scale=True)
    bbox = [relief.matrix_world @ mathutils.Vector(b) for b in relief.bound_box]
    cx = (min(b.x for b in bbox) + max(b.x for b in bbox)) * 0.5
    cy = (min(b.y for b in bbox) + max(b.y for b in bbox)) * 0.5
    cz = min(b.z for b in bbox)
    relief.location = (-cx, -cy, 0.09 - cz)
    bpy.ops.object.transform_apply(location=True)

# Export GLB
os.makedirs(os.path.dirname("{glb_s}"), exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath="{glb_s}", export_format='GLB', use_selection=True, export_apply=True)

# Render Studio Preview if requested
prev_s = "{prev_s}"
if prev_s:
    os.makedirs(os.path.dirname(prev_s), exist_ok=True)
    scene = bpy.context.scene
    available_engines = [e.identifier for e in scene.render.bl_rna.properties['engine'].enum_items]
    scene.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in available_engines else ('BLENDER_EEVEE' if 'BLENDER_EEVEE' in available_engines else 'CYCLES')
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1000

    world = bpy.data.worlds.new("MedallionWorld")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.05, 0.06, 0.08, 1.0)

    for name, loc, rot, eng in [
        ("Key", (2.2, -2.5, 3.0), (35, 0, 40), 160.0),
        ("Fill", (-2.5, -2.0, 2.2), (45, 0, -45), 90.0),
        ("Rim", (0.0, 2.5, 2.5), (-40, 0, 180), 180.0),
    ]:
        ld = bpy.data.lights.new(name, 'AREA')
        ld.energy = eng
        ld.size = 2.5
        lo = bpy.data.objects.new(name, ld)
        scene.collection.objects.link(lo)
        lo.location = loc
        lo.rotation_euler = [math.radians(a) for a in rot]

    cam_d = bpy.data.cameras.new("Cam")
    cam_d.lens = 55
    cam_o = bpy.data.objects.new("Cam", cam_d)
    scene.collection.objects.link(cam_o)
    scene.camera = cam_o
    cam_o.location = (0.0, -2.1, 2.45)
    cam_o.rotation_euler = (math.radians(40), 0, 0)

    scene.render.filepath = prev_s
    bpy.ops.render.render(write_still=True)

# Join all mesh objects, Voxel Remesh (adaptivity=0.0) for 100% watertight manifold shell, scale to target_diameter_mm (100mm), and export STL
all_meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
bpy.ops.object.select_all(action='DESELECT')
for m in all_meshes:
    m.select_set(True)
bpy.context.view_layer.objects.active = all_meshes[0]
if len(all_meshes) > 1:
    bpy.ops.object.join()

med_obj = bpy.context.active_object
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

remesh_mod = med_obj.modifiers.new(name="MedallionVoxelRemesh", type='REMESH')
remesh_mod.mode = 'VOXEL'
remesh_mod.voxel_size = 0.012
remesh_mod.adaptivity = 0.0
remesh_mod.use_smooth_shade = True
bpy.ops.object.modifier_apply(modifier=remesh_mod.name)

bbox_m = [med_obj.matrix_world @ mathutils.Vector(c) for c in med_obj.bound_box]
cur_diam = max(
    max(c.x for c in bbox_m) - min(c.x for c in bbox_m),
    max(c.y for c in bbox_m) - min(c.y for c in bbox_m),
    1e-4,
)
sc_mm = {float(target_diameter_mm)} / cur_diam
med_obj.scale = (sc_mm, sc_mm, sc_mm)
bpy.ops.object.transform_apply(scale=True)

bbox_mm = [med_obj.matrix_world @ mathutils.Vector(c) for c in med_obj.bound_box]
cx_m = (min(c.x for c in bbox_mm) + max(c.x for c in bbox_mm)) * 0.5
cy_m = (min(c.y for c in bbox_mm) + max(c.y for c in bbox_mm)) * 0.5
cz_m = min(c.z for c in bbox_mm)
med_obj.location = (-cx_m, -cy_m, -cz_m)
bpy.ops.object.transform_apply(location=True)

os.makedirs(os.path.dirname("{stl_s}"), exist_ok=True)
bpy.ops.object.select_all(action='DESELECT')
med_obj.select_set(True)
if hasattr(bpy.ops.wm, "stl_export"):
    bpy.ops.wm.stl_export(filepath="{stl_s}", export_selected_objects=True)
else:
    bpy.ops.export_mesh.stl(filepath="{stl_s}", use_selection=True)
"""
        res = self.execute_mcp_code(code, timeout=180.0)
        return {
            "success": Path(output_glb_path).exists() and Path(output_stl_path).exists(),
            "glb_path": str(output_glb_path),
            "stl_path": str(output_stl_path),
            "preview_png": str(preview_png_path) if preview_png_path else None,
            "blender_result": res,
        }


blender_bridge = BlenderBridge()

