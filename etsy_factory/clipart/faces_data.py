"""Cute baby animal face clipart (AI, ComfyUI): 30 animals x 2 styles = 60 designs.

The first 20 animals match the procedural vector pack in etsy_factory/faces; the last 10 are bonus animals. Prompts are text-free and use
generic animals only (no characters, brands or logos). Style rotation in packs.jobs gives every animal both looks.
"""
from __future__ import annotations

FACE_STYLES = [
    ("plush", "adorable kawaii 3D rendered plush toy portrait, soft fuzzy felt and velvet texture, huge round glossy eyes with sparkle highlights, "
              "rosy cheeks, tiny smile, soft studio lighting, smooth pastel colors, premium children's product design"),
    ("storybook", "sweet children's book watercolor illustration, soft pastel washes, huge round glossy eyes with sparkle highlights, rosy cheeks, "
                  "tiny smile, delicate fine ink linework, gentle blended colors, nursery art, polished and charming"),
]

FACE_SUBJECTS = [
    ("cat", "a cute baby kitten face, head only, front view, symmetrical, orange tabby with white muzzle and small whiskers"),
    ("bear", "a cute baby brown bear face, head only, front view, symmetrical, round ears and a cream muzzle"),
    ("bunny", "a cute baby bunny face, head only, front view, symmetrical, long floppy ears with pink inner ears and a tiny pink nose"),
    ("panda", "a cute baby panda face, head only, front view, symmetrical, black ears and black eye patches on a white face"),
    ("pig", "a cute baby piglet face, head only, front view, symmetrical, pink with a round snout and small floppy ears"),
    ("owl", "a cute baby owl face, head only, front view, symmetrical, big round eyes with soft brown feathers and a tiny beak"),
    ("chick", "a cute fluffy baby chick face, head only, front view, symmetrical, yellow downy feathers, a tiny orange beak and a small tuft on top"),
    ("dino", "a cute baby dinosaur face, head only, front view, symmetrical, soft green with little cream spikes on top of the head"),
    ("fox", "a cute baby fox face, head only, front view, symmetrical, orange fur, white cheeks and pointed ears"),
    ("koala", "a cute baby koala face, head only, front view, symmetrical, grey fur, big fluffy round ears and a large dark nose"),
    ("lion", "a cute baby lion cub face, head only, front view, symmetrical, golden fur with a small fluffy mane"),
    ("mouse", "a cute baby mouse face, head only, front view, symmetrical, grey fur, big round ears with pink insides and a tiny pink nose"),
    ("sheep", "a cute baby lamb face, head only, front view, symmetrical, fluffy cream wool curls and a soft face"),
    ("cow", "a cute baby calf face, head only, front view, symmetrical, white with brown patches, small horns and a pink muzzle"),
    ("frog", "a cute baby frog face, head only, front view, symmetrical, bright green with big bulging round eyes on top and a wide smile"),
    ("penguin", "a cute baby penguin face, head only, front view, symmetrical, black and white feathers with a small orange beak"),
    ("unicorn", "a cute baby unicorn face, head only, front view, symmetrical, white with a golden spiral horn and a pastel rainbow mane"),
    ("giraffe", "a cute baby giraffe face, head only, front view, symmetrical, yellow with brown spots, two little horns with round tips and small ears"),
    ("elephant", "a cute baby elephant face, head only, front view, symmetrical, light grey with big floppy ears and a short trunk"),
    ("hippo", "a cute baby hippo face, head only, front view, symmetrical, soft lilac-grey with a wide round snout and small round ears"),
    ("raccoon", "a cute baby raccoon face, head only, front view, symmetrical, grey fur with a dark mask around the eyes and a white muzzle"),
    ("hedgehog", "a cute baby hedgehog face, head only, front view, symmetrical, soft brown spikes around a cream face and a tiny dark nose"),
    ("deer", "a cute baby fawn face, head only, front view, symmetrical, light brown with white spots, big ears and tiny antler buds"),
    ("tiger", "a cute baby tiger cub face, head only, front view, symmetrical, orange fur with black stripes and white cheeks"),
    ("monkey", "a cute baby monkey face, head only, front view, symmetrical, brown fur with a cream face and big round ears"),
    ("zebra", "a cute baby zebra face, head only, front view, symmetrical, black and white stripes and a soft grey muzzle"),
    ("sloth", "a cute baby sloth face, head only, front view, symmetrical, soft brown fur with a pale face and dark eye patches, gentle smile"),
    ("otter", "a cute baby otter face, head only, front view, symmetrical, sleek brown fur with a cream muzzle and little whiskers"),
    ("duck", "a cute baby duckling face, head only, front view, symmetrical, fluffy yellow feathers with a small orange bill"),
    ("llama", "a cute baby llama face, head only, front view, symmetrical, fluffy cream wool with long soft ears and a gentle smile"),
]
assert len(FACE_SUBJECTS) == 30
