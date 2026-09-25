#include "ui_panel.h"
#include "inventory.h"
#include "text.h"
#include "game.h"

static const char *const facingLetter[4] = { "N", "O", "S", "W" };

#define SLOT_ROWS 3                    // avatar height in tiles == rows per party slot
#define TEXT_COL  (UI_PANEL_COL + 3)   // right of the 3-tile-wide avatar

static void drawSlotText(u8 i)
{
    u16 row = i * SLOT_ROWS;
    const Character *c = &party.members[i];

    if (!c->active)
    {
        text_draw("---LEER---  ", UI_PANEL_COL, row);
        return;
    }

    for (u8 r = 0; r < SLOT_ROWS; r++)   // the slot may still show "---LEER---" from before
        text_draw("         ", TEXT_COL, row + r);

    char text[16];
    text_draw(c->name, TEXT_COL, row);
    sprintf(text, "KP %2d/%2d", c->hp, c->hpMax);
    text_draw(text, TEXT_COL, row + 1);
    if (c->mpMax > 0)
    {
        sprintf(text, "ZP %2d/%2d", c->mp, c->mpMax);
        text_draw(text, TEXT_COL, row + 2);
    }
}

static Sprite *avatars[PARTY_MAX];

void uiPanel_initSprites(void)
{
    for (u8 i = 0; i < PARTY_MAX; i++)
    {
        if (!party.members[i].active || avatars[i]) continue;
        u16 row = i * SLOT_ROWS;
        const SpriteDefinition *def;
        switch (party.members[i].cls)
        {
            case CLASS_WIR:    def = &avatar_wir_sprite; break;
            case CLASS_LAEZEL: def = &avatar_laezel_sprite; break;
            default:           def = &avatar_sprite; break;
        }
        avatars[i] = SPR_addSprite(def, UI_PANEL_COL * 8, row * 8, TILE_ATTR(PAL1, FALSE, FALSE, FALSE));
    }
}

void uiPanel_drawInventory(void)
{
    char text[24];

    text_draw("INVENTAR", UI_PANEL_COL, 13);
    sprintf(text, "GOLD:   %3d", inventory.gold);
    text_draw(text, UI_PANEL_COL, 14);
    sprintf(text, "EDELST.: %2d", inventory.gems);
    text_draw(text, UI_PANEL_COL, 15);
    sprintf(text, "TRÄNKE:  %2d", inventory.healingPotions);
    text_draw(text, UI_PANEL_COL, 16);
    text_draw(inventory.hasBasicGear ? "AUSRÜST.: JA" : "AUSRÜST.: - ", UI_PANEL_COL, 17);
}

void uiPanel_redrawChrome(void)
{
    for (u8 i = 0; i < PARTY_MAX; i++)
        drawSlotText(i);

    uiPanel_drawInventory();

    text_draw("STEUERKREUZ:", UI_PANEL_COL, 19);
    text_draw("GEHEN/DREHEN", UI_PANEL_COL, 20);
    text_draw("A: BENUTZEN", UI_PANEL_COL, 21);
}

void uiPanel_drawStatus(const Player *p)
{
    char text[UI_PANEL_W + 1];
    sprintf(text, "%s (%02d,%02d)", facingLetter[p->facing], p->x, p->y);
    text_draw(text, UI_PANEL_COL, 27);
}
