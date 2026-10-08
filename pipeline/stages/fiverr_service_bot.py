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
                "title": "I will create a 60s viral video teaser & 9:16 vertical reels from your raw shoot",
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
                "title": "I will write high-converting social media captions and hashtag kits for content creators",
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
            }
        }

    def get_all_gigs(self) -> List[Dict[str, Any]]:
        return list(self.gigs.values())

    def get_gig(self, gig_id: str) -> Optional[Dict[str, Any]]:
        return self.gigs.get(gig_id)

    def generate_delivery_note(self, gig_id: str, client_name: str = "Valued Client") -> str:
        """Generate a professional 5-star review request delivery message."""
        gig = self.gigs.get(gig_id, self.gigs["gig_retouch"])
        note = f"""Hello {client_name}! 🌟

Your order for '{gig['title']}' is officially completed and packaged!

📦 WHAT IS INCLUDED IN YOUR DELIVERY:
- All high-resolution master deliverables organized in your download package.
- Formatted and optimized assets ready for immediate posting/publishing.
- Complete release bundle formatted to social platform guidelines.

💡 A QUICK FAVOR:
If you love the quality of this delivery, please consider leaving a 5-STAR REVIEW! ⭐⭐⭐⭐⭐
As a specialized creator studio, your feedback helps us tremendously and means the world to our team.

If there is anything you'd like adjusted or if you need any revisions, please let me know right here before completing the order—I am always happy to ensure you are 100% thrilled with your results!

Thank you again for your business, and I look forward to working on your next shoot!

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
