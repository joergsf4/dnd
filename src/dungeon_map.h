#ifndef _DUNGEON_MAP_H_
#define _DUNGEON_MAP_H_

#include <genesis.h>

#define MAP_W 14
#define MAP_H 10

// facing: 0=North 1=East 2=South 3=West (rotates clockwise)
typedef enum
{
    FACE_NORTH = 0,
    FACE_EAST  = 1,
    FACE_SOUTH = 2,
    FACE_WEST  = 3
} Facing;

typedef struct
{
    s16 x, y;
    Facing facing;
} Player;

bool map_isWall(s16 x, s16 y);
void map_forward(Facing f, s16 *dx, s16 *dy);
void map_left(Facing f, s16 *dx, s16 *dy);
void map_right(Facing f, s16 *dx, s16 *dy);

// attempts to step the player one cell forward (sign<0 for backward); no-op if blocked
void player_step(Player *p, s16 sign);
void player_turn(Player *p, s16 sign); // sign +1 = turn right (CW), -1 = turn left (CCW)

#endif
