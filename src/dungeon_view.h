#ifndef _DUNGEON_VIEW_H_
#define _DUNGEON_VIEW_H_

#include <genesis.h>
#include "dungeon_map.h"

// Sets up the BG_B tileset/palette for the dungeon view. Call once before the first render.
void dungeonView_init(void);

// Redraws the first-person view for the player's current position/facing onto BG_B.
// Only needs to run after the player moves or turns, not every frame.
void dungeonView_render(const Player *p);

// Pixel rect (rects[1], the near ring's inner aperture) that a wall-mounted object sprite
// should be centered in -- exact centering/sizing is tuned visually (tools/emutest.py), this
// just spares dungeon_objects.c from duplicating the rects[] geometry.
void dungeonView_getObjectAnchor(s16 *px, s16 *py, s16 *pw, s16 *ph);

#endif
