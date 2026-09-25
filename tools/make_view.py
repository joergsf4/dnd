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
# The Nautiloid (the mind flayers' ship the vertical slice takes place on), after BG3's look:
# near-black, blue-grey chitin ribs with glowing red membranes between them, a fleshy mauve floor,
# everything grown rather than built; cold blue light for the ship's "technology".
BLACK = 0
CH0, CH1, CH2, CH3 = 1, 2, 3, 4          # chitin, darkest to highlight
FL0, FL1, FL2 = 5, 6, 7                  # fleshy floor, dark to wet sheen
MEM0, MEM1, MEM2 = 8, 9, 10              # glowing membrane, dark red to hot glow
TEAL = 11                                # slime, pod glass
BONE = 12                                # bone, cartilage, pale skin
BLUE = 13                                # psionic / technological glow
FLESH = 14                               # mind flayer skin, brains, fleshy rims
GLINT = 15
PAL = [
    (0, 0, 0),   # BLACK
    (1, 1, 1),   # CH0
    (2, 2, 3),   # CH1
    (3, 3, 4),   # CH2
    (5, 5, 6),   # CH3
    (2, 1, 2),   # FL0
    (4, 2, 3),   # FL1
    (5, 3, 4),   # FL2
    (3, 0, 1),   # MEM0
    (5, 1, 1),   # MEM1
    (7, 3, 2),   # MEM2
    (1, 5, 5),   # TEAL
    (6, 5, 4),   # BONE
    (3, 5, 7),   # BLUE
    (5, 2, 4),   # FLESH
    (7, 7, 6),   # GLINT
]
RGB = [tuple(round(c * 255 / 7) for c in p) for p in PAL]
SHADE_F = [1.0, 0.72, 0.48, 0.3]   # per distance band


def band_of(z):
    return 0 if z < 1.5 else 1 if z < 2.5 else 2 if z < 3.5 else 3


def nearest(rgb, family=range(16)):
    return min(family, key=lambda i: sum((a - b) ** 2 for a, b in zip(rgb, RGB[i])))


def family_of(i):
    """Colours darken with distance within their own family (chitin, floor, membrane), so the
    distance keeps the tint instead of drifting into another material."""
    if i <= CH3:
        return range(0, CH3 + 1)
    if i <= FL2:
        return (BLACK, FL0, FL1, FL2)
    if i <= MEM2:
        return (BLACK, MEM0, MEM1, MEM2)
    return range(16)


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


def membrane(t, x0, y0, x1, y1):
    """A glowing red membrane between ribs: an elongated oval, hottest down the middle, with
    fibrous vertical striations and a dark chitin seam around it."""
    cx, cy = (x0 + x1 - 1) / 2, (y0 + y1 - 1) / 2
    rx, ry = (x1 - x0) / 2, (y1 - y0) / 2
    for y in range(y0 - 1, y1 + 1):
        for x in range(x0 - 1, x1 + 1):
            if not (0 <= x < TEX and 0 <= y < TEX):
                continue
            if in_ellipse(x, y, cx, cy, rx, ry):
                e = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                c = MEM2 if e < 0.12 else MEM1 if e < 0.6 else MEM0
                if c != MEM2 and (x - x0) % 3 == 0:
                    c = MEM0 if c == MEM1 else CH0             # fibres
                t[y][x] = c
            elif in_ellipse(x, y, cx, cy, rx + 1.2, ry + 1.2):
                t[y][x] = CH0


def organic_wall(seed):
    """Two bays per cell: dark, slightly arched chitin ribs with lit edges, a glowing membrane in
    each bay, and irregular overlapping chitin scales around it (nothing straight, nothing
    regular -- straight plate lines read as riveted metal)."""
    rng = random.Random(seed)
    t = blank(CH0)
    for y in range(TEX):                                   # scales: short lit arcs on dark ground
        for x in range(TEX):
            if rng.random() < 0.05:
                t[y][x] = CH1
    for _ in range(26):
        cx, cy = rng.randint(0, 63), rng.randint(0, 63)
        r = rng.randint(3, 6)
        for dx in range(-r, r + 1):
            yy = cy - int(math.sqrt(max(0, r * r - dx * dx)) * 0.6)
            if 0 <= cx + dx < TEX and 0 <= yy < TEX:
                t[yy][cx + dx] = CH1
                if 0 <= yy + 1 < TEX:
                    t[yy + 1][cx + dx] = CH0
    for bay in (0, 32):
        membrane(t, bay + 9, 10 + rng.randint(0, 3), bay + 27, 52 + rng.randint(0, 3))
        for y in range(TEX):                               # rib, bowing out towards the middle
            x = bay + int(round(2.5 * math.sin(math.pi * y / TEX)))
            for i, c in enumerate((CH1, CH2, CH3, CH2, CH1, BLACK)):
                if 0 <= x + i < TEX:
                    t[y][x + i] = c
            if y % 11 == 5 and 0 <= x + 2 < TEX:
                t[y][x + 1] = t[y][x + 2] = CH1            # rib segments
    rect(t, 0, 61, TEX, TEX, BLACK)                        # dark footing along the floor
    return t


def tex_wall():
    return organic_wall(1)


def tex_door():
    """Sphincter door: folds of red flesh drawn shut in a ring of chitin."""
    t = organic_wall(7)
    ellipse(t, 32, 33, 29, 31, CH0)
    ellipse(t, 32, 33, 27, 29, CH2)                        # chitin ring
    ellipse(t, 32, 33, 23, 25, MEM1)
    for i in range(14):                                    # folds
        a = i * math.tau / 14
        for rr in range(3, 24):
            x = int(32 + math.cos(a) * rr * 0.95)
            y = int(33 + math.sin(a) * rr * 1.05)
            if in_ellipse(x, y, 32, 33, 23, 25):
                t[y][x] = MEM0
    ellipse(t, 32, 33, 9, 10, MEM2)                        # glow from the other side
    for i in range(14):
        a = i * math.tau / 14
        for rr in range(2, 10):
            t[int(33 + math.sin(a) * rr)][int(32 + math.cos(a) * rr)] = MEM1
    ellipse(t, 32, 33, 2, 3, BLACK)
    return t


def tex_tablet():
    """A slate of dark chitin grown into the wall, blue glowing diagrams on it (Room 2 lore)."""
    rng = random.Random(10)
    t = organic_wall(10)
    rect(t, 8, 8, 56, 54, CH0)
    rect(t, 10, 10, 54, 52, CH2)                           # ridged frame
    rect(t, 10, 10, 54, 11, CH3)
    rect(t, 13, 13, 51, 49, BLACK)
    ellipse(t, 32, 24, 9, 8, BLUE)                         # a head...
    ellipse(t, 32, 24, 7, 6, BLACK)
    for dx in (-6, -2, 2, 6):                              # ...with tentacles reaching round it
        vein(t, rng, 32 + dx, 30, 10, BLUE)
    for y in range(41, 48, 3):                             # rows of glyphs
        for x in range(16, 49, 4):
            if rng.random() < 0.8:
                rect(t, x, y, x + 2, y + 1, BLUE)
    return t


def tex_breach():
    """A tear in the hull (Room 3): ragged chitin edges, and outside the burning sky of Avernus --
    glowing red haze, black rocks drifting in it, a dragon's silhouette far away."""
    rng = random.Random(12)
    t = organic_wall(12)
    edge = []
    for y in range(TEX):                                   # ragged outline of the hole
        w = 22 + int(6 * math.sin(y / 5.0)) + rng.randint(-2, 2)
        if y < 5 or y > 58:
            w = max(0, w - (5 - y if y < 5 else y - 58) * 6)
        edge.append(w)
    for y in range(TEX):
        for x in range(TEX):
            if abs(x - 32) < edge[y]:
                v = y + ((x * 5 + y * 3) % 7) - 3 + rng.randint(-3, 3)   # dithered bands
                c = MEM2 if v > 42 else MEM1 if v > 20 else MEM0   # sky: hotter towards below
                t[y][x] = c
            elif abs(x - 32) < edge[y] + 2:
                t[y][x] = CH3                              # torn, lit edge
    for cx, cy, r in ((20, 20, 4), (41, 30, 3), (29, 48, 5), (46, 50, 2)):   # drifting rocks
        for y in range(TEX):
            for x in range(TEX):
                if abs(x - 32) < edge[y] and (x - cx) ** 2 + ((y - cy) * 1.3) ** 2 < r * r:
                    t[y][x] = BLACK
    for dx, dy in ((0, 0), (1, 0), (2, 0), (-1, -1), (-2, -2), (3, -1), (4, -2), (1, 1)):
        t[14 + dy][36 + dx] = BLACK                        # a dragon, wings spread
    return t


TEXTURES = [tex_wall(), tex_door(), tex_tablet(), tex_breach()]
TEX_NAMES = ["TEX_WALL", "TEX_DOOR", "TEX_TABLET", "TEX_BREACH"]

# ---------------------------------------------------------------- props (free-standing objects)
# A prop stands in the middle of a floor cell, drawn as an upright billboard one cell wide and one
# cell high (64x64 texels, bottom row on the floor), pre-scaled per distance like the originals
# did it. T marks transparent texels. Nothing on this ship is built, it's all grown: stalks,
# claws, shells, membranes.

T = -1


def shade_body(t, x0, x1, c, lit, dark):
    """Side lighting for a round body: left edge lit, right edge in shadow."""
    for y in range(TEX):
        for x in range(TEX):
            if t[y][x] == c:
                if x < x0:
                    t[y][x] = lit
                elif x > x1:
                    t[y][x] = dark


def shadow(t, rx):
    ellipse(t, 32, 62, rx, 2, BLACK)


def claw(t, x, y0, y1, bend, c=CH2, tip=CH3):
    """A curved chitin claw/finger rising from the floor, bending by `bend` towards the top."""
    for y in range(y0, y1):
        k = (y1 - y) / max(1, y1 - y0)                     # 0 at the root, 1 at the tip
        xx = int(round(x + bend * k * k))
        w = 2 if k < 0.7 else 1
        for i in range(w):
            if 0 <= xx + i < TEX:
                t[y][xx + i] = tip if k > 0.85 else c


def prop_pool(broken):
    """Larva pool: a chitin basin with a fleshy rim, teal slime and tadpoles in it (burst: torn,
    drained, slime running down)."""
    rng = random.Random(2)
    t = blank(T)
    shadow(t, 30)
    if broken:
        ellipse(t, 32, 61, 31, 3, TEAL)                    # slime puddle round the base
    for y in range(38, 63):                                # basin, rounded towards the floor
        for x in range(TEX):
            if in_ellipse(x, y, 32, 38, 27, 24):
                t[y][x] = CH2
    shade_body(t, 12, 51, CH2, CH3, CH1)
    for x in range(10, 56, 7):                             # ribs round the basin
        for y in range(40, 61):
            if t[y][x] != T:
                t[y][x] = CH0
    ellipse(t, 32, 38, 27, 8, FLESH)                       # fleshy rim, seen slightly from above
    ellipse(t, 32, 37, 26, 6, FL2)
    if broken:
        ellipse(t, 32, 38, 23, 6, BLACK)                   # drained
        for _ in range(9):                                 # torn edge
            x = rng.randint(8, 56)
            rect(t, x - 2, 29, x + 2, 36, T)
        for _ in range(6):
            vein(t, rng, rng.randint(10, 54), 42, rng.randint(6, 16), TEAL)
    else:
        ellipse(t, 32, 38, 23, 6, TEAL)                    # slime
        ellipse(t, 29, 37, 12, 3, BLUE)                    # glow on the surface
        for _ in range(9):                                 # tadpoles: head + tail
            x, y = rng.randint(14, 48), rng.randint(35, 41)
            if in_ellipse(x, y, 32, 38, 21, 5):
                t[y][x] = t[y][x + 1] = CH0
                t[y + 1][x + 2] = CH0
        for _ in range(4):
            x, y = rng.randint(14, 50), rng.randint(35, 41)
            if in_ellipse(x, y, 32, 38, 21, 5):
                t[y][x] = GLINT                            # bubbles
    return t


def prop_chest(opened):
    """A cartilage chest: a ribbed, rounded box of pale cartilage with a fleshy clasp; the lid
    peeled back once looted."""
    t = blank(T)
    shadow(t, 28)
    if opened:
        ellipse(t, 32, 30, 21, 12, FL1)                    # lid peeled back, inside facing us
        ellipse(t, 32, 30, 18, 9, FL0)
        for dx in (-9, 0, 9):
            vein(t, random.Random(dx), 32 + dx, 22, 14, MEM0)
    for y in range(36, 63):                                # body: rounded box
        for x in range(TEX):
            if in_ellipse(x, y, 32, 48, 24, 16) and y >= 38:
                t[y][x] = FL2
    shade_body(t, 14, 50, FL2, BONE, FL1)
    for x in (15, 23, 32, 41, 49):                         # cartilage ribs
        for y in range(39, 62):
            if t[y][x] != T:
                t[y][x] = BONE if x < 32 else FL1
            if x + 1 < TEX and t[y][x + 1] != T:
                t[y][x + 1] = FL0
    if opened:
        ellipse(t, 32, 39, 22, 4, FL0)                     # the open top
        ellipse(t, 32, 39, 19, 3, BLACK)
    else:
        ellipse(t, 32, 39, 24, 6, BONE)                    # domed lid
        ellipse(t, 32, 38, 21, 4, FL2)
        rect(t, 12, 38, 52, 39, BONE)
        ellipse(t, 32, 44, 4, 3, MEM1)                     # fleshy sphincter clasp
        t[44][32] = BLACK
    return t


def prop_corpse():
    """A dead mind flayer, slumped on the floor: purple head, tentacles, dark robe with red trim."""
    t = blank(T)
    shadow(t, 30)
    ellipse(t, 32, 53, 21, 11, CH1)                        # robe
    rect(t, 11, 53, 54, 63, CH1)
    for y in range(44, 63):                                # a fold in the robe
        t[y][40 + (y - 44) // 6] = CH0
    rect(t, 20, 43, 44, 45, MEM1)                          # red collar trim
    ellipse(t, 30, 34, 9, 10, FLESH)                       # head, lolling to one side
    ellipse(t, 27, 30, 4, 3, FL2)                          # shine on the skull
    for dx in (-5, -2, 1, 4):                              # tentacles over the robe
        rect(t, 30 + dx, 40, 30 + dx + 1, 53 - abs(dx), FLESH)
    t[33][26] = t[33][33] = GLINT                          # dead white eyes
    ellipse(t, 12, 60, 5, 3, FLESH)                        # hands on the floor
    ellipse(t, 53, 60, 5, 3, FLESH)
    return t


def prop_shrine():
    """Restoration station: a big blue glowing tentacle bladder on a ribbed chitin stalk."""
    t = blank(T)
    shadow(t, 18)
    for dx, bend in ((-12, -6), (-7, -3), (7, 3), (12, 6)):   # roots spreading into the floor
        claw(t, 32 + dx // 2, 52, 63, -bend, CH1, CH1)
    for y in range(32, 60):                                # stalk, thicker at the bottom
        w = 5 + (y - 32) // 7
        rect(t, 32 - w, y, 32 + w, y + 1, CH2)
        t[y][32 - w] = t[y][33 - w] = CH3
        t[y][31 + w] = CH0
        if y % 5 == 0:
            rect(t, 32 - w, y, 32 + w, y + 1, CH0)         # ribs
    for x, h in ((13, 16), (18, 22), (44, 22), (49, 16)):  # tentacles hanging from the bladder
        rect(t, x, 26, x + 2, 26 + h, BLUE)
        t[26 + h][x + (2 if x < 32 else -1)] = BLUE        # curled tip
    ellipse(t, 32, 21, 19, 16, BLUE)                       # bladder
    ellipse(t, 32, 27, 16, 8, TEAL)                        # darker underside
    ellipse(t, 32, 21, 17, 12, BLUE)
    for i in range(5):                                     # veins over it
        vein(t, random.Random(20 + i), 20 + i * 6, 8, 12, TEAL)
    ellipse(t, 26, 15, 6, 4, GLINT)                        # glow highlight
    return t


def prop_pod(broken):
    """Clone pod: an upright egg of ridged red flesh, held by dark chitin claws, its teal glass
    front swung open (or shattered)."""
    rng = random.Random(8 if broken else 9)
    t = blank(T)
    shadow(t, 24)
    ellipse(t, 32, 33, 20, 30, MEM0)                       # fleshy shell
    for y in range(4, 63, 4):                              # horizontal ridges
        for x in range(TEX):
            if t[y][x] == MEM0:
                t[y][x] = MEM1
    shade_body(t, 17, 47, MEM1, MEM2, MEM0)
    ellipse(t, 32, 35, 13, 22, BLACK)                      # dark inside
    if broken:
        for y in range(TEX):                               # jagged remains of the glass
            for x in range(TEX):
                if in_ellipse(x, y, 32, 35, 13, 22) and not in_ellipse(x, y, 32, 35, 10, 18):
                    if (x * 7 + y * 3) % 5 < 3:
                        t[y][x] = TEAL
        for _ in range(5):
            t[rng.randint(22, 50)][rng.randint(24, 40)] = GLINT
        for _ in range(8):                                 # shards on the floor
            t[rng.randint(60, 63)][rng.randint(6, 58)] = rng.choice((TEAL, GLINT))
    else:
        for _ in range(6):                                 # slime running down inside
            vein(t, rng, rng.randint(24, 40), rng.randint(16, 30), rng.randint(8, 20), TEAL)
        for y in range(TEX):                               # glass front swung open to the left
            for x in range(TEX):
                if in_ellipse(x, y, 8, 34, 5, 21):
                    t[y][x] = TEAL if x > 5 else GLINT
    for x, bend in ((13, 7), (17, 10), (47, -10), (51, -7)):   # claws gripping the shell
        claw(t, x, 30, 63, bend)
    ellipse(t, 32, 61, 16, 2, CH1)                         # root
    return t


def prop_myrnath(dead):
    """Myrnath: an elf in a chitin cradle, bound by fleshy tentacles, skull sawn open and the brain
    bulging out (dead: slumped sideways, the skull empty)."""
    t = blank(T)
    shadow(t, 30)
    hx = 38 if dead else 32                                # head position (slumped when dead)
    hy = 22 if dead else 18
    for y in range(26, 63):                                # cradle: a chitin shell behind him
        for x in range(TEX):
            if in_ellipse(x, y, 32, 46, 26, 20) and not in_ellipse(x, y, 32, 40, 17, 16):
                t[y][x] = CH2
    shade_body(t, 12, 52, CH2, CH3, CH1)
    for x in (9, 18, 46, 55):
        for y in range(30, 62):
            if t[y][x] != T:
                t[y][x] = CH0                              # ribs of the cradle
    rect(t, 24, 28, 41, 48, BONE)                          # pale torso
    for y in (32, 38):
        rect(t, 24, y, 41, y + 2, GLINT)                   # bandages
    rect(t, 19, 29, 24, 46, BONE)                          # arms
    rect(t, 41, 29, 46, 46, BONE)
    rect(t, 24, 44, 41, 48, CH1)                           # torn tunic
    rect(t, 25, 48, 31, 60, CH1)                           # legs
    rect(t, 34, 48, 40, 60, CH1)
    for y in (40, 54):                                     # tentacle restraints
        rect(t, 14, y, 51, y + 2, FLESH)
        rect(t, 14, y + 2, 51, y + 3, MEM0)
    ellipse(t, hx, hy, 7, 8, BONE)                         # face
    t[hy + 1][hx - 3] = t[hy + 1][hx + 3] = CH0            # eyes
    rect(t, hx - 2, hy + 5, hx + 3, hy + 6, MEM0)          # mouth, twisted with pain
    t[hy - 2][hx - 8] = t[hy - 1][hx - 8] = BONE           # pointed ears
    t[hy - 2][hx + 8] = t[hy - 1][hx + 8] = BONE
    if dead:
        ellipse(t, hx, hy - 6, 6, 3, BLACK)                # the empty skull
        rect(t, hx - 4, hy - 4, hx + 4, hy - 3, MEM1)
    else:
        ellipse(t, hx, hy - 8, 8, 6, FLESH)                # the brain, bulging out
        for dx in (-5, -2, 1, 4):
            rect(t, hx + dx, hy - 13, hx + dx + 1, hy - 4, MEM0)   # folds
        t[hy - 12][hx - 3] = GLINT
    return t


def prop_op_table():
    """A vivisection table: a chitin slab carried by curved claws, lit red from below, remains
    on it."""
    t = blank(T)
    shadow(t, 26)
    for x, bend in ((14, 8), (24, 3), (40, -3), (50, -8)):   # claws carrying the slab
        claw(t, x, 42, 63, bend, CH1, CH2)
    ellipse(t, 32, 44, 22, 3, MEM1)                        # red glow on the underside
    rect(t, 4, 36, 60, 42, CH2)                            # slab
    rect(t, 4, 36, 60, 37, CH3)
    rect(t, 4, 41, 60, 42, CH0)
    for x in range(8, 60, 8):
        t[38][x] = t[39][x] = CH1
    ellipse(t, 22, 33, 10, 4, FLESH)                       # remains
    ellipse(t, 22, 33, 6, 2, MEM1)
    ellipse(t, 40, 34, 7, 3, BONE)
    rect(t, 48, 33, 56, 35, BONE)                          # a bone
    rect(t, 10, 30, 12, 36, CH3)                           # a surgical claw
    return t


def prop_lectern():
    """A lectern grown from the floor: a twisted chitin stalk opening into a shell-shaped plate
    with blue glowing script on it -- the mind flayers' notes."""
    rng = random.Random(11)
    t = blank(T)
    shadow(t, 16)
    for dx, bend in ((-8, -5), (8, 5)):
        claw(t, 32 + dx // 2, 54, 63, -bend, CH1, CH1)     # roots
    for y in range(34, 60):                                # twisted stalk
        x0 = 28 + int(2 * math.sin(y / 3))
        rect(t, x0, y, x0 + 8, y + 1, CH2)
        t[y][x0] = CH3
        t[y][x0 + 7] = CH0
    for y in range(16, 38):                                # shell-shaped plate, fanned ridges
        for x in range(TEX):
            if in_ellipse(x, y, 32, 38, 25, 20) and y < 36:
                a = math.atan2(38 - y, x - 32)
                t[y][x] = CH0 if int(a * 9) % 2 else CH1
    for y in range(16, 38):                                # lit rim
        for x in range(TEX):
            if t[y][x] != T and not in_ellipse(x, y, 32, 38, 23, 18):
                t[y][x] = CH3
    for _ in range(9):                                     # glowing script, curling strokes
        x, y = rng.randint(16, 46), rng.randint(22, 33)
        for i in range(rng.randint(3, 6)):
            if 0 <= y < TEX and 0 <= x + i < TEX and in_ellipse(x + i, y, 32, 38, 21, 16):
                t[y][x + i] = BLUE
            y += rng.choice((-1, 0, 1))
    ellipse(t, 32, 36, 5, 2, MEM1)                         # where plate meets stalk: a fleshy node
    return t


def prop_fire():
    """Burning wreckage on the floor: charred chitin, flames licking up from it."""
    rng = random.Random(13)
    t = blank(T)
    shadow(t, 26)
    for x0, x1, y0 in ((8, 30, 52), (26, 56, 55), (14, 44, 58)):   # charred debris
        rect(t, x0, y0, x1, y0 + 5, CH0)
        rect(t, x0, y0, x1, y0 + 1, CH1)
    for _ in range(9):                                     # flames: tapering tongues
        x, h = rng.randint(12, 50), rng.randint(14, 34)
        for i in range(h):
            y = 58 - i
            w = max(0, int(4 * (1 - i / h)) + 1)
            k = i / h
            c = BONE if k < 0.3 else MEM2 if k < 0.7 else MEM1
            xx = x + int(2 * math.sin(i / 3.0 + x))
            rect(t, xx - w, y, xx + w, y + 1, c)
    for _ in range(10):
        t[rng.randint(8, 30)][rng.randint(12, 52)] = MEM2  # embers
    return t


def prop_tank(broken):
    """Nautiloid acid tank: a cartilage barrel filled with purple acid, veins over it (burst:
    torn open, acid spilled)."""
    rng = random.Random(14)
    t = blank(T)
    shadow(t, 20)
    if broken:
        ellipse(t, 32, 61, 30, 3, FLESH)                   # spilled acid
    for y in range(22, 62):
        for x in range(TEX):
            if in_ellipse(x, y, 32, 42, 16, 21):
                t[y][x] = FLESH
    shade_body(t, 22, 42, FLESH, FL2, FL0)
    for y in (26, 40, 54):                                 # cartilage hoops
        for x in range(TEX):
            if t[y][x] != T:
                t[y][x] = BONE
                t[y + 1][x] = FL1
    for _ in range(4):
        vein(t, rng, rng.randint(20, 44), 28, 10, MEM0)
    if broken:
        ellipse(t, 32, 26, 13, 6, T)                       # the top blown away
        for _ in range(10):
            x = rng.randint(18, 46)
            rect(t, x - 1, 22, x + 1, 30 + rng.randint(0, 5), T)
        for _ in range(5):
            vein(t, rng, rng.randint(20, 44), 32, 20, FL2)
    else:
        ellipse(t, 32, 23, 14, 3, FL2)                     # lid
        ellipse(t, 28, 34, 3, 5, GLINT)                    # glossy shine
    return t


def prop_imps():
    """A troop of three imps hovering in the corridor, as seen before a fight."""
    t = blank(T)
    for cx, cy, s in ((16, 28, 1.1), (48, 26, 1.1), (32, 36, 1.4)):   # back to front
        for side in (-1, 1):                               # wings
            for i in range(int(10 * s)):
                for j in range(int(7 * s) - i // 2):
                    x = int(cx + side * (4 * s + i))
                    y = int(cy - 6 * s + j + i // 3)
                    if 0 <= x < TEX and 0 <= y < TEX:
                        t[y][x] = CH0
        ellipse(t, cx, cy, 4 * s, 6 * s, MEM1)             # body
        ellipse(t, cx, cy - 9 * s, 4 * s, 4 * s, MEM1)     # head
        t[int(cy - 9 * s)][int(cx - 2 * s)] = t[int(cy - 9 * s)][int(cx + 2 * s)] = BONE   # eyes
        t[int(cy - 14 * s)][int(cx - 3 * s)] = t[int(cy - 14 * s)][int(cx + 3 * s)] = CH2  # horns
        for i in range(int(12 * s)):                       # tail
            t[int(cy + 5 * s + i)][int(cx + 2 * math.sin(i / 2.0))] = MEM0
        rect(t, int(cx + 6 * s), int(cy - 16 * s), int(cx + 6 * s) + 1, int(cy + 8 * s), CH2)  # trident
    return t


PROPS = [prop_pool(False), prop_pool(True), prop_chest(False), prop_chest(True), prop_corpse(),
         prop_shrine(), prop_pod(False), prop_pod(True), prop_myrnath(False), prop_myrnath(True),
         prop_op_table(), prop_lectern(), prop_fire(), prop_tank(False), prop_tank(True), prop_imps()]
PROP_NAMES = ["PROP_POOL", "PROP_POOL_BROKEN", "PROP_CHEST", "PROP_CHEST_OPEN", "PROP_CORPSE",
              "PROP_SHRINE", "PROP_POD_OPEN", "PROP_POD_BROKEN", "PROP_MYRNATH", "PROP_MYRNATH_DEAD",
              "PROP_OP_TABLE", "PROP_LECTERN", "PROP_FIRE", "PROP_TANK", "PROP_TANK_BROKEN", "PROP_IMPS"]


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
    band = band_of(z)
    if ceil:
        # dark chitin vault, ribs across it, a thin red glow along each rib
        fz = (z - 0.5) % 1.0
        w = 0.06 * max(1.0, z)
        if fz < w or fz > 1 - w:
            c = CH2
        elif fz < 2 * w or fz > 1 - 2 * w:
            c = CH1
        else:
            c = MEM0 if fz < 2.6 * w or fz > 1 - 2.6 * w else CH0   # red glow along the ribs
        return SHADE[band][c]
    # fleshy floor: irregular bulging plates with dark creases, a wet sheen on each bulge,
    # fixed in world space (the wobble keeps the creases from reading as a tiled grid)
    u = lat * 2.2 + 0.35 * math.sin(z * 2.7)
    v = z * 2.2 + 0.35 * math.sin(lat * 3.1)
    fu, fv = u % 1.0, v % 1.0
    w = 0.07 * max(1.0, z * 0.8)
    n = hash01(math.floor(u), math.floor(v))
    if fu < w or fv < w:
        c = FL0
    elif (fu - 0.45) ** 2 + (fv - 0.55) ** 2 < 0.012 + 0.015 * n:
        c = FL2
    else:
        c = FL1 if n > 0.25 else FL0
    return SHADE[band][c]


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
    save(render(bd, cols, {(1, 0): 2}), os.path.join(outdir, "adjacent_tablet.png"))
    save(render(bd, cols, {(1, 0): 3}), os.path.join(outdir, "adjacent_breach.png"))
    # every prop at distance 1 and 3, for judging the art
    sheet = Image.new("RGB", (VW * 4, VH * ((len(PROPS) + 3) // 4)))
    for i in range(len(PROPS)):
        im = Image.new("RGB", (VW, VH))
        im.putdata([RGB[c] for row in render(bd, cols, room, {(1, 0): i, (3, 1): i}) for c in row])
        sheet.paste(im, ((i % 4) * VW, (i // 4) * VH))
    sheet.save(os.path.join(outdir, "props.png"))
    print(f"previews in {outdir}")


if __name__ == "__main__":
    main()
