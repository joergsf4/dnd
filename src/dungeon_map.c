#include "dungeon_map.h"

static const RoomDef *currentRoom;
static RoomObject roomState[ROOM_COUNT][ROOM_MAX_OBJECTS];
static bool roomVisited[ROOM_COUNT];
static const RoomDef *roomTable[ROOM_COUNT];

void map_registerRoom(const RoomDef *room)
{
    roomTable[room->roomId] = room;
}

const RoomDef *map_findRoom(RoomId id)
{
    return roomTable[id];
}

void map_loadRoom(const RoomDef *room, Player *p)
{
    currentRoom = room;

    if (!roomVisited[room->roomId])
    {
        for (u8 i = 0; i < room->objectCount; i++)
            roomState[room->roomId][i] = room->objects[i];
        roomVisited[room->roomId] = TRUE;
    }

    p->x = room->startX;
    p->y = room->startY;
    p->facing = room->startFacing;

    if (room->onEnter) room->onEnter(p);
}

const RoomDef *map_currentRoom(void)
{
    return currentRoom;
}

RoomObject *map_objectAt(s16 x, s16 y)
{
    if (!currentRoom) return NULL;

    RoomObject *objects = roomState[currentRoom->roomId];
    for (u8 i = 0; i < currentRoom->objectCount; i++)
        if (objects[i].kind != OBJ_NONE && objects[i].x == x && objects[i].y == y)
            return &objects[i];
    return NULL;
}

bool map_isWall(s16 x, s16 y)
{
    if (!currentRoom || x < 0 || y < 0 || x >= currentRoom->w || y >= currentRoom->h) return TRUE;
    return currentRoom->grid[y][x] == '1';
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
