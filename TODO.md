# TODO

Technical setup is done (toolchain, build/run scripts, boot boilerplate, a working depth-tiled
first-person renderer with grid movement). Next steps for turning this into an actual game,
roughly in order:

## Core loop
- [ ] Real level data format (author dungeons as data, not a hardcoded C string grid) — probably a
      small binary format converted by a Python tool at build time, like `world_gen.h` in the
      Wanderburg project.
- [ ] Doors, secret doors, locked doors/keys.
- [ ] Wall decorations (levers, plaques, torches) as overlays on the depth-tile view.
- [ ] Strafing (classic EOB/DM control scheme uses a 3x3 or 4x4 button/D-pad layout; Mega Drive's
      3-button pad is cramped — decide on a control scheme early, maybe 6-button pad only).

## Party & characters
- [ ] Party data model (up to ~4-6 characters: class, stats, HP/MP, inventory, equipment).
- [ ] Character creation or pre-made party.
- [ ] D&D-derived stat block (STR/DEX/CON/INT/WIS/CHA, AC, saving throws) — decide how much of
      real D&D rules to keep vs. simplify for a console action-lite crawler.

## Combat
- [ ] Turn-based or real-time-with-pause encounter system.
- [ ] Enemy placement in the dungeon grid, line-of-sight/engagement range.
- [ ] Spellcasting (spell list, MP cost, targeting).

## UI/UX
- [ ] Proper HUD layout (portraits, compass, message log) instead of the debug text line —
      the viewport/HUD split in `dungeon_view.c` (BG_B view, rows 0-17 / BG_A text, rows 18+)
      leaves room on the right (cols 32-39) for portraits if the viewport stays at 256px wide.
- [ ] Inventory screen, equipment screen.
- [ ] Automap.

## Art
- [ ] Replace `res/gfx/dungeon_tiles.png` placeholder brick texture with real pixel art
      (keep the same tile-slot layout, or refactor `dungeon_view.c` if the slot scheme changes).
- [ ] Monster sprites (as VDP sprites overlaid on the view, same layer trick as Wanderburg's
      enemy castles).
- [ ] Title screen, party portraits.

## Audio
- [ ] Music/SFX pipeline — the other projects use XGM2 (see `tools/generate_music.py` /
      `tools/generate_sfx.py` in the Wanderburg project for the conversion approach).
