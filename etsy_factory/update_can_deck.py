with open(r"F:\WORKHORSE\etsy_factory\assemble_can_holders_deck.py", "r", encoding="utf-8") as f:
    content = f.read()

bg_and_c1 = '''# -----------------------------------------------------------------------------
# CARD 01: HERO COVER (UNIVERSAL 3D BESTSELLER LAYOUT)
# -----------------------------------------------------------------------------
def make_bg_collage(seed: int = 42) -> Image.Image:
    """Builds a tilted collage of the 8 single can holder models in the background."""
    import random
    rng = random.Random(seed)
    single_files = [RENDERS_DIR / f"single_{i:02d}.png" for i in range(1, 9)]
    thumbs = []
    for p in single_files:
        if p.exists():
            im = Image.open(p).convert("RGBA")
            bbox = im.getbbox()
            if bbox:
                im = im.crop(bbox)
            th = im.resize((320, 320), Image.Resampling.LANCZOS)
            thumbs.append(th)

    if not thumbs:
        return Image.new("RGBA", (SIZE, SIZE), BG_COLOR + (255,))

    big = int(SIZE * 1.55)
    base = Image.new("RGBA", (big, big), BG_COLOR + (255,))
    order = thumbs[:]
    rng.shuffle(order)

    edge_cols = [
        (44, 98, 62),    # Forest Green
        (212, 92, 36),   # Terracotta
        (29, 99, 184),   # Denim Blue
        (200, 140, 30),  # Honey Ochre
        (123, 82, 148),  # Violet
        (45, 50, 55),    # Charcoal
    ]

    row_h, gap = 380, 35
    y, k = -60, 0
    while y < big:
        x = -rng.randrange(0, 200)
        while x < big:
            t = order[k % len(order)]
            k += 1
            cw, ch = 360, row_h
            card = M.rounded((cw, ch), 42, (255, 255, 255, 255), outline=rng.choice(edge_cols) + (255,), width=10)
            card.alpha_composite(t, ((cw - t.width) // 2, (ch - t.height) // 2))
            base.alpha_composite(card, (x, y))
            x += cw + gap
        y += row_h + gap

    base = base.rotate(8, resample=Image.Resampling.BICUBIC, center=(big // 2, big // 2), fillcolor=BG_COLOR + (255,))
    o = (big - SIZE) // 2
    cropped = base.crop((o, o, o + SIZE, o + SIZE))

    glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((80, 80, SIZE - 80, SIZE - 80), fill=BG_COLOR + (190,))
    cropped.alpha_composite(glow.filter(ImageFilter.GaussianBlur(140)))
    return cropped


def make_card_01() -> Image.Image:
    base = make_bg_collage(seed=42)

    # Central white rounded card container - perfectly centered!
    cw, ch = 1960, 1820
    cx, cy = (SIZE - cw) // 2, (SIZE - ch) // 2
    card = M.rounded((cw, ch), 85, (255, 255, 255, 255), outline=INK + (255,), width=12)
    M.shadowed(base, card, (cx, cy), blur=38, off=(0, 24), alpha=130)

    d = ImageDraw.Draw(base)

    # Top ribbon pill: "COMMERCIAL USE INCLUDED"
    rb = "COMMERCIAL USE INCLUDED"
    f_rb = M.fit(d, rb, M.poppins_x, 1250, 52)
    tw = M.text_w(d, rb, f_rb)
    pill = M.rounded((tw + 110, 96), 48, ACCENT + (255,))
    base.alpha_composite(pill, (SIZE // 2 - (tw + 110) // 2, cy - 48))
    d.text((SIZE // 2, cy), rb, font=f_rb, fill=WHITE, anchor="mm")

    # Primary Title Line
    ty = cy + 55
    t_text = "8 CAN & DRINK HOLDERS"
    fl = M.fit(d, t_text, M.anton, cw - 180, 115, 70)
    bb = d.textbbox((0, 0), t_text, font=fl, anchor="ma")
    d.text((SIZE // 2, ty - bb[1]), t_text, font=fl, fill=INK, anchor="ma")

    # Cursive Subtitle
    sub = "4-Cup Caddy  *  Can Coolers  *  Car Adapter  *  Adventure Holster"
    fs = M.fit(d, sub, M.pacifico, cw - 240, 52, 30)
    bbs = d.textbbox((0, 0), sub, font=fs, anchor="ma")
    sub_y = ty + (bb[3] - bb[1]) + 12
    d.text((SIZE // 2, sub_y - bbs[1]), sub, font=fs, fill=ACCENT, anchor="ma")

    # Hero Product Showcase in center of card (uncropped, centered!)
    hero_y = sub_y + (bbs[3] - bbs[1]) + 24
    hero_w = cw - 140
    hero_h = 1040

    p_cluster = RENDERS_DIR / "cluster_hero.png"
    if p_cluster.exists():
        im_hero = load_render_cropped(p_cluster)
        s = min((hero_w - 60) / im_hero.width, (hero_h - 60) / im_hero.height)
        nw, nh = int(im_hero.width * s), int(im_hero.height * s)
        im_scaled = im_hero.resize((nw, nh), Image.LANCZOS)

        # Grounded contact shadow
        sh = make_contact_shadow(int(nw * 0.90), 80, blur=30, alpha=150)
        base.alpha_composite(sh, (SIZE // 2 - sh.width // 2, hero_y + nh - 30))

        # Paste product
        base.alpha_composite(im_scaled, (SIZE // 2 - nw // 2, hero_y + (hero_h - nh) // 2 - 10))

    # Format Chips across bottom of card container
    n_chips = len(CHIP_COLS)
    r = 76
    gap = 32
    total_w = n_chips * 2 * r + (n_chips - 1) * gap
    x0 = SIZE // 2 - total_w // 2 + r
    cyy = cy + ch - 120
    for j, (label, col) in enumerate(CHIP_COLS):
        xx = x0 + j * (2 * r + gap)
        d.ellipse((xx - r, cyy - r, xx + r, cyy + r), fill=col, outline=INK, width=6)
        fc = M.fit(d, label, M.anton, 2 * r - 22, 54, 20)
        d.text((xx, cyy + 3), label, font=fc, fill=WHITE, anchor="mm")

    # Bottom machine strip on beige canvas
    strip = "BAMBU LAB  *  PRUSA  *  CREALITY  *  ANY SLICER"
    fs2 = M.fit(d, strip, M.poppins_x, SIZE - 260, 48, 24)
    sw = M.text_w(d, strip, fs2)
    sp = M.rounded((sw + 90, 84), 42, INK + (255,))
    base.alpha_composite(sp, (SIZE // 2 - (sw + 90) // 2, SIZE - 125))
    d.text((SIZE // 2, SIZE - 83), strip, font=fs2, fill=WHITE, anchor="mm")

    # 40-Point Yellow Starburst Badge ("INSTANT DOWNLOAD")
    bx, by, br = SIZE - 240, 240, 200
    pts = []
    for q in range(40):
        a = math.pi * 2 * q / 40
        rr = br if q % 2 == 0 else br * 0.82
        pts.append((bx + rr * math.cos(a), by + rr * math.sin(a)))
    star = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(star).polygon(pts, fill=GOLD + (255,), outline=INK + (255,), width=8)
    base.alpha_composite(star)

    burst_lines = ["INSTANT", "DOWNLOAD"]
    fz = M.anton(66)
    for li, l in enumerate(burst_lines):
        ImageDraw.Draw(base).text((bx, by + (li - 0.5) * 72), l, font=fz, fill=INK, anchor="mm")

    return base.convert("RGB")
'''

start_c1 = content.find("# CARD 01: HERO COVER")
start_c2 = content.find("# CARD 02: FULL 8-PACK")
assert start_c1 != -1 and start_c2 != -1, "Could not find c1 or c2 markers"

content = content[:start_c1] + bg_and_c1 + "\n" + content[start_c2:]

new_c8 = '''# -----------------------------------------------------------------------------
# CARD 08: PRINT SETTINGS & SLICER GUIDE (BIG INFO-CARD FORMAT)
# -----------------------------------------------------------------------------
def make_card_08() -> Image.Image:
    out_p = IMAGES_DIR / "08_specs_dimensions.jpg"
    rows = [
        ("NOZZLE", "0.4 mm standard brass or hardened steel nozzle"),
        ("LAYER HEIGHT", "0.20 mm standard / 0.28 mm draft for rapid prints"),
        ("WALL LOOPS", "4 to 6 perimeters (2.4mm) for rugged structural rigidity"),
        ("INFILL DENSITY", "15% to 20% Gyroid pattern for balanced strength and speed"),
        ("ZERO SUPPORTS", "100% self-supporting geometry - flat planar bed contact at Z=0"),
        ("MATERIALS", "PETG recommended for car consoles; PLA for indoor desks and gifts"),
    ]
    M.info_card(
        out_p,
        title="RECOMMENDED PRINT SETTINGS",
        kicker="OPTIMIZED FDM 3D PRINTING",
        rows=rows,
        accent=ACCENT,
        ink=INK,
        bg=BG_COLOR,
        footer="Tested on Bambu Lab X1C/P1S/A1, Prusa MK3/MK4, Creality Ender, and Anycubic."
    )
    return Image.open(out_p).convert("RGB")
'''

start_c8 = content.find("# CARD 08: EXACT DIMENSIONS")
start_c9 = content.find("# CARD 09: WHAT")
assert start_c8 != -1 and start_c9 != -1, "Could not find c8 or c9 markers"

content = content[:start_c8] + new_c8 + "\n" + content[start_c9:]

with open(r"F:\WORKHORSE\etsy_factory\assemble_can_holders_deck.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated assemble_can_holders_deck.py cleanly!")
