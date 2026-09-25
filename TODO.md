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
- [x] Party data model (`src/party.c/.h`): up to 4 members, class + HP/MP. No inventory/equipment
      fields yet.
- [x] Character creation (`src/char_create.c/.h`): pick one of Fighter/Rogue/Mage at game start,
      auto-named after the class (no letter-grid name entry — decided against it for now, see below).
- [ ] Letter-grid name entry (D-pad-driven on-screen keyboard) if auto-naming ever feels wrong —
      explicitly deferred when this was built, not forgotten.
- [ ] Recruiting the other 3 party slots during play — `party_addMember()` exists and
      `uiPanel_init()` already renders empty slots as "---EMPTY---", but nothing in the dungeon
      triggers a recruit yet. Explicitly deferred, not forgotten; the POC room has no NPCs.
- [ ] D&D-derived stat block (STR/DEX/CON/INT/WIS/CHA, AC, saving throws) — the current model is
      just class + HP/MP. Decide how much of real D&D rules to keep vs. simplify.
- [ ] Inventory/equipment data on `Character` (the panel shows a placeholder item grid with no
      backing data yet).

## Combat
- [ ] Turn-based or real-time-with-pause encounter system.
- [ ] Enemy placement in the dungeon grid, line-of-sight/engagement range.
- [ ] Spellcasting (spell list, MP cost, targeting).

## UI/UX
- [x] Screen split: dungeon view left (28x28 tiles, BG_B), party/inventory panel right
      (12 cols, BG_A) — see `src/ui_panel.c` and the layout note at the top of `dungeon_view.c`.
- [ ] Compass.
- [ ] Message log (combat/pickup text) — the panel has no room reserved for one yet; would need
      to shrink the item grid or the party block, or add a scrolling area.
- [ ] Inventory screen, equipment screen (the panel's `[][][][]` grid is a placeholder graphic,
      not an interactive screen).
- [ ] Automap.

## Art
- [ ] Replace `res/gfx/dungeon_tiles.png` placeholder brick texture with real pixel art
      (keep the same tile-slot layout, or refactor `dungeon_view.c` if the slot scheme changes).
- [x] Hero avatar (`res/gfx/avatar.png`, `tools/make_avatar.py`) — one generic 24x24 cloaked-figure
      placeholder shared by all 3 classes. Replace with real art, and/or split into per-class
      avatars, whenever that's worth the extra tile budget.
- [ ] Monster sprites (as VDP sprites overlaid on the view, same layer trick as Wanderburg's
      enemy castles).
- [ ] Title screen.

## Audio
- [ ] Music/SFX pipeline — the other projects use XGM2 (see `tools/generate_music.py` /
      `tools/generate_sfx.py` in the Wanderburg project for the conversion approach).
