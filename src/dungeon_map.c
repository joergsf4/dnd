#include "dungeon_map.h"

// test dungeon: 1 = wall, 0 = floor. Placeholder for the real level data format.
static const char *const grid[MAP_H] = {
    "11111111111111",
    "10000000000001",
    "10010000010001",
    "10010010010001",
    "10010010010001",
    "10010010000001",
    "10000010000001",
    "10000111000001",
    "10000000000001",
    "11111111111111",
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
