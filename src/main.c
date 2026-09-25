#include "game.h"
#include "dungeon_map.h"
#include "dungeon_view.h"
#include "dungeon_objects.h"
#include "ui_panel.h"
#include "party.h"
#include "inventory.h"
#include "char_create.h"
#include "room1.h"
#include "room2.h"
#include "text.h"

// Sprite tiles are reserved just below the font; the default 420 would collide with the view's two
// 560-tile buffers (dungeon_view.c). The avatar needs 9 tiles, so 256 leaves plenty for later.
#define SPRITE_VRAM_TILES 256

static const RoomDef *shownRoom;

// Redraws the view and panel status. When the player has just arrived in a different room (game
// start, or through a door), also runs that room's onEnter hook -- after the new view is on
// screen, so an arrival text shows over the room rather than a blank view.
static void redrawWorld(Player *p)
{
    dungeonView_render(p);
    uiPanel_drawStatus(p);

    const RoomDef *room = map_currentRoom();
    if (room != shownRoom)
    {
        shownRoom = room;
        if (room->onEnter)
        {
            room->onEnter(p);
            uiPanel_redrawChrome();
        }
    }
}

int main(bool hardReset)
{
    VDP_setScreenWidth320();
    VDP_setScreenHeight224();
    SPR_initEx(SPRITE_VRAM_TILES);
    PAL_setPalette(PAL1, avatar_sprite.palette->data, DMA);
    text_init();

    CharClass heroClass = charCreate_run();
    party_init();
    party_addMember(heroClass);
    inventory_init();

    dungeonView_init();
    uiPanel_initSprites();
    uiPanel_redrawChrome();
    SPR_update();   // drops the creation screen's avatar sprite before the first view is drawn

    map_registerRoom(&ROOM1);
    map_registerRoom(&ROOM2);
    Player player;
    map_loadRoom(&ROOM1, &player);
    redrawWorld(&player);

    u16 prevJoy = JOY_readJoypad(JOY_1);
    while (TRUE)
    {
        u16 joy = JOY_readJoypad(JOY_1);
        u16 pressed = joy & ~prevJoy;
        bool moved = FALSE;

        if (pressed & BUTTON_UP) { player_step(&player, 1); moved = TRUE; }
        else if (pressed & BUTTON_DOWN) { player_step(&player, -1); moved = TRUE; }

        if (pressed & BUTTON_LEFT) { player_turn(&player, -1); moved = TRUE; }
        else if (pressed & BUTTON_RIGHT) { player_turn(&player, 1); moved = TRUE; }

        if (moved) redrawWorld(&player);

        if (pressed & BUTTON_A)
        {
            RoomObject *target = dungeonObjects_interactTarget(&player);
            if (target)
            {
                map_currentRoom()->onInteract(&player, target);
                redrawWorld(&player);
                uiPanel_redrawChrome();
            }
        }

        prevJoy = joy;
        SPR_update();
        SYS_doVBlankProcess();
    }

    return 0;
}
