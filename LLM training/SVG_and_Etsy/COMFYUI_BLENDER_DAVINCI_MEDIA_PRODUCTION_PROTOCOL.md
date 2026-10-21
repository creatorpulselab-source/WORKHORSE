# Master Media Production Protocol: ComfyUI – Blender – DaVinci Resolve
### *The Universal Standard for WORKHORSE Autonomous Product Design, 3D Engineering & Media Creation*
*Enacted 2026-10-21 by Commander Directive: "The process for any and all products and media should be at expert level and run through Comfyui-Blender-Davinci or Comfyui-Davinci or some combination of those 3. But Comfyui is the main go to for any and all generation of images, video, 3D elements any kind of media needed can be made in comfyui and refined with blender or Davinci. That needs to be in the protocol."*

---

## 1. Core Architectural Law: Division of Responsibilities

Every digital product, physical 3D print asset, listing photo, promotional video, and brand asset in the WORKHORSE ecosystem must adhere to this tri-engine architecture:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        WORKHORSE MASTER MEDIA PRODUCTION TRIAD                         │
└────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────┐
    │          1. COMFYUI           │  ◄── PRIMARY GENERATION ENGINE FOR ALL MEDIA
    │     (RTX 5070 Ti @ 16GB)      │      • All Image Generation (Listing photos, mockups, flatlays)
    │     http://192.168.1.74:8188  │      • All 3D Volumetric Generation (Trellis 2, Hunyuan3D, Pixal3D)
    └──────────────┬────────────────┘      • All Video Generation (FastH3, Wan2.1, MiniMax, LTX)
                   │
         ┌─────────┴─────────┐
         │                   │
         ▼                   ▼
┌──────────────────┐  ┌──────────────────┐
│    2. BLENDER    │  │3. DAVINCI RESOLVE│
│ 5.2 (HEADLESS)   │  │   21.1+ STUDIO   │
│ Dual RTX 3060    │  │   NEURAL ENGINE  │
└────────┬─────────┘  └────────┬─────────┘
         │                     │
         ▼                     ▼
• 3D Geometry Repair  • Cinematic Color Grading
• Voxel Remesh        • Neural 3D LUT Application
• Seam Weld / Smooth  • Video Editing & Master Reels
• 0 Non-Manifold Edges• Motion Graphics & Sound
• Support-Free Cut Z=0• Etsy Cover Videos / Shorts
• Watertight STL / 3MF
```

---

## 2. Engine 1: ComfyUI (The Universal Generation Engine)

> [!IMPORTANT]
> **COMFYUI IS THE PRIMARY SOURCE FOR ALL MEDIA GENERATION.**
> Under NO circumstances should an agent use basic procedural CAD blocks or Blender camera renders when high-converting visual media is required. ComfyUI generates the initial vision, the sculpted 3D mesh, and all photorealistic listing media.

### 2.1 Media Types Produced in ComfyUI
1. **3D Volumetric Meshes (`.glb`):**
   - **Models:** Trellis 2 (`trellis_2_int8_convrot.safetensors`), Hunyuan3D v2.1, Pixal3D.
   - **Generation:** High-detail 3D geometry generated from text prompts or concept plates.
2. **Photorealistic Product Photography:**
   - 3D products staged on modern oak desks, concrete countertops, windowsill planes, or lifestyle setups.
   - Realistic material shaders (matte PLA, PETG, frosted resin, brushed metal).
   - Natural soft contact occlusion shadows anchored to the ground plane (ZERO floating).
3. **Lifestyle & Context Imagery:**
   - Products shown in real environments (gym bags, car cupholders, kitchen counters, craft fair tables).
4. **Cinematic Video Clips:**
   - 360-degree turntable spins, dynamic push-in camera moves, slow-motion lighting reveals.

### 2.2 Standard 3D Generation Pipeline in ComfyUI
- **Step 1 (Concept Isolation):** Render isolated three-quarter view of the product on a solid neutral studio background (1024x1024).
- **Step 2 (Background Stripping):** Run through `PixaromaRemoveBackground` / BiRefNet for clean silhouette alpha.
- **Step 3 (Volumetric Reconstruction):** Pass to Trellis 2 KSampler pipeline (Structure -> Shape -> 1024 Upsample -> Texture Bake).
- **Step 4 (Save):** Export high-density PBR mesh (`.glb`) for Blender post-processing.

---

## 3. Engine 2: Blender 5.2 (The 3D Topology & Mechanical Refinement Engine)

> [!CAUTION]
> **BLENDER IS FOR MESH REFINEMENT ONLY — NOT MEDIA RENDERS.**
> Blender is used headlessly as an engineering tool to clean raw AI meshes into 100% watertight, print-ready FDM solid models. Agents do NOT use Blender to render the listing photos.

### 3.1 Blender Refinement Pipeline (Automated via Python / `bpy`)
1. **Import & Scale Normalization:**
   - Import `.glb` from ComfyUI.
   - Scale mesh to true millimetre dimensions (e.g., 45-65mm for keychains, 70-120mm for planters).
2. **Topology Repair & Seam Welding:**
   - `remove_doubles(threshold=0.0002)` to weld disconnected surface vertices.
   - `delete_loose()` to purge floating degenerate geometry.
   - Recalculate face normals outward (`inside=False`).
3. **Mechanical Utility Integration:**
   - For keychains: Attach a reinforced 4.2mm keyring torus with 2.2mm wall thickness.
   - For planters: Bore 7mm drainage holes in the floor; model matching nesting saucers.
   - For holders: Model internal step collars and support-free draft angles.
4. **Voxel Remesh (Manifold Guarantee):**
   - Apply `REMESH` modifier in `VOXEL` mode (`voxel_size = 0.65mm - 0.8mm`).
   - Melds all separate shells and intersecting geometry into ONE continuous, solid volume.
5. **Surface Polish:**
   - Apply `SMOOTH` modifier (`factor=0.45`, `iterations=2`) to soften voxel stepping.
6. **Support-Free Base Cut:**
   - Boolean difference with a ground plane at $Z=0$ to ensure a perfectly flat first-layer bed contact surface.
7. **Watertight Manifold Validation:**
   ```python
   bm = bmesh.new()
   bm.from_mesh(ob.data)
   assert len([e for e in bm.edges if not e.is_manifold]) == 0, "Non-manifold edges detected!"
   assert len([e for e in bm.edges if e.is_boundary]) == 0, "Boundary holes detected!"
   assert len([v for v in bm.verts if not v.link_edges]) == 0, "Loose vertices detected!"
   ```
8. **Export:** Export clean `.stl` and assemble multi-part `.3mf` plates.

---

## 4. Engine 3: DaVinci Resolve 21.1+ (The Color Correction & Cinematic Mastering Engine)

> [!TIP]
> **DAVINCI RESOLVE POWERS ALL IMAGE & VIDEO COLOR CORRECTION**:
> DaVinci Resolve Studio is the world's premier color science and post-production engine. Use it for color correction on both images and video, ensuring studio-grade color fidelity, tonal consistency, and high-impact visual appeal across all Etsy listing media.

### 4.1 DaVinci Resolve Image & Video Color Science
1. **Still Image Color Correction & Grading:**
   - Color match product photos across different lighting setups.
   - Neutralize color casts, correct skin tones, enhance PLA filament saturation without clipping.
   - Apply 33x33x33 `.cube` 3D LUTs (filmic S-curves, Kodak 2383 emulation, warm editorial tone curves).
2. **Video Color Grading & Mastering:**
   - Grade 360-degree turntable spins and product reveal reels.
   - Speed ramping, motion stabilization, and audio sync.
   - Export 15-second looping Etsy cover videos (`.mp4`) and vertical 9:16 reels (1080x1920) for TikTok/Instagram.
3. **Resolve Scripting API & ResolveMCP:**
   - Automate via `DaVinciResolveScript` (`bmd.scriptapp("Resolve")`) and `ResolveMCP.exe` tools.
   - Batch process timeline clips, apply grades, and render headless deliverables.
   - 5 to 15 second looping video clips highlighting the 3D model in action.
   - Dynamic zoom, turntable spin, and macro detail inspection.
3. **Social Media Mastery:**
   - Vertical 9:16 export (1080x1920) for Instagram Reels, YouTube Shorts, and TikTok.
   - High-fidelity audio sync and graphic overlays.

---

## 5. Standard Combination Workflows

Depending on the deliverable, agents must execute one of these approved combinations:

### Workflow A: 3D Printable Digital Products (STLs / 3MFs / GLBs)
```
[ ComfyUI ] ──────► Generates sculpted 3D mesh (.glb) + All photorealistic listing media
    │
    ▼
[ Blender ] ──────► Headless mesh cleanup: Voxel remesh, 0 non-manifold edges, watertight STL export
    │
    ▼
[ DaVinci ] ──────► (Optional/Recommended) Masters the 15-second Etsy listing cover video & social reel
```

### Workflow B: Digital Art, SVG Stencils & Craft Bundles
```
[ ComfyUI ] ──────► Generates high-res vector concepts + Photorealistic physical mockups (t-shirts, mugs, wood)
    │
    ▼
[ DaVinci ] ──────► Applies 3D LUT color grading, masters promotional video clips and product previews
```

### Workflow C: Marketing & Social Content (Reels / Shorts)
```
[ ComfyUI ] ──────► Generates video animations, camera turntables & dynamic product movement
    │
    ▼
[ DaVinci ] ──────► Color grading, speed ramping, sound design, vertical 9:16 mastering and export
```

---

## 6. Hardware Allocation Matrix

To prevent system lockups and ensure maximum throughput, hardware is strictly allocated:

| Hardware Resource | Designated Role | Software Bound |
| :--- | :--- | :--- |
| **NVIDIA RTX 5070 Ti (16GB VRAM)** | Universal Media Generation (Images, Video, 3D Trellis 2) | ComfyUI Standalone Server (`192.168.1.74:8188`) |
| **Dual NVIDIA RTX 3060 (12GB + 12GB)** | Mesh Topology Processing & Background Tasks | Blender 5.2 OptiX Engine |
| **Local CPU & Neural Acceleration** | Color Science & NLE Mastering | DaVinci Resolve 21.1+ Studio |

---

## 7. Operational Compliance Mandate

1. **NO Procedural CAD Shortcuts For Sculpted Goods:** When the catalog calls for character keychains, figurines, animal cups, or artistic planters, agents must NEVER substitute flat 2D extrusions or basic primitive boxes. Use ComfyUI Trellis 2 to generate genuine sculpted 3D models.
2. **NO Blender Camera Renders For Media:** All visual listing images, hero cards, and lifestyle shots belong in ComfyUI. Blender is restricted to geometry repair, slicing, and STL export.
3. **ZERO Non-Manifold Tolerated:** Every STL delivered to an Etsy package must pass the automated manifold topology test (0 non-manifold edges, 0 boundary holes, positive volume).
4. **All Media at $2400 \times 2400$ Quality=95:** Listing card decks follow the Cute Animal Pencil Cups 10-card formula with grounded contact shadows, Anton/Pacifico typography, and zero validation errors.

---

## 9. The Zero False Advertising / 1:1 Product-to-File Law

> [!CAUTION]
> **ABSOLUTE LAW: 100% 1:1 PRODUCT-TO-FILE MATCHING**
> It is illegal, deceptive, and a violation of Etsy marketplace policy and federal consumer protection laws to display one product in the listing images and deliver a different product in the download package. Showing a gorgeous AI render or high-end sculpt and shipping a generic, different, or lower-quality mesh results in immediate 1-star reviews, fraud flags, and account suspension.
> 
> **Every single 3D model shown in the listing images MUST BE THE EXACT SAME physical 3D model packaged in the customer's STL/3MF download zip.**

### 9.1 The Two Compliant Production Pipelines
To guarantee a 100% 1:1 geometric match between images and download files, agents MUST follow one of two verified pipelines:

1. **Pipeline Alpha: Image-First (Image-to-3D Volumetric Mesh)**
   - Used when high-end visual product concepts are generated in ComfyUI first.
   - The photorealistic isolated product image from ComfyUI is fed directly into **Trellis 2 / Hunyuan3D v2.1** on the RTX 5070 Ti (`generate_image_to_3d_pbr`).
   - The resulting `.glb` is imported into Blender 5.2 headless (`_cleanup_step.py`), voxel-remeshed to 0.65mm, given mechanical loops/holes, flattened at $Z=0$, and exported as the final watertight `.stl`.
   - Result: The physical STL is an exact 3D recreation of the product shown in the photo.

2. **Pipeline Beta: CAD/Mesh-First (ControlNet / Depth / Shaded Pass)**
   - Used for parametric, architectural, or mechanical goods (planters, desk organizers, can holders, cookie cutters).
   - The watertight solid 3D models are engineered first in CAD / Blender.
   - To generate the photorealistic ComfyUI listing media, an orthographic or perspective depth map / normal map is extracted from Blender and passed into ComfyUI with **ControlNet Depth** (`depth_anything_v2` or `metric3d`).
   - Result: ComfyUI applies photorealistic textures and studio lighting strictly to the *exact surface contours* of the physical STL, with zero geometric hallucination.

### 9.2 Pre-Publish 1:1 Verification Check
Before any listing zip is finalized:
- A Blender Cycles headless snapshot (`_verify_stl_XX.png`) must be rendered of each STL in `files/STL/`.
- The snapshot must be visually compared against the corresponding listing image (`comfy_single_XX.png`).
- If any discrepancy exists (e.g. octopus has different tentacle pose, dragon has different horns, item is a sneaker instead of a chalice), the package is REJECTED.

---

## 10. Universal 3D Bestseller Cover Layout Specification

Every 3D listing cover (`01_cover.jpg`) must adopt the proven high-converting layout architecture from `kawaii_plush_baby_animal_faces_clipart_png\images\01_cover.jpg`:

```
+-------------------------------------------------------------------+
|  [Tilted 8-deg Colorful Card Collage of All Files in Bundle]      |
|  [Soft Center Radial Glow to clear focus for center container]    |
|                                                                   |
|   +-----------------------------------------------------------+   |
|   | [Top Ribbon Kicker: e.g. "COMMERCIAL USE INCLUDED"]       |   |
|   |                                                           |   |
|   |         PRIMARY TITLE (Anton, 115-125pt, Bold Deep Slate) |   |
|   |         Subtitle Cursive (Pacifico, 48-56pt, Accent Blue) |   |
|   |                                                           |   |
|   |   +---------------------------------------------------+   |   |
|   |   |                                                   |   |   |
|   |   |   UNCROPPED HERO PRODUCT SHOWCASE (Centered)      |   |   |
|   |   |   Full bodies, wings, tentacles, contact shadows   |   |   |
|   |   |   (Zero clipped heads or cut off feet)            |   |   |
|   |   |                                                   |   |   |
|   |   +---------------------------------------------------+   |   |
|   |                                                           |   |
|   |    (STL)   (3D PRINT)   (NO SUPPORTS)   (TESTED)   (COMM) |   |
|   +-----------------------------------------------------------+   |
|                                                                   |
|   [ 40-Point Yellow Starburst Badge: "INSTANT DOWNLOAD" ] (TR)    |
|   [ Machine Compatibility Pill: "BAMBU LAB * PRUSA * CREALITY" ] |
+-------------------------------------------------------------------+
```

### 10.1 Key Geometric Rules
1. **Background Collage:** Tilted ($8^\circ$) repeating grid of cards showing all single models in the pack with alternating colored borders (`#1D63B8`, `#D45C24`, `#2E7D72`, `#C88C1E`, `#7B5294`). Soft radial glow (`radius=140`) at center keeps focus on the hero.
2. **Centered Container:** Card container is perfectly centered horizontally (`cx = (SIZE - cw) // 2`).
3. **Hero Image Centering & Aspect Ratio:**
   - The hero product cluster MUST be rendered in wide 16:11 or 16:9 aspect ratio (`1216 x 832` or `1680 x 1150`).
   - NEVER use naive `ImageOps.fit` that cuts off the heads or bases of the models. The full geometry from crown to tabletop shadow must remain 100% visible inside the frame.
4. **Starburst Badge:** 40-point yellow starburst badge (`#FFD600`) anchored in upper-right quadrant ($x=2160, y=240, r=200$).
5. **Feature Strip:** Circular or rounded square chips at bottom with bold Anton typography.

---

## 11. Large-Font Information Cards Specification (`M.info_card`)

Cards 08 (Specs & Dimensions / Print Settings), 09 (What's in Your Download / Formats), and 10 (Commercial License) must use the big-font information card architecture modeled after `sarcastic_funny_quotes_svg_png_bundle\images\08_formats.jpg` and `09_license.jpg`:

1. **Section Headers:** 78pt bold Anton headlines inside rounded rectangular headline banners.
2. **Content Cards:** Alternating background tint cards (520px wide or full-width rounded rows, 12px border, 24px drop shadow).
3. **Body Text:** Minimum 48pt to 54pt bold clean sans-serif typography (`Poppins-SemiBold` or `Poppins-Bold`) for effortless legibility on smartphone screens without pinch-to-zoom.
4. **Highlights:** Bullet badges with high-contrast icon chips or bold kicker labels (`#1D63B8`, `#2E7D50`, `#D45C24`).

---

## 12. End-to-End Repeatable Production Pipeline Template for 3D STL Listings

> [!IMPORTANT]
> **UNIVERSAL REPEATABLE TEMPLATE FOR ALL 3D LISTINGS**
> This end-to-end pipeline template is the mandatory standard for every 3D model pack published to Etsy (Keychains, Planters, Can Holders, Desk Organizers, Cookie Cutters, Figurines, Pencil Cups). It guarantees that every product listed has 100% 1:1 file-to-image fidelity, zero holes, zero blobs, and passes all Etsy marketplace constraints.

### 12.1 The 4-Stage Manufacturing Pipeline

> [!IMPORTANT]
> **COMFYUI AS THE UNIVERSAL MULTI-MODAL GENERATION ENGINE (3D, 2D & VIDEO)**
> ComfyUI is NOT merely an image generator. On the RTX 5070 Ti, ComfyUI serves as the core generative engine across all three critical media domains:
> 1. **3D Files & Products:** Direct volumetric 3D mesh synthesis (.glb, .obj, point clouds, meshes) via 113+ specialized 3D nodes (Trellis 2, Hunyuan3D v2.1, Pixal3D, VoxelToMesh). All organic and physical 3D products originate directly inside ComfyUI.
> 2. **2D Listing Media & Textures:** Photorealistic commercial catalog photography, authentic matte PLA textures, micro-layer line details, grounded contact shadows, and BiRefNet clean foreground/background segmentation.
> 3. **Video Assets:** 15-second looping turntable animations and lifestyle showcase videos for Etsy listing video slots (Wan 2.1, HunyuanVideo Image-to-Video, MiniMax, LTX-Video).

`
[ STAGE 1: COMFYUI MULTI-MODAL ENGINE (3D, 2D & VIDEO) ]
  ├─ 1. 3D SYNTHESIS: Volumetric 3D mesh generation (.glb / .obj / point clouds via Trellis 2, Hunyuan3D v2.1, Pixal3D, VoxelToMesh)
  ├─ 2. 2D ASSET CREATION: Photorealistic commercial catalog photography, authentic matte PLA textures, micro-layer lines, grounded contact shadows & BiRefNet segmentation
  └─ 3. VIDEO GENERATION: 15-second looping product turntable & lifestyle showcase videos for Etsy listing slots (Wan 2.1, HunyuanVideo, MiniMax, LTX-Video)

[ STAGE 2: BLENDER 5.2 HEADLESS CLEANUP ]
  ├─ 1. Import GLB & normalize height to true millimeters
  ├─ 2. Center XY and ground base at Z=0
  ├─ 3. Pre-remesh clean: remove_doubles(0.005) & purge islands < 500 verts
  ├─ 4. High-resolution Voxel Remesh (0.040 - 0.045 cm) for closed 2-manifold shell
  ├─ 5. Monolithic Boolean Union of mechanical loop/eyelet (sturdy 4.2mm keyring torus)
  ├─ 6. Leveled flat print bed cut at Z=0 (support-free first layer adhesion)
  ├─ 7. Post-boolean filter: keep ONLY the single largest connected component
  ├─ 8. Style-specific topology:
  │    ├─ Low-Poly Geometric: Decimate collapse to crisp planar faces + shade_flat() (ZERO smoothing)
  │    └─ Organic Sculpted: Subtle surface polish, sleek tapered extremities (NO blobs on tails/tentacles)
  ├─ 9. Rigorous Topology Audit:
  │    ├─ assert n_non_manifold == 0 (Zero non-manifold edges)
  │    ├─ assert n_boundary == 0 (Zero boundary holes)
  │    ├─ assert n_loose == 0 (Zero loose vertices)
  │    └─ assert len(islands) == 1 (Exactly 1 solid monolithic shell)
  └─ 10. Export watertight .stl & Cycles GPU verification snapshot

[ STAGE 3: DAVINCI RESOLVE COLOR MASTERING ]
  ├─ 3D LUT application (Workhorse Cinematic Filmic Matte 33x33x33 .cube)
  ├─ Neutralize color casts & enhance PLA filament saturation
  └─ Export graded listing photos & 15-second looping cover video

[ STAGE 4: PACKAGING & ETSY COMPLIANCE ]
  ├─ Clean purge of all old/mismatched files from files/STL/
  ├─ Zip packaging partitioned into parts <= 20.0 MB (Part1.zip, Part2.zip, etc.)
  ├─ Printable PDF Setup Guide & Lifetime Commercial License (kit.pdf_guide)
  ├─ Synchronized catalog.json, listing.json, and listing.md
  ├─ 10-Card visual listing deck (2400x2400, quality=95, Bestseller Cover, Big-Font Info Cards)
  └─ Final validation gate (listing.validate) -> 0 errors
```

### 12.2 Model-Specific Topology Guidelines
1. **Low-Poly Geometric Models (e.g. Bulldog, Geometric Planters, Low-Poly Wildlife):**
   - Must use `voxel_size = 0.040` cm for watertight manifold foundation.
   - Followed by `Decimate(COLLAPSE)` to targeted face count (1,500 - 3,500 faces).
   - Set `p.use_smooth = False` (`shade_flat()`).
   - NEVER apply global smooth modifiers: planar facets must remain razor-sharp.
2. **Organic Sculpted Models (e.g. Dragon, Axolotl, Octopus, Skull, Astronaut):**
   - Must use `voxel_size = 0.044 - 0.048` cm to prevent chunky voxel stepping while avoiding bloated file sizes.
   - Gentle `Smooth(factor=0.32, iterations=2)` to polish voxel stair-stepping.
   - Tail tips, tentacles, horns, and ears must be inspected to ensure they taper naturally without lumpy nodules.

---

## 13. Public Git & Developer Reference Knowledge Base

Agents should leverage public GitHub repositories, developer documentation, and open scripting APIs for deep implementation details on all three tools:

### 13.1 ComfyUI (Multi-Modal Powerhouse: 3D, 2D, and Video)
Over 3,200 active node types running on the RTX 5070 Ti (16GB VRAM):
- **3D & Mesh Generation (113+ nodes):**
  - TRELLIS-2 (ComfyUI-Trellis2): Trellis2Conditioning, Trellis2ShapeStage for photorealistic direct image-to-3D mesh (.glb).
  - Hunyuan3D v2.1 (ComfyUI-Hunyuan3DWrapper): Hunyuan3Dv2Conditioning, Hunyuan3Dv2ConditioningMultiView, VAEDecodeHunyuan3D for multi-view conditioned 3D generation.
  - Mesh synthesis: VoxelToMesh, VoxelToMeshBasic, Load3D, Preview3DAdvanced, Pixal3DConditioning.
- **2D Asset & Product Photography (2,700+ nodes):**
  - SDXL & Flux commercial product photography with studio key lighting and authentic matte PLA filament textures.
  - BiRefNet (ComfyUI-BiRefNet): Ultra-crisp foreground extraction and alpha transparency for compositing.
- **Video & Turntable Animation (399+ nodes):**
  - Wan 2.1 (ComfyUI-WanVideoWrapper / ModelMergeWAN2_1): High-definition video generation.
  - HunyuanVideo: TextEncodeHunyuanVideo_ImageToVideo for 360-degree product turntable rotations.
  - MiniMax (FastH3) & LTX-Video: Smooth 15-second looping Etsy listing videos.
- **API Spec:** Standard REST endpoints /prompt, /queue, /view, /history, and /system_stats at http://192.168.1.74:8188.

### 13.2 Blender 5.2
- **Python API (`bpy` & `bmesh`):** Official documentation for headless execution (`blender --background --python script.py`).
- **Remeshing & Boolean:** Voxel remeshing modifier, exact solver booleans, topology inspection (`is_manifold`, `is_boundary`).
- **Blender MCP:** JSON-RPC tool integration for remote scene queries, mesh imports, and object transforms.

### 13.3 DaVinci Resolve Studio 21.1+
- **Developer Scripting API:** Located in `C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\`.
- **Python Bridge:** `DaVinciResolveScript` (`bmd.scriptapp("Resolve")`) providing access to `ProjectManager`, `Project`, `MediaPool`, `Timeline`, and `TimelineItem`.
- **ResolveMCP:** Stdio JSON-RPC bridge (`ResolveMCP.exe`) enabling programmatic LUT application, clip cutting, and timeline renders without manual UI interaction.
- **Color Science:** Custom 33x33x33 `.cube` LUT generation and GPU `.dctl` transform scripts.


---

## 14. Master Listing Deck Layout Standard & Golden Blueprint Laws

### 14.1 The Golden Reference Standard
- **Golden Reference Package:** `F:\WORKHORSE\workspace\etsy_listings\highland_cow_sublimation_clipart_png`
- **Cover Engine:** `etsy_factory.typo.cover2.vibrant`
- **Universal Deck Builder:** `F:\WORKHORSE\etsy_factory\build_3d_listing_deck.py`
- **Rule of Visual Continuity:** Never reinvent layout or visual styling. The bold, colorful, diner-menu/concert-poster visual architecture proven in the Golden Standard must be preserved across every Etsy listing.

### 14.2 Strict 10-Card Deck Architecture
Every 3D listing must present exactly 10 cards at 2400x2400 resolution:
1. **Card 01 (`01_cover.jpg`): `cover2.vibrant`**
   - Deep rich vignette background (`vbg`) with repeating tilted product card collage darkening toward center.
   - Layered 3D folded ribbons with swallowtails and white inner pinstripes.
   - Giant 3D extruded gold number (`power_text`, 700pt Anton with shine band and 34px drop extrusion).
   - Massive 3D Anton title lines (175pt) with dark drop extrusion.
   - 22-spike starburst badge (`#FFD600`, "INSTANT DOWNLOAD").
   - 5-badge gold-bordered bottom feature strip (`STL`, `PRINT`, `CAD`/`FIT`, `TESTED`, `COMM`).
2. **Card 02 (`02_cover_grid.jpg`): `grid_cover_3d`**
   - Solid 540px dark ink header block.
   - Giant white Anton headline (180pt) + accent/gold subheadline (150pt) + Pacifico cursive line (68pt).
   - Full-pack clean grid with grounded contact shadows.
   - Bottom rounded machine compatibility strip (`"BAMBU LAB * PRUSA * CREALITY * ANY SLICER"`).
3. **Card 03 & Card 04 (`03_preview_1.jpg`, `04_preview_2.jpg`): `preview_sheet_3d`**
   - Anton 150pt headline + Pacifico 74pt cursive subtitle on warm sunny cream canvas.
   - White rounded cards (radius 40, width 680, height 840) with drop shadows.
   - Perfectly centered rows (3 cards top row, 2 cards bottom row centered).
   - High-contrast typography on each card: Anton 48pt bold uppercase title + Poppins 30pt dimensions/specs.
4. **Cards 05, 06, 07: ComfyUI Photorealistic Showcase Mockups**
   - Card 05: Hero cluster showing all products interacting together in a lifestyle scene.
   - Cards 06 & 07: Feature showcases with authentic matte PLA layer lines, natural contact shadows, and realistic wood/desktop grounding (zero floating).
5. **Cards 08, 09, 10 (`08_specs_settings.jpg`, `09_whats_included.jpg`, `10_license.jpg`): Large-Font `M.info_card`**
   - Solid 430px dark ink header block (`(0, 0, SIZE, 430)` in ink).
   - 58pt Poppins kicker in accent + 170pt Anton title in white.
   - Alternating vibrant 520px pills cycling through Coral, Teal, Hot Pink, Emerald, Honey Gold, and Royal Purple.
   - Giant 78pt Anton uppercase bold heads centered in each pill.
   - Large 52pt Poppins body text at 62px line height.
   - Clean dark-ink footer text (up to 50pt Poppins).

### 14.3 Zero False Advertising / 1:1 Product-to-File Law
- Every item depicted in listing images must be an exact physical match to the STLs in download zips.
- Low-poly designs must retain sharp planar geometric facets (no smooth-shading blur).
- Organic sculpts must retain clean, continuous surfaces free of stray blobs, holes, or boolean seam artifacts.

### 14.4 Automated Manufacturing Guarantee
- All STLs must pass the automated Blender topology audit:
  - `n_non_manifold == 0`
  - `n_boundary == 0`
  - `len(islands) == 1`
  - Leveled planar base at Z=0 for support-free first-layer bed adhesion.
- All download zips must strictly adhere to Etsy's 20.0 MB limit per file (partitioned into numbered parts when required).

---

## 15. MiniMax H3 Video Character Swap & DaVinci Resolve 4K Production Protocol

### 15.1 Multi-Angle Character Sheet Golden Architecture
1. **Source Photo Standards:**
   - 6 to 10 photos captured under uniform studio lighting on a seamless gray cyclorama (`#EDEFF2`).
   - Subject wears identical clothing across all shots to prevent silhouette or skin tone drift.
2. **Master Dual-Tier Sheet (`character_card_master.png`, 3840×2160):**
   - **Top Tier (1400px height):** 4 standardized standing views aligned head-to-toe (Front, Left Profile, Right 3/4, Full Back).
   - **Bottom Tier (560px height):** 4 high-resolution macro crops for facial features, neck/throat tattoos, and side profiles.
   - Generated via automated utility: `python F:\WORKHORSE\pipeline\assemble_character_sheet.py <input_folder> <output_folder>`.

### 15.2 Anti-Nudity & Garment Preservation Rules
1. **SAM3 Mask Target (Node 950):**
   - **MANDATORY:** Set mask prompt strictly to `"face, neck, arms"`.
   - **NEVER** set to `"woman"` on clothed subjects; whole-silhouette masking blacks out the garments, forcing diffusion to synthesize bare skin.
2. **Prompt Garment Locking:**
   - Always include the anchor clause:
     > *"Strictly preserve her original outfit and clothing from <Video_1> completely unchanged. She remains fully clothed in the original garments from <Video_1>."*

### 15.3 Tattoo Transfer Protocol
1. **Never Prompt Covered Tattoos:**
   - If the subject wears a shirt or dress in the performance video, do NOT prompt covered tattoos (e.g. sternum, chest, or full back pieces).
2. **Transfer to Exposed Skin Only:**
   - Anchor prompt tokens: *"Transfer the character's facial identity, hairstyle, throat/neck tattoos, and sleeve tattoos onto exposed arm skin from <Picture_1>."*

### 15.4 Audio Stream Pre-Flight Check
MiniMax H3 and ComfyUI's `VHS_LoadVideo` require an active audio track. Silent video containers throw an ffmpeg extraction failure.
- Auto-mux silent AAC sync audio prior to queuing:
  ```bash
  ffmpeg -y -i input.mp4 -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=44100 -c:v copy -c:a aac -shortest output_with_audio.mp4
  ```

### 15.5 Mandatory DaVinci Resolve Studio 4K SuperScale & Color Grading Pass
Raw ComfyUI generations render at 768×1376 with soft facial micro-details and flat Rec.709 digital contrast. Every video asset must pass through DaVinci Resolve Studio 21.1.1 before client delivery:
1. **3× Neural SuperScale:**
   - Upscale raw 768p to 4K UHD (2160×3840 for 9:16 portrait) using `superScale: 3` with `imageResizeMode: "sharper"`.
2. **Commercial Beauty Color Grading:**
   - **Prohibited:** Heavy analog print film LUTs (e.g. Kodak 2383), which double saturation and crush shadow detail into dark mud.
   - **Approved Preset 1 (`Workhorse_Clean_Studio_Beauty.cube`):** Custom 3D LUT lifting shadows by 1.5%, applying a luminous 0.94 gamma curve, and holding natural saturation at 32.7.
   - **Approved Preset 2 (Pure Natural CDL):** Offset +0.01 (open shadows), Power 0.99, Saturation 1.00.
3. **Hardware NVENC Acceleration:**
   - Export via NVIDIA NVENC H.264/H.265 at Best Quality (~2.2s render time for 5-second video).
   - Executable via: `python F:\WORKHORSE\pipeline\h3_davinci_postprocess.py <input_video.mp4>`.
