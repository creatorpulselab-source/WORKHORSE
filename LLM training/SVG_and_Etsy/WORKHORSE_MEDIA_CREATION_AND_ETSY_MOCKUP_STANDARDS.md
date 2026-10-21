# WORKHORSE Media Creation & Etsy Mockup Standards
### *Foundational Manual & Execution Protocol for WORKHORSE Autonomous Agents*
*Added 2026-10-20 following Commander Directive: "Use ComfyUI, Blender and DaVinci Resolve Studio for any and all media that needs to be created. Everything needs to be expert level quality in design and in products."*

---

## 1. Executive Directive & Core Invariants

> [!IMPORTANT]
> **ZERO AMATEUR GEOMETRY RULE**: Under NO circumstances may an agent generate product mockups using 2D procedural drawing primitives (e.g. PIL/ImageDraw rectangles, flat polygons, or synthetic pastel blocks). Every buyer-facing mockup must look like high-end commercial product photography or 3D raytraced studio photography.

> [!WARNING]
> **PHYSICAL CONTEXT INVARIANT**: Products and decals must make physical, real-world sense in their environment:
> - **Die-cut stickers** belong on **closed laptop lids**, **stainless steel / insulated tumblers**, **paper journals / spiral bullet notebooks**, and **craft cutting mats**.
> - **NEVER paste physical stickers floating across an iPad screen** or glass tablet display.
> - **Mockup elements must NEVER look floating**: apply directional contact drop shadows matching scene light sources, specular rim highlights, and cylindrical curvature mapping for rounded products.

---

## 2. The Three WORKHORSE Media Engines

WORKHORSE leverages three dedicated, hardware-accelerated local engines for all media generation:

```
                                  WORKHORSE MEDIA SUITE
                                            │
        ┌───────────────────────────────────┼───────────────────────────────────┐
        ▼                                   ▼                                   ▼
   1. ComfyUI                           2. Blender 5.2                   3. DaVinci Resolve
(RTX 5070 Ti / 3060)                  (Cycles / EEVEE Next)               (Studio 21.1+ NVENC)
  • Photorealistic Backdrops            • 3D Product Renders (STL/3MF)      • 5-15s Listing Video Previews
  • Product Staging (Laptops,           • Parametric Materials (PLA,        • Neural Engine Super Scale (3x)
    Tumblers, Craft Desks, Journals)      Dough, Wood, Marble)              • 3D LUT Color Science (Cinema)
  • BiRefNet Edge Mattes                • Decal Surface Wrapping            • High-Impact Short-Form Reels
  • Harmonizing img2img Passes          • Watertight Mesh Verification        (TikTok, Instagram, YouTube)
```

---

## 3. Engine 1: ComfyUI E-Commerce & Product Mockups

### 3.1 Network Endpoint & Hardware Setup
- **Endpoint:** `http://192.168.1.74:8188` (verified active with `system_stats`).
- **Primary Checkpoint:** `cyberrealisticXL_v80.safetensors` or `epicrealismXL_vxviiCrystalclear.safetensors`.
- **Inference Mode:** Run one generation at a time (check `/queue` before submitting). Cache backdrops by `(name, seed)` in `workspace/etsy_mockups/` or `workspace/etsy_backgrounds/`.

### 3.2 Standard E-Commerce Product Backdrops
Always generate spacious, clean commercial staging environments with empty center surfaces:
1. **Laptop Tech Mockup:**
   - *Prompt:* `professional product photography, directly overhead 90-degree flat lay view looking straight down at a closed sleek modern silver metallic laptop centered on a bright oak desk, clean blank brushed aluminum lid, no logo, no branding, cup of tea and pen at the outer edges, soft morning sunlight, sharp focus, 8k`
   - *Negative:* `apple logo, stickers, text on laptop, cluttered center, scratches, dark`
2. **Insulated Water Bottle / Tumbler:**
   - *Prompt:* `professional product photography, eye-level front centered view of a blank pastel insulated stainless steel tumbler water bottle standing upright on a light wooden table, soft natural daylight, clean matte powder-coated surface, completely blank, no logos, no branding, no text, shallow depth of field, 8k, sharp focus`
   - *Negative:* `stickers, decals, brand logos, pattern, ugly, deformed, blurry`
3. **Paper Journal / Bullet Planner:**
   - *Prompt:* `professional product photography, top-down flat lay of an open aesthetic paper notebook journal with dotted grid paper on a clean wooden desk, decorated with cute pastel kawaii animal stickers and washi tape, a brass pen resting beside it, soft natural morning window light, high detail, photorealistic, 8k`
4. **Print-at-Home Craft Flat-Lay:**
   - *Prompt:* `professional product photography, top-down flat lay of a bright cozy craft workspace table, light birch wood surface, craft cutting mat, pastel pink scissors, rolls of washi tape neatly placed along the outer edges, completely empty clear wooden table in the center, soft warm daylight, 8k`

### 3.3 Realistic Decal & Sticker Compositing
When adhering digital designs onto photographic backdrops:
1. **Directional Contact Shadows:** Never use symmetric circular blurs. Shift shadows according to the window light direction (e.g., `off=(12, 14)` for top-left sunlight), using two-stage Gaussian blur (hard contact shadow + soft diffuse ambient occlusion).
2. **Cylindrical Surface Wrapping:** For tumblers and mugs, apply a horizontal squeeze ratio ($0.92 - 0.94$) or perspective wrap so the sticker contours mathematically around the cylinder.
3. **Harmonizing img2img Pass:** For ultra-realistic integration, upload the composited plate back to ComfyUI and run an `img2img` pass at low denoise ($0.20 - 0.25$). This naturally unifies scene lighting, casts authentic contact shadows, and softens sharp vector edges into tactile vinyl laminate.

---

## 4. Engine 2: Blender 5.2 LTS (3D Product Staging & Slicer Prep)

### 4.1 Headless Execution Architecture
- **Binary Path:** `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`
- **Execution Script:** `etsy_factory/blender_render.py` (via `blender --background --python`).
- **Units & Scale:** 1 Blender unit = 1 cm; STL meshes are in millimetres (scale factor `0.1`).

### 4.2 Material Shader Requirements
Never render raw solid plastic. Use principled shader networks with realistic physical imperfections:
- **PLA 3D Prints:** Principled BSDF with faint Z-axis wave bump (`ShaderNodeTexWave`, scale 90.0, strength 0.08) to authentically replicate FDM layer lines, coat weight `0.06`, specular `0.35`.
- **Cookie Cutters & Dough:** Subsurface scattering (`Subsurface Weight: 0.12`, radius `(0.9, 0.6, 0.35)`) and micro-noise bump (`ShaderNodeTexNoise`, scale 140.0, strength 0.25) for authentic flour-dusted rolled cookie dough.
- **Tabletops & Cutting Boards:** Procedural oak/walnut mapping (`ShaderNodeTexWave` + `ShaderNodeTexCoord`).
- **Shadow Catcher Plane:** Always render on a transparent shadow catcher plane so the 3D model can be composited seamlessly onto ComfyUI photographic table-view backdrops.

### 4.3 Watertight STL Quality Gate
- All 3D printable designs must pass manifold inspection (`boundary_edges == 0`, `nonmanifold_edges == 0`).
- Apply the Blender `REMESH` modifier in `VOXEL` mode (`voxel_size=0.012`, `adaptivity=0.0`) to weld intersecting geometries before exporting.

---

## 5. Engine 3: DaVinci Resolve Studio 21.1+ (Video Listings & Motion Media)

### 5.1 Pipeline Integration
- **Executable:** `C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe` with `ResolvePython.exe` and `ResolveMCP.exe`.
- **Bridge Script:** `davinci_resolve_bridge.py`.

### 5.2 Listing Video Teasers & Viral Reels
Etsy listings reward video previews (5 to 15 seconds, 1080x1080 square or 1080x1920 portrait):
- **Neural Engine Super Scale:** Upscale low-res ComfyUI video frames (e.g. 480x864 FastH3 outputs) using `Super Scale 3x` with `superScaleSharpness=0.75` and Optical Flow motion estimation.
- **Cinematic Color Grading:** Apply the mathematical `WORKHORSE_Cinema_Grade.cube` 33x33x33 3D LUT (film contrast S-curve, soft highlight roll-off, teal-orange shadow split).
- **GPU Accelerated Mastering:** Export via `H264_NVIDIA` / `H265_NVIDIA` on the dual RTX 3060 / 5070 Ti hardware encoders.

---

## 6. Etsy 10-Card Listing Image Formula

Every WORKHORSE digital pack must ship an expert-level 10-card visual deck:

| Card # | Card Role | Visual Construction & Rules |
| :---: | :--- | :--- |
| **01** | **Hero Cover** | High-energy dense collage (`cover2.vibrant`). Giant count number as hero. Badge strip at bottom (Formats, DPI, Cut lines, License, Sizes). NO empty frosted center panels. |
| **02** | **Sheet / Product Overview** | Full catalog overview. If 2x2 grid: ensure `ch` and `cw` are properly scaled (e.g. `ch=880, cw=680` on 2400 canvas) so all rows fit with generous margins and ZERO bottom clipping. |
| **03** | **Individual Components** | Clean numbered grid of all individual items with clean labels and white bleed/kiss-cut borders. |
| **04** | **Tech Mockup** | ComfyUI photographic closed silver laptop on sunlit oak desk with decal placement. |
| **05** | **Drinkware Mockup** | ComfyUI photographic stainless tumbler / hydroflask with cylindrical sticker wrapping. |
| **06** | **Stationery / Journal** | ComfyUI photographic open paper journal / planner with dotted grid pages, brass pen, washi tape. (NO iPad stickers). |
| **07** | **Craft Flat-Lay** | ComfyUI photographic cutting mat, scissors, washi tape, with angled printed sticker sheet and paper drop shadow. |
| **08** | **How It Works / Cut Guide** | 3-step visual infographic: Step 1 (Print), Step 2 (Cut - Cricut/Silhouette/Scissors), Step 3 (Peel & Enjoy). Software compatibility badges. |
| **09** | **Specs & What's Included** | High-contrast info card detailing exact formats (SVG, DXF, PNG, PDF), sizes (US Letter, A4), 300 DPI guarantee. |
| **10** | **Commercial License** | Clear commercial terms: Physical products allowed up to 500 units, no digital resale, no POD upload, 100% original. |

---

## 7. Quality Gate Checklist (Mandatory Pre-Flight)

Before presenting any finished listing to the Commander:
1. **Eyeball Every Image:** Run `read_file` on every single generated `.jpg` card. If any text is clipped, any sticker looks floating, or any element looks artificial, FIX IT IMMEDIATELY.
2. **Schema & File Count Validation:** Ensure exactly 10 images are in `images/` (no stale drafts). `listing.validate()` must report **0 problems**.
3. **Etsy File Size Caps:** Max 5 files per listing, max 20 MB each.
4. **Trademark Audit:** Zero brand names (Apple, Hydroflask, Disney, Cricut logos on products). Generic descriptions only.
