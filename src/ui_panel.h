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

// Adds each active party member's avatar sprite. Call exactly once, after the party is set up --
// calling it again would duplicate the sprites. Split out from the text chrome specifically so
// a textbox interaction can refresh the text (HP changed, an item was found, ...) without
// re-adding sprites; see uiPanel_redrawChrome.
void uiPanel_initSprites(void);

// (Re)draws all the panel's text: party name/HP/MP per slot ("---EMPTY---" for unjoined slots),
// the item block (via uiPanel_drawInventory), and the control hints. Safe to call as often as
// needed -- call it after every textbox interaction closes, since a textbox may have covered the
// panel's status row (see textbox.h).
void uiPanel_redrawChrome(void);

// Redraws just the ITEMS block from the live `inventory` global. Also called by
// uiPanel_redrawChrome; exposed separately so a loot pickup can refresh just this part.
void uiPanel_drawInventory(void);

// Redraws just the facing/coordinates line; call after each player move/turn.
void uiPanel_drawStatus(const Player *p);

#endif
