#!/usr/bin/env python3
"""Generates the figure sprites: characters and monsters shown in front of the first-person view
during dialogue scenes and combat (hardware sprites, not part of the view's bitmap). All figures
share one palette, since they all use PAL2 (loaded from fig_imp_sprite in src/figures.c):

    res/gfx/fig_imp.png      Niederer Kobold (imp), 32x48, 3 frames of wing beat side by side
    res/gfx/fig_laezel.png   Lae'zel, 48x96
    res/gfx/fig_arrow.png    8x8 target marker for combat menus

Sizes are what's shown on screen: a figure one cell ahead is about as tall as the wall there
(112 px), so a human is ~96 px, an imp (small, hovering) 48 px. Indexed PNGs, index 0 is
transparent on the hardware.
"""
import math
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "res", "gfx")

PALETTE = [
    (0xFF, 0x00, 0xFF),   # 0 transparent
    (0x10, 0x0C, 0x10),   # 1 OUTLINE
    (0xD0, 0x30, 0x28),   # 2 RED (imp skin)
    (0x80, 0x18, 0x18),   # 3 RED_D
    (0x48, 0x2C, 0x24),   # 4 WING (dark leathery brown)
    (0xF0, 0xD0, 0x40),   # 5 YELLOW (eyes)
    (0x90, 0x98, 0xA8),   # 6 STEEL
    (0xD8, 0xE0, 0xE8),   # 7 STEEL_L
    (0xB8, 0xC8, 0x70),   # 8 GITH (Lae'zel's yellow-green skin)
    (0x78, 0x90, 0x48),   # 9 GITH_D
    (0xB8, 0x88, 0x40),   # 10 BRONZE
    (0x70, 0x50, 0x28),   # 11 BRONZE_D
    (0x98, 0x38, 0x28),   # 12 RUST (leather)
    (0x50, 0x38, 0x28),   # 13 HAIR
    (0x2C, 0x24, 0x20),   # 14 BOOT
    (0xF8, 0xF8, 0xF0),   # 15 WHITE
]
(TR, OUTLINE, RED, RED_D, WING, YELLOW, STEEL, STEEL_L, GITH, GITH_D, BRONZE, BRONZE_D, RUST,
 HAIR, BOOT, WHITE) = range(16)


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = [[TR] * w for _ in range(h)]

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = c

    def rect(self, x0, y0, x1, y1, c):
        for y in range(y0, y1):
            for x in range(x0, x1):
                self.set(x, y, c)

    def ellipse(self, cx, cy, rx, ry, c):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1:
                    self.set(x, y, c)

    def poly(self, pts, c):
        """Filled polygon (even-odd scanline)."""
        for y in range(self.h):
            xs = []
            for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
                if (y0 <= y + 0.5 < y1) or (y1 <= y + 0.5 < y0):
                    xs.append(x0 + (y + 0.5 - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for a, b in zip(xs[::2], xs[1::2]):
                for x in range(int(round(a)), int(round(b))):
                    self.set(x, y, c)

    def outline(self):
        """Dark outline around every opaque shape, so figures read against the busy view."""
        src = [row[:] for row in self.px]
        for y in range(self.h):
            for x in range(self.w):
                if src[y][x] != TR:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < self.w and 0 <= yy < self.h and src[yy][xx] not in (TR, OUTLINE):
                        self.px[y][x] = OUTLINE
                        break


def save(frames, name):
    w, h = frames[0].w, frames[0].h
    img = Image.new("P", (w * len(frames), h), 0)
    img.putpalette([v for c in PALETTE for v in c] + [0] * (768 - 48))
    for i, f in enumerate(frames):
        for y in range(h):
            for x in range(w):
                img.putpixel((i * w + x, y), f.px[y][x])
    path = os.path.join(OUT, name)
    img.save(path)
    print("wrote", os.path.normpath(path), img.size)


def imp(frame):
    """Tiny crimson devil: goat horns, bat wings (3-frame beat), thin arrow tail, iron trident."""
    c = Canvas(32, 48)
    wing_y = (0, 6, 12)[frame]                            # wing tips: up, level, down
    for side in (-1, 1):
        root = (16 + side * 4, 20)
        tip = (16 + side * 15, 8 + wing_y)
        low = (16 + side * 12, 24 + wing_y // 2)
        c.poly([root, tip, low], WING)
        c.set(tip[0], tip[1], RED_D)
    for i in range(16):                                   # tail, curling behind
        x = 16 + int(6 * math.sin(i / 3.0))
        c.set(x, 30 + i, RED_D)
    c.poly([(14, 45), (19, 45), (16, 41)], RED_D)         # arrow tip of the tail
    c.ellipse(16, 27, 6, 7, RED)                          # body
    c.ellipse(14, 25, 2, 3, (RED))
    c.rect(12, 32, 15, 38, RED_D)                         # legs
    c.rect(18, 32, 21, 38, RED_D)
    c.ellipse(16, 15, 6, 6, RED)                          # head
    c.ellipse(14, 13, 2, 2, RED)
    c.poly([(11, 11), (9, 4), (13, 9)], BRONZE_D)         # goat horns
    c.poly([(21, 11), (23, 4), (19, 9)], BRONZE_D)
    c.set(13, 15, YELLOW)                                 # eyes
    c.set(18, 15, YELLOW)
    c.rect(14, 18, 19, 19, RED_D)                         # grin
    c.rect(26, 6, 27, 40, STEEL)                          # trident shaft
    for x in (24, 26, 28):
        c.rect(x, 3, x + 1, 8, STEEL_L)
    c.rect(24, 7, 29, 8, STEEL)
    c.rect(21, 24, 26, 26, RED)                           # arm holding it
    c.outline()
    return c


def laezel():
    """Lae'zel: yellow-green githyanki, braided dark hair, bronze half-plate with sharp pauldrons,
    rust-red leather, greatsword held diagonally."""
    c = Canvas(48, 96)
    c.rect(19, 62, 23, 90, RUST)                          # legs in leather
    c.rect(26, 62, 30, 90, RUST)
    c.rect(18, 86, 24, 95, BOOT)                          # iron-shod boots
    c.rect(25, 86, 31, 95, BOOT)
    c.rect(18, 90, 24, 91, STEEL)
    c.rect(25, 90, 31, 91, STEEL)
    c.poly([(15, 34), (33, 34), (31, 64), (17, 64)], BRONZE)   # breastplate
    c.rect(24, 36, 25, 62, BRONZE_D)
    c.rect(17, 50, 31, 53, RUST)                          # belt
    c.poly([(16, 56), (32, 56), (34, 68), (14, 68)], RUST)     # tassets
    for x in (17, 22, 27, 32):
        c.rect(x, 58, x + 1, 68, BRONZE_D)
    c.poly([(6, 38), (16, 30), (19, 36), (12, 44)], BRONZE)    # sharp pauldrons
    c.poly([(42, 38), (32, 30), (29, 36), (36, 44)], BRONZE)
    c.set(6, 38, BRONZE_D)
    c.set(42, 38, BRONZE_D)
    c.rect(10, 42, 14, 60, RUST)                          # arms
    c.rect(34, 42, 38, 60, RUST)
    c.rect(10, 58, 15, 63, GITH)                          # hands
    c.rect(33, 58, 38, 63, GITH)
    c.rect(21, 27, 27, 33, GITH_D)                        # neck
    c.ellipse(24, 20, 7, 9, GITH)                         # head
    c.poly([(16, 17), (11, 13), (17, 21)], GITH)          # pointed ears
    c.poly([(32, 17), (37, 13), (31, 21)], GITH)
    c.poly([(17, 15), (24, 9), (31, 15), (31, 12), (24, 10), (17, 12)], HAIR)
    c.ellipse(24, 12, 7, 4, HAIR)                         # hair pulled back tight
    for y in range(12, 44, 3):                            # braid down the back, metal bands
        c.rect(30, y, 33, y + 2, HAIR)
        c.rect(30, y + 2, 33, y + 3, STEEL)
    c.rect(20, 19, 23, 21, OUTLINE)                       # almond eyes
    c.rect(26, 19, 29, 21, OUTLINE)
    c.set(23, 24, GITH_D)                                 # nostrils, no nose ridge
    c.set(25, 24, GITH_D)
    c.rect(22, 27, 27, 28, GITH_D)                        # stern mouth
    for i in range(46):                                   # greatsword, held diagonally
        x, y = 12 + i * 0.62, 62 - i * 1.25
        c.rect(int(x), int(y), int(x) + 2, int(y) + 1, STEEL_L if i > 8 else STEEL)
    c.rect(9, 60, 18, 62, BRONZE_D)                       # crossguard
    c.rect(9, 62, 13, 66, RUST)                           # leather grip
    c.outline()
    return c


def arrow():
    c = Canvas(8, 8)
    c.poly([(0, 1), (8, 1), (4, 7)], YELLOW)
    c.rect(0, 0, 8, 1, OUTLINE)
    return c


if __name__ == "__main__":
    save([imp(0), imp(1), imp(2)], "fig_imp.png")
    save([laezel()], "fig_laezel.png")
    save([arrow()], "fig_arrow.png")
