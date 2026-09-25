#!/usr/bin/env python3
"""Generates everything the first-person renderer (src/dungeon_view.c) needs that depends only
on screen geometry, never on the map -- so it's computed once here, not on the 68000:

    src/view_gen.h          palette, per-column event tables
    res/view/columns.bin    every wall column the view can show, textured and shaded (BIN resource)
    res/view/backdrops.bin  the floor/ceiling backdrop and its mirror image, in tile layout
    res/view/adjacent.bin   the full view of a wall right in front of the player, per texture

How the view works (Eye of the Beholder / Dungeon Master style): the player always stands in a
cell centre and faces a cardinal direction, so the ray through every 2-pixel screen column pair
crosses a fixed sequence of cells (relative to the player). That sequence is precomputed here as
a list of "events" (cell offset, wall top row, visible rows). Since a given wall face at a given
screen position always looks the same, each event's pixels are also baked here once per texture.
At runtime dungeon_view.c walks each column's list and copies the baked bytes of the first event
whose cell is a wall. Floor and ceiling are a static perspective backdrop, exactly like the
originals, which never redrew them per map either; walls are drawn over it.

    python3 tools/make_view.py            # writes the three files above
    python3 tools/make_view.py --preview  # also writes a few sample renders to out/view_preview/

Outputs are deterministic; commit them.
"""
import math
import os
import random
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))

# ---------------------------------------------------------------- geometry
VW, VH = 224, 160          # view size in pixels (28 x 20 tiles, top-left of the screen)
TW, TH = VW // 8, VH // 8
CX, CY = VW / 2, VH / 2    # horizon in the middle
F = VW / 2                 # focal length: the wall right in front (z = 0.5) spans the full width
HALF_K = 0.5 * F           # walls are 1 cell high, eye at mid-height: half-height on screen = HALF_K / z
MAXZ = 5.5                 # draw distance (cells); beyond it: darkness
TEX = 64                   # texture size (texels)
NPAIR = VW // 2            # the renderer works on 2-pixel column pairs (one byte per row)
LMAX = 5                   # lateral cells visible either side
DMAX = 5                   # depth cells visible

# ---------------------------------------------------------------- palette (Mega Drive levels 0-7)
PAL = [
    (0, 0, 0),   # 0 black / darkness
    (1, 1, 1),   # 1 stone, darkest (mortar)
    (2, 2, 3),   # 2 stone
    (3, 3, 4),   # 3 stone
    (5, 5, 5),   # 4 stone, lightest
    (1, 1, 0),   # 5 floor dark
    (2, 2, 1),   # 6 floor mid
    (3, 3, 2),   # 7 floor light
    (0, 0, 1),   # 8 ceiling dark
    (1, 1, 2),   # 9 ceiling light
    (1, 3, 1),   # 10 green dark
    (3, 6, 2),   # 11 green light
    (4, 2, 5),   # 12 purple (mindflayer)
    (6, 5, 4),   # 13 bone
    (3, 5, 7),   # 14 blue glow
    (5, 1, 2),   # 15 flesh red
]
RGB = [tuple(round(c * 255 / 7) for c in p) for p in PAL]
SHADE_F = [1.0, 0.72, 0.48, 0.3]   # per distance band


def band_of(z):
    return 0 if z < 1.5 else 1 if z < 2.5 else 2 if z < 3.5 else 3


def nearest(rgb):
    return min(range(16), key=lambda i: sum((a - b) ** 2 for a, b in zip(rgb, RGB[i])))


SHADE = [[i if b == 0 else nearest(tuple(c * SHADE_F[b] for c in RGB[i])) for i in range(16)]
         for b in range(4)]

# ---------------------------------------------------------------- textures (64x64, palette indices)
rng = random.Random(1234)


def stone_base():
    t = [[3] * TEX for _ in range(TEX)]
    for y in range(TEX):
        course = y // 16
        for x in range(TEX):
            bx = (x + (16 if course % 2 else 0)) % 32
            by = y % 16
            if by < 2 or bx < 2:
                t[y][x] = 1                      # mortar
            elif by == 2 or bx == 2:
                t[y][x] = 4                      # lit top/left edge
            elif by == 15 or bx == 31:
                t[y][x] = 2                      # shadowed bottom/right edge
            else:
                r = rng.random()
                t[y][x] = 2 if r < 0.12 else 4 if r < 0.16 else 3
    return t


def rect(t, x0, y0, x1, y1, c):
    for y in range(y0, y1):
        for x in range(x0, x1):
            t[y][x] = c


def disc(t, cx, cy, r, c):
    for y in range(TEX):
        for x in range(TEX):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                t[y][x] = c


def tex_stone():
    return stone_base()


def tex_tank():
    t = stone_base()
    rect(t, 14, 10, 50, 56, 1)                   # recess
    rect(t, 16, 12, 48, 54, 2)                   # tank frame
    rect(t, 19, 16, 45, 51, 10)                  # liquid
    rect(t, 19, 16, 45, 20, 11)                  # surface glow
    for _ in range(14):
        disc(t, rng.randint(22, 42), rng.randint(24, 48), 1, 1)   # larvae
    for _ in range(6):
        t[rng.randint(21, 49)][rng.randint(21, 43)] = 11          # bubbles
    return t


def tex_corpse():
    t = stone_base()
    rect(t, 12, 34, 54, 58, 6)                   # floor shadow in the alcove
    disc(t, 24, 36, 7, 12)                       # head
    for dx in (-4, -1, 2, 5):                    # tentacles
        rect(t, 24 + dx, 40, 25 + dx, 48, 12)
    rect(t, 20, 42, 52, 56, 1)                   # dark robe
    rect(t, 22, 44, 50, 54, 2)
    t[35][21] = t[35][27] = 13                   # dead eyes
    return t


def tex_chest():
    t = stone_base()
    rect(t, 10, 24, 54, 60, 1)                   # niche
    rect(t, 14, 36, 50, 58, 13)                  # chest body
    rect(t, 14, 30, 50, 36, 7)                   # lid
    for x in range(18, 50, 6):
        rect(t, x, 36, x + 2, 58, 7)             # ribs
    return t


def tex_shrine():
    t = stone_base()
    rect(t, 24, 44, 40, 60, 2)                   # pedestal
    rect(t, 26, 44, 38, 46, 4)
    disc(t, 32, 28, 14, 1)                       # halo shadow
    disc(t, 32, 28, 12, 14)                      # glowing bladder
    disc(t, 30, 24, 5, 4)                        # highlight
    return t


def tex_door():
    t = stone_base()
    rect(t, 8, 4, 56, 64, 1)                     # frame
    rect(t, 10, 6, 54, 64, 15)                   # flesh
    for i in range(12):                          # radial folds of the sphincter
        a = i * math.pi / 6
        for rr in range(4, 24):
            x = int(32 + math.cos(a) * rr)
            y = int(34 + math.sin(a) * rr)
            if 10 <= x < 54 and 6 <= y < 64:
                t[y][x] = 12
    disc(t, 32, 34, 4, 1)                        # the (closed) opening
    return t


TEXTURES = [tex_stone(), tex_tank(), tex_corpse(), tex_chest(), tex_shrine(), tex_door()]
TEX_NAMES = ["TEX_STONE", "TEX_TANK", "TEX_CORPSE", "TEX_CHEST", "TEX_SHRINE", "TEX_DOOR"]

# ---------------------------------------------------------------- backdrop (floor + ceiling)


def backdrop_pixel(x, y):
    if y < CY:
        dy = CY - (y + 0.5)
        ceil = True
    else:
        dy = (y + 0.5) - CY
        ceil = False
    z = HALF_K / dy
    if z > MAXZ:
        return 0
    lat = (x + 0.5 - CX) * z / F
    fl = (lat + 0.5) % 1.0
    fz = (z - 0.5) % 1.0
    w = 0.035 * max(1.0, z)                      # grout lines stay visible in the distance
    line = fl < w or fl > 1 - w or fz < w or fz > 1 - w
    if ceil:
        beam = fz < 2 * w or fz > 1 - 2 * w      # cross beams only: lengthwise ones made an X
        c = 8 if beam else 9
    else:
        c = 6 if line else 7                     # soft grout: a floor of flagstones, not a grid
    return SHADE[band_of(z)][c]


def backdrop():
    img = [[backdrop_pixel(x, y) for x in range(VW)] for y in range(VH)]
    mirrored = [row[::-1] for row in img]
    return img, mirrored

# ---------------------------------------------------------------- column events


def column_events(pc):
    """The cells the ray through pair `pc` crosses, nearest first."""
    s = (2 * pc + 1 - CX) / F
    events = []
    d, l, z = 0, 0, 0.0
    while True:
        zf = d + 0.5
        if s > 0:
            zl = (l + 0.5) / s
        elif s < 0:
            zl = (l - 0.5) / s
        else:
            zl = float("inf")
        if zf <= zl:
            z, d, face = zf, d + 1, "front"
        else:
            z, l, face = zl, l + (1 if s > 0 else -1), "side"
        if z >= MAXZ or d > DMAX or abs(l) > LMAX:
            break
        half = HALF_K / z
        y0, y1 = CY - half, CY + half
        top = max(0, math.ceil(y0 - 0.5))
        bot = min(VH, math.ceil(y1 - 0.5))
        rows = bot - top
        vstep = int(TEX / (2 * half) * 256)
        vstart = int(((top + 0.5) - y0) / (2 * half) * TEX * 256)
        while vstart + (rows - 1) * vstep >= TEX * 256:
            vstep -= 1
        us = []
        for i in (0, 1):
            si = (2 * pc + 0.5 + i - CX) / F
            if face == "front":
                u = si * z - (l - 0.5)
            else:
                b = l - 0.5 if s > 0 else l + 0.5          # the face plane we entered through
                zi = b / si if si != 0 else z
                u = zi - (d - 0.5)
                if s > 0:
                    u = 1.0 - u                          # keep texture reading left-to-right
            us.append(min(TEX - 1, max(0, int(u * TEX))))
        events.append((d, l, top, rows, us[0], us[1], band_of(z), vstart, vstep))
    return events


def tiles_bytes(img):
    """Pixel rows -> Mega Drive 4bpp tile layout (tile rows 0..TH-1, tiles 0..TW-1 each)."""
    out = []
    for ty in range(TH):
        for tx in range(TW):
            for r in range(8):
                row = img[ty * 8 + r]
                for k in range(4):
                    x = tx * 8 + k * 2
                    out.append((row[x] << 4) | row[x + 1])
    return out


def c_array(name, ctype, values, per_line=24):
    lines = [f"static const {ctype} {name}[{len(values)}] = {{"]
    for i in range(0, len(values), per_line):
        lines.append("    " + ", ".join(str(v) for v in values[i:i + per_line]) + ",")
    lines.append("};")
    return "\n".join(lines)


def bake(ev, t):
    """The finished bytes (both pixels of the pair, shaded) of one event drawn with texture t."""
    (d, l, top, rows, u0, u1, band, vstart, vstep) = ev
    tex = TEXTURES[t]
    out = []
    v = vstart
    for _ in range(rows):
        out.append((SHADE[band][tex[v >> 8][u0]] << 4) | SHADE[band][tex[v >> 8][u1]])
        v += vstep
    return out


def main():
    bd, bd_mirror = backdrop()
    cols = [column_events(pc) for pc in range(NPAIR)]
    start, flat, bake_off = [], [], []
    total_rows = 0
    for ev in cols:
        start.append(len(flat))
        for e in ev:
            flat.append(e)
            bake_off.append(total_rows)
            total_rows += e[3]
    start.append(len(flat))
    assert total_rows < 65536

    # Every wall column the view can ever show, pre-textured and pre-shaded, so the 68000 only
    # copies bytes (see src/view_draw.s). Block per texture, events in the same order as viewEvents.
    columns = bytearray()
    for t in range(len(TEXTURES)):
        for e in flat:
            columns.extend(bake(e, t))
    backdrops = bytearray(tiles_bytes(bd) + tiles_bytes(bd_mirror))
    # A wall right in front of the player (cell d=1, l=0) always covers the whole view, so that
    # common case (every object interaction) is one memcpy of a finished image per texture.
    adjacent = bytearray()
    for t in range(len(TEXTURES)):
        adjacent.extend(tiles_bytes(render(bd, cols, {(1, 0): t})))

    resdir = os.path.join(ROOT, "res", "view")
    os.makedirs(resdir, exist_ok=True)
    for name, data in (("columns.bin", columns), ("backdrops.bin", backdrops), ("adjacent.bin", adjacent)):
        with open(os.path.join(resdir, name), "wb") as f:
            f.write(data)

    vdp = [(b << 9) | (g << 5) | (r << 1) for r, g, b in PAL]
    out = []
    out.append("// Generated by tools/make_view.py -- do not edit by hand, re-run the script.")
    out.append("#ifndef _VIEW_GEN_H_\n#define _VIEW_GEN_H_\n")
    out.append(f"#define VIEW_W {VW}\n#define VIEW_H {VH}\n#define VIEW_TW {TW}\n#define VIEW_TH {TH}")
    out.append(f"#define VIEW_TILES {TW * TH}\n#define VIEW_BYTES {TW * TH * 32}")
    out.append(f"#define VIEW_PAIRS {NPAIR}\n#define VIEW_DMAX {DMAX}\n#define VIEW_LMAX {LMAX}")
    out.append(f"#define VIEW_TEX_ROWS {total_rows}   // bytes per texture block in viewColumns")
    for i, n in enumerate(TEX_NAMES):
        out.append(f"#define {n} {i}")
    out.append(f"#define TEX_COUNT {len(TEX_NAMES)}\n")
    out.append("// One wall crossing of a column pair's ray: the cell (d cells ahead, l to the right), the\n"
               "// wall's first visible row and row count, and its pre-baked bytes' offset in viewColumns.")
    out.append("typedef struct { s8 d, l; u8 top, rows; u16 bake; } ViewEvent;\n")
    out.append(c_array("viewPalette", "u16", vdp))
    out.append(c_array("viewColStart", "u16", start))
    ev_lines = [f"static const ViewEvent viewEvents[{len(flat)}] = {{"]
    for e, off in zip(flat, bake_off):
        ev_lines.append("    {%d, %d, %d, %d, %d}," % (e[0], e[1], e[2], e[3], off))
    ev_lines.append("};")
    out.append("\n".join(ev_lines))
    out.append("\n#endif")

    path = os.path.join(ROOT, "src", "view_gen.h")
    with open(path, "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"wrote {path}: {len(flat)} events, max {max(len(c) for c in cols)} per column; "
          f"res/view/*.bin {len(columns) + len(backdrops) + len(adjacent)} bytes")

    if "--preview" in sys.argv:
        preview(bd, cols)


# ---------------------------------------------------------------- preview (same algorithm as the C code)

def render(bd, cols, grid):
    """grid: dict (d, l) -> texture index for wall cells."""
    img = [row[:] for row in bd]
    for pc, evs in enumerate(cols):
        for ev in evs:
            if (ev[0], ev[1]) not in grid:
                continue
            for y, b in zip(range(ev[2], ev[2] + ev[3]), bake(ev, grid[(ev[0], ev[1])])):
                img[y][2 * pc] = b >> 4
                img[y][2 * pc + 1] = b & 15
            break
    return img


def save(img, path):
    im = Image.new("RGB", (VW, VH))
    im.putdata([RGB[c] for row in img for c in row])
    im.resize((VW * 3, VH * 3), Image.NEAREST).save(path)


def preview(bd, cols):
    outdir = os.path.join(ROOT, "out", "view_preview")
    os.makedirs(outdir, exist_ok=True)
    corridor = {}
    for d in range(0, 6):
        for l in range(-5, 6):
            if abs(l) >= 1:
                corridor[(d, l)] = 0
    corridor[(4, 0)] = 0
    save(render(bd, cols, corridor), os.path.join(outdir, "corridor.png"))
    room = {(d, l): 0 for d in range(0, 6) for l in range(-5, 6) if d == 4 or abs(l) == 3}
    room[(4, 1)] = 5
    save(render(bd, cols, room), os.path.join(outdir, "room.png"))
    save(render(bd, cols, {(1, 0): 1}), os.path.join(outdir, "adjacent_tank.png"))
    junction = {(d, l): 0 for d in range(0, 6) for l in range(-5, 6) if abs(l) >= 1 and d != 2}
    junction[(3, 0)] = 0
    save(render(bd, cols, junction), os.path.join(outdir, "junction.png"))
    print(f"previews in {outdir}")


if __name__ == "__main__":
    main()
