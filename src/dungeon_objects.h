#ifndef _DUNGEON_OBJECTS_H_
#define _DUNGEON_OBJECTS_H_

#include "dungeon_map.h"

// Loads the object-icon spritesheet's palette (PAL2). Call once before the first render.
void dungeonObjects_init(void);

// The object directly ahead of the player (one step, in the facing direction), or NULL.
// Interactive objects always sit on a wall cell, so this is always the one currently rendered
// as the front (dead-end) wall texture at ring 0 -- see dungeon_view.c's renderDepth logic.
RoomObject *dungeonObjects_interactTarget(const Player *p);

// Shows/hides/repositions the one shared object sprite for whatever's (not) directly ahead.
// Call this alongside dungeonView_render after every move/turn and after every interaction.
void dungeonObjects_render(const Player *p);

// Shared handler for OBJ_DOOR_EXIT objects (param0 = target RoomId): transitions to the target
// room if it's been registered (map_registerRoom), otherwise shows a "still sealed" stub -- every
// room's exit door needs this same not-built-yet check before it's actually wired up.
void dungeonObjects_tryDoor(Player *p, RoomObject *obj);

#endif
