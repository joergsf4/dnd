#include "game.h"
#include "dungeon_map.h"
#include "dungeon_view.h"
#include "ui_panel.h"
#include "party.h"
#include "char_create.h"

int main(bool hardReset)
{
    VDP_setScreenWidth320();
    VDP_setScreenHeight224();
    SPR_init();
    PAL_setPalette(PAL1, avatar_sprite.palette->data, DMA);

    CharClass heroClass = charCreate_run();
    party_init();
    party_addMember(heroClass);

    dungeonView_init();
    uiPanel_init();

    Player player = { 4, 10, FACE_NORTH };
    dungeonView_render(&player);
    uiPanel_drawStatus(&player);

    u16 prevJoy = 0;
    while (TRUE)
    {
        u16 joy = JOY_readJoypad(JOY_1);
        u16 pressed = joy & ~prevJoy;
        bool moved = FALSE;

        if (pressed & BUTTON_UP) { player_step(&player, 1); moved = TRUE; }
        else if (pressed & BUTTON_DOWN) { player_step(&player, -1); moved = TRUE; }

        if (pressed & BUTTON_LEFT) { player_turn(&player, -1); moved = TRUE; }
        else if (pressed & BUTTON_RIGHT) { player_turn(&player, 1); moved = TRUE; }

        if (moved)
        {
            dungeonView_render(&player);
            uiPanel_drawStatus(&player);
        }

        prevJoy = joy;
        SPR_update();
        SYS_doVBlankProcess();
    }

    return 0;
}
