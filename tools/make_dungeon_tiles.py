#!/usr/bin/env python3
"""Generates the placeholder dungeon-view tileset (res/gfx/dungeon_tiles.png).

16 used tiles of 8x8 px on a 16x4 sheet (rescomp needs a source image >= 128x32 px),
saved as an indexed (palette-mode) PNG so rescomp reads the palette directly instead
of trying to reconstruct one from RGB data. Slot order is fixed and indexed directly
by src/dungeon_view.c; re-running this script regenerates the sheet from scratch,
replace with hand-drawn art later as long as the slot order stays in sync.

Slots 0-2   ceiling (near/mid/far)
Slots 3-5   floor (near/mid/far)
Slots 6-8   side wall brick (near/mid/far)
Slots 9-11  front wall brick (near/mid/far)
Slot 12     vanishing-point mist (far darkness)
Slots 13-63 unused (kept black; padding to satisfy rescomp's minimum image size)
"""
from PIL import Image

TILE = 8
COLS = 16  # rescomp requires the source image to be >= 128x32 px
ROWS = 4

BLACK = (0, 0, 0)
# depth shading, brightest (near) to darkest (far)
BRICK = [(0xA8, 0x78, 0x50), (0x7A, 0x5A, 0x3C), (0x4E, 0x3A, 0x26)]
MORTAR = [(0x6B, 0x4A, 0x32), (0x4A, 0x32, 0x22), (0x2E, 0x20, 0x14)]
CEIL = [(0x3A, 0x4A, 0x6B), (0x26, 0x31, 0x4A), (0x16, 0x1C, 0x2C)]
FLOOR = [(0x4A, 0x3A, 0x28), (0x33, 0x29, 0x1C), (0x20, 0x18, 0x0F)]
MIST = (0x0A, 0x0A, 0x12)

palette = [BLACK] + BRICK + MORTAR + CEIL + FLOOR + [MIST]
color_index = {c: i for i, c in enumerate(palette)}

sheet = Image.new("P", (TILE * COLS, TILE * ROWS), 0)
flat_palette = [v for color in palette for v in color] + [0, 0, 0] * (256 - len(palette))
sheet.putpalette(flat_palette)


def put(slot, px):
    ox = (slot % COLS) * TILE
    oy = (slot // COLS) * TILE
    for y in range(TILE):
        for x in range(TILE):
            sheet.putpixel((ox + x, oy + y), color_index[px(x, y)])


def flat(color):
    return lambda x, y: color


def brick_tile(depth):
    brick, mortar = BRICK[depth], MORTAR[depth]

    def px(x, y):
        # coarse brick coursing: a mortar line every 4th row, staggered every other course
        if y % 4 == 0:
            return mortar
        course = (y // 4) % 2
        offset = 4 if course else 0
        if (x + offset) % 8 == 0:
            return mortar
        return brick
    return px


for d in range(3):
    put(d, flat(CEIL[d]))
    put(3 + d, flat(FLOOR[d]))
    put(6 + d, brick_tile(d))
    put(9 + d, brick_tile(d))
put(12, flat(MIST))
for s in range(13, COLS * ROWS):
    put(s, flat(BLACK))

sheet.save("res/gfx/dungeon_tiles.png")
print("wrote res/gfx/dungeon_tiles.png", sheet.size, "colors:", len(palette))
