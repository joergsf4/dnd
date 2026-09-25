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
    { 11, 11, 6, 6 },
    { 13, 13, 2, 2 },
};

static u16 tileAt(u8 slot)
{
    return TILE_ATTR_FULL(PAL0, FALSE, FALSE, FALSE, TILE_USER_INDEX + slot);
}

static void fillArea(u16 x0, u16 y0, u16 x1, u16 y1, u16 attr)
{
    for (u16 y = y0; y < y1; y++)
        for (u16 x = x0; x < x1; x++)
            VDP_setTileMapXY(BG_B, attr, x, y);
}

static void fillRect(Rect r, u16 attr)
{
    fillArea(r.x, r.y, r.x + r.w, r.y + r.h, attr);
}

// Draws the left or right side of ring `depth` between the outer rect and the next-inner rect:
// solid wall brick if that side is blocked, otherwise ceiling above / floor below (open passage).
static void drawSide(Rect outer, Rect inner, bool onLeft, bool wall, u8 depth)
{
    u16 x0 = onLeft ? outer.x : inner.x + inner.w;
    u16 x1 = onLeft ? inner.x : outer.x + outer.w;
    if (wall)
    {
        fillArea(x0, inner.y, x1, inner.y + inner.h, tileAt(T_WALL(depth)));
        return;
    }
    u16 mid = inner.y + inner.h / 2;
    fillArea(x0, inner.y, x1, mid, tileAt(T_CEIL(depth)));
    fillArea(x0, mid, x1, inner.y + inner.h, tileAt(T_FLOOR(depth)));
}

void dungeonView_init(void)
{
    VDP_loadTileSet(&dungeon_tiles, TILE_USER_INDEX, DMA);
    PAL_setPalette(PAL0, dungeon_pal.data, DMA);
    VDP_setBackgroundColor(0);
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
        Rect outer = rects[r];
        Rect inner = rects[r + 1];

        if (r == renderDepth)
        {
            fillRect(outer, tileAt(T_FRONT(r)));
            return;
        }

        fillArea(outer.x, outer.y, outer.x + outer.w, inner.y, tileAt(T_CEIL(r)));                         // top band
        fillArea(outer.x, inner.y + inner.h, outer.x + outer.w, outer.y + outer.h, tileAt(T_FLOOR(r)));    // bottom band

        s16 ax = p->x + dx * (r + 1);
        s16 ay = p->y + dy * (r + 1);
        bool leftWall = map_isWall(ax + lx, ay + ly);
        bool rightWall = map_isWall(ax + rx, ay + ry);
        drawSide(outer, inner, TRUE, leftWall, r);
        drawSide(outer, inner, FALSE, rightWall, r);
    }

    fillRect(rects[3], tileAt(T_MIST));
}
