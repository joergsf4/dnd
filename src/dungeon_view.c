#include "dungeon_view.h"
#include "game.h"

// Tile slots inside res/gfx/dungeon_tiles.png (see tools/make_dungeon_tiles.py for the layout).
#define T_CEIL(d)   (0 + (d))
#define T_FLOOR(d)  (3 + (d))
#define T_WALL(d)   (6 + (d))
#define T_FRONT(d)  (9 + (d))
#define T_MIST      12

typedef struct { u8 x, y, w, h; } Rect;

// Concentric rectangles (in BG_B tiles) the corridor view is built from: rects[0] is the
// full 28x28 viewport (the left 28 of the screen's 40 tile columns; the right 12 columns
// are the UI panel, see ui_panel.h), rects[1..2] the mid/far apertures, rects[3] the
// vanishing-point cap. Square viewport -> the mid rect ends up taller than wide, which is
// the correct consequence of that (not a mistake to "fix" back to landscape).
static const Rect rects[4] = {
    { 0, 0, 28, 28 },
    { 7, 6, 14, 16 },
    { 12, 10, 4, 8 },
    { 13, 12, 2, 4 },
};

static u16 tileAt(u8 slot, bool hflip)
{
    return TILE_ATTR_FULL(PAL0, FALSE, FALSE, hflip, TILE_USER_INDEX + slot);
}

static void fillRect(Rect r, u16 attr)
{
    for (s16 y = r.y; y < r.y + r.h; y++)
        for (s16 x = r.x; x < r.x + r.w; x++)
            VDP_setTileMapXY(BG_B, attr, x, y);
}

// Fills the ring between outer and inner (inner must be centered inside outer) so it reads as a
// tunnel: every tile is classified, picture-frame-style, into the left/right wall band or the
// ceiling/floor band by comparing how far off-centre it is horizontally vs. vertically -- the
// two mitred diagonals this draws are what actually bounds the tunnel left/right and tapers it
// into the distance, instead of a flat rectangle that just floats in front of the next ring in.
// (An earlier version filled the wall and ceiling/floor trapezoids separately, column-wise and
// row-wise; independent integer rounding left 1-tile gaps at the seam between them, confirmed by
// screenshot -- see tools/emutest.py. This single per-tile classification can't gap: every tile
// in the ring gets exactly one band.)
static void renderRing(Rect outer, Rect inner, u8 depth, bool leftWall, bool rightWall)
{
    s16 cx2 = outer.x * 2 + outer.w;   // 2x the ring's centre, so the per-tile midpoint stays integer
    s16 cy2 = outer.y * 2 + outer.h;
    u16 ceilAttr = tileAt(T_CEIL(depth), FALSE);
    u16 floorAttr = tileAt(T_FLOOR(depth), FALSE);
    u16 wallAttr[2] = { tileAt(T_WALL(depth), FALSE), tileAt(T_WALL(depth), TRUE) }; // [onLeft]

    for (s16 y = outer.y; y < outer.y + outer.h; y++)
    {
        for (s16 x = outer.x; x < outer.x + outer.w; x++)
        {
            if (x >= inner.x && x < inner.x + inner.w && y >= inner.y && y < inner.y + inner.h)
                continue; // inside the inner rect: the next ring (or the cap) owns this tile

            s16 dx2 = x * 2 + 1 - cx2; // 2x the offset from centre to this tile's midpoint
            s16 dy2 = y * 2 + 1 - cy2;
            s16 adx = dx2 < 0 ? -dx2 : dx2;
            s16 ady = dy2 < 0 ? -dy2 : dy2;
            bool inSideBand = (s32) adx * outer.h >= (s32) ady * outer.w;

            u16 attr;
            if (inSideBand)
            {
                bool onLeft = dx2 < 0;
                bool wall = onLeft ? leftWall : rightWall;
                attr = wall ? wallAttr[onLeft] : (dy2 < 0 ? ceilAttr : floorAttr);
            }
            else
            {
                attr = dy2 < 0 ? ceilAttr : floorAttr;
            }
            VDP_setTileMapXY(BG_B, attr, x, y);
        }
    }
}

void dungeonView_init(void)
{
    VDP_loadTileSet(&dungeon_tiles, TILE_USER_INDEX, DMA);
    PAL_setPalette(PAL0, dungeon_pal.data, DMA);
    VDP_setBackgroundColor(0);

    // SGDK's default font renders with PAL0, indices 14/15 -- dungeon_pal only defines 14
    // colors, so rescomp pads the rest with black, which made every VDP_drawText call
    // invisible wherever BG_B has no content underneath it (i.e. the whole UI panel, columns
    // 28+): black text on the black backdrop. Not a rendering bug, just missing contrast --
    // took a long empirical bisection (removing dungeonView_init() entirely made text at
    // column 30 render fine again) to trace it back to these two unset palette entries.
    PAL_setColor((16 * PAL0) + 14, RGB24_TO_VDPCOLOR(0xFFFFFF));
    PAL_setColor((16 * PAL0) + 15, RGB24_TO_VDPCOLOR(0xFFFFFF));
}

void dungeonView_render(const Player *p)
{
    s16 dx, dy, lx, ly, rx, ry;
    map_forward(p->facing, &dx, &dy);
    map_left(p->facing, &lx, &ly);
    map_right(p->facing, &rx, &ry);

    u8 renderDepth = 3; // 3 = open through all rendered rings, cap it with the vanishing mist
    for (u8 d = 0; d < 3; d++)
    {
        if (map_isWall(p->x + dx * (d + 1), p->y + dy * (d + 1)))
        {
            renderDepth = d;
            break;
        }
    }

    for (u8 r = 0; r < 3; r++)
    {
        if (r == renderDepth)
        {
            fillRect(rects[r], tileAt(T_FRONT(r), FALSE));
            return;
        }

        s16 ax = p->x + dx * (r + 1);
        s16 ay = p->y + dy * (r + 1);
        bool leftWall = map_isWall(ax + lx, ay + ly);
        bool rightWall = map_isWall(ax + rx, ay + ry);
        renderRing(rects[r], rects[r + 1], r, leftWall, rightWall);
    }

    fillRect(rects[3], tileAt(T_MIST, FALSE));
}

void dungeonView_getObjectAnchor(s16 *px, s16 *py, s16 *pw, s16 *ph)
{
    *px = rects[1].x * 8;
    *py = rects[1].y * 8;
    *pw = rects[1].w * 8;
    *ph = rects[1].h * 8;
}
