#include "ui_panel.h"

static const char facingLetter[4] = { 'N', 'E', 'S', 'W' };

// Placeholder party roster: name + a stat line, both within the 12-column budget.
// No character data model yet -- these are literal strings, not struct data (see TODO.md).
static const char *const partyName[4] = { "1 FIGHTER", "2 CLERIC", "3 WIZARD", "4 ROGUE" };
static const char *const partyStat[4] = { " HP 20/20", " HP 18/18", " MP 12/12", " HP 16/16" };

void uiPanel_init(void)
{
    for (u8 i = 0; i < 4; i++)
    {
        VDP_drawText(partyName[i], UI_PANEL_COL, i * 2);
        VDP_drawText(partyStat[i], UI_PANEL_COL, i * 2 + 1);
    }

    VDP_drawText("ITEMS", UI_PANEL_COL, 9);
    VDP_drawText("[][][][]", UI_PANEL_COL + 2, 10);
    VDP_drawText("[][][][]", UI_PANEL_COL + 2, 11);

    VDP_drawText("UP/DN WALK", UI_PANEL_COL, 13);
    VDP_drawText("L/R TURN", UI_PANEL_COL, 14);
}

void uiPanel_drawStatus(const Player *p)
{
    char text[UI_PANEL_W + 1];
    sprintf(text, "%c (%02d,%02d)", facingLetter[p->facing], p->x, p->y);
    VDP_drawText(text, UI_PANEL_COL, 27);
}
