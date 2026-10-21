# ComfyUI + Blender 3D STL Production Pipeline
### *Foundational Manual & Operational Standard for WORKHORSE Autonomous Agents*
*Created 2026-10-21 following Commander Directives: "Comfyui makes great stl files. Use blender to clean up the STL files after you make them in Comfyui. Check the stl files from comfyui in blender to make sure the edges are clean and there are no artifacts. Also make sure blender is running on GPU not CPU. We need to make the same level of quality and export design with different products that sell."*

---

## 1. Executive Directive & Intellectual Property Rules

> [!IMPORTANT]
> **ORIGINAL DESIGNS ONLY — SAMPLES ARE BENCHMARKS, NEVER TEMPLATES**:
> Customer-supplied samples, reference files, or downloaded STLs in `F:\WORKHORSE\LLM training\SVG_and_Etsy` or `etsy_ideas\` are strictly **QUALITY BENCHMARKS** and **STYLE BRIEFS**.
> - Agents must **NEVER copy, re-export, or bundle external sample files** into commercial Etsy packages.
> - All delivered STL files, 3MF plates, and GLB assets must be **100% original WORKHORSE creations** generated via procedural CAD geometry or ComfyUI Trellis 2 + Blender sculpting.

> [!WARNING]
> **HIGH-DEMAND PRODUCTS THAT SELL**:
> Do NOT create flat, amateur 2D extrusions (e.g. flat cookie-cutter silhouettes with a rim). Customers on Etsy and MakerWorld buy:
> 1. **Functional EDC & Mechanical Gear**: Dual-angle folding phone stands, 1/4" hex bit pocket tools, AirTag protective cases, shopping cart quick-release tokens.
> 2. **Gym & Fitness Gear**: Realistic 3D hex dumbbells (embossed 20KG with knurled bar), Olympic bumper weight plates (45LB/20KG), cast iron kettlebells.
> 3. **Articulated & Flexi Sculptures**: Cute baby octopus, flexi dinosaurs, articulated dragons, sleeping chibi animals.
> 4. **Ergonomic Beverage Carriers & Adapters**: 4-cup takeout/coffee caddies with arch handles, double-wall knurled can coolers, car cup holder stepped adapters.
> 5. **Architectural Planters**: Faceted low-poly planters with integrated drainage holes and matching nesting saucers.

---

## 2. The 3-Engine Architecture for 3D Listings

```
┌────────────────────────────────────────────────────────────────────────┐
│                        WORKHORSE 3D PIPELINE                           │
└────────────────────────────────────────────────────────────────────────┘
                                    │
    ┌───────────────────────────────┼───────────────────────────────┐
    ▼                               ▼                               ▼
1. ComfyUI (Generation Engine)  2. Blender 5.2 (Headless Cleanup) 3. DaVinci / Deck Composer
(RTX 5070 Ti @ 192.168.1.74)    (Dual RTX 3060 OptiX GPU)       (Studio Grading & 2400x2400)
 • 3D Volumetric Mesh Gen (GLB) • Voxel Remeshing & Seam Weld   • 10-Card Listing Deck
 • ALL Media & Listing Renders   • Non-Manifold Error Remediation• Zero-Floating Contact Shadows
 • Tabletop Photos & Lifestyle   • Keyring Loop & Flat Bed Planing• Neural 3D LUT Color Grade
 • 360 Turntable Video Gen       • 100% Watertight STL/3MF Export• Video Listing Cover (DaVinci)
```

---

## 3. Engine 1: ComfyUI Trellis 2 (3D Volumetric Generation)

### 3.1 Network Endpoint & Primary Model
- **Endpoint:** `http://192.168.1.74:8188` (managed via `pipeline.stages.comfyui_bridge.comfy_bridge`).
- **Core 3D Checkpoint:** `trellis_2_int8_convrot.safetensors` (located in `models/diffusion_models/3D/`).
- **Vision Model:** `dino_v3_vit_l.safetensors` (`models/clip_vision/`).
- **VAEs:** `trellis_2_shape_vae_bf16.safetensors` & `trellis_2_texture_vae_bf16.safetensors`.

### 3.2 Concept Plate Generation Prompting
Always generate an isolated, high-contrast, three-quarter view of the subject centered on a solid neutral studio background:
- *Positive Prompt:* `three-quarter front view of [SUBJECT], centered complete object visible, isolated on solid neutral grey studio background, soft even studio product lighting, ultra detailed 3d sculpt render, no text, no watermark`
- *Negative Prompt:* `text, letters, words, watermark, signature, cluttered background, cropped, cut off, multiple objects, blurry, flat 2d, harsh cast shadows, frame, border`
- *Resolution:* `1024 x 1024`, `steps=24`, `cfg=6.5`.

### 3.3 Trellis 2 Image-to-3D Workflow Execution
1. Send image to `PixaromaRemoveBackground` (`birefnet.safetensors`).
2. Crop and center to 1024x1024 mask.
3. Pass through 4 KSampler stages:
   - **Stage 1 (Structure):** Rough voxel blob (resolution 32).
   - **Stage 2 (Shape):** Real shape extraction.
   - **Stage 3 (Upsample):** Detail refinement (`target_resolution=1024`).
   - **Stage 4 (Texture):** Surface coloring & bake (`texture_size=1024` or `2048`).
4. Output: `Save3DAdvanced` writes the master volumetric mesh to `output/3d/WORKHORSE_[slug]_[seed].glb`.

---

## 4. Engine 2: Blender 5.2 MCP (Mesh Cleanup & Watertight STL)

Raw AI meshes from Trellis 2 contain internal cavities, non-manifold edges, and uneven polygons. Blender 5.2 cleans them into professional 3D-printable solid geometry.

### 4.1 Mandatory Mesh Cleanup Protocol (Python / `bpy`)

```python
import bpy, bmesh, math, mathutils

# 1. Import raw GLB from ComfyUI
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb_in)
mesh_objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in mesh_objs: o.select_set(True)
bpy.context.view_layer.objects.active = mesh_objs[0]
if len(mesh_objs) > 1: bpy.ops.object.join()
ob = bpy.context.active_object

# 2. Clean topology & eliminate non-manifold seams
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=0.0002)
bpy.ops.mesh.delete_loose()
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode='OBJECT')

# 3. Normalize scale (mm -> cm in Blender workspace)
xs = [v.co.x for v in ob.data.vertices]
ys = [v.co.y for v in ob.data.vertices]
zs = [v.co.z for v in ob.data.vertices]
scale_factor = (target_height_mm / 10.0) / max(max(zs) - min(zs), 0.001)
ob.scale = (scale_factor, scale_factor, scale_factor)
bpy.ops.object.transform_apply(scale=True)

# 4. Center XY and ground base at Z=0
xs, ys, zs = [v.co.x for v in ob.data.vertices], [v.co.y for v in ob.data.vertices], [v.co.z for v in ob.data.vertices]
ob.data.transform(mathutils.Matrix.Translation((-(min(xs) + max(xs)) / 2.0, -(min(ys) + max(ys)) / 2.0, -min(zs))))

# 5. Add functional keyring eyelet (for keychains)
top_z = max(v.co.z for v in ob.data.vertices)
bpy.ops.mesh.primitive_torus_add(major_radius=0.42, minor_radius=0.14, location=(0, 0, top_z + 0.32), rotation=(math.pi / 2, 0, 0))
loop_ob = bpy.context.active_object
ob.select_set(True); loop_ob.select_set(True); bpy.context.view_layer.objects.active = ob
bpy.ops.object.join()

# 6. VOXEL REMESH: Fuses all intersecting bodies into a 100% solid, watertight manifold shell
remesh = ob.modifiers.new(name='VoxelRemesh', type='REMESH')
remesh.mode = 'VOXEL'
remesh.voxel_size = 0.065 # 0.65 mm resolution
bpy.ops.object.modifier_apply(modifier='VoxelRemesh')

# 7. SMOOTH MODIFIER: Eliminates stair-stepping and AI voxel artifacts
smooth = ob.modifiers.new(name='Smooth', type='SMOOTH')
smooth.factor = 0.45
smooth.iterations = 2
bpy.ops.object.modifier_apply(modifier='Smooth')

# 8. SUPPORT-FREE BED PLANING: Boolean difference with cutting box at Z=0 ensures 100% flat print bed contact
bpy.ops.mesh.primitive_cube_add(size=20, location=(0, 0, -10))
cutter = bpy.context.active_object
b_cut = ob.modifiers.new(name='BottomCut', type='BOOLEAN')
b_cut.operation = 'DIFFERENCE'; b_cut.object = cutter
bpy.ops.object.modifier_apply(modifier='BottomCut')
bpy.data.objects.remove(cutter, do_unlink=True)

# 9. Convert to millimeters and export STL
ob.scale = (10.0, 10.0, 10.0)
bpy.ops.object.transform_apply(scale=True)
bpy.ops.wm.stl_export(filepath=stl_out)
```

### 4.2 Watertight Quality Gate Inspection
Every exported STL must pass validation before being accepted:
```python
bm = bmesh.new()
bm.from_mesh(ob.data)
non_manifold = [e for e in bm.edges if not e.is_manifold]
boundary_edges = [e for e in bm.edges if e.is_boundary]
loose_verts = [v for v in bm.verts if not v.link_edges]
assert len(non_manifold) == 0, f"Mesh has {len(non_manifold)} non-manifold edges!"
assert len(boundary_edges) == 0, f"Mesh has {len(boundary_edges)} boundary holes!"
assert len(loose_verts) == 0, f"Mesh has {len(loose_verts)} loose vertices!"
```

---

## 5. Engine 3: ComfyUI Media Renders & DaVinci Resolve Video Mastering

> [!IMPORTANT]
> **COMFYUI IS FOR ALL MEDIA RENDERS — BLENDER IS MESH CLEANUP ONLY**:
> All listing photos, tabletop scene compositions, hero product shots, and lifestyle media are rendered directly in ComfyUI. Blender is NEVER used to render customer-facing media; Blender's sole role is headless geometry cleanup, manifold enforcement, and watertight STL/3MF export. DaVinci Resolve is used for cinematic color grading (3D LUTs) and video listing mastering.

### 5.1 ComfyUI Photorealistic Product Media Generation
Configure ComfyUI to render the product firmly anchored to a realistic tabletop plane with soft contact shadows:
- *Prompt formula:* `photorealistic product photography of [SUBJECT 3D PRINT], 3d printed in matte PLA filament with authentic fine layer line texture, resting firmly on clean modern tabletop surface, natural soft contact occlusion shadows beneath product, soft warm directional studio key light, crisp subtle rim accent, shallow depth of field, 8k commercial catalog photo, no floating, no artifacts`
- *Colors:* Sophisticated matte PLA colorways (matte terracotta clay, forest moss green, desert sand almond, stealth charcoal, denim slate).

### 5.2 DaVinci Resolve Listing Video & 3D LUT Mastering
- Apply signature 33x33x33 `.cube` LUTs for uniform catalog color science.
- Master 15-second looping Etsy cover videos and 9:16 vertical reels for TikTok/Instagram.

---

## 6. Etsy 10-Card Visual Deck Architecture ($2400 \times 2400$)

All digital STL packs must ship an expert-level 10-card visual deck:

| Card # | File Name | Content & Composition |
| :---: | :--- | :--- |
| **01** | `01_cover.jpg` | Warm cream `#FAF5EE` canvas, central white card container with dark ink border, giant gradient number (e.g. "8"), Anton title, Pacifico cursive subtitle, featured hero render with grounded shadow, circular format chips, slicer pill, 40-point yellow starburst badge ("INSTANT DOWNLOAD"). |
| **02** | `02_preview_all.jpg` | Full 8-Pack Overview in a 4x2 grid of floating rounded white cards with soft drop shadows. Each card holds one 3D item with its grounded contact shadow, item name, and measured mm dimensions. |
| **03** | `03_feature_1.jpg` | Primary feature spotlight with specs, callout pills, and closeup render. |
| **04** | `04_feature_2.jpg` | Secondary feature spotlight (e.g. standard vs slim models, knurling textures). |
| **05** | `05_feature_3.jpg` | Functional utility spotlight (e.g. car expander, clip-on outdoor holster). |
| **06** | `06_lifestyle.jpg` | Product-in-use staging (tailgate, desk, kitchen, or outdoor scene). |
| **07** | `07_feature_quality.jpg` | 100% Support-Free Printing & Watertight Shell Guarantee (walls, infill, nozzle). |
| **08** | `08_specs_dimensions.jpg` | Complete measured dimensions table (mm & inches) + slicer settings table. |
| **09** | `09_formats.jpg` | What's in your download (STL files, organized folders, printable PDF guide). |
| **10** | `10_commercial_license.jpg` | Clear commercial license terms (Sell physical 3D prints freely, zero digital resale, 100% original designs). |

---

## 7. Execution Checklist Before Publishing

1. **Geometry Check:** `trimesh.load()` confirms `is_watertight == True`, `boundary_edges == 0`, `faces >= 10,000`.
2. **Bed Size Check:** Max dimension fits within $220 \times 220$ mm (standard FDM build volume).
3. **Eyeball Renders:** Run `read_file` on all 10 cards. Verify 0 text clipping, 0 floating products, clean contact shadows, rich matte PLA colors.
4. **Etsy Constraints:** Exactly 10 JPEG images ($2400 \times 2400$, quality=95, subsampling=0), title $\le 140$ characters, exactly 13 tags $\le 20$ characters, $\le 5$ ZIP upload files $\le 20$ MB each.
5. **Validator Verification:** Run `listing.validate()` — must return **0 problems**.
