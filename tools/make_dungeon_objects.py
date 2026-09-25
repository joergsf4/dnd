#!/usr/bin/env python3
"""Generates the placeholder interactive-object sprite sheet (res/gfx/dungeon_objects.png).

One 64x64 px (8x8 tile) frame per ObjectKind (src/dungeon_map.h), laid out in a single row/
animation (rescomp's SPRITE format: each row is an animation, each cell a frame) so
src/dungeon_objects.c can pick one with SPR_setFrame(sprite, kind - 1) -- OBJ_NONE has no frame.
Saved as an indexed PNG (palette index 0 is the sprite's transparent color on real hardware).

Frame order (must match ObjectKind's declaration order, minus OBJ_NONE):
  0  OBJ_LARVA_TANK          a squat glass tank with a few dark larvae
  1  OBJ_MINDFLAYER_CORPSE   a slumped purple humanoid silhouette
  2  OBJ_CARTILAGE_CHEST     a ribbed bone-colored chest
  3  OBJ_RESTORATION_SHRINE  a glowing blue pillar
  4  OBJ_DOOR_EXIT           a reddish iris/sphincter door
"""
from PIL import Image

SIZE = 64
FRAMES = 5

TRANSPARENT = (0xFF, 0x00, 0xFF)
GLASS = (0x4A, 0x6B, 0x5A)
LIQUID = (0x3A, 0x6B, 0x3E)
LARVA = (0x1E, 0x3A, 0x1E)
CORPSE_SKIN = (0x6B, 0x4A, 0x78)
CORPSE_SHADOW = (0x3E, 0x2A, 0x4A)
ROBE = (0x2E, 0x1E, 0x3A)
BONE = (0xC8, 0xB4, 0x8C)
BONE_SHADOW = (0x8C, 0x78, 0x54)
RIB = (0x5A, 0x46, 0x30)
SHRINE_GLOW = (0x60, 0xA8, 0xE0)
SHRINE_CORE = (0xD0, 0xEC, 0xFF)
SHRINE_BASE = (0x3A, 0x3A, 0x4A)
DOOR_OUTER = (0x6B, 0x2A, 0x32)
DOOR_MID = (0x94, 0x3E, 0x46)
DOOR_INNER = (0x1A, 0x0A, 0x0C)

palette = [TRANSPARENT, GLASS, LIQUID, LARVA, CORPSE_SKIN, CORPSE_SHADOW, ROBE,
           BONE, BONE_SHADOW, RIB, SHRINE_GLOW, SHRINE_CORE, SHRINE_BASE,
           DOOR_OUTER, DOOR_MID, DOOR_INNER]
color_index = {c: i for i, c in enumerate(palette)}

sheet = Image.new("P", (SIZE * FRAMES, SIZE), 0)
flat_palette = [v for c in palette for v in c] + [0, 0, 0] * (256 - len(palette))
sheet.putpalette(flat_palette)


def px(fx, x, y, color):
    ox = fx * SIZE
    if 0 <= x < SIZE and 0 <= y < SIZE:
        sheet.putpixel((ox + x, y), color_index[color])


def fill_rect(fx, x0, y0, x1, y1, color):
    for y in range(y0, y1):
        for x in range(x0, x1):
            px(fx, x, y, color)


def fill_circle(fx, cx, cy, r, color):
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                px(fx, x, y, color)


# frame 0: larva tank -- a squat rounded glass tank, greenish liquid, a few dark larvae
fill_rect(0, 12, 20, 52, 52, GLASS)
fill_rect(0, 15, 24, 49, 50, LIQUID)
for lx, ly in ((22, 34), (32, 40), (40, 30), (26, 44)):
    fill_circle(0, lx, ly, 3, LARVA)

# frame 1: mindflayer corpse -- a slumped humanoid silhouette, lying on its side
fill_circle(1, 20, 40, 8, CORPSE_SKIN)     # head
fill_rect(1, 24, 34, 52, 48, CORPSE_SKIN)  # torso
fill_rect(1, 44, 36, 58, 46, ROBE)         # trailing robe
fill_rect(1, 24, 44, 52, 48, CORPSE_SHADOW)  # ground shadow line

# frame 2: cartilage chest -- a ribbed bone-colored box with a domed lid
fill_rect(2, 12, 30, 52, 52, BONE)
fill_rect(2, 12, 20, 52, 30, BONE_SHADOW)
for rx in range(16, 52, 6):
    fill_rect(2, rx, 32, rx + 2, 50, RIB)

# frame 3: restoration shrine -- a glowing pillar on a dark base
fill_rect(3, 26, 44, 38, 56, SHRINE_BASE)
fill_rect(3, 28, 16, 36, 46, SHRINE_GLOW)
fill_circle(3, 32, 20, 6, SHRINE_CORE)

# frame 4: door -- a reddish iris/sphincter door, concentric rings
fill_circle(4, 32, 32, 26, DOOR_OUTER)
fill_circle(4, 32, 32, 18, DOOR_MID)
fill_circle(4, 32, 32, 9, DOOR_INNER)

sheet.save("res/gfx/dungeon_objects.png")
print("wrote res/gfx/dungeon_objects.png", sheet.size, "colors:", len(palette))
