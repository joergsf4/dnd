#ifndef _DUNGEON_MAP_H_
#define _DUNGEON_MAP_H_

#include <genesis.h>

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

// Every room in the vertical slice, in map-flow order (see BeschreibungInhaltVerticalSlice.md).
// Rooms without a RoomDef yet are still listed so door objects can already target them (a door
// to an unbuilt room stays shut) -- adding one is a matter of writing src/roomN.c, registering
// it in main.c and pointing a door's param0 at it, no struct/array resize needed.
typedef enum
{
    ROOM_1 = 0,
    ROOM_2,
    ROOM_3,
    ROOM_4,
    ROOM_5,
    ROOM_6,
    ROOM_COUNT
} RoomId;

#define ROOM_MAX_OBJECTS 12
#define OBJFLAG_TRIGGERED 0x01 // a one-shot object has fired (loot taken, chest opened)
#define OBJFLAG_BROKEN    0x02 // destroyed for good (the larva pool after it burst)
#define OBJFLAG_MARKED    0x04 // a skill check revealed it (the larva pool's unstable shell)

typedef enum
{
    OBJ_NONE = 0,
    OBJ_LARVA_TANK,
    OBJ_MINDFLAYER_CORPSE,
    OBJ_CARTILAGE_CHEST,
    OBJ_RESTORATION_SHRINE,
    OBJ_DOOR_EXIT,
    OBJ_POD_OPEN,          // the player's own clone pod, open and empty
    OBJ_POD_BROKEN,        // a shattered clone pod (scenery, flavour text only)
    OBJ_MYRNATH,           // Room 2: the elf on the operating couch, "Wir" in his skull
    OBJ_OP_TABLE,          // Room 2: vivisection table (scenery; param0 picks the text)
    OBJ_LECTERN,           // Room 2: lectern grown from the floor, notes on it (lore)
    OBJ_TABLET,            // Room 2: cartilage tablet on a wall (lore; param0 picks the text)
    OBJ_KIND_COUNT
} ObjectKind;

typedef struct
{
    s8 x, y;
    ObjectKind kind;
    u8 param0, param1; // kind-specific payload, e.g. OBJ_DOOR_EXIT: param0 = target RoomId
                       // (the target room needs a door back to this room; see map_enterRoom)
    u8 flags;
} RoomObject;

typedef void (*RoomInteractFn)(Player *p, RoomObject *obj);
// Called by main.c each time the player arrives in the room, once its first view is on screen
// (so a textbox shows over the room, not a blank view). May be NULL.
typedef void (*RoomEnterFn)(Player *p);

typedef struct
{
    RoomId roomId;
    u8 w, h;
    const char *const *grid;    // h strings of w chars, '1' = wall, '0' = floor
    s8 startX, startY;
    Facing startFacing;
    u8 objectCount;
    const RoomObject *objects;  // ROM template, copied to RAM state on first visit
    RoomInteractFn onInteract;
    RoomEnterFn onEnter;
} RoomDef;

// Enters a room: sets the player's position/facing from the RoomDef, and -- only on the very
// first visit -- copies its object template into per-room RAM state (so objects can be looted/
// flagged and, if the player ever backtracks, stay that way). Does not run onEnter (see above).
void map_loadRoom(const RoomDef *room, Player *p);
const RoomDef *map_currentRoom(void);

// Enters a room through a door: like map_loadRoom, but the player stands in front of the target
// room's door that leads back to `from`, facing into the room. Falls back to the room's start if
// it has no such door.
void map_enterRoom(const RoomDef *room, Player *p, RoomId from);

// A tiny room registry so a door object can check whether its target room is actually built yet
// (see dungeonObjects_tryDoor) without dungeon_map.c hardcoding a dependency on specific room
// content files -- main.c registers each room it knows about at boot.
void map_registerRoom(const RoomDef *room);
const RoomDef *map_findRoom(RoomId id); // NULL if that room hasn't been registered yet

// NULL if there's no object at (x,y) in the current room.
RoomObject *map_objectAt(s16 x, s16 y);

bool map_isWall(s16 x, s16 y);
void map_forward(Facing f, s16 *dx, s16 *dy);
void map_left(Facing f, s16 *dx, s16 *dy);
void map_right(Facing f, s16 *dx, s16 *dy);

// attempts to step the player one cell forward (sign<0 for backward); no-op if blocked
void player_step(Player *p, s16 sign);
void player_turn(Player *p, s16 sign); // sign +1 = turn right (CW), -1 = turn left (CCW)

#endif
