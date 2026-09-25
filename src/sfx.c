#include "sfx.h"
#include "game.h"

typedef struct
{
    const u8 *data;
    u32 size;
    u8 priority;        // 0..15: a sound with a lower priority cannot cut a higher one off
} Sfx;

static const Sfx sounds[SFX_COUNT] =
{
    { sfx_hit,       sizeof(sfx_hit),       6 },
    { sfx_miss,      sizeof(sfx_miss),      4 },
    { sfx_hurt,      sizeof(sfx_hurt),      7 },
    { sfx_spell,     sizeof(sfx_spell),     6 },
    { sfx_fire,      sizeof(sfx_fire),      6 },
    { sfx_heal,      sizeof(sfx_heal),      6 },
    { sfx_explosion, sizeof(sfx_explosion), 9 },
    { sfx_door,      sizeof(sfx_door),      5 },
    { sfx_land,      sizeof(sfx_land),      10 },
    { sfx_dice,      sizeof(sfx_dice),      5 },
    { sfx_victory,   sizeof(sfx_victory),   12 },
    { sfx_gameover,  sizeof(sfx_gameover),  12 },
    { sfx_menu,      sizeof(sfx_menu),      2 },
    { sfx_quake,     sizeof(sfx_quake),     11 },
    { sfx_item,      sizeof(sfx_item),      5 },
    { sfx_intro,     sizeof(sfx_intro),     12 },
};

static MusicId currentMusic = MUSIC_NONE;

void sfx_init(void)
{
    Z80_loadDriver(Z80_DRIVER_XGM2, TRUE);
    currentMusic = MUSIC_NONE;
}

void sfx_play(SfxId id)
{
    const Sfx *s = &sounds[id];
    XGM2_playPCMEx(s->data, s->size, SOUND_PCM_CH_AUTO, s->priority, FALSE, FALSE);
}

void music_play(MusicId id)
{
    if (id == currentMusic) return;
    currentMusic = id;
    switch (id)
    {
        case MUSIC_TITLE:   XGM2_play(music_title); break;
        case MUSIC_DUNGEON: XGM2_play(music_dungeon); break;
        case MUSIC_COMBAT:  XGM2_play(music_combat); break;
        case MUSIC_BRIDGE:  XGM2_play(music_bridge); break;
        case MUSIC_ENDING:  XGM2_play(music_ending); break;
        default:            XGM2_stop(); break;
    }
}

void music_playRoom(RoomId room)
{
    music_play(room == ROOM_6 ? MUSIC_BRIDGE : MUSIC_DUNGEON);
}
