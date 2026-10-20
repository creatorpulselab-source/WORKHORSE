"""Prompt matrices for the illustrated sublimation clipart packs.

Every pack = subjects x style variants. All art is text-free (AI text is unreliable) and uses generic motifs only: no
characters, brands or logos.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

KEYS = {
    "magenta": "pure magenta (#FF00FF)",
    "cyan": "pure bright cyan (#00FFFF)",
    "green": "pure bright lime green (#00FF00)",
}


def key_for(subject: str, style: str) -> str:
    """Pick a key colour that is absent from the art: pinks -> cyan, pinks+teals -> green, else magenta."""
    s = f"{subject} {style}".lower()
    pink = re.search(r"pink|rose|blush|heart|peon|valentine|cherr|strawberr|poppy|poppies|leopard|flamingo|mauve|dusty", s)
    cool = re.search(r"teal|aqua|mint|turquoise|blue|sky|cyan", s)
    if pink and cool:
        return "green"
    if pink:
        return "cyan"
    return "magenta"


def tail(key: str) -> str:
    return (f"single isolated clipart illustration centered on a plain solid flat {KEYS[key]} background, perfectly uniform, "
            "no gradient, no vignette, the whole subject fully visible with a generous margin of background color around it, crisp clean "
            "edges, the background color is not used anywhere on the subject, no text, no letters, no words, no watermark, no frame, "
            "no cast shadow")


@dataclass
class Pack:
    key: str
    slug: str
    name: str
    short: str
    styles: List[Tuple[str, str]]          # (style key, style prompt)
    subjects: List[Tuple[str, str]]        # (subject key, subject prompt)
    seed0: int = 20261018
    title: str = ""
    tags: List[str] = field(default_factory=list)
    price: float = 3.99
    list_price: float = 9.99
    intro: str = ""
    uses: str = ""
    theme: str = ""


# ------------------------------------------------------------------------------------------------ highland cow
COW_STYLES = [
    ("watercolor", "soft hand-painted watercolor clipart, delicate brush texture, gentle blended pastel colors, cute"),
    ("flat", "cute flat vector style clipart, clean smooth shapes, soft shading, warm pastel boho colors, subtle thin outline"),
    ("boho", "boho illustration, muted earthy terracotta sage cream and mustard palette, simple stylized shapes with fine detail, charming"),
]
_COW = "a fluffy ginger highland cow with long shaggy fringe and curved horns, "
COW_SUBJECTS = [
    ("rose_crown", _COW + "front-facing portrait wearing a crown of pink roses and green leaves"),
    ("sunflowers", _COW + "front-facing portrait with big yellow sunflowers tucked in its fringe"),
    ("cowboy_hat", _COW + "wearing a tan western cowboy hat and a red bandana, front-facing portrait"),
    ("daisies", _COW + "portrait with white daisies and small wildflowers in its hair"),
    ("santa_hat", _COW + "wearing a red Santa hat with holly leaves and red berries, front-facing portrait"),
    ("valentine", _COW + "portrait with red and pink hearts and a small bouquet of roses"),
    ("pumpkin_fall", _COW + "portrait wearing an autumn leaf crown with a small orange pumpkin and fall leaves"),
    ("cactus_western", _COW + "portrait wearing a cowboy hat with a prickly pear cactus and desert flowers"),
    ("easter", _COW + "portrait wearing bunny ears with pastel spring flowers and painted Easter eggs"),
    ("tulips", _COW + "portrait with a spring wreath of pink and yellow tulips"),
    ("sunglasses_summer", _COW + "portrait wearing round sunglasses and a flower lei, summer vibe"),
    ("butterfly", _COW + "portrait with colorful butterflies and meadow flowers around its face"),
    ("full_body_meadow", _COW + "full body standing in a small patch of wildflowers and grass"),
    ("leopard_print", _COW + "portrait wearing a leopard print bandana and pink flowers"),
    ("winter_scarf", _COW + "portrait in a cozy knitted red scarf and beanie with a few snowflakes"),
    ("rainbow", _COW + "portrait with a pastel rainbow arch behind it and fluffy clouds"),
    ("floral_wreath", _COW + "portrait framed by a full round floral wreath of roses, leaves and berries"),
    ("calf", "an adorable baby highland calf with fluffy ginger fur and tiny horns, sitting, with small daisies"),
    ("lavender", _COW + "portrait with sprigs of purple lavender and eucalyptus leaves"),
    ("feathers_boho", _COW + "boho portrait with feathers, pampas grass and dried flowers in its fringe"),
    ("clover", _COW + "portrait wearing a green top hat with four-leaf clovers and a gold coin"),
    ("coffee", _COW + "portrait holding a steaming coffee mug with little hearts rising up"),
    ("strawberries", _COW + "portrait with strawberries, strawberry blossoms and green leaves"),
    ("autumn_leaves", _COW + "portrait with colorful maple leaves, acorns and a plaid blanket scarf"),
    ("poppies", _COW + "portrait with red poppies and wheat stalks"),
    ("bluebonnets", _COW + "portrait with blue bonnet flowers and a straw hat, spring"),
    ("mama_baby", "a mother highland cow standing next to her tiny fluffy calf, with flowers, full body"),
    ("pink_flowers", _COW + "portrait with big pink peonies and blush roses behind its horns"),
    ("graduation", _COW + "portrait wearing a graduation cap with a tassel"),
    ("pine_christmas", _COW + "portrait wearing a pine garland and red bow with gold ornaments"),
]

# ------------------------------------------------------------------------------------------------ retro Christmas
XM_STYLES = [
    ("groovy70s", "retro 1970s groovy Christmas clipart, flat shapes with thick clean outlines, mustard yellow burnt orange olive green teal and cranberry red on cream, vintage print feel"),
    ("mcm", "mid-century modern Christmas illustration, simple geometric shapes, retro color palette of red, aqua, gold and forest green, vintage greeting card style"),
    ("vintage_cute", "cute vintage Christmas clipart, soft rounded shapes, muted retro pastel red mint and cream palette, slight paper grain, charming"),
]
XM_SUBJECTS = [
    ("candy_cane", "a swirly red and white candy cane tied with a bow"),
    ("santa_face", "a jolly Santa Claus face with a white beard and red hat"),
    ("ornaments", "a set of three round glass Christmas ornaments hanging from ribbon"),
    ("mcm_tree", "a stylized Christmas tree made of layered triangles with a star on top"),
    ("gingerbread_man", "a smiling gingerbread man cookie with icing and buttons"),
    ("reindeer", "a cute reindeer head with antlers and a red nose and a jingle bell collar"),
    ("snowman", "a friendly snowman with a top hat, carrot nose and striped scarf"),
    ("gift_boxes", "a stack of wrapped Christmas presents with big bows"),
    ("stocking", "a red Christmas stocking with white cuff filled with candy canes and toys"),
    ("poinsettia", "a red poinsettia flower with green leaves"),
    ("holly", "holly leaves and red berries with a red ribbon bow"),
    ("wreath", "a Christmas wreath with pine, pinecones, berries and a big red bow"),
    ("star", "a gold sparkling Christmas star with little twinkles around"),
    ("cocoa", "a mug of hot cocoa with marshmallows, a candy cane and steam"),
    ("bells", "two golden jingle bells tied with a red ribbon and holly"),
    ("snowflake", "an intricate decorative snowflake"),
    ("peppermint", "a round peppermint swirl candy"),
    ("lights", "a loop of retro bulb Christmas lights on a green wire"),
    ("angel", "a sweet little angel with wings and a halo"),
    ("nutcracker", "a classic toy nutcracker soldier in a red uniform"),
    ("gingerbread_house", "a cozy gingerbread house decorated with candy and icing"),
    ("camper", "a vintage retro camper van with a small Christmas tree on its roof"),
    ("truck_tree", "a retro pickup truck carrying a Christmas tree in its bed"),
    ("cookies", "a plate of assorted decorated Christmas sugar cookies"),
    ("bow", "a big red satin Christmas bow with long ribbon tails"),
    ("mistletoe", "a mistletoe sprig with white berries and a red ribbon"),
    ("sled", "a wooden vintage sled with a red scarf and a small gift"),
    ("fireplace", "a cozy brick fireplace with a roaring fire and two hanging stockings"),
    ("elf_hat", "a green elf hat with a jingle bell and a red feather"),
    ("pine_branch", "a snowy pine branch with pinecones and red berries"),
]

# ------------------------------------------------------------------------------------------------ boho
BOHO_STYLES = [
    ("terracotta", "boho clipart, flat shapes with subtle texture, terracotta, sage green, sand, cream and rust palette, minimal and warm"),
    ("blush", "boho clipart, soft blush pink, dusty rose, beige, mauve and gold palette, delicate and dreamy, flat shapes with subtle texture"),
    ("retro", "retro groovy boho clipart, mustard yellow, teal, burnt orange, brown and cream palette, thick smooth shapes, 70s feel"),
]
BOHO_SUBJECTS = [
    ("rainbow", "a layered boho rainbow arch with a small sun"),
    ("sun", "a stylized sun with wavy rays and a simple face-less centre"),
    ("moon_phases", "a row of moon phases from new moon to full moon with tiny stars"),
    ("daisy", "a large retro daisy flower with a round centre and leaves"),
    ("wildflowers", "a loose bouquet of wildflowers with long stems"),
    ("pampas", "a bunch of fluffy pampas grass and dried reeds"),
    ("cactus", "a potted cactus with a small pink flower in a terracotta pot"),
    ("mushrooms", "a cluster of whimsical mushrooms with spots"),
    ("arch_frame", "a boho arch frame with botanical leaves, empty inside"),
    ("leopard_heart", "a heart filled with leopard print pattern"),
    ("hand_flower", "an open hand holding a flower"),
    ("butterfly", "a decorative boho butterfly with patterned wings"),
    ("feather", "three boho feathers with beads and fringe"),
    ("dreamcatcher", "a boho dreamcatcher with feathers and beads"),
    ("crescent_stars", "a crescent moon with stars and sparkles"),
    ("monstera", "a monstera leaf and two palm leaves"),
    ("sunflower", "a sunflower with round brown centre and long petals"),
    ("protea", "a protea flower bloom with eucalyptus leaves"),
    ("dried_bouquet", "a dried flower bouquet tied with twine"),
    ("smiley_flower", "a groovy retro flower with a happy smile"),
    ("lightning", "a groovy lightning bolt with stripes and stars"),
    ("peace", "a retro peace sign decorated with flowers"),
    ("cow_skull", "a boho cow skull with flowers and feathers"),
    ("desert", "a desert landscape with cacti, mountains and a setting sun"),
    ("wavy_lines", "layered wavy rainbow lines forming a bold retro stripe"),
    ("hearts", "three overlapping retro hearts in a trio"),
    ("western_boot", "a cowboy boot decorated with flowers and a small cactus"),
    ("cherry", "a pair of groovy cherries with leaves"),
    ("palm_sunset", "palm trees against a retro striped sunset"),
    ("wreath", "a delicate round botanical wreath of leaves and small blooms, empty centre"),
]


# ------------------------------------------------------------------------------------------------ sarcastic animals (captions added by sass_pack.py)
from etsy_factory.clipart.sass_data import SASS as _SASS  # noqa: E402

SASS_STYLES = [
    ("ink", "highly detailed hand-drawn illustration, realistic ink and watercolor portrait, fine individual fur and feather detail, rich natural "
            "colors, expressive funny face, polished professional t-shirt graphic, sharp clean edges, the whole subject fully inside the frame"),
]
SASS_SUBJECTS = [(k, s) for k, s, _t, _b in _SASS]

PACKS: Dict[str, Pack] = {
    "sass": Pack(
        key="sass", slug="sarcastic_leopard_animals_shirt_designs_png", name="Sarcastic Animals Shirt Designs", short="sarcastic animal",
        styles=SASS_STYLES, subjects=SASS_SUBJECTS, seed0=74000,
        title="Funny Animal PNG Bundle, {n} Sarcastic Leopard Print Animal Shirt Designs, Sassy Sublimation Clipart, Humor Quote Transparent PNG",
        tags=["funny animal png", "sarcastic png", "leopard print png", "sassy png", "animal clipart", "sublimation png", "humor shirt png",
              "funny shirt design", "tumbler wrap png", "sarcasm png bundle", "cute animal png", "sublimation designs", "commercial use png"],
        intro="Detailed hand-drawn animals in leopard print accessories with sarcastic captions - ready to press on shirts, tumblers and mugs.",
        uses="Sublimation and DTF shirts, tumblers, mugs, tote bags, stickers, print-then-cut, gifts for animal lovers and sarcasm fans.",
        theme="sarcastic animal"),
    "cow": Pack(
        key="cow", slug="highland_cow_sublimation_clipart_png", name="Highland Cow Clipart", short="highland cow",
        styles=COW_STYLES, subjects=COW_SUBJECTS, seed0=71000,
        title="Highland Cow Clipart PNG Bundle, {n} Cute Cow Sublimation Designs, Western Floral Highland Cow Transparent PNG, Commercial Use",
        tags=["highland cow png", "cow clipart", "sublimation png", "highland cow svg", "western png", "cow png bundle", "floral cow",
              "tumbler wrap png", "farmhouse png", "cute cow png", "sublimation designs", "t-shirt png", "commercial use png"],
        intro="Fluffy highland cows with flowers, hats and seasonal touches - hand-styled illustrations ready for sublimation, tumblers, shirts, mugs, stickers and scrapbooking.",
        uses="Sublimation shirts and tumblers, mugs, stickers, cards, scrapbooking, nursery and farmhouse decor, planner printables, party invitations.",
        theme="highland cow"),
    "xmas": Pack(
        key="xmas", slug="retro_christmas_sublimation_clipart_png", name="Retro Christmas Clipart", short="retro Christmas",
        styles=XM_STYLES, subjects=XM_SUBJECTS, seed0=72000,
        title="Retro Christmas Clipart PNG Bundle, {n} Groovy Vintage Christmas Sublimation Designs, Santa Candy Cane Tree PNG, Commercial Use",
        tags=["retro christmas png", "christmas clipart", "vintage christmas", "groovy christmas", "xmas sublimation png", "christmas png bundle",
              "santa png", "candy cane png", "christmas shirt png", "holiday clipart", "tumbler wrap png", "sublimation designs", "commercial use png"],
        intro="Groovy retro and vintage Christmas illustrations in 70s and mid-century palettes - candy canes, ornaments, trees, gingerbread, campers and more.",
        uses="Christmas shirts and sweatshirts, ornaments, mugs and tumblers, cards, gift tags, stickers, planners, holiday crafts and printables.",
        theme="retro Christmas"),
    "boho": Pack(
        key="boho", slug="boho_retro_sublimation_clipart_png", name="Boho Clipart", short="boho",
        styles=BOHO_STYLES, subjects=BOHO_SUBJECTS, seed0=73000,
        title="Boho Clipart PNG Bundle, {n} Retro Boho Sublimation Designs, Rainbow Daisy Leopard Heart Wildflower PNG, Commercial Use",
        tags=["boho png", "boho clipart", "retro boho", "sublimation png", "rainbow png", "daisy png", "leopard print png", "wildflower png",
              "groovy png", "tumbler wrap png", "boho shirt png", "sublimation designs", "commercial use png"],
        intro="Warm retro boho illustrations - rainbows, daisies, moons, pampas, leopard hearts and wildflowers in three on-trend palettes.",
        uses="Sublimation tumblers and shirts, mugs, stickers, planners, scrapbooking, wall art, invitations, and digital paper projects.",
        theme="boho"),
}


def jobs(pack: Pack, limit: int | None = None, styles_per_subject: int = 3) -> List[Tuple[str, str, int, str, str]]:
    """-> (name, prompt, seed, subject_key, style_key) with a stable ordering: every subject once, then the next style round."""
    out = []
    idx = 0
    for round_ in range(min(styles_per_subject, len(pack.styles))):
        for si, (sk, sp) in enumerate(pack.subjects):
            stk, stp = pack.styles[(si + round_) % len(pack.styles)]
            idx += 1
            name = f"{idx:03d}_{sk}_{stk}"
            prompt = f"{stp}. {sp}. {tail(key_for(sp, stp))}"
            out.append((name, prompt, pack.seed0 + idx * 37, sk, stk))
    return out[:limit] if limit else out
