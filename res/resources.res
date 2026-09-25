// Dungeon-view tileset: 16 8x8 tiles (ceiling/floor/wall at 3 depths + vanishing mist).
// Slot order is fixed by tools/make_dungeon_tiles.py and indexed directly in src/dungeon_view.c
// -> keep NONE/NONE so rescomp does not reorder or dedupe tiles.
TILESET dungeon_tiles "gfx/dungeon_tiles.png" NONE NONE
PALETTE dungeon_pal "gfx/dungeon_tiles.png"

// Generic hero avatar (see tools/make_avatar.py), used on the character creation screen and
// in the party panel. Carries its own palette (PAL1) via avatar_sprite.palette.
SPRITE avatar_sprite "gfx/avatar.png" 3 3
