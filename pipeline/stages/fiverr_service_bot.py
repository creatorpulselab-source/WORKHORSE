import os
import json
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional
import shutil

class FiverrServiceBot:
    def __init__(self, output_base: str = "F:/WORKHORSE/workspace/fiverr_deliveries"):
        self.output_base = Path(output_base)
        self.output_base.mkdir(parents=True, exist_ok=True)

        self.gigs = {
            "gig_retouch": {
                "id": "gig_retouch",
                "title": "I will color grade and retouch your glamour & model photo shoot",
                "category": "Graphics & Design > Image Editing > Photo Retouching",
                "search_tags": ["boudoir retouch", "glamour edit", "photo retouching", "color grading", "skin smoothing"],
                "pricing": {
                    "basic": {"name": "Essential Glamour", "price": "$20", "desc": "5 Photos: Skin smoothing + 1 color grade + 4:5 Instagram crop", "delivery": "1 Day"},
                    "standard": {"name": "Full Editorial Drop", "price": "$45", "desc": "15 Photos: Bilateral smoothing + 2 color grades + 4:5 & 9:16 crops + watermarked teasers", "delivery": "2 Days"},
                    "premium": {"name": "VIP Studio Master Set", "price": "$85", "desc": "40 Photos: Complete batch retouch + all 5 color grades + story crops + high-res ZIP", "delivery": "3 Days"}
                },
                "description": """Are you a content creator, glamour model, or photographer looking for magazine-quality retouching without the plastic, fake look?

I provide elite, studio-grade retouching tailored specifically for boudoir, glamour, and creator photography. Using advanced frequency-separation techniques, I soften blemishes and balance skin tones while preserving 100% of your natural skin pores, eyelashes, and hair texture!

✨ WHAT YOU GET:
• High-End Bilateral Skin Smoothing (Flawless yet 100% natural)
• Cinematic Color Grading (Moody Boudoir, Golden Hour, Cyber Neon, B&W Noir, 35mm Film)
• Optimized Social Crops (4:5 Instagram Portrait & 9:16 Vertical Story/Reel)
• Promotional Watermarked Teasers ready to post on social media
• Full Resolution Master JPEGs (300 DPI)

Send over your raw shoot and let's create stunning editorial results!"""
            },
            "gig_teaser": {
                "id": "gig_teaser",
                "title": "I will create a 60s viral video teaser and vertical reels from your footage",
                "category": "Video & Animation > Video Editing > Social Media Videos",
                "search_tags": ["video teaser", "reels editor", "promo video", "creator video", "short form video"],
                "pricing": {
                    "basic": {"name": "Quick Teaser Reel", "price": "$30", "desc": "One 30-60s teaser cut from raw footage + 6 high-res pose screenshots", "delivery": "1 Day"},
                    "standard": {"name": "Social Promo Duo", "price": "$65", "desc": "60s Master teaser + 9:16 Vertical Reel cut + spoken hook clips + 6 pose stills", "delivery": "2 Days"},
                    "premium": {"name": "Full Release Video Kit", "price": "$120", "desc": "60s Teaser + 9:16 Reel + 1:1 Square + Audio Hook Extraction + Full promo package", "delivery": "3 Days"}
                },
                "description": """Turn your raw photoshoot or behind-the-scenes footage into high-converting promotional video teasers that drive subscriptions and sales!

I will professionally edit your raw footage into an alluring, high-energy 60-second teaser and vertical 9:16 social reel optimized for Instagram Reels, TikTok, X, and subscription platforms.

✨ WHAT IS INCLUDED:
• Fast-paced cinematic cuts capturing the most captivating moments
• 9:16 Vertical format conversion for mobile-first engagement
• 1080p / 4K 60fps high-bitrate video export
• 6 High-resolution pose screenshot captures for promo flyers
• Audio isolation and spoken hook detection

Order now to elevate your video promo workflow!"""
            },
            "gig_copy": {
                "id": "gig_copy",
                "title": "I will write high-converting social captions and hashtag kits for creators",
                "category": "Writing & Translation > Social Media Copywriting",
                "search_tags": ["creator captions", "onlyfans captions", "social media copy", "hashtag research", "content strategy"],
                "pricing": {
                    "basic": {"name": "Single Drop Kit", "price": "$15", "desc": "5 Platform captions (OnlyFans, IG, X, TikTok, Reddit) + 30 researched hashtags", "delivery": "1 Day"},
                    "standard": {"name": "Weekly Release Plan", "price": "$40", "desc": "7 Days of promotional captions + PPV teaser hooks + viral short-form scripts", "delivery": "2 Days"},
                    "premium": {"name": "Monthly Agency Kit", "price": "$90", "desc": "30 Days of comprehensive multi-platform release copy + PPV upsell scripts + hashtags", "delivery": "3 Days"}
                },
                "description": """Struggling to write captions that actually get clicks, tips, and unlocks? 

I craft psychological, high-converting social media copy designed specifically for boudoir creators, adult performers, and glamour models. Every caption uses proven hooks that pique curiosity, build intimacy, and convert casual scrollers into paying VIPs.

✨ WHAT YOU RECEIVE:
• OnlyFans / Fansly PPV Teaser Hooks (Curiosity-driven paywall text)
• Instagram Captions (Algorithm-friendly with call-to-actions)
• X / Twitter Teasers (Spicy, punchy, high engagement)
• TikTok / Reels Sound Hooks (Trending short-form hooks)
• Reddit Captions (Authentic, community-compliant)
• 30 Researched Niche Hashtags

Boost your unlock rates today with elite creator copy!"""
            },
            "gig_banner": {
                "id": "gig_banner",
                "title": "I will design custom OnlyFans / Fansly promo banners and tip menus",
                "category": "Graphics & Design > Web & Mobile Design > Social Media Graphics",
                "search_tags": ["onlyfans banner", "tip menu", "fansly header", "cam profile", "creator graphics"],
                "pricing": {
                    "basic": {"name": "Header Banner", "price": "$20", "desc": "Custom high-resolution OnlyFans / Fansly welcome header banner", "delivery": "1 Day"},
                    "standard": {"name": "Banner & Tip Menu Duo", "price": "$45", "desc": "Header banner + Custom styled Tip Menu graphic + room rules card", "delivery": "2 Days"},
                    "premium": {"name": "Complete Branding Suite", "price": "$85", "desc": "Header banner + Tip menu + Schedule flyer + OBS webcam stream overlay HTML", "delivery": "3 Days"}
                },
                "description": """First impressions determine whether a fan subscribes or leaves. Transform your profile into a luxury VIP destination with custom branded graphics!

I design custom OnlyFans / Fansly welcome banners, high-converting tip menus, and interactive OBS stream overlays that look sleek, professional, and alluring.

✨ PACKAGE OPTIONS:
• Custom Profile Headers & Banners (16:9 & 3:1 aspect ratios)
• Interactive Tip Menus (Table & Badge Card layouts)
• OBS Webcam Stream Overlays (Transparent floating tip menus for live broadcasts)
• VIP Reward & PPV Price Flyers
• Ready-to-use HTML/CSS code or high-res PNG/JPG graphics

Order now to give your creator page the 5-star look it deserves!"""
            },
            "gig_photo_to_3d": {
                "id": "gig_photo_to_3d",
                "title": "I will convert your 2D photo into a 3D PBR model and textured GLB asset",
                "category": "Graphics & Design > 3D Modeling & Rendering > 3D Models",
                "search_tags": ["photo to 3d", "3d model", "pbr texture", "glb model", "game asset"],
                "pricing": {
                    "basic": {"name": "Single 3D Mesh & Preview", "price": "$35", "desc": "1 Photo/Product converted to textured 3D GLB/OBJ + 2K PBR materials + 360 MP4 turntable preview", "delivery": "1 Day"},
                    "standard": {"name": "Pro Game & VR Asset", "price": "$75", "desc": "3 Angles/Photos + 4K PBR Maps (Albedo, Normal, Roughness) + GLB/FBX/USDZ + Interactive HTML 3D viewer", "delivery": "2 Days"},
                    "premium": {"name": "Commercial 3D Product Suite", "price": "$150", "desc": "Up to 8 Objects/Assets + 4K PBR textures + Unreal/Unity ready + 4K turntable video + full source files", "delivery": "3 Days"}
                },
                "description": """Need a photorealistic 3D model from a single photo, concept sketch, or product image?

Using state-of-the-art neural reconstruction pipelines (Trellis.2 & Pixal3D), I convert your 2D images into game-ready, production-quality 3D assets with physically-based rendering (PBR) textures!

✨ PERFECT FOR:
• eCommerce & Shopify AR (Let buyers view your product in 3D / augmented reality)
• Indie Game Developers (Clean low/mid-poly meshes for Unreal Engine 5 & Unity)
• 3D Printing & Prototyping (.OBJ and manifold .STL files)
• Apple Vision Pro & AR Quick Look (.USDZ native format)
• Metaverse & VRChat Avatars and Props

📦 WHAT YOU RECEIVE:
• Industry-standard 3D formats: .GLB, .OBJ, .FBX, and .USDZ
• 2K to 4K PBR Texture Maps (Base Color / Albedo, Normal, Roughness, Metallic, Ambient Occlusion)
• 360° MP4 Turntable Preview Video showcasing geometry and lighting
• Interactive HTML 3D Web Viewer (Drag to rotate in any web browser)
• 100% Commercial Usage Rights

Simply send a clear photo or concept art, and I will synthesize your 3D model!"""
            },
            "gig_photo_to_video": {
                "id": "gig_photo_to_video",
                "title": "I will animate your still photo into a 4K 60fps cinematic video loop",
                "category": "Video & Animation > Animation for Streamers > Animated Intros & Loops",
                "search_tags": ["photo animation", "cinemagraph", "video loop", "animated portrait", "motion photo"],
                "pricing": {
                    "basic": {"name": "Micro Motion Loop", "price": "$30", "desc": "1 Photo animated: realistic micro-motion (breathing, hair sway, light drift) + 1080p 10s seamless loop", "delivery": "1 Day"},
                    "standard": {"name": "Cinematic 4K Motion Scene", "price": "$65", "desc": "3 Photos animated + 4K 60fps ProRes & MP4 + dynamic camera motion (push-in/orbit) + ambient audio SFX", "delivery": "2 Days"},
                    "premium": {"name": "Ultimate Living Portrait Suite", "price": "$125", "desc": "6 Photos animated + 4K 60fps + 9:16 Vertical Reels & 16:9 Landscape + Custom lighting animation + Sound design", "delivery": "3 Days"}
                },
                "description": """Transform your static photography into hypnotic, living cinematic motion that captures attention and stops the scroll!

Using cutting-edge AI video synthesis (WAN 2.1 & LTX-Video) combined with professional optical flow interpolation, I animate still portraits, landscapes, and promotional photos into fluid 60fps seamless loops.

✨ PERFECT FOR:
• Spotify Canvas & Apple Music Animated Album Covers
• Twitch / Kick Streamer Screens (Be Right Back, Stream Starting Soon)
• Instagram Reels, TikTok & YouTube Shorts Video Hooks
• Luxury Brand Video Billboards & Digital Menu Displays
• Creator Teasers & VIP Content Announcements

📦 WHAT YOU RECEIVE:
• 4K Ultra-HD & 1080p High-Bitrate MP4 & Apple ProRes 422 exports
• 100% Seamless Looping (Zero jarring jump cuts or stutter)
• Natural Organic Physics: Realistic hair movement, subtle breathing, eye micro-movements, atmospheric lighting drifts
• Both 16:9 Widescreen & 9:16 Vertical Social formats
• Ambient Sound Design & Atmospheric SFX track (Standard & Premium)

Send me your favorite still photo and watch it come to life!"""
            },
            "gig_relight": {
                "id": "gig_relight",
                "title": "I will relight your portrait and replace backdrop with luxury studio lighting",
                "category": "Graphics & Design > Image Editing > Photo Retouching",
                "search_tags": ["studio relighting", "headshot edit", "background change", "portrait lighting", "editorial photo"],
                "pricing": {
                    "basic": {"name": "Studio Key Light", "price": "$25", "desc": "3 Portraits relit with realistic studio lighting (Rembrandt, Beauty Dish, or Warm Sun) + Clean solid/textured backdrop", "delivery": "1 Day"},
                    "standard": {"name": "Executive Studio Glow", "price": "$50", "desc": "10 Portraits relit + 3 Lighting styles per photo (Golden hour, Cyber neon, Editorial softbox) + Luxury penthouse/office backdrop", "delivery": "2 Days"},
                    "premium": {"name": "Celebrity Editorial Portfolio", "price": "$95", "desc": "25 Portraits fully relit + Full lighting consistency across set + High-end commercial studio environments + 300 DPI master exports", "delivery": "3 Days"}
                },
                "description": """Tired of harsh shadows, yellow indoor lighting, or boring bedroom backgrounds ruining your portraits?

I provide physically accurate neural portrait relighting and realistic environment replacement using IC-Light diffusion models. We don't just cut out your subject and paste them onto a flat wallpaper—we mathematically recalculate the light rays, rim lighting, ambient bounces, and shadow falloff so your subject blends seamlessly into their new luxury environment!

✨ LIGHTING STYLES AVAILABLE:
• Rembrandt Studio Key Light (Classic dramatic portraiture)
• Golden Hour Warm Sunset (Flattering outdoor amber glow)
• Soft Editorial Beauty Dish (Flawless, diffused magazine headshot)
• Cyber Neon / Dual Gel (Moody magenta and cyan creative edge)
• Minimalist High-Key Daylight (Crisp commercial clean look)

📦 LUXURY BACKDROPS INCLUDED:
• Architectural Concrete & Warm Wood Slats (Modern Studio)
• High-Rise Penthouse Skyline (Executive / Corporate)
• Moody Dark Velvet Studio Backdrop
• Sun-Drenched Parisian Loft / Clean Scandinavian Interior

100% natural skin pore retention. Zero plastic look. Send your photos today!"""
            }
        }

    def get_all_gigs(self) -> List[Dict[str, Any]]:
        return list(self.gigs.values())

    def get_gig(self, gig_id: str) -> Optional[Dict[str, Any]]:
        return self.gigs.get(gig_id)

    def generate_delivery_note(self, gig_id: str, client_name: str = "Valued Client") -> str:
        """Generate a professional 5-star review request delivery message tailored to the gig."""
        gig = self.gigs.get(gig_id, self.gigs["gig_retouch"])
        
        # Gig-specific delivery highlights
        gig_deliverable_bullets = {
            "gig_photo_to_3d": """- Master 3D Asset Package (.GLB, Watertight 3D-Printable .STL, .OBJ, and .USDZ files).
- High-Resolution PBR Texture Maps (Base Color, Normal, Roughness, Metallic) + Blender 5.2 Manifold Proof.
- 360° Turntable Video Preview showcasing geometry and lighting.
- Browser-based 3D interactive viewer for quick 1-click preview.""",
            "gig_photo_to_video": """- Ultra-HD 4K 60fps Seamless Looping Master Video (MP4 & ProRes, DaVinci Resolve Super Scale mastered).
- Formatted crops for both 16:9 Widescreen and 9:16 Vertical Reels/Shorts.
- Atmospheric sound design and ambient audio track.
- Seamless loop playback verification (zero stutter).""",
            "gig_relight": """- Full-Resolution 300 DPI Relit Master Portraits.
- Signature studio lighting variations (Key Light, Golden Hour, Editorial).
- Realistic architectural environment integration with accurate light falloff.
- Original framing and high-resolution JPEG master files.""",
            "gig_retouch": """- All high-resolution master retouched deliverables (300 DPI).
- 5 Signature editorial color grades (Golden Hour, Boudoir, 35mm, Cyber Neon, Noir).
- Bilateral frequency-separation preserving 100% natural skin texture.
- Formatted and optimized assets ready for immediate posting.""",
            "gig_teaser": """- 60-Second Master Promotional Teaser (NVENC 60fps).
- 9:16 Vertical Social Reel cut optimized for mobile engagement.
- 6 High-resolution pose screenshot captures for promo flyers.
- Audio hook extraction and isolation.""",
            "gig_copy": """- Multi-platform high-converting captions (Instagram, X, OnlyFans, TikTok, Reddit).
- High-engagement psychological teaser hooks and curiosity openers.
- 30 Niche-researched algorithmic hashtags for maximum reach.""",
            "gig_banner": """- Custom high-resolution profile header banners (16:9 & 3:1).
- Custom styled Tip Menu graphic & room rules card.
- Ready-to-use PNG/JPG graphics and optional OBS webcam overlay code."""
        }
        
        bullets = gig_deliverable_bullets.get(gig_id, """- All high-resolution master deliverables organized in your download package.
- Formatted and optimized assets ready for immediate posting/publishing.
- Complete release bundle formatted to platform guidelines.""")

        note = f"""Hello {client_name}! 🌟

Your order for '{gig['title']}' is officially completed and packaged!

📦 WHAT IS INCLUDED IN YOUR DELIVERY:
{bullets}

💡 A QUICK FAVOR:
If you love the quality of this delivery, please consider leaving a 5-STAR REVIEW! ⭐⭐⭐⭐⭐
As a specialized creator studio, your feedback helps us tremendously and means the world to our team.

If there is anything you'd like adjusted or if you need any revisions, please let me know right here before completing the order—I am always happy to ensure you are 100% thrilled with your results!

Thank you again for your business, and I look forward to working on your next project!

Best regards,
CreatorMediaLab Studio"""
        return note

    def fulfill_order(
        self,
        gig_id: str,
        order_number: str = "FO_1001",
        client_name: str = "CreatorClient",
        assets: Optional[List[str]] = None,
        notes: str = ""
    ) -> Dict[str, Any]:
        """Bundle finished files into a professional client delivery package with review note."""
        order_dir = self.output_base / f"{order_number}_{gig_id}"
        order_dir.mkdir(parents=True, exist_ok=True)

        delivery_note = self.generate_delivery_note(gig_id, client_name)
        (order_dir / "DELIVERY_NOTE_AND_INSTRUCTIONS.txt").write_text(delivery_note, encoding="utf-8")

        # Copy any generated assets into order directory
        copied_files = ["DELIVERY_NOTE_AND_INSTRUCTIONS.txt"]
        if assets:
            for a in assets:
                src = Path(a)
                if src.exists() and src.is_file():
                    dest = order_dir / src.name
                    shutil.copy(src, dest)
                    copied_files.append(src.name)

        # Create Client Delivery ZIP
        zip_path = self.output_base / f"{order_number}_DELIVERY_PACKAGE.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(order_dir):
                for file in files:
                    fp = Path(root) / file
                    zipf.write(fp, arcname=str(fp.relative_to(order_dir)))

        return {
            "status": "completed",
            "order_number": order_number,
            "gig_id": gig_id,
            "client_name": client_name,
            "delivery_zip": str(zip_path),
            "delivery_zip_name": zip_path.name,
            "delivery_zip_size_kb": round(zip_path.stat().st_size / 1024, 1),
            "files_count": len(copied_files),
            "delivery_note": delivery_note
        }

if __name__ == "__main__":
    bot = FiverrServiceBot()
    print("Fiverr Service Bot initialized. Total gigs:", len(bot.gigs))
