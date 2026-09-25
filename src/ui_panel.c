#include "ui_panel.h"
#include "game.h"

static const char facingLetter[4] = { 'N', 'E', 'S', 'W' };

#define SLOT_ROWS 3                    // avatar height in tiles == rows per party slot
#define TEXT_COL  (UI_PANEL_COL + 3)   // right of the 3-tile-wide avatar

static void drawSlot(u8 i)
{
    u16 row = i * SLOT_ROWS;
    const Character *c = &party.members[i];

    if (!c->active)
    {
        VDP_drawText("---EMPTY---", UI_PANEL_COL, row);
        VDP_drawText("           ", UI_PANEL_COL, row + 1);
        return;
    }

    SPR_addSprite(&avatar_sprite, UI_PANEL_COL * 8, row * 8, TILE_ATTR(PAL1, FALSE, FALSE, FALSE));

    char text[16];
    sprintf(text, "%s", c->name);
    VDP_drawText(text, TEXT_COL, row);
    if (c->mpMax > 0)
        sprintf(text, "MP%2d/%2d", c->mp, c->mpMax);
    else
        sprintf(text, "HP%2d/%2d", c->hp, c->hpMax);
    VDP_drawText(text, TEXT_COL, row + 1);
}

void uiPanel_init(void)
{
    for (u8 i = 0; i < PARTY_MAX; i++)
        drawSlot(i);

    VDP_drawText("ITEMS", UI_PANEL_COL, 13);
    VDP_drawText("[][][][]", UI_PANEL_COL + 2, 14);
    VDP_drawText("[][][][]", UI_PANEL_COL + 2, 15);

    VDP_drawText("UP/DN WALK", UI_PANEL_COL, 17);
    VDP_drawText("L/R TURN", UI_PANEL_COL, 18);
}

void uiPanel_drawStatus(const Player *p)
{
    char text[UI_PANEL_W + 1];
    sprintf(text, "%c (%02d,%02d)", facingLetter[p->facing], p->x, p->y);
    VDP_drawText(text, UI_PANEL_COL, 27);
}
