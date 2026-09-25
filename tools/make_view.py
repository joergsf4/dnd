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
# The Nautiloid (the mind flayers' ship the vertical slice takes place on) is organic throughout:
# chitin-plated walls with sinews and veins, wet floors, ribbed ceilings.
PAL = [
    (0, 0, 0),   # 0 black / darkness
    (1, 0, 1),   # 1 wall darkest: sinew gaps, deep shadow
    (2, 1, 2),   # 2 wall dark
    (3, 2, 3),   # 3 wall: chitin plates
    (5, 3, 4),   # 4 wall highlight
    (1, 1, 1),   # 5 floor dark (wet)
    (2, 2, 2),   # 6 floor
    (3, 3, 4),   # 7 floor sheen
    (4, 2, 5),   # 8 purple (mind flayer skin)
    (1, 3, 1),   # 9 slime green dark
    (3, 6, 2),   # 10 slime green light
    (1, 5, 5),   # 11 turquoise pod glass
    (6, 5, 4),   # 12 bone / cartilage
    (3, 5, 7),   # 13 blue glow
    (5, 1, 2),   # 14 flesh red
    (7, 7, 6),   # 15 bright glint
]
RGB = [tuple(round(c * 255 / 7) for c in p) for p in PAL]
SHADE_F = [1.0, 0.72, 0.48, 0.3]   # per distance band


def band_of(z):
    return 0 if z < 1.5 else 1 if z < 2.5 else 2 if z < 3.5 else 3


def nearest(rgb, family=range(16)):
    return min(family, key=lambda i: sum((a - b) ** 2 for a, b in zip(rgb, RGB[i])))


def family_of(i):
    """Wall colours only darken into wall colours, floor into floor, so distance keeps the tint."""
    return range(0, 5) if i <= 4 else (0, 5, 6, 7) if i <= 7 else range(16)


SHADE = [[i if b == 0 else nearest(tuple(c * SHADE_F[b] for c in RGB[i]), family_of(i))
          for i in range(16)] for b in range(4)]

# ---------------------------------------------------------------- textures (64x64, palette indices)


def blank(c=0):
    return [[c] * TEX for _ in range(TEX)]


def rect(t, x0, y0, x1, y1, c):
    for y in range(max(0, y0), min(TEX, y1)):
        for x in range(max(0, x0), min(TEX, x1)):
            t[y][x] = c


def ellipse(t, cx, cy, rx, ry, c):
    for y in range(TEX):
        for x in range(TEX):
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                t[y][x] = c


def in_ellipse(x, y, cx, cy, rx, ry):
    return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0


def vein(t, rng, x, y, length, c):
    """A thin wandering line, mostly downwards."""
    for _ in range(length):
        if 0 <= x < TEX and 0 <= y < TEX:
            t[y][x] = c
        y += 1
        x += rng.choice((-1, 0, 0, 1))


def organic_wall(seed):
    """Chitin plates in columns, separated by dark sinew gaps, with segment joints and veins."""
    rng = random.Random(seed)
    t = blank(3)
    joints = [rng.randint(8, 24) for _ in range(4)]        # joint height per plate column
    for x in range(TEX):
        col, px = x // 16, x % 16
        for y in range(TEX):
            jy = (y + joints[col]) % 22
            if px < 2:
                c = 1                                      # sinew gap between plates
            elif jy < 2:
                c = 2 if jy == 1 else 1                    # segment joint
            elif px < 4 or jy == 2:
                c = 4                                      # lit plate edge
            elif px > 13:
                c = 2                                      # plate curving away
            else:
                r = rng.random()
                c = 2 if r < 0.10 else 4 if r < 0.13 else 3
            t[y][x] = c
    for _ in range(3):
        vein(t, rng, rng.randint(4, 60), rng.randint(0, 30), rng.randint(14, 30), 14)
    return t


def tex_wall():
    return organic_wall(1)


def tex_door():
    """Sphincter door: a ring of flesh folded shut in a chitin frame."""
    t = organic_wall(7)
    rect(t, 6, 2, 58, 64, 1)                               # frame
    ellipse(t, 32, 34, 24, 28, 14)
    for i in range(14):                                    # folds of the sphincter
        a = i * math.tau / 14
        for rr in range(3, 26):
            x = int(32 + math.cos(a) * rr * 0.95)
            y = int(34 + math.sin(a) * rr * 1.1)
            if in_ellipse(x, y, 32, 34, 24, 28):
                t[y][x] = 2
    ellipse(t, 32, 34, 3, 4, 1)                            # the closed opening
    return t


TEXTURES = [tex_wall(), tex_door()]
TEX_NAMES = ["TEX_WALL", "TEX_DOOR"]

# ---------------------------------------------------------------- props (free-standing objects)
# A prop stands in the middle of a floor cell, drawn as an upright billboard one cell wide and one
# cell high (64x64 texels, bottom row on the floor), pre-scaled per distance like the originals
# did it. T marks transparent texels.

T = -1


def shade_body(t, x0, x1, c=3, lit=4, dark=2):
    """Side lighting for a round body: left edge lit, right edge in shadow."""
    for y in range(TEX):
        for x in range(TEX):
            if t[y][x] == c:
                if x < x0:
                    t[y][x] = lit
                elif x > x1:
                    t[y][x] = dark


def prop_pool(broken):
    """Larva pool: a fleshy basin on the floor, slime and tadpoles in it (burst: torn, empty)."""
    rng = random.Random(2)
    t = blank(T)
    if broken:
        ellipse(t, 32, 61, 31, 3, 9)                       # acid puddle around the base
    for y in range(38, 63):                                # bowl body, rounded towards the floor
        for x in range(TEX):
            if in_ellipse(x, y, 32, 38, 27, 24):
                t[y][x] = 3
    shade_body(t, 12, 51)
    for x in (18, 31, 44):                                 # veins down the bowl
        vein(t, rng, x, 42, 18, 14)
    ellipse(t, 32, 38, 27, 8, 14)                          # rim, seen slightly from above
    if broken:
        ellipse(t, 32, 38, 23, 6, 1)                       # drained, dark
        for _ in range(9):                                 # torn edge on the rim
            x = rng.randint(8, 56)
            rect(t, x - 2, 29, x + 2, 36, T)
        for _ in range(6):
            vein(t, rng, rng.randint(10, 54), 42, rng.randint(6, 16), 9)   # acid running down
    else:
        ellipse(t, 32, 38, 23, 6, 9)                       # slime
        ellipse(t, 29, 37, 12, 3, 10)                      # glow on the surface
        for _ in range(9):                                 # tadpoles: head + tail
            x, y = rng.randint(14, 48), rng.randint(35, 41)
            if in_ellipse(x, y, 32, 38, 21, 5):
                t[y][x] = t[y][x + 1] = 1
                t[y + 1][x + 2] = 1
        for _ in range(4):
            x, y = rng.randint(14, 50), rng.randint(35, 41)
            if in_ellipse(x, y, 32, 38, 21, 5):
                t[y][x] = 15                               # bubbles
    return t


def prop_chest(opened):
    """A cartilage chest: ribbed, bone coloured; lid thrown back once looted."""
    t = blank(T)
    ellipse(t, 32, 62, 28, 2, 1)                           # shadow on the floor
    if opened:
        rect(t, 11, 18, 53, 36, 3)                         # lid, inside facing us
        rect(t, 11, 18, 53, 20, 12)
        rect(t, 11, 18, 13, 36, 12)
        rect(t, 51, 18, 53, 36, 12)
        rect(t, 10, 34, 54, 41, 12)                        # rim of the open box
        rect(t, 13, 35, 51, 40, 1)                         # dark, empty inside
    else:
        rect(t, 9, 32, 55, 41, 12)                         # closed lid
        rect(t, 9, 32, 55, 34, 15)
    rect(t, 10, 41, 54, 62, 12)                            # body
    for x in range(14, 52, 7):
        rect(t, x, 41, x + 2, 62, 3)                       # cartilage ribs
    rect(t, 10, 60, 54, 62, 3)
    if not opened:
        rect(t, 29, 38, 35, 46, 14)                        # fleshy clasp
    return t


def prop_corpse():
    """A dead mind flayer, slumped on the floor: purple head, tentacles, dark robe."""
    t = blank(T)
    ellipse(t, 32, 62, 30, 2, 1)                           # shadow
    ellipse(t, 32, 53, 21, 11, 2)                          # robe
    rect(t, 11, 53, 54, 63, 2)
    rect(t, 20, 43, 44, 45, 12)                            # collar trim
    ellipse(t, 30, 34, 9, 10, 8)                           # head, lolling to one side
    for dx in (-5, -2, 1, 4):                              # tentacles over the robe
        rect(t, 30 + dx, 40, 30 + dx + 1, 53 - abs(dx), 8)
    t[32][26] = t[32][33] = 15                             # dead white eyes
    ellipse(t, 12, 60, 5, 3, 8)                            # hands on the floor
    ellipse(t, 53, 60, 5, 3, 8)
    return t


def prop_shrine():
    """Restoration station: a big blue glowing tentacle bladder on a column."""
    t = blank(T)
    ellipse(t, 32, 62, 16, 2, 1)
    rect(t, 20, 57, 44, 63, 2)                             # base
    rect(t, 20, 57, 44, 58, 4)
    rect(t, 26, 34, 38, 57, 3)                             # column
    rect(t, 26, 34, 28, 57, 4)
    rect(t, 36, 34, 38, 57, 2)
    for x, h in ((14, 16), (19, 22), (43, 22), (48, 16)):  # tentacles hanging from the bladder
        rect(t, x, 26, x + 2, 26 + h, 13)
        t[26 + h][x + (2 if x < 32 else -1)] = 13          # curled tip
    ellipse(t, 32, 21, 19, 16, 13)                         # bladder
    ellipse(t, 32, 26, 16, 9, 11)                          # darker underside
    ellipse(t, 32, 21, 17, 12, 13)
    ellipse(t, 26, 15, 6, 4, 15)                           # glow highlight
    return t


def prop_pod(broken):
    """Clone pod: an upright egg of chitin with a turquoise glass front (open, or shattered)."""
    rng = random.Random(8 if broken else 9)
    t = blank(T)
    ellipse(t, 32, 62, 22, 2, 1)
    ellipse(t, 32, 33, 20, 30, 2)                          # chitin shell
    ellipse(t, 32, 33, 18, 28, 3)
    shade_body(t, 19, 46)
    ellipse(t, 32, 35, 13, 22, 1)                          # dark inside
    if broken:
        for y in range(TEX):                               # jagged remains of the glass
            for x in range(TEX):
                if in_ellipse(x, y, 32, 35, 13, 22) and not in_ellipse(x, y, 32, 35, 10, 18):
                    if (x * 7 + y * 3) % 5 < 3:
                        t[y][x] = 11
        for _ in range(5):
            t[rng.randint(22, 50)][rng.randint(24, 40)] = 15   # glints on the shards
        for _ in range(8):                                 # shards on the floor
            x = rng.randint(6, 58)
            t[rng.randint(60, 63)][x] = rng.choice((11, 15))
    else:
        for _ in range(6):                                 # slime running down inside
            vein(t, rng, rng.randint(24, 40), rng.randint(16, 30), rng.randint(8, 20), 10)
        ellipse(t, 32, 53, 11, 3, 9)                       # slime pooled at the bottom
        for y in range(TEX):                               # glass front swung open to the left
            for x in range(TEX):
                if in_ellipse(x, y, 9, 34, 5, 21):
                    t[y][x] = 11 if x > 6 else 15
        rect(t, 13, 30, 18, 34, 12)                        # hinge
    ellipse(t, 32, 60, 18, 3, 14)                          # sinews anchoring it to the floor
    return t


PROPS = [prop_pool(False), prop_pool(True), prop_chest(False), prop_chest(True), prop_corpse(),
         prop_shrine(), prop_pod(False), prop_pod(True)]
PROP_NAMES = ["PROP_POOL", "PROP_POOL_BROKEN", "PROP_CHEST", "PROP_CHEST_OPEN", "PROP_CORPSE",
              "PROP_SHRINE", "PROP_POD_OPEN", "PROP_POD_BROKEN"]


def bake_prop(sprite, d):
    """A prop at distance d, pre-scaled and shaded, as column pairs relative to its centre pair:
    (left pair offset, [(top, rows, [mask, data] * rows)]). mask keeps the background nibble
    where a texel is transparent."""
    half = HALF_K / d
    y0 = CY - half
    scale = TEX / (2 * half)                               # texels per pixel, both axes
    band = band_of(d)
    k0 = math.floor(-half / 2) - 1
    cols = []
    for k in range(k0, -k0 + 1):
        px = []
        for y in range(VH):
            v = int((y + 0.5 - y0) * scale)
            pair = []
            for i in (0, 1):
                u = int(TEX / 2 + (2 * k + i + 0.5) * scale)
                c = sprite[v][u] if 0 <= v < TEX and 0 <= u < TEX else T
                pair.append(c)
            px.append(pair)
        ys = [y for y in range(VH) if px[y] != [T, T]]
        if not ys:
            cols.append((0, 0, []))
            continue
        top, bot = ys[0], ys[-1] + 1
        data = []
        for y in range(top, bot):
            a, b = px[y]
            mask = (0xF0 if a == T else 0) | (0x0F if b == T else 0)
            val = ((SHADE[band][a] << 4) if a != T else 0) | (SHADE[band][b] if b != T else 0)
            data += [mask, val]
        cols.append((top, bot - top, data))
    while cols and cols[0][1] == 0:
        cols.pop(0)
        k0 += 1
    while cols and cols[-1][1] == 0:
        cols.pop()
    return k0, cols


def prop_center(d, l):
    """Column pair of a prop's centre, d cells ahead and l to the right."""
    return round((CX + l * F / d) / 2)


# ---------------------------------------------------------------- backdrop (floor + ceiling)


def hash01(a, b):
    h = (a * 73856093) ^ (b * 19349663)
    h = (h ^ (h >> 13)) * 1274126177
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0


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
    w = 0.035 * max(1.0, z)                      # lines stay visible in the distance
    if ceil:
        rib = fz < 2.5 * w or fz > 1 - 2.5 * w   # organic ribs across the corridor
        c = 2 if rib else 1
    else:
        seam = fl < w or fl > 1 - w or fz < w or fz > 1 - w
        # wet, uneven floor: dark patches and glossy puddles, fixed in world space
        n = hash01(math.floor(lat * 3), math.floor(z * 5))
        c = 5 if seam else 7 if n < 0.12 else 5 if n < 0.35 else 6
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

    # Props, pre-scaled per distance: per (prop, d) a record [pair count, left pair offset (s8),
    # then per pair: top row, row count, (mask, data) byte pairs]; offsets in viewPropOffset.
    props = bytearray()
    prop_off = []
    for sprite in PROPS:
        row = [0]
        for d in range(1, DMAX + 1):
            row.append(len(props))
            left, pcols = bake_prop(sprite, d)
            props.extend([len(pcols), left & 0xFF])
            for top, rows, data in pcols:
                props.extend([top, rows] + data)
        prop_off.append(row)

    resdir = os.path.join(ROOT, "res", "view")
    os.makedirs(resdir, exist_ok=True)
    for name, data in (("columns.bin", columns), ("backdrops.bin", backdrops), ("adjacent.bin", adjacent),
                       ("props.bin", props)):
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
    out.append(f"#define TEX_COUNT {len(TEX_NAMES)}")
    for i, n in enumerate(PROP_NAMES):
        out.append(f"#define {n} {i}")
    out.append(f"#define PROP_COUNT {len(PROP_NAMES)}")
    out.append(f"#define VIEW_HALF_K {int(HALF_K)}   // a wall at depth z is 2 * VIEW_HALF_K / z rows high")
    out.append(f"#define VIEW_CY {int(CY)}\n")
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
    out.append("\n// Props: record offset in viewProps per prop and distance (d = 1..VIEW_DMAX), and the column\n"
               "// pair of a prop's centre d cells ahead and l to the right (index l + VIEW_LMAX).")
    out.append(f"static const u32 viewPropOffset[{len(PROPS)}][{DMAX + 1}] = {{")
    for row in prop_off:
        out.append("    { " + ", ".join(str(v) for v in row) + " },")
    out.append("};")
    out.append(f"static const s16 viewPropCenter[{DMAX + 1}][{2 * LMAX + 1}] = {{")
    for d in range(DMAX + 1):
        out.append("    { " + ", ".join(str(prop_center(d, l) if d else 0) for l in range(-LMAX, LMAX + 1)) + " },")
    out.append("};")
    out.append("\n#endif")

    path = os.path.join(ROOT, "src", "view_gen.h")
    with open(path, "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"wrote {path}: {len(flat)} events, max {max(len(c) for c in cols)} per column; "
          f"res/view/*.bin {len(columns) + len(backdrops) + len(adjacent) + len(props)} bytes")

    if "--preview" in sys.argv:
        preview(bd, cols)


# ---------------------------------------------------------------- preview (same algorithm as the C code)

def render(bd, cols, grid, props=None):
    """grid: dict (d, l) -> texture index for wall cells; props: dict (d, l) -> prop index."""
    img = [row[:] for row in bd]
    wall_h = [0] * NPAIR                   # height above the horizon of the wall drawn per pair
    for pc, evs in enumerate(cols):
        for ev in evs:
            if (ev[0], ev[1]) not in grid:
                continue
            for y, b in zip(range(ev[2], ev[2] + ev[3]), bake(ev, grid[(ev[0], ev[1])])):
                img[y][2 * pc] = b >> 4
                img[y][2 * pc + 1] = b & 15
            wall_h[pc] = int(CY) - ev[2]
            break
    for d in range(DMAX, 0, -1):          # far to near, so nearer props cover farther ones
        for l in range(-min(d, LMAX), min(d, LMAX) + 1):
            if (props or {}).get((d, l)) is None:
                continue
            left, pcols = bake_prop(PROPS[props[(d, l)]], d)
            for k, (top, rows, data) in enumerate(pcols):
                pc = prop_center(d, l) + left + k
                if not 0 <= pc < NPAIR or wall_h[pc] * d >= int(HALF_K):
                    continue               # off screen, or the wall in this column is nearer
                for i in range(rows):
                    mask, val = data[2 * i], data[2 * i + 1]
                    for j, (m, v) in enumerate(((mask >> 4, val >> 4), (mask & 15, val & 15))):
                        if not m:
                            img[top + i][2 * pc + j] = v
    return img


def save(img, path):
    im = Image.new("RGB", (VW, VH))
    im.putdata([RGB[c] for row in img for c in row])
    im.resize((VW * 3, VH * 3), Image.NEAREST).save(path)


def preview(bd, cols):
    outdir = os.path.join(ROOT, "out", "view_preview")
    os.makedirs(outdir, exist_ok=True)
    corridor = {(d, l): 0 for d in range(0, 6) for l in range(-5, 6) if abs(l) >= 1}
    corridor[(4, 0)] = 1
    save(render(bd, cols, corridor, {(2, 0): 2}), os.path.join(outdir, "corridor.png"))
    room = {(d, l): 0 for d in range(0, 6) for l in range(-5, 6) if d == 4 or abs(l) == 3}
    room[(4, 1)] = 1
    save(render(bd, cols, room, {(2, 0): 0, (1, -1): 6, (3, 2): 5, (3, -2): 7, (2, 1): 4, (1, 1): 3}),
         os.path.join(outdir, "room.png"))
    save(render(bd, cols, room, {(1, 0): 6}), os.path.join(outdir, "adjacent_pod.png"))
    # every prop at distance 1 and 3, for judging the art
    sheet = Image.new("RGB", (VW * len(PROPS) // 2, VH * 2))
    for i in range(len(PROPS)):
        im = Image.new("RGB", (VW, VH))
        im.putdata([RGB[c] for row in render(bd, cols, room, {(1, 0): i, (3, 1): i}) for c in row])
        sheet.paste(im, ((i % 4) * VW, (i // 4) * VH))
    sheet.save(os.path.join(outdir, "props.png"))
    print(f"previews in {outdir}")


if __name__ == "__main__":
    main()
