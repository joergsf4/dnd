#!/usr/bin/env python3
"""Generates the party avatars, 24x24 px (3x3 tiles) each, as indexed PNGs (palette index 0 is
the sprite's transparent color on real hardware):

    res/gfx/avatar.png      the generic hooded hero, shared by all three starting classes
    res/gfx/avatar_wir.png  "Wir", the intellect devourer from Room 2: a brain on four legs
    res/gfx/avatar_laezel.png  Lae'zel (Room 3): githyanki, yellow-green skin, bronze armour
    res/gfx/avatar_shadowheart.png  Schattenherz (Room 4): black hair, fringe, grey chain

Both use the same palette, since all avatars share PAL1 (loaded from avatar_sprite in main.c).
"""
from PIL import Image

SIZE = 24
CX = 12

TRANSPARENT = (0xFF, 0x00, 0xFF)  # index 0; color value is irrelevant, hardware treats it as transparent
SKIN = (0xE0, 0xB0, 0x88)
EYE = (0x1A, 0x14, 0x10)
CLOTH = (0x5A, 0x3E, 0x78)
CLOTH_SHADOW = (0x3E, 0x2A, 0x54)
BELT = (0x2A, 0x1E, 0x14)
BRAIN = (0xE8, 0x90, 0xA0)
BRAIN_FOLD = (0x90, 0x30, 0x40)
HORN = (0xD8, 0xC8, 0xA0)
GLOW = (0xB0, 0x60, 0xE0)
GITH = (0xB8, 0xC8, 0x70)
BRONZE = (0xB8, 0x88, 0x40)
HAIR = (0x50, 0x38, 0x28)
STEEL = (0xB0, 0xB8, 0xC8)

palette = [TRANSPARENT, SKIN, EYE, CLOTH, CLOTH_SHADOW, BELT, BRAIN, BRAIN_FOLD, HORN, GLOW,
           GITH, BRONZE, HAIR, STEEL]
color_index = {c: i for i, c in enumerate(palette)}

img = Image.new("P", (SIZE, SIZE), 0)
flat_palette = [v for color in palette for v in color] + [0, 0, 0] * (256 - len(palette))
img.putpalette(flat_palette)


def set_px(x, y, color):
    if 0 <= x < SIZE and 0 <= y < SIZE:
        img.putpixel((x, y), color_index[color])


# head: a small filled circle
for y in range(1, 8):
    for x in range(8, 17):
        if (x - CX) ** 2 + (y - 4) ** 2 <= 9:
            set_px(x, y, SKIN)
set_px(10, 4, EYE)
set_px(14, 4, EYE)

# body: a tapering cloak trapezoid, narrow at the shoulders, wide at the hem,
# with a simple left-light/right-shadow split and a belt band
for y in range(7, SIZE):
    half = 5 + (y - 7) * (10 - 5) // (SIZE - 1 - 7)
    is_belt = 15 <= y <= 16
    for x in range(CX - half, CX + half + 1):
        if is_belt:
            set_px(x, y, BELT)
        else:
            set_px(x, y, CLOTH_SHADOW if x >= CX else CLOTH)

img.save("res/gfx/avatar.png")
print("wrote res/gfx/avatar.png", img.size, "colors:", len(palette))

# ---- "Wir": a wrinkled brain on four sinewy, clawed legs, with a faint psionic glow
img = Image.new("P", (SIZE, SIZE), 0)
img.putpalette(flat_palette)
for y in range(3, 16):
    for x in range(2, 22):
        if ((x - 12) / 10) ** 2 + ((y - 10) / 7) ** 2 <= 1:
            set_px(x, y, BRAIN)
for x, y0 in ((6, 5), (10, 4), (14, 4), (18, 6)):   # folds
    for y in range(y0, y0 + 8):
        set_px(x + (y % 3 == 0), y, BRAIN_FOLD)
for y in range(10, 16):
    set_px(12, y, BRAIN_FOLD)                        # the fissure between the halves
set_px(8, 6, GLOW)
set_px(15, 7, GLOW)
for x0, dx in ((5, -1), (9, 0), (14, 0), (18, 1)):   # legs, the outer ones splayed
    for i, y in enumerate(range(15, 22)):
        set_px(x0 + dx * (i // 2), y, HORN if y < 21 else BRAIN_FOLD)
        set_px(x0 + 1 + dx * (i // 2), y, HORN)
img.save("res/gfx/avatar_wir.png")
print("wrote res/gfx/avatar_wir.png", img.size)

# ---- Lae'zel: head and shoulders -- sharp bronze pauldrons, green face, hair pulled back
img = Image.new("P", (SIZE, SIZE), 0)
img.putpalette(flat_palette)
for y in range(15, SIZE):                            # armour, widening into pauldrons
    half = 7 + min(4, (y - 15))
    for x in range(CX - half, CX + half + 1):
        set_px(x, y, BRONZE if abs(x - CX) > 2 or y > 18 else BELT)
set_px(CX - 11, 16, BRONZE)
set_px(CX + 11, 16, BRONZE)
for y in range(3, 15):                               # face
    for x in range(6, 19):
        if ((x - CX) / 5.5) ** 2 + ((y - 9) / 6.5) ** 2 <= 1:
            set_px(x, y, GITH)
for x in range(6, 19):                               # hair, tight to the skull
    for y in range(2, 6):
        if ((x - CX) / 6) ** 2 + ((y - 6) / 4) ** 2 <= 1:
            set_px(x, y, HAIR)
set_px(5, 8, GITH)                                   # pointed ears
set_px(4, 7, GITH)
set_px(19, 8, GITH)
set_px(20, 7, GITH)
for x in (9, 10, 14, 15):                            # almond eyes
    set_px(x, 9, EYE)
set_px(11, 11, BELT)                                 # nostrils
set_px(13, 11, BELT)
for x in range(10, 15):
    set_px(x, 13, BELT)                              # stern mouth
for y in range(2, 22):                               # sword hilt over the shoulder
    set_px(20 + (y > 12), y, STEEL if y < 14 else HAIR)
img.save("res/gfx/avatar_laezel.png")
print("wrote res/gfx/avatar_laezel.png", img.size)

# ---- Schattenherz: pale face, straight black fringe, braid, grey chain shirt, shield rim
img = Image.new("P", (SIZE, SIZE), 0)
img.putpalette(flat_palette)
for y in range(15, SIZE):                            # chain shirt
    half = 7 + min(3, (y - 15))
    for x in range(CX - half, CX + half + 1):
        set_px(x, y, STEEL if (x + y) % 2 else CLOTH_SHADOW)
for y in range(3, 15):                               # face
    for x in range(6, 19):
        if ((x - CX) / 5.5) ** 2 + ((y - 9) / 6.5) ** 2 <= 1:
            set_px(x, y, SKIN)
for x in range(6, 19):                               # black hair, straight fringe
    for y in range(1, 7):
        if ((x - CX) / 6.5) ** 2 + ((y - 6) / 5) ** 2 <= 1:
            set_px(x, y, EYE)
for y in range(6, 16):                               # hair falling at the sides, braid
    set_px(6, y, EYE)
    set_px(18, y, EYE)
    set_px(19, y + 3, EYE)
set_px(5, 8, SKIN)                                   # ears
set_px(19, 8, SKIN)
for x in (9, 10, 14, 15):
    set_px(x, 9, EYE)
for x in range(11, 14):
    set_px(x, 13, BRAIN_FOLD)                        # mouth
img.save("res/gfx/avatar_shadowheart.png")
print("wrote res/gfx/avatar_shadowheart.png", img.size)
