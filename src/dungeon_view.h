#ifndef _DUNGEON_VIEW_H_
#define _DUNGEON_VIEW_H_

#include <genesis.h>
#include "dungeon_map.h"

// Sets up the BG_B tileset/palette for the dungeon view. Call once before the first render.
void dungeonView_init(void);

// Redraws the first-person view for the player's current position/facing onto BG_B.
// Only needs to run after the player moves or turns, not every frame.
void dungeonView_render(const Player *p);

#endif
