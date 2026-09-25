#ifndef _FIGURES_H_
#define _FIGURES_H_

#include <genesis.h>

// Figures: characters and monsters shown in front of the first-person view during dialogue
// scenes and combat, as hardware sprites on PAL2 (tools/make_figures.py). Unlike props they're
// never occluded or scaled -- they only ever stand right in front of the player.

// Loads the shared figure palette into PAL2. Call once at boot.
void figures_init(void);

// Adds a figure centred at screen x `cx` with its feet at screen y `bottom` (view coordinates).
Sprite *figures_add(const SpriteDefinition *def, s16 cx, s16 bottom);

// Blinks a figure `times` times (a hit), blocking.
void figures_blink(Sprite *s, u8 times);

// Shakes the view horizontally for a moment (the party takes a hit, something lands), blocking.
void figures_shakeView(void);

// Waits n frames, keeping sprites (animations) updated.
void figures_wait(u16 n);

#endif
