# TODO

Technical setup is done (toolchain, build/run scripts, boot boilerplate, a mitred-ring first-person
renderer with grid movement). The vertical-slice foundation is also done now: data-driven rooms,
interactive objects, a textbox/menu system, skill checks, and a minimal inventory, all wired
together in Room 1 (the "Klonkammer" — see `BeschreibungInhaltVerticalSlice.md`). Next steps:

## Vertical slice — Room 1 (done)
- [x] Data-driven room format (`RoomDef`/`RoomObject` in `src/dungeon_map.h/.c`) — `MAP_W`/`MAP_H`
      `#define`s are gone, replaced by per-room `const` structs (`src/room1.c` is the pattern for
      future rooms). Object runtime state (looted/flagged) lives in per-room RAM, copied from the
      ROM template on first visit, so it survives backtracking once rooms link up to each other.
- [x] Interactive objects in the first-person view (`src/dungeon_objects.c/.h`) — objects always
      sit on a wall cell, so they're always the ring-0 front wall when faced; one shared sprite
      shows/hides/repositions via `dungeonObjects_render`, frame-selected by `ObjectKind`.
- [x] Textbox/menu system (`src/textbox.c/.h`) — modal, full-40-column overlay on the lower BG_A
      rows (19-27), pauses the world. `uiPanel_redrawChrome()` must be called after any interaction
      closes, since a textbox can cover the panel's status row.
- [x] Skill checks (`src/skill_check.c/.h`) — d20 + a flat attribute modifier vs. a threshold, with
      a short "rolling" animation. `Character` gained `str`/`dex`/`intl` (placeholder 1-5 modifiers
      per class, not real ability scores — see the D&D-fidelity item below).
- [x] Minimal inventory (`src/inventory.c/.h`) — party-wide gold/gems/potions/basic-gear flag, shown
      live in the panel (`uiPanel_drawInventory`). Not a real item system yet, see below.
- [x] Room 1 content wired end-to-end and verified via `tools/emutest.py room1` (screenshots of
      every object interaction, including both larva-tank branches).

## Room-by-room roadmap (light — detailed planning happens per room, not now)
- [ ] **Room 2** (Myrnath/"Wir"): multi-stage branching `onInteract`, no new engine needed;
      `party_addMember()` is already "Wir joins". Doc's "Medizin" check doesn't map to STR/DEX/INT
      — needs either a 4th attribute or a documented stand-in when this room is planned.
- [ ] **Room 3** (Lae'zel ambush + first combat): needs an entry-triggered cutscene — `RoomDef`
      already has an `onEnter` hook reserved for this (`NULL` in Room 1). Combat itself is a new
      subsystem (see Combat below), would plug in as another blocking sub-loop like `onInteract`.
- [ ] **Room 4** (locked door + console): needs an identified-item inventory (`hasItem[]`, see
      below) and uses `RoomObject`'s already-reserved `param0`/`param1` fields (target room +
      required item) — no struct changes needed. Multi-button console is just another `ObjectKind`.
- [ ] **Room 5** (transformation reveal): a sequence of no-choice `textbox_show()` calls, no new
      system needed. The morph itself is a sprite-frame swap, art not mechanics.
- [ ] **Room 6** (timed boss): needs a persistent countdown on the panel and the combat system's
      notion of "rounds" — unspecified until combat exists.

## Core loop
- [ ] Doors, secret doors — `OBJ_DOOR_EXIT` + `dungeonObjects_tryDoor` exist and correctly stub
      "not built yet" (see Room 1); an actual room-to-room transition is untested since Room 2
      doesn't exist. Locked doors/keys: see the identified-item inventory item below.
- [ ] Wall decorations (levers, plaques, torches) as overlays — could reuse the `dungeonObjects`
      sprite mechanism, or be purely visual (part of the wall tileset instead).
- [ ] Strafing (classic EOB/DM control scheme uses a 3x3 or 4x4 button/D-pad layout; Mega Drive's
      3-button pad is cramped — decide on a control scheme early, maybe 6-button pad only).

## Party & characters
- [ ] Letter-grid name entry (D-pad-driven on-screen keyboard) if auto-naming ever feels wrong —
      explicitly deferred when this was built, not forgotten.
- [ ] Recruiting the other 3 party slots during play — `party_addMember()` exists and the panel
      already renders empty slots as "---EMPTY---"; Room 2's "Wir" is the first real recruit, once
      that room exists.
- [ ] D&D-derived stat block (STR/DEX/CON/INT/WIS/CHA, AC, saving throws) — the current model is
      class + HP/MP + three small (1-5) skill-check modifiers, not real ability scores. Decide how
      much of real D&D rules to keep vs. simplify (Room 2's "Medizin" check will force this).
- [ ] Identified-item inventory (`ItemId` enum + `bool hasItem[]`, additive alongside
      `src/inventory.c`'s stackable counts) — needed once Room 4/5 introduce key items (Eldritch
      Rune, Gold Key).
- [ ] Real inventory/equipment screen — the panel's item block is a live readout, not an
      interactive screen.

## Combat
- [ ] Turn-based or real-time-with-pause encounter system — would plug in as a blocking sub-loop
      (`combat_run(...)`) the same way `onInteract`/`textbox_show` do. Needed starting Room 3.
- [ ] Enemy placement in the dungeon grid, line-of-sight/engagement range.
- [ ] Spellcasting (spell list, MP cost, targeting).

## UI/UX
- [x] Screen split: dungeon view left (28x28 tiles, BG_B), party/inventory panel right
      (12 cols, BG_A) — see `src/ui_panel.c` and the layout note at the top of `dungeon_view.c`.
- [x] Textbox/menu overlay (`src/textbox.c`) — see above.
- [ ] Compass.
- [ ] Message log (combat/pickup text) beyond the modal textbox — the panel has no room reserved
      for a persistent log; would need to shrink the item grid or the party block.
- [ ] Automap.
- [ ] Room 6's countdown timer display (see roadmap above).

## Art
- [ ] Replace `res/gfx/dungeon_tiles.png` placeholder brick texture with real pixel art
      (keep the same tile-slot layout, or refactor `dungeon_view.c` if the slot scheme changes).
- [x] Hero avatar (`res/gfx/avatar.png`, `tools/make_avatar.py`) — one generic 24x24 cloaked-figure
      placeholder shared by all 3 classes. Replace with real art, and/or split into per-class
      avatars, whenever that's worth the extra tile budget.
- [x] Interactive-object icons (`res/gfx/dungeon_objects.png`, `tools/make_dungeon_objects.py`) —
      5 placeholder 64x64 icons (larva tank, corpse, chest, shrine, door), one per `ObjectKind`.
- [ ] Monster/companion sprites for Room 2+ (as VDP sprites overlaid on the view, same layer trick
      as `dungeonObjects` and Wanderburg's enemy castles).
- [ ] Title screen.

## Audio
- [ ] Music/SFX pipeline — the other projects use XGM2 (see `tools/generate_music.py` /
      `tools/generate_sfx.py` in the Wanderburg project for the conversion approach).

## Gotchas worth remembering
- SGDK's default font renders with PAL0, indices 14/15. Any palette we load into PAL0 that doesn't
  explicitly define 16 colors (rescomp pads the rest with black) will make `VDP_drawText` invisible
  wherever the backdrop is also black — not a rendering bug, just missing contrast. Fixed once in
  `dungeonView_init()` (forces indices 14/15 to white); remember this if PAL0 is ever reassigned to
  a different, differently-sized palette.
- `tools/emutest.py`: consecutive `press()` calls for the *same* button need a `frames()` gap
  between them, or BlastEm's bindup+binddown can land inside the same polled frame and the ROM's
  edge-detection (`pressed = joy & ~prevJoy`) never sees the release — the second press silently
  does nothing (looks like a movement bug, isn't one).
