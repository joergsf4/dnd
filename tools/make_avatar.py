#!/usr/bin/env python3
"""Generates the placeholder hero avatar (res/gfx/avatar.png): one generic hooded/cloaked
adventurer icon, 24x24 px (3x3 tiles), reused for all three starting classes (Fighter/Rogue/
Mage) -- per-class art is future work, this is the technical skeleton's stand-in. Saved as an
indexed PNG (palette index 0 is the sprite's transparent color on real hardware).
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

palette = [TRANSPARENT, SKIN, EYE, CLOTH, CLOTH_SHADOW, BELT]
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
