"""Builds the media kit (9 images) + listing.md for a quote pack that pack.py already generated.

Run:  F:\\WORKHORSE\\.venv\\Scripts\\python.exe -m etsy_factory.typo.build_listing <sarcasm|faith|mom> [--no-mockups]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image

sys.path.insert(0, r"F:\WORKHORSE")

from etsy_factory import listing as lst
from etsy_factory.typo import cover2
from etsy_factory.typo import media as M
from etsy_factory.typo.pack import get_niche

# Chest / body print areas as fractions of the photo (x0, y0, x1, y1) - calibrated in media.MOCKUP_BOXES
BOXES = M.MOCKUP_BOXES

TEAL, ORANGE, PURPLE, GREEN = (0, 150, 170), (255, 112, 67), (88, 36, 120), (46, 160, 90)

# Per-niche media settings. ribbons = [(face, dark), (face, dark)] for the vibrant cover; vbg = collage background.
MEDIA: Dict[str, Dict] = {
    "sarcasm": dict(
        kicker="FUNNY SARCASTIC", title_lines=["QUOTES SVG + PNG", "CUT FILE BUNDLE"], sub="CRICUT  *  SILHOUETTE  *  SUBLIMATION",
        grid_title=["FUNNY SARCASTIC", "QUOTES SVG PNG BUNDLE"], grid_sub="Cricut * Silhouette * Sublimation",
        sheet1=("Sassy Sarcastic Designs", "{n} original quote designs - a peek inside"), sheet2=("Color PNGs For Sublimation", "ready to print, press and sell"),
        ribbons=[((255, 64, 129), (150, 20, 80)), ((0, 150, 170), (0, 90, 110))], vbg=(46, 14, 84), bg=(255, 248, 236),
        mockups=[("tee_black", "Eye roll champion", "PNG_White"), ("tee_oat", "Queen of snark", "PNG_Color"), ("tote", "Girl bye", "PNG_Black")],
        chip_cols=[(255, 64, 129), TEAL, ORANGE, PURPLE, GREEN]),
    "faith": dict(
        kicker="CHRISTIAN FAITH", title_lines=["QUOTES SVG + PNG", "CUT FILE BUNDLE"], sub="BIBLE VERSES  *  CRICUT  *  SUBLIMATION",
        grid_title=["CHRISTIAN FAITH", "QUOTES SVG PNG BUNDLE"], grid_sub="Scripture * Encouragement * Worship",
        sheet1=("Faith Over Fear", "{n} faith & scripture designs - a peek inside"), sheet2=("Color PNGs For Sublimation", "ready to print, press and sell"),
        ribbons=[((28, 120, 130), (14, 70, 80)), ((205, 150, 50), (130, 88, 18))], vbg=(24, 40, 62), bg=(250, 246, 238),
        mockups=[("tee_black", "Faith over fear", "PNG_White"), ("tee_oat", "Blessed beyond measure", "PNG_Color"), ("tote", "Grace upon grace", "PNG_Black")],
        chip_cols=[(28, 120, 130), (176, 120, 90), (205, 150, 50), (88, 60, 110), GREEN]),
    "mom": dict(
        kicker="MOM LIFE MAMA", title_lines=["QUOTES SVG + PNG", "CUT FILE BUNDLE"], sub="MAMA  *  BOY MOM  *  GIRL MOM  *  SUBLIMATION",
        grid_title=["MOM LIFE MAMA", "QUOTES SVG PNG BUNDLE"], grid_sub="Cricut * Silhouette * Sublimation",
        sheet1=("Mama Needs Coffee", "{n} mom life designs - a peek inside"), sheet2=("Color PNGs For Sublimation", "ready to print, press and sell"),
        ribbons=[((236, 98, 100), (150, 44, 60)), ((52, 150, 130), (26, 92, 80))], vbg=(84, 28, 60), bg=(255, 246, 240),
        mockups=[("tee_black", "Mom life", "PNG_White"), ("tee_oat", "Mama bear", "PNG_Color"), ("tote", "Boy mom", "PNG_Black")],
        chip_cols=[(236, 98, 100), (52, 150, 130), (240, 170, 60), (120, 80, 150), GREEN]),
    "teacher": dict(
        kicker="TEACHER LIFE", title_lines=["QUOTES SVG + PNG", "CUT FILE BUNDLE"], sub="BACK TO SCHOOL  *  CRICUT  *  SUBLIMATION",
        grid_title=["TEACHER LIFE", "QUOTES SVG PNG BUNDLE"], grid_sub="Cricut * Silhouette * Sublimation",
        sheet1=("Teach Love Inspire", "{n} teacher designs - a peek inside"), sheet2=("Color PNGs For Sublimation", "ready to print, press and sell"),
        ribbons=[((232, 84, 72), (140, 36, 32)), ((36, 110, 150), (18, 66, 96))], vbg=(24, 44, 78), bg=(255, 249, 238),
        mockups=[("tee_black", "Teacher life", "PNG_White"), ("tee_oat", "Teach love inspire", "PNG_Color"), ("tote", "Best teacher ever", "PNG_Black")],
        chip_cols=[(232, 84, 72), (36, 110, 150), (250, 180, 50), (120, 80, 150), GREEN]),
    "nurse": dict(
        kicker="NURSE LIFE", title_lines=["QUOTES SVG + PNG", "CUT FILE BUNDLE"], sub="NURSES WEEK  *  CRICUT  *  SUBLIMATION",
        grid_title=["NURSE LIFE", "QUOTES SVG PNG BUNDLE"], grid_sub="Cricut * Silhouette * Sublimation",
        sheet1=("Nurse Life", "{n} nurse designs - a peek inside"), sheet2=("Color PNGs For Sublimation", "ready to print, press and sell"),
        ribbons=[((28, 150, 160), (14, 88, 100)), ((236, 100, 130), (150, 44, 72))], vbg=(16, 52, 72), bg=(250, 248, 244),
        mockups=[("tee_black", "Nurse life", "PNG_White"), ("tee_oat", "Nurses rock", "PNG_Color"), ("tote", "Best nurse ever", "PNG_Black")],
        chip_cols=[(28, 150, 160), (236, 100, 130), (250, 180, 50), (120, 80, 150), GREEN]),
    "coffee": dict(
        kicker="COFFEE LOVER", title_lines=["QUOTES SVG + PNG", "CUT FILE BUNDLE"], sub="MUG  *  TUMBLER  *  CRICUT  *  SUBLIMATION",
        grid_title=["COFFEE LOVER", "QUOTES SVG PNG BUNDLE"], grid_sub="Latte * Iced Coffee * Caffeine",
        sheet1=("But First Coffee", "{n} coffee designs - a peek inside"), sheet2=("Color PNGs For Sublimation", "ready to print, press and sell"),
        ribbons=[((176, 108, 64), (100, 58, 28)), ((60, 120, 110), (30, 76, 70))], vbg=(58, 36, 28), bg=(255, 247, 236),
        mockups=[("tee_black", "But first coffee", "PNG_White"), ("tee_oat", "Coffee is my love language", "PNG_Color"), ("tote", "Iced coffee please", "PNG_Black")],
        chip_cols=[(176, 108, 64), (60, 120, 110), (240, 170, 60), (120, 80, 150), GREEN]),
    "valentine": dict(
        kicker="VALENTINES DAY", title_lines=["QUOTES SVG + PNG", "CUT FILE BUNDLE"], sub="LOVE  *  GALENTINE  *  CRICUT  *  SUBLIMATION",
        grid_title=["VALENTINES DAY", "QUOTES SVG PNG BUNDLE"], grid_sub="Love * Galentine * Kids",
        sheet1=("Be Mine", "{n} valentine designs - a peek inside"), sheet2=("Color PNGs For Sublimation", "ready to print, press and sell"),
        ribbons=[((226, 48, 92), (130, 18, 52)), ((120, 60, 140), (70, 28, 88))], vbg=(110, 20, 50), bg=(255, 244, 246),
        mockups=[("tee_black", "Be mine", "PNG_White"), ("tee_oat", "Love bug", "PNG_Color"), ("tote", "Hugs and kisses", "PNG_Black")],
        chip_cols=[(226, 48, 92), (120, 60, 140), (250, 170, 60), (36, 140, 160), GREEN]),
    "motivational": dict(
        kicker="MOTIVATIONAL", title_lines=["QUOTES SVG + PNG", "CUT FILE BUNDLE"], sub="POSITIVE VIBES  *  CRICUT  *  SUBLIMATION",
        grid_title=["MOTIVATIONAL", "QUOTES SVG PNG BUNDLE"], grid_sub="Positive * Inspirational * Self Love",
        sheet1=("You Got This", "{n} positive designs - a peek inside"), sheet2=("Color PNGs For Sublimation", "ready to print, press and sell"),
        ribbons=[((250, 130, 60), (150, 70, 20)), ((40, 110, 150), (20, 66, 98))], vbg=(30, 50, 82), bg=(255, 249, 238),
        mockups=[("tee_black", "You got this", "PNG_White"), ("tee_oat", "Stay positive", "PNG_Color"), ("tote", "Be kind", "PNG_Black")],
        chip_cols=[(250, 130, 60), (40, 110, 150), (240, 180, 50), (120, 80, 150), GREEN]),
    "pets": dict(
        kicker="DOG MOM  CAT MOM", title_lines=["QUOTES SVG + PNG", "CUT FILE BUNDLE"], sub="PET LOVER  *  CRICUT  *  SUBLIMATION",
        grid_title=["DOG MOM CAT MOM", "QUOTES SVG PNG BUNDLE"], grid_sub="Dog * Cat * Rescue",
        sheet1=("Dog Mom Life", "{n} pet lover designs - a peek inside"), sheet2=("Color PNGs For Sublimation", "ready to print, press and sell"),
        ribbons=[((204, 108, 64), (120, 56, 24)), ((52, 120, 140), (26, 72, 88))], vbg=(64, 44, 34), bg=(255, 247, 238),
        mockups=[("tee_black", "Dog mom life", "PNG_White"), ("tee_oat", "Cat mom", "PNG_Color"), ("tote", "Dog dad", "PNG_Black")],
        chip_cols=[(204, 108, 64), (52, 120, 140), (240, 170, 60), (120, 80, 150), GREEN]),
    "grad": dict(
        kicker="GRADUATION 2027", title_lines=["QUOTES SVG + PNG", "CUT FILE BUNDLE"], sub="CLASS OF 2027  *  CRICUT  *  SUBLIMATION",
        grid_title=["GRADUATION 2027", "QUOTES SVG PNG BUNDLE"], grid_sub="Senior * Grad * Proud Family",
        sheet1=("Class Of 2027", "{n} graduation designs - a peek inside"), sheet2=("Color PNGs For Sublimation", "ready to print, press and sell"),
        ribbons=[((30, 52, 120), (14, 26, 70)), ((200, 150, 30), (120, 86, 10))], vbg=(18, 30, 70), bg=(252, 249, 240),
        mockups=[("tee_black", "Class of 2027", "PNG_White"), ("tee_oat", "Grad life", "PNG_Color"), ("tote", "Senior 2027", "PNG_Black")],
        chip_cols=[(30, 52, 120), (200, 150, 30), (210, 70, 80), (36, 140, 130), GREEN]),
    "military": dict(
        kicker="MILITARY MOM + WIFE", title_lines=["QUOTES SVG + PNG", "CUT FILE BUNDLE"], sub="HOMEFRONT  *  CRICUT  *  SUBLIMATION",
        grid_title=["MILITARY MOM + WIFE", "QUOTES SVG PNG BUNDLE"], grid_sub="Deployment * Homecoming * Proud Family",
        sheet1=("Proud Military Family", "{n} homefront designs - a peek inside"), sheet2=("Color PNGs For Sublimation", "ready to print, press and sell"),
        ribbons=[((34, 52, 90), (16, 26, 54)), ((176, 36, 48), (110, 18, 28))], vbg=(30, 38, 24), bg=(250, 247, 238),
        mockups=[("tee_black", "Proud military mom", "PNG_White"), ("tee_oat", "Military wife strong", "PNG_Color"), ("tote", "Military mom life", "PNG_Black")],
        chip_cols=[(34, 52, 90), (176, 36, 48), (120, 130, 90), (88, 74, 52), GREEN]),
    "vacation": dict(
        kicker="MAGICAL FAMILY VACATION", title_lines=["QUOTES SVG + PNG", "CUT FILE BUNDLE"], sub="MATCHING SHIRTS  *  CRICUT  *  SUBLIMATION",
        grid_title=["MAGICAL VACATION", "QUOTES SVG PNG BUNDLE"], grid_sub="Family Trip * Girls Trip * Memory Makers",
        sheet1=("Magical Family Trips", "{n} vacation designs - a peek inside"), sheet2=("Color PNGs For Sublimation", "ready to print, press and sell"),
        ribbons=[((236, 100, 160), (150, 50, 100)), ((90, 40, 120), (50, 20, 70))], vbg=(44, 24, 84), bg=(255, 246, 250),
        mockups=[("tee_black", "Magical vacation", "PNG_White"), ("tee_oat", "Making memories together", "PNG_Color"), ("tote", "Family vacation mode", "PNG_Black")],
        chip_cols=[(236, 100, 160), (90, 40, 120), (246, 190, 70), (30, 70, 120), GREEN]),
}


def _find(files: Path, sub: str, idx: int) -> Optional[Path]:
    hits = sorted((files / sub).glob(f"{idx:03d}_*.png"))
    return hits[0] if hits else None


def _idx_for(meta: List[Dict], text: str) -> Optional[int]:
    t = text.lower()
    for m in meta:
        if m["text"].lower() == t:
            return m["index"]
    for m in meta:
        if t in m["text"].lower():
            return m["index"]
    return None


def _mockup(kind: str, files: Path, idx: int, sub: str, out: Path, seed: int = 11) -> Optional[Path]:
    prompt, _ = M.MOCKUP_PROMPTS[kind]
    photo = M.comfy_photo(kind, prompt, seed=seed)
    src = _find(files, sub, idx)
    if photo is None or src is None:
        print(f"  ! mockup {kind} skipped (photo={photo}, design={src})")
        return None
    ph = Image.open(photo).convert("RGB").resize((M.SIZE, M.SIZE), Image.LANCZOS)
    des = Image.open(src).convert("RGBA")
    bb = des.getbbox()
    if bb:
        des = des.crop(bb)
    f = BOXES[kind]
    box = (int(f[0] * M.SIZE), int(f[1] * M.SIZE), int(f[2] * M.SIZE), int(f[3] * M.SIZE))
    return M.save_jpg(M.place_on_fabric(ph, des, box), out)


def build(key: str, mockups: bool = True) -> Dict:
    niche = get_niche(key)
    cfg = MEDIA[key]
    root = Path(r"F:\WORKHORSE\workspace\etsy_listings") / niche.slug
    files, thumbs, imgs = root / "files", root / "_work" / "thumbs", root / "images"
    meta: List[Dict] = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    n = len(meta)
    imgs.mkdir(parents=True, exist_ok=True)
    for old in imgs.glob("*.jpg"):
        old.unlink()
    pal = niche.palettes[0]
    accent, ink = pal["accent"], pal["main"]
    chips = cfg["chip_cols"]
    bg = cfg["bg"]

    cover2.vibrant(meta, thumbs, imgs / "01_cover.jpg", str(n), cfg["kicker"], cfg["title_lines"], cfg["sub"], cfg["ribbons"], (26, 26, 34), cfg["vbg"],
                   [("SVG", "Cricut\nfriendly", chips[0]), ("PNG", "300 DPI\ntransparent", chips[1]), ("DXF", "Laser\nready", chips[2]),
                    ("EPS", "Illustrator\nCorel", chips[3]), ("USE", "Commercial\nincluded", chips[4])])
    M.cover(meta, thumbs, imgs / "02_cover_grid.jpg", str(n), cfg["grid_title"], cfg["grid_sub"], accent, ink,
            [("SVG", chips[0]), ("PNG", chips[1]), ("DXF", chips[2]), ("EPS", chips[3]), ("300DPI", ink)])
    s1, s2 = cfg["sheet1"], cfg["sheet2"]
    M.sheet(meta, thumbs, imgs / "03_preview_1.jpg", s1[0], s1[1].format(n=n), accent, ink, bg, 0, 20)
    M.sheet(meta, thumbs, imgs / "04_preview_2.jpg", s2[0], s2[1], chips[1], ink, bg, 40, 20)
    nxt = 5
    if mockups:
        for kind, text, sub in cfg["mockups"]:
            idx = _idx_for(meta, text)
            if idx is None:
                print(f"  ! no design matching '{text}'")
                continue
            if _mockup(kind, files, idx, sub, imgs / f"{nxt:02d}_mockup_{kind}.jpg"):
                nxt += 1
    M.info_card(imgs / f"{nxt:02d}_formats.jpg", "What's in your download", "instant digital download",
                [("SVG", "One welded cut path per design - Cricut, Silhouette, Glowforge, xTool"),
                 ("DXF + EPS", "Laser cutters, Illustrator, CorelDRAW, Inkscape"),
                 ("PNG black", "Transparent 300 dpi - light shirts, print-then-cut"),
                 ("PNG white", "Transparent 300 dpi - dark shirts and mugs"),
                 ("PNG color", "Multi-color 300 dpi - sublimation ready"),
                 ("PDF guide", "Quick-start and the commercial license")],
                accent, ink, bg, footer=f"{n} designs x 6 file types")
    nxt += 1
    M.info_card(imgs / f"{nxt:02d}_license.jpg", "Commercial use included", "small business friendly",
                [("YES", "Sell shirts, mugs, tumblers, totes, signs and stickers you make"),
                 ("500 units", "per design - no credit required"),
                 ("NO", "Reselling or sharing the digital files, or adding them to other bundles"),
                 ("Original", "Typography only - no characters, brands or logos"),
                 ("Help", "Message the shop if any file needs fixing")],
                chips[1], ink, bg)
    made = sorted(imgs.glob("[0-9][0-9]_*.jpg"))
    print("images:", [p.name for p in made])

    title = niche.title.format(n=n)
    if len(title) > 140:
        title = title[:140].rsplit(" ", 1)[0].rstrip(",")
    non_affil = ("\n- Independent family vacation & travel designs; not affiliated with or endorsed by any theme park or entertainment company."
                 if key == "vacation" else "")
    desc = (f"{niche.intro}\n\nWHAT YOU GET\n- {n} original {niche.short.lower()} quote designs\n"
            "- Every design in 6 formats: SVG, DXF, EPS, black PNG, white PNG and full-color PNG (300 dpi, transparent)\n"
            "- PDF quick-start guide and commercial license\n\n"
            f"PERFECT FOR\n{niche.uses}\n\nWORKS WITH\nCricut Design Space, Silhouette Studio (SVG needs Designer Edition - use the DXF otherwise), "
            "Glowforge, xTool, Brother ScanNCut, Inkscape, Illustrator, CorelDRAW, and sublimation printers.\n\n"
            "COMMERCIAL USE\nUse the designs on physical products you sell, up to 500 units per design, no credit needed. "
            "You may not resell or share the digital files.\n\n"
            "DESIGN & CREATION TRANSPARENCY\n"
            "- Original typography compositions and welded vector cut paths procedurally engineered by CraftyMyia using licensed commercial fonts and custom vector ornaments.\n"
            f"- Listing photos show digital 3D renders and AI-assisted lifestyle mockups to illustrate how the designs look when cut or printed.{non_affil}\n\n"
            "DIGITAL DOWNLOAD & COMPATIBILITY NOTICE\n"
            "- DIGITAL DOWNLOAD ONLY — no physical product will be shipped. Files are available instantly after purchase. Colors on screen may vary slightly from print.\n"
            "- All machine, software, and brand names (including Cricut, Silhouette, Glowforge, xTool, Brother, Adobe, and Corel) are trademarks of their respective owners; CraftyMyia is an independent studio and is not affiliated with or endorsed by them.")
    data = lst.write_listing(root, title=title, tags=niche.tags, description=desc, price_usd=niche.price,
                             sale_hint=f"list ${niche.list_price:.2f}, run a sale to show the discount", category="Craft Supplies & Tools > Patterns & How To > Digital",
                             materials="digital files", whats_in_the_files=[f"{n} designs x 6 formats (SVG, DXF, EPS, PNG black/white/color)", "PDF guide and license"])
    print(json.dumps({"title_chars": data["title_chars"], "problems": data["validation_problems"]}, indent=2))
    return data


if __name__ == "__main__":
    k = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "sarcasm"
    build(k, mockups="--no-mockups" not in sys.argv)
