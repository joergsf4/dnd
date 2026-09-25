#ifndef _UI_PANEL_H_
#define _UI_PANEL_H_

#include <genesis.h>
#include "dungeon_map.h"
#include "party.h"

// The right-hand panel occupies the 12 columns to the right of the 28-tile dungeon view
// (28 + 12 = 40, the full screen width). Every draw call in ui_panel.c stays at x >= UI_PANEL_COL:
// the dungeon view now fills all 28 rows on BG_B, and BG_A composites in front of BG_B, so any
// text left of this column would visibly cut into the view.
#define UI_PANEL_COL 28
#define UI_PANEL_W   12

// Draws the panel chrome once: one 3-row block per party slot (avatar sprite + name/HP for
// active members, "EMPTY" placeholder for slots nobody has joined yet -- see party.h) and a
// placeholder inventory grid below it. Reads the current state of `party`; call after the
// party is set up (party_init() + party_addMember() calls), not before.
void uiPanel_init(void);

// Redraws just the facing/coordinates line; call after each player move/turn.
void uiPanel_drawStatus(const Player *p);

#endif
