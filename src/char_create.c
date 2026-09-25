#include "char_create.h"
#include "text.h"
#include "game.h"

static const CharClass classOrder[3] = { CLASS_FIGHTER, CLASS_ROGUE, CLASS_MAGE };

static void drawMenu(u8 cursor)
{
    for (u8 i = 0; i < 3; i++)
    {
        char line[20];
        sprintf(line, "%s %s", (i == cursor) ? ">" : " ", class_name(classOrder[i]));
        text_draw(line, 15, 14 + i * 2);
    }
}

CharClass charCreate_run(void)
{
    Sprite *avatar = SPR_addSprite(&avatar_sprite, 148, 60, TILE_ATTR(PAL1, FALSE, FALSE, FALSE));

    text_draw("ERSCHAFFE DEINEN HELDEN", 8, 4);
    text_draw("KREUZ: WÄHLEN   START: OK", 7, 24);

    u8 cursor = 0;
    drawMenu(cursor);

    u16 prevJoy = 0;
    while (TRUE)
    {
        u16 joy = JOY_readJoypad(JOY_1);
        u16 pressed = joy & ~prevJoy;

        if (pressed & BUTTON_UP) cursor = (cursor + 2) % 3;
        if (pressed & BUTTON_DOWN) cursor = (cursor + 1) % 3;
        if (pressed & (BUTTON_UP | BUTTON_DOWN)) drawMenu(cursor);

        if (pressed & (BUTTON_START | BUTTON_A)) break;

        prevJoy = joy;
        SPR_update();
        SYS_doVBlankProcess();
    }

    SPR_releaseSprite(avatar);
    VDP_clearPlane(BG_A, TRUE);
    return classOrder[cursor];
}
