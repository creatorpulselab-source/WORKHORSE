"""60 sarcastic leopard-accessory animal designs: (key, art prompt, top caption, bottom caption).

Art is generated TEXT-FREE (AI text is unreliable); captions are set procedurally by sass_pack.py so they are always spelled
correctly. All captions are original wordplay; none is a brand name, a character or a known slogan. Run the trademark scan in
STATUS_AND_NEXT_STEPS.md against the caption strings before listing.
"""
from __future__ import annotations

LEO = "leopard print"

# (key, subject prompt, TOP caption, BOTTOM caption)
SASS = [
    ("cheetah_coffee", f"a cheetah head portrait wearing {LEO} sunglasses and its furry spotted cheetah paw with claws wrapped around a takeaway coffee cup with a {LEO} sleeve", "I WOULD RUN", "BUT I HAVE COFFEE"),
    ("lab_bandana", f"a yellow labrador retriever head and chest portrait wearing {LEO} sunglasses and a {LEO} bandana", "I DON'T BITE", "BUT I WILL JUDGE YOU"),
    ("raccoon_purse", f"a raccoon wearing a {LEO} eye mask and holding a small {LEO} purse", "NIGHT SHIFT", "SNACK MANAGER"),
    ("sloth_sleep", f"a sloth hanging from a branch wearing a {LEO} sleep mask", "WOKE UP", "REGRET EVERYTHING"),
    ("owl_coffee", f"an owl wearing round {LEO} glasses and a coffee cup gripped in its feathered wing", "WISE ENOUGH", "TO IGNORE YOUR TEXT"),
    ("llama_bow", f"a llama head portrait with a big {LEO} bow on its head", "I LOVE MY", "PERSONAL SPACE"),
    ("frog_tea", f"a green frog wearing {LEO} sunglasses sipping tea from a teacup", "RIBBIT", "OKAY BYE"),
    ("flamingo_shades", f"a pink flamingo head and neck portrait wearing {LEO} sunglasses", "STANDING HERE", "LOOKING FABULOUS"),
    ("cat_mug", f"a smug tabby cat wearing a {LEO} collar sitting beside a coffee mug about to be pushed off the edge", "I DID THAT", "ON PURPOSE"),
    ("pug_bow", f"a pug portrait wearing a {LEO} bow", "ENERGY LEVEL:", "NAP"),
    ("frenchie_bandana", f"a french bulldog portrait wearing a {LEO} bandana", "NOT LAZY", "ENERGY EFFICIENT"),
    ("corgi_scrunchie", f"a corgi portrait wearing {LEO} sunglasses and a {LEO} scrunchie", "SHORT LEGS", "BIG ATTITUDE"),
    ("giraffe_shades", f"a giraffe head and neck portrait wearing {LEO} sunglasses", "I CAN SEE", "YOUR BAD DECISIONS FROM HERE"),
    ("hippo_handbag", f"a hippo with a {LEO} handbag hooked over its front foot", "ON MY WAY", "BUT NOT IN A HURRY"),
    ("penguin_scarf", f"a penguin wearing a {LEO} scarf", "COLD HEARTED", "WARM SCARF"),
    ("fox_headband", f"a red fox portrait wearing a {LEO} headband", "SLY AND", "SLIGHTLY SASSY"),
    ("bunny_bow", f"a fluffy bunny wearing a {LEO} bow", "HOPPING OUT OF", "THIS CONVERSATION"),
    ("hedgehog_glasses", f"a hedgehog wearing {LEO} glasses", "PRICKLY BY NATURE", "PRETTY BY CHOICE"),
    ("cow_bandana", f"a cow head portrait wearing a {LEO} bandana", "UDDERLY", "UNBOTHERED"),
    ("pig_shades", f"a cute pink pig wearing {LEO} sunglasses", "OINK IF YOU", "NEED A NAP"),
    ("hen_bow", f"a hen portrait wearing a {LEO} bow", "THE HEN IS", "OFF DUTY"),
    ("duck_hat", f"a duck wearing a {LEO} rain hat", "WATER OFF", "MY BACK"),
    ("bear_beanie", f"a brown bear wearing a {LEO} beanie and a coffee cup held in its big furry bear paw", "NO TALKING", "BEFORE COFFEE"),
    ("koala_sleep", f"a koala wearing a {LEO} sleep mask hugging a eucalyptus branch", "NAPTIME IS", "MY CARDIO"),
    ("panda_shades", f"a giant panda wearing {LEO} sunglasses with a bamboo stalk in its black furry paw", "BAMBOO BREAK", "DO NOT DISTURB"),
    ("unicorn_mane", f"a unicorn head portrait with a {LEO} streak in its mane", "NOT A PHASE", "JUST MAGICAL"),
    ("dragon_bow", f"a tiny cute dragon wearing a {LEO} bow", "TINY DRAGON", "ZERO CHILL"),
    ("octopus_busy", f"an octopus holding a coffee cup, a phone and a book in different arms, wearing {LEO} glasses", "EIGHT ARMS", "STILL NO HELP"),
    ("shark_bow", f"a cute cartoon shark wearing a {LEO} bow", "NOT GRUMPY", "JUST HUNGRY"),
    ("turtle_sneakers", f"a turtle wearing {LEO} sneakers", "I'LL GET THERE", "WHEN I GET THERE"),
    ("snail_shell", f"a snail with a {LEO} shell", "SLOW", "AND PROUD"),
    ("bat_mask", f"a bat hanging upside down wearing a {LEO} sleep mask", "AWAKE AT", "THE WRONG HOURS"),
    ("skunk_bow", f"a skunk wearing a {LEO} bow", "MY STINK", "IS ALL ATTITUDE"),
    ("moose_glasses", f"a moose head portrait wearing {LEO} glasses", "NOPE", "NOT TODAY"),
    ("deer_bow", f"a doe deer portrait wearing a {LEO} bow", "DEER DIARY:", "I SAID NO"),
    ("goat_bandana", f"a goat portrait wearing a {LEO} bandana", "IN MY", "GOAT ERA"),
    ("alpaca_hat", f"an alpaca portrait wearing a {LEO} hat", "FLUFFY ON THE OUTSIDE", "SPITTY ON THE INSIDE"),
    ("elephant_purse", f"an elephant holding a {LEO} purse with its trunk", "I NEVER FORGET", "WHO ANNOYED ME"),
    ("zebra_bow", f"a zebra portrait wearing a {LEO} bow", "STRIPES ARE", "SO LAST SEASON"),
    ("croc_shades", f"a crocodile head portrait wearing {LEO} sunglasses", "SMILE", "IT MAKES THEM NERVOUS"),
    ("monkey_banana", f"a monkey wearing a {LEO} bow and holding a banana", "MONKEY BUSINESS", "NONE OF YOURS"),
    ("otter_float", f"an otter floating on its back wearing {LEO} sunglasses", "I'M OTTER", "HERE"),
    ("lioness_bow", f"a lioness portrait wearing a {LEO} bow", "QUEEN OF", "THE COUCH"),
    ("wolf_glasses", f"a wolf portrait wearing {LEO} glasses", "LONE WOLF", "WITH SNACKS"),
    ("horse_bridle", f"a horse head portrait with a {LEO} halter", "NEIGH MEANS", "NEIGH"),
    ("donkey_bow", f"a donkey portrait wearing a {LEO} bow", "STUBBORN", "ON PURPOSE"),
    ("possum_glasses", f"an opossum wearing {LEO} glasses", "PLAYING DEAD", "UNTIL FRIDAY"),
    ("ferret_bow", f"a ferret wearing a {LEO} bow", "SMALL BODY", "CHAOS ENERGY"),
    ("dachshund_scarf", f"a dachshund wearing a {LEO} scarf", "LONG BODY", "SHORT FUSE"),
    ("poodle_shades", f"a fluffy poodle portrait wearing {LEO} sunglasses", "DIVA ON", "THE LEASH"),
    ("chameleon_spots", f"a chameleon with {LEO} skin pattern", "BLENDING IN", "WAS NEVER MY THING"),
    ("bee_shades", f"a fuzzy bee wearing {LEO} sunglasses", "BEE-ING", "EXTRA TODAY"),
    ("ladybug_spots", f"a ladybug with a {LEO} pattern on its wings", "LOVE BUG", "WITH ATTITUDE"),
    ("triceratops_bow", f"a triceratops dinosaur wearing a {LEO} bow", "EXTINCT", "BUT STILL FABULOUS"),
    ("trex_shades", f"a T-rex dinosaur wearing {LEO} sunglasses", "SMALL ARMS", "BIG OPINIONS"),
    ("sheep_bow", f"a fluffy sheep wearing a {LEO} bow", "BAA-SICALLY", "I'M DONE"),
    ("mouse_cheese", f"a mouse wearing a {LEO} bow and with a wedge of cheese in its tiny pink paws", "I'M BASICALLY", "A CHEESE EXPERT"),
    ("raccoon_pizza", f"a raccoon wearing {LEO} sunglasses with a slice of pizza in its small dark raccoon paws", "BIN DIVING", "IS MY CARDIO"),
    ("blackcat_shades", f"a black cat portrait wearing {LEO} sunglasses", "CAT-ITUDE", "LOADING"),
    ("tiger_bow", f"a tiger cub portrait wearing a {LEO} bow", "STRIPES AND SPOTS", "BECAUSE I CAN"),
]

assert len(SASS) == 60, len(SASS)
assert len({k for k, *_ in SASS}) == 60
