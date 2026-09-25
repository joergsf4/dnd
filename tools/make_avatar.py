#!/usr/bin/env python3
"""Generates the party avatars, 24x24 px (3x3 tiles) each, as indexed PNGs (palette index 0 is
the sprite's transparent color on real hardware):

    res/gfx/avatar.png      the generic hooded hero, shared by all three starting classes
    res/gfx/avatar_wir.png  "Wir", the intellect devourer from Room 2: a brain on four legs
    res/gfx/avatar_laezel.png  Lae'zel (Room 3): githyanki, yellow-green skin, bronze armour
    res/gfx/avatar_shadowheart.png  Schattenherz (Room 4): black hair, fringe, grey chain

Both use the same palette, since all avatars share PAL1 (loaded from avatar_sprite in main.c).
"""
import os

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
GITH = (0xB0, 0xB0, 0x58)
BRONZE = (0xF0, 0xB0, 0x38)      # amber eyes, gold
HAIR = (0x84, 0x40, 0x28)        # Lae'zel's reddish brown
STEEL = (0xB0, 0xB8, 0xC8)
STEEL_H = (0xF0, 0xF2, 0xF8)
GITH_D = (0x74, 0x74, 0x34)

palette = [TRANSPARENT, SKIN, EYE, CLOTH, CLOTH_SHADOW, BELT, BRAIN, BRAIN_FOLD, HORN, GLOW,
           GITH, BRONZE, HAIR, STEEL, STEEL_H, GITH_D]
color_index = {c: i for i, c in enumerate(palette)}

img = Image.new("P", (SIZE, SIZE), 0)
flat_palette = [v for color in palette for v in color] + [0, 0, 0] * (256 - len(palette))
img.putpalette(flat_palette)


def set_px(x, y, color):
    if 0 <= x < SIZE and 0 <= y < SIZE:
        img.putpixel((x, y), color_index[color])


# The hero: head and shoulders of a hooded adventurer -- the hood throws the face into shadow,
# only the lower face and a glint of the eyes catch the light; cloak over the shoulders, a gold
# clasp, a leather strap across the chest. Shared by all three classes.
for y in range(12, SIZE):                            # cloak over the shoulders
    half = 6 + min(6, (y - 12) * 2 // 2)
    for x in range(CX - half, CX + half + 1):
        set_px(x, y, CLOTH if x < CX - 2 else CLOTH_SHADOW)
for i in range(10):                                  # leather strap across the chest
    set_px(CX - 4 + i, 14 + i, BELT)
    set_px(CX - 3 + i, 14 + i, BELT)
for y in range(1, 15):                               # hood
    for x in range(3, 22):
        if ((x + 0.5 - CX) / 8.5) ** 2 + ((y + 0.5 - 8) / 7.5) ** 2 <= 1:
            set_px(x, y, CLOTH if x < CX - 1 or y < 4 else CLOTH_SHADOW)
for y in range(5, 15):                               # the opening, face in shadow
    for x in range(7, 18):
        if ((x + 0.5 - CX) / 5) ** 2 + ((y + 0.5 - 10) / 5) ** 2 <= 1:
            set_px(x, y, EYE if y < 9 else SKIN if x < CX + 2 else HORN if y > 12 else SKIN)
set_px(10, 8, STEEL_H)                               # eyes glinting under the hood
set_px(14, 8, STEEL_H)
for x in range(11, 14):
    set_px(x, 12, CLOTH_SHADOW)                      # a faint mouth
set_px(CX, 15, BRONZE)                               # gold clasp
set_px(CX - 1, 15, BRONZE)
set_px(CX, 16, BRONZE)

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

# ---- Lae'zel and Schattenherz: scaled down from their dialogue busts (tools/make_figures.py),
# so panel and close-up look like the same person; mapped onto the shared avatar palette.
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_figures as figs


def from_bust(canvas, fig_palette, crop, path):
    src = figs.to_rgba(canvas, fig_palette).crop(crop).resize((SIZE, SIZE), Image.BOX)
    out = Image.new("P", (SIZE, SIZE), 0)
    out.putpalette(flat_palette)
    for y in range(SIZE):
        for x in range(SIZE):
            r, g, b, a = src.getpixel((x, y))
            if a < 140:
                continue
            best = min(range(1, len(palette)),
                       key=lambda i: sum((u - v) ** 2 for u, v in zip((r, g, b), palette[i])))
            out.putpixel((x, y), best)
    out.save(path)
    print("wrote", path, out.size)


from_bust(figs.laezel_bust(), figs.LZ_PAL, (10, 6, 70, 66), "res/gfx/avatar_laezel.png")
from_bust(figs.shadowheart_bust(), figs.SH_PAL, (12, 10, 68, 66), "res/gfx/avatar_shadowheart.png")
