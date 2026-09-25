#include "figures.h"
#include "game.h"

void figures_init(void)
{
    PAL_setPalette(PAL2, fig_imp_sprite.palette->data, DMA);
}

Sprite *figures_add(const SpriteDefinition *def, s16 cx, s16 bottom)
{
    return SPR_addSprite(def, cx - def->w / 2, bottom - def->h, TILE_ATTR(PAL2, FALSE, FALSE, FALSE));
}

void figures_wait(u16 n)
{
    for (u16 i = 0; i < n; i++)
    {
        SPR_update();
        SYS_doVBlankProcess();
    }
}

void figures_blink(Sprite *s, u8 times)
{
    for (u8 i = 0; i < times; i++)
    {
        SPR_setVisibility(s, HIDDEN);
        figures_wait(4);
        SPR_setVisibility(s, VISIBLE);
        figures_wait(4);
    }
}

void figures_shakeView(void)
{
    static const s8 offsets[] = { 5, -5, 4, -4, 3, -3, 2, -1, 0 };
    for (u8 i = 0; i < sizeof(offsets); i++)
    {
        VDP_setHorizontalScroll(BG_B, offsets[i]);
        figures_wait(2);
    }
}
