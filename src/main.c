#include "game.h"
#include "dungeon_map.h"
#include "dungeon_view.h"

static const char facingLetter[4] = { 'N', 'E', 'S', 'W' };

static void drawStatus(const Player *p)
{
    char text[40];
    sprintf(text, "FACING %c   X:%02d Y:%02d", facingLetter[p->facing], p->x, p->y);
    VDP_drawText(text, 2, 20);
}

int main(bool hardReset)
{
    VDP_setScreenWidth320();
    VDP_setScreenHeight224();

    dungeonView_init();

    Player player = { 1, 1, FACE_EAST };
    dungeonView_render(&player);

    VDP_drawText("D-PAD: UP/DOWN WALK, LEFT/RIGHT TURN", 2, 18);
    drawStatus(&player);
    VDP_drawText("HP 20/20   MP 12/12   GOLD 0", 2, 22);

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
            drawStatus(&player);
        }

        prevJoy = joy;
        SYS_doVBlankProcess();
    }

    return 0;
}
