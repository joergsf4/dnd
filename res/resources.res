// Dungeon-view tileset: 16 8x8 tiles (ceiling/floor/wall at 3 depths + vanishing mist).
// Slot order is fixed by tools/make_dungeon_tiles.py and indexed directly in src/dungeon_view.c
// -> keep NONE/NONE so rescomp does not reorder or dedupe tiles.
TILESET dungeon_tiles "gfx/dungeon_tiles.png" NONE NONE
PALETTE dungeon_pal "gfx/dungeon_tiles.png"

// Generic hero avatar (see tools/make_avatar.py), used on the character creation screen and
// in the party panel. Carries its own palette (PAL1) via avatar_sprite.palette.
SPRITE avatar_sprite "gfx/avatar.png" 3 3

// Interactive-object icons (see tools/make_dungeon_objects.py): one 8x8-tile frame per
// ObjectKind (src/dungeon_map.h), in kind order starting at OBJ_LARVA_TANK (frame = kind - 1).
// Own palette (PAL2) via dungeon_objects_sprite.palette.
SPRITE dungeon_objects_sprite "gfx/dungeon_objects.png" 8 8
