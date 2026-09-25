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
#include "room3.h"
#include "room4.h"
#include "room5.h"
#include "room6.h"
#include "countdown.h"
#include "title.h"
#include "figures.h"
#include "encounter.h"
#include "abilities.h"
#include "text.h"

// Sprite tiles are reserved just below the font; the default 420 would collide with the view's two
// 560-tile buffers (dungeon_view.c). Avatars take 9 tiles each, figures up to 120 (a bust), a
// fight at most 2 cambions (2 x 72) or Zhalk (112) plus the marker (encounter.c).
#define SPRITE_VRAM_TILES 304   // all there is: tile maps start at 0xC000 (1536 tiles), the font
                                // takes the top 96, the view 16 + 2 x 560 below

#define ENEMY_STEP_FRAMES 45

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
    PAL_setPalette(PAL1, avatar_wir_sprite.palette->data, DMA);   // the companions' avatars
    text_init();

    title_run();
    u8 portrait;
    CharClass heroClass = charCreate_run(&portrait);
    party_init();
    party_addMember(heroClass)->portrait = portrait;
    inventory_init();

    dungeonView_init();
    uiPanel_initSprites();
    uiPanel_redrawChrome();
    SPR_update();   // drops the creation screen's avatar sprite before the first view is drawn

    map_registerRoom(&ROOM1);
    map_registerRoom(&ROOM2);
    map_registerRoom(&ROOM3);
    map_registerRoom(&ROOM4);
    map_registerRoom(&ROOM5);
    map_registerRoom(&ROOM6);
    Player player;
    map_loadRoom(&ROOM1, &player);
    redrawWorld(&player);

    u16 prevJoy = JOY_readJoypad(JOY_1);
    u16 enemyTimer = 0;
    while (TRUE)
    {
        u16 joy = JOY_readJoypad(JOY_1);
        u16 pressed = joy & ~prevJoy;
        bool moved = FALSE;

        if (pressed & (BUTTON_UP | BUTTON_DOWN))
        {
            if (player_step(&player, (pressed & BUTTON_UP) ? 1 : -1)) countdown_step();
            moved = TRUE;
        }

        if (pressed & BUTTON_LEFT) { player_turn(&player, -1); moved = TRUE; }
        else if (pressed & BUTTON_RIGHT) { player_turn(&player, 1); moved = TRUE; }

        if (moved) redrawWorld(&player);

        if (pressed & BUTTON_B)
        {
            ab_partyMenu(&player);
            redrawWorld(&player);
            uiPanel_redrawChrome();
        }

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

        // Enemies close in in real time, one cell every ENEMY_STEP_FRAMES; next to the party, the
        // fight starts.
        if (++enemyTimer >= ENEMY_STEP_FRAMES)
        {
            enemyTimer = 0;
            if (encounter_tick(&player)) redrawWorld(&player);
        }
        RoomObject *foe = encounter_adjacent(&player);
        if (foe)
        {
            encounter_fight(&player, foe);
            redrawWorld(&player);
            uiPanel_redrawChrome();
            enemyTimer = 0;
        }

        countdown_update();
        prevJoy = joy;
        SPR_update();
        SYS_doVBlankProcess();
    }

    return 0;
}
