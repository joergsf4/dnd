#include "dungeon_map.h"

// POC dungeon: a 1-cell-wide, 4-cell-long corridor opening into a 6x6 room.
// 1 = wall, 0 = floor. Placeholder for the real level data format.
static const char *const grid[MAP_H] = {
    "11111111",   // y=0  room north wall
    "10000001",   // y=1  room interior (x=1..6) starts here, 6x6
    "10000001",   // y=2
    "10000001",   // y=3
    "10000001",   // y=4
    "10000001",   // y=5
    "10000001",   // y=6
    "11110111",   // y=7  room south wall, doorway at x=4 = corridor cell 1
    "11110111",   // y=8  corridor cell 2
    "11110111",   // y=9  corridor cell 3
    "11110111",   // y=10 corridor cell 4 = player start (x=4,y=10), facing north
    "11111111",   // y=11 south wall (dead end behind the player)
};

bool map_isWall(s16 x, s16 y)
{
    if (x < 0 || y < 0 || x >= MAP_W || y >= MAP_H) return TRUE;
    return grid[y][x] == '1';
}

void map_forward(Facing f, s16 *dx, s16 *dy)
{
    switch (f)
    {
        case FACE_NORTH: *dx = 0;  *dy = -1; break;
        case FACE_EAST:  *dx = 1;  *dy = 0;  break;
        case FACE_SOUTH: *dx = 0;  *dy = 1;  break;
        default:         *dx = -1; *dy = 0;  break; // FACE_WEST
    }
}

void map_left(Facing f, s16 *dx, s16 *dy)
{
    s16 fx, fy;
    map_forward(f, &fx, &fy);
    *dx = fy;
    *dy = -fx;
}

void map_right(Facing f, s16 *dx, s16 *dy)
{
    s16 fx, fy;
    map_forward(f, &fx, &fy);
    *dx = -fy;
    *dy = fx;
}

void player_step(Player *p, s16 sign)
{
    s16 dx, dy;
    map_forward(p->facing, &dx, &dy);
    s16 nx = p->x + dx * sign;
    s16 ny = p->y + dy * sign;
    if (!map_isWall(nx, ny))
    {
        p->x = nx;
        p->y = ny;
    }
}

void player_turn(Player *p, s16 sign)
{
    p->facing = (Facing) (((s16) p->facing + sign + 4) & 3);
}
