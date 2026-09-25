#include "game.h"
#include "dungeon_map.h"
#include "dungeon_view.h"
#include "dungeon_objects.h"
#include "ui_panel.h"
#include "party.h"
#include "inventory.h"
#include "char_create.h"
#include "room1.h"

int main(bool hardReset)
{
    VDP_setScreenWidth320();
    VDP_setScreenHeight224();
    SPR_init();
    PAL_setPalette(PAL1, avatar_sprite.palette->data, DMA);

    CharClass heroClass = charCreate_run();
    party_init();
    party_addMember(heroClass);
    inventory_init();

    dungeonView_init();
    dungeonObjects_init();
    uiPanel_initSprites();
    uiPanel_redrawChrome();

    map_registerRoom(&ROOM1);
    Player player;
    map_loadRoom(&ROOM1, &player);

    dungeonView_render(&player);
    dungeonObjects_render(&player);
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
            dungeonObjects_render(&player);
            uiPanel_drawStatus(&player);
        }

        if (pressed & BUTTON_A)
        {
            RoomObject *target = dungeonObjects_interactTarget(&player);
            if (target)
            {
                map_currentRoom()->onInteract(&player, target);
                dungeonView_render(&player);
                dungeonObjects_render(&player);
                uiPanel_drawStatus(&player);
                uiPanel_redrawChrome();
            }
        }

        prevJoy = joy;
        SPR_update();
        SYS_doVBlankProcess();
    }

    return 0;
}
