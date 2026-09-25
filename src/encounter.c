#include "encounter.h"
#include "dungeon_view.h"
#include "ui_panel.h"

typedef struct
{
    u8 count;
    const EnemyDef *enemies[COMBAT_MAX_ENEMIES];
    u8 gold;
} Encounter;

static const Encounter encounters[] = {
    [ENC_IMPS3] = { 3, { &ENEMY_IMP, &ENEMY_IMP, &ENEMY_IMP }, 6 },
    [ENC_IMPS2] = { 2, { &ENEMY_IMP, &ENEMY_IMP }, 4 },
};

#define CHASE_RANGE 6   // cells (not diagonal); groups farther away stay put
#define TANK_RANGE  3

static s16 dist(s16 x0, s16 y0, s16 x1, s16 y1)
{
    return abs(x1 - x0) + abs(y1 - y0);
}

static bool isEnemy(const RoomObject *o)
{
    return o->kind == OBJ_ENEMY_GROUP && !(o->flags & OBJFLAG_HIDDEN);
}

static bool tryStep(RoomObject *o, const Player *p, s16 dx, s16 dy)
{
    if (!dx && !dy) return FALSE;
    s16 x = o->x + dx, y = o->y + dy;
    if (map_isWall(x, y) || map_objectAt(x, y) || (x == p->x && y == p->y)) return FALSE;
    o->x = x;
    o->y = y;
    return TRUE;
}

bool encounter_tick(const Player *p)
{
    u8 count;
    RoomObject *objects = map_roomObjects(&count);
    bool moved = FALSE;
    for (u8 i = 0; i < count; i++)
    {
        RoomObject *o = &objects[i];
        if (!isEnemy(o)) continue;
        s16 d = dist(o->x, o->y, p->x, p->y);
        if (d <= 1 || d > CHASE_RANGE) continue;

        // Close in along the longer axis first, the other one if that's blocked.
        s16 dx = p->x - o->x, dy = p->y - o->y;
        s16 sx = dx > 0 ? 1 : dx < 0 ? -1 : 0;
        s16 sy = dy > 0 ? 1 : dy < 0 ? -1 : 0;
        if (abs(dx) >= abs(dy))
            moved |= tryStep(o, p, sx, 0) || tryStep(o, p, 0, sy);
        else
            moved |= tryStep(o, p, 0, sy) || tryStep(o, p, sx, 0);
    }
    return moved;
}

RoomObject *encounter_adjacent(const Player *p)
{
    u8 count;
    RoomObject *objects = map_roomObjects(&count);
    for (u8 i = 0; i < count; i++)
        if (isEnemy(&objects[i]) && dist(objects[i].x, objects[i].y, p->x, p->y) == 1)
            return &objects[i];
    return NULL;
}

void encounter_fight(Player *p, RoomObject *group)
{
    for (u8 f = 0; f < 4; f++)
    {
        s16 dx, dy;
        map_forward((Facing) f, &dx, &dy);
        if (p->x + dx == group->x && p->y + dy == group->y) p->facing = (Facing) f;
    }

    // The group's prop gives way to its figures for the fight.
    group->flags |= OBJFLAG_HIDDEN;
    dungeonView_render(p);
    uiPanel_drawStatus(p);

    u8 count;
    RoomObject *objects = map_roomObjects(&count);
    RoomObject *tank = NULL;
    for (u8 i = 0; i < count; i++)
        if (objects[i].kind == OBJ_ACID_TANK && !(objects[i].flags & OBJFLAG_BROKEN)
            && dist(objects[i].x, objects[i].y, p->x, p->y) <= TANK_RANGE)
            tank = &objects[i];

    const Encounter *e = &encounters[group->param0];
    combat_run(p, e->enemies, e->count, tank, e->gold);
    group->kind = OBJ_NONE;
}
