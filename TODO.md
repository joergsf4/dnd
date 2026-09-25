# TODO

Technical setup is done (toolchain, build/run scripts, boot boilerplate, an Eye-of-the-Beholder-
style textured first-person renderer with grid movement). The vertical-slice foundation is also done now: data-driven rooms,
interactive objects, a textbox/menu system, skill checks, and a minimal inventory, all wired
together in Room 1 (the "Klonkammer" — see `BeschreibungInhaltVerticalSlice.md`). Next steps:

## Vertical slice — Room 1 (done)
- [x] Data-driven room format (`RoomDef`/`RoomObject` in `src/dungeon_map.h/.c`) — `MAP_W`/`MAP_H`
      `#define`s are gone, replaced by per-room `const` structs (`src/room1.c` is the pattern for
      future rooms). Object runtime state (looted/flagged) lives in per-room RAM, copied from the
      ROM template on first visit, so it survives backtracking once rooms link up to each other.
- [x] Interactive objects in the first-person view — objects sit on wall cells and are drawn as
      that wall's texture (`kindTexture` in `src/dungeon_view.c`), visible from any distance;
      `src/dungeon_objects.c` only does "what's straight ahead" and the shared door handler.
- [x] Textbox/menu system (`src/textbox.c/.h`) — the message area below the view (rows 20-27,
      columns 0-27), 27 characters per line, pauses the world while open.
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
- [ ] Wall decorations (levers, plaques, torches) — a new texture in `tools/make_view.py` plus an
      `ObjectKind`, same as the tank/chest. Limitation: a texture applies to every face of its wall
      cell; fine on room borders (only one face is ever visible), needs per-face textures for
      free-standing wall blocks.
- [ ] Doors *between* cells (EOB-style door frames in a corridor, open/closed state) — the room 1
      exit is a door texture on a border wall, which is enough for room-to-room exits but not for
      doors you walk through inside a level.
- [ ] Monsters/NPCs in the view: sprites over the view, pre-drawn at 3-4 sizes by distance (the
      hardware can't scale), positioned from the same geometry as `tools/make_view.py`.
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
- [x] Screen layout: view top-left (28x20 tiles, BG_B), message area below it (rows 20-27),
      party/inventory panel right (12 columns) — see README.md, "Screen layout".
- [x] Message area / menus (`src/textbox.c`) — see above.
- [ ] Compass.
- [ ] Persistent message log (the message area is currently only used while a textbox is open).
- [ ] Automap.
- [ ] Room 6's countdown timer display (see roadmap above).

## Art
- [ ] Real wall/floor/ceiling art — textures are procedural placeholders in `tools/make_view.py`
      (64x64, palette indices into the 16-colour view palette). Could load hand-drawn indexed PNGs
      there instead; the rest of the pipeline stays the same. The Nautiloid rooms want an organic,
      bio-mechanical look rather than plain stone.
- [x] Hero avatar (`res/gfx/avatar.png`, `tools/make_avatar.py`) — one generic 24x24 cloaked-figure
      placeholder shared by all 3 classes. Replace with real art, and/or split into per-class
      avatars, whenever that's worth the extra tile budget.
- [x] Object/door wall textures (larva tank, corpse, chest, shrine, door) — placeholders in
      `tools/make_view.py`.
- [ ] Monster/companion sprites for Room 2+ (see "Monsters/NPCs in the view" above).
- [ ] Title screen.

## Audio
- [ ] Music/SFX pipeline — the other projects use XGM2 (see `tools/generate_music.py` /
      `tools/generate_sfx.py` in the Wanderburg project for the conversion approach).

## Gotchas worth remembering
- Text uses its own palette (PAL3, `VDP_setTextPalette` in `main.c`). SGDK's default is PAL0, and
  when PAL0 held a palette that left the font's colour slots black, all panel text was invisible on
  the black backdrop — not a rendering bug, just missing contrast. PAL0 now belongs to the view.
- VRAM: the view needs two sets of 560 tiles (double buffering) from `TILE_USER_INDEX`, which only
  fits because `main.c` shrinks the sprite reservation to 256 tiles (`SPR_initEx`). More sprite
  tiles (monsters) means revisiting that split.
- Redraw cost is 3-5 frames and grows with the number of wall pixels copied (`src/view_draw.s`).
  A longer draw distance (`MAXZ` in `tools/make_view.py`) adds events per column and baked data.
- `tools/emutest.py`: use `act()` for presses. Consecutive presses of the same button need a gap,
  or BlastEm's bindup+binddown land inside one polled frame and the ROM's edge-detection
  (`pressed = joy & ~prevJoy`) never sees the second press (looks like a movement bug, isn't one);
  and a move needs a few frames to redraw before a screenshot shows it.
