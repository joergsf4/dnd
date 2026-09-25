#include "dungeon_view.h"
#include "game.h"
#include "view_gen.h"

// First-person view, Eye of the Beholder / Dungeon Master style.
//
// The player always stands in a cell centre facing a cardinal direction, so the ray through
// each 2-pixel screen column pair crosses a fixed sequence of cells relative to the player.
// tools/make_view.py precomputes that sequence per column (view_gen.h) and, since a given wall
// face at a given screen position always looks the same, bakes every such wall column's pixels
// once per texture (res/view/columns.bin). Rendering is then:
//   1. copy the static floor/ceiling backdrop into a RAM tile buffer (mirrored on alternate
//      steps, the classic trick that makes stepping forward read as movement),
//   2. per column pair, copy the baked bytes of the first wall its ray hits (src/view_draw.s),
//   3. DMA the buffer into the VRAM tile set that isn't on screen, then point BG_B's tilemap at
//      it during vblank (double buffered: no half-drawn frame is ever visible).
// Walls come out pixel-accurate, with real perspective and distance shading, including side
// walls several cells away -- the earlier tile-ring renderer could only say "wall or not" once
// per depth ring and side, which is why open rooms showed walls inconsistently and floor and
// ceiling as flat colour.
//
// Doors and tablets are wall cells and render as that wall's texture. Other objects (pool, corpse, chest,
// shrine, pods) are props: they stand free in the middle of a floor cell, drawn after the walls
// as pre-scaled billboards (one image per distance, like the originals), far to near, and per
// column only where the wall behind is farther away than the prop. Some have an image per
// state (pool burst, chest opened), see objectProp.

#define VIEW_TILE_BASE TILE_USER_INDEX   // two sets of VIEW_TILES tiles; see SPR_initEx in main.c

void viewCopySpan(u8 *dst, const u8 *src, u32 rows, u32 r0);   // src/view_draw.s
void viewMaskSpan(u8 *dst, const u8 *src, u32 rows, u32 r0);   // src/view_draw.s

static u8 viewBuf[VIEW_BYTES] __attribute__((aligned(4)));
static u8 cellTex[VIEW_DMAX + 1][2 * VIEW_LMAX + 1];   // 0 = open, else texture + 1
static u8 cellProp[VIEW_DMAX + 1][2 * VIEW_LMAX + 1];  // 0 = none, else prop + 1
static u8 wallH[VIEW_PAIRS];   // per column pair: rows above the horizon of the wall drawn, 0 = none
static u8 frontSet;
static bool mirror;
static s16 lastX = -1, lastY = -1;
static Facing lastFacing;

static u8 objectTexture(const RoomObject *o)
{
    switch (o->kind)
    {
        case OBJ_DOOR_EXIT: return TEX_DOOR;
        case OBJ_TABLET:    return TEX_TABLET;
        default:            return TEX_WALL;
    }
}

static u8 objectProp(const RoomObject *o)
{
    switch (o->kind)
    {
        case OBJ_LARVA_TANK:         return (o->flags & OBJFLAG_BROKEN) ? PROP_POOL_BROKEN : PROP_POOL;
        case OBJ_MINDFLAYER_CORPSE:  return PROP_CORPSE;
        case OBJ_CARTILAGE_CHEST:    return (o->flags & OBJFLAG_TRIGGERED) ? PROP_CHEST_OPEN : PROP_CHEST;
        case OBJ_RESTORATION_SHRINE: return PROP_SHRINE;
        case OBJ_POD_OPEN:           return PROP_POD_OPEN;
        case OBJ_MYRNATH:            return (o->flags & OBJFLAG_TRIGGERED) ? PROP_MYRNATH_DEAD : PROP_MYRNATH;
        case OBJ_OP_TABLE:           return PROP_OP_TABLE;
        case OBJ_LECTERN:            return PROP_LECTERN;
        default:                     return PROP_POD_BROKEN;
    }
}

// One prop d cells ahead, l to the right. Record layout: see bake_prop in tools/make_view.py.
static void drawProp(u8 prop, s16 d, s16 l)
{
    const u8 *src = viewProps + viewPropOffset[prop][d];
    u8 count = *src++;
    s16 pc = viewPropCenter[d][l + VIEW_LMAX] + (s8) *src++;
    for (u8 k = 0; k < count; k++, pc++)
    {
        u8 top = *src++;
        u8 rows = *src++;
        if (pc >= 0 && pc < VIEW_PAIRS && rows && wallH[pc] * d < VIEW_HALF_K)
        {
            u8 *dst = viewBuf + ((top >> 3) * VIEW_TW + (pc >> 2)) * 32 + (top & 7) * 4 + (pc & 3);
            viewMaskSpan(dst, src, rows, top & 7);
        }
        src += rows * 2;
    }
}

void dungeonView_init(void)
{
    VDP_clearPlane(BG_B, TRUE);
    PAL_setPalette(PAL0, viewPalette, DMA);
    VDP_setBackgroundColor(0);
    frontSet = 0;
    VDP_fillTileMapRectInc(BG_B, TILE_ATTR_FULL(PAL0, FALSE, FALSE, FALSE, VIEW_TILE_BASE), 0, 0, VIEW_TW, VIEW_TH);
}

void dungeonView_render(const Player *p)
{
    if (p->x != lastX || p->y != lastY || p->facing != lastFacing)
    {
        mirror = !mirror;
        lastX = p->x;
        lastY = p->y;
        lastFacing = p->facing;
    }

    s16 fx, fy, rx, ry;
    map_forward(p->facing, &fx, &fy);
    map_right(p->facing, &rx, &ry);
    for (s16 d = 0; d <= VIEW_DMAX; d++)
    {
        for (s16 l = -VIEW_LMAX; l <= VIEW_LMAX; l++)
        {
            s16 cx = p->x + fx * d + rx * l;
            s16 cy = p->y + fy * d + ry * l;
            u8 t = 0, prop = 0;
            RoomObject *o = map_objectAt(cx, cy);
            if (map_isWall(cx, cy))
                t = 1 + (o ? objectTexture(o) : TEX_WALL);
            else if (o)
                prop = 1 + objectProp(o);
            cellTex[d][l + VIEW_LMAX] = t;
            cellProp[d][l + VIEW_LMAX] = prop;
        }
    }

    u8 ahead = cellTex[1][VIEW_LMAX];
    if (ahead)  // a wall right in front covers the whole view: take the pre-rendered image
        memcpy(viewBuf, viewAdjacent + (u32) (ahead - 1) * VIEW_BYTES, VIEW_BYTES);
    else
        memcpy(viewBuf, viewBackdrops + (mirror ? VIEW_BYTES : 0), VIEW_BYTES);

    for (u16 pc = 0; !ahead && pc < VIEW_PAIRS; pc++)
    {
        const ViewEvent *e = &viewEvents[viewColStart[pc]];
        const ViewEvent *end = &viewEvents[viewColStart[pc + 1]];
        wallH[pc] = 0;
        for (; e < end; e++)
        {
            u8 t = cellTex[(u8) e->d][(u8) (e->l + VIEW_LMAX)];
            if (t)
            {
                u8 *dst = viewBuf + ((e->top >> 3) * VIEW_TW + (pc >> 2)) * 32 + (e->top & 7) * 4 + (pc & 3);
                const u8 *src = viewColumns + (u32) (t - 1) * VIEW_TEX_ROWS + e->bake;
                viewCopySpan(dst, src, e->rows, e->top & 7);
                wallH[pc] = VIEW_CY - e->top;
                break;
            }
        }
    }

    // Props: far to near, so nearer ones cover farther ones. Only |l| <= d can be on screen.
    for (s16 d = VIEW_DMAX; !ahead && d >= 1; d--)
    {
        s16 lmax = d < VIEW_LMAX ? d : VIEW_LMAX;
        for (s16 l = -lmax; l <= lmax; l++)
        {
            u8 prop = cellProp[d][l + VIEW_LMAX];
            if (prop)
                drawProp(prop - 1, d, l);
        }
    }

    u8 back = frontSet ^ 1;
    u16 base = VIEW_TILE_BASE + back * VIEW_TILES;
    VDP_loadTileData((const u32 *) viewBuf, base, VIEW_TILES, DMA);
    SYS_doVBlankProcess();
    VDP_fillTileMapRectInc(BG_B, TILE_ATTR_FULL(PAL0, FALSE, FALSE, FALSE, base), 0, 0, VIEW_TW, VIEW_TH);
    frontSet = back;
}
