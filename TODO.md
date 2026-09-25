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
- [x] Interactive objects in the first-person view — free-standing props on floor cells,
      pre-scaled per distance and occluded by nearer walls (`objectProp()` in
      `src/dungeon_view.c`, with per-state variants); doors stay wall textures;
      `src/dungeon_objects.c` only does "what's straight ahead" and the shared door handler.
- [x] Textbox/menu system (`src/textbox.c/.h`) — the message area below the view (rows 20-27,
      columns 0-27), 27 characters per line, pauses the world while open.
- [x] Skill checks (`src/skill_check.c/.h`) — d20 + a flat attribute modifier vs. a threshold, with
      a short "rolling" animation. `Character` gained `str`/`dex`/`intl` (placeholder 1-5 modifiers
      per class, not real ability scores — see the D&D-fidelity item below).
- [x] Minimal inventory (`src/inventory.c/.h`) — party-wide gold/gems/potions/basic-gear flag, shown
      live in the panel (`uiPanel_drawInventory`). Not a real item system yet, see below.
- [x] Room 1 content from the design doc, German text with umlauts (`src/text.c`,
      `tools/make_font.py`): intro on first entry, larva pool (burst/marked states), corpse,
      chest, restoration station, open and broken clone pods, sphincter door. Verified via
      `tools/emutest.py room1`. Adaptations to the grid engine: see README, "Current state".

- [x] Room 2 (Operationssaal): Myrnath with the two-stage menu from the doc's demake dialogue
      (STÄ/GES to free the brain, failure kills it; lobotomise [GES 15] or take along), "Wir"
      joins with its own class and avatar, lore lectern/tablets, vivisection tables. Flat, no lift.
      Verified via `tools/emutest.py room2`.
- [x] Room-to-room doors, both ways (`map_enterRoom`: arrive in front of the matching door).
- [x] Combat (`src/combat.c`): turn-based menu fights in the first-person view, Shining in the
      Darkness style — see README, "Combat". Enemy groups roam rooms and close in
      (`src/encounter.c`).
- [x] Room 3 (Außendeck): hull breaches onto Avernus, fires, Lae'zel lands in front of the
      player and joins (dialogue per the doc's demake version), three imps come through the
      breach, the fight, an acid tank to burst, a restoration station before the door to Room 4.
      Verified via `tools/emutest.py room3`.

## Room-by-room roadmap (light — detailed planning happens per room, not now)
- [ ] **Order: Room 5 before Room 4** — Room 4's console needs the rune from Room 5. The doc is
      inconsistent about where the 3-button console stands (Room 4 in the overview, the lab in
      Szene 5); decide when planning those rooms.
- [ ] **Room 4** (locked door + console): needs an identified-item inventory (`hasItem[]`, see
      below) and uses `RoomObject`'s already-reserved `param0`/`param1` fields (target room +
      required item) — no struct changes needed. Multi-button console is just another `ObjectKind`.
- [ ] **Room 5** (transformation reveal): a sequence of no-choice `textbox_show()` calls, no new
      system needed. The morph itself is a sprite-frame swap, art not mechanics.
- [ ] **Room 6** (timed boss): a persistent countdown on the panel. With combat in place, "rounds"
      can be combat rounds plus steps outside fights; bigger figures (Zhalk 48x64 in the doc, far
      larger on our screen) may need drawing into the view instead of hardware sprites (sprite
      VRAM is 256 tiles, see main.c).

## Core loop
- [ ] Secret doors, locked doors/keys — room-to-room doors work (`dungeonObjects_tryDoor`,
      a door to an unbuilt room stays shut); keys: see the identified-item inventory item below.
- [ ] Wall decorations (levers, plaques, torches) — a new wall texture in `tools/make_view.py`
      plus an `ObjectKind`, same as the door. Limitation: a texture applies to every face of its wall
      cell; fine on room borders (only one face is ever visible), needs per-face textures for
      free-standing wall blocks.
- [ ] Doors *between* cells (EOB-style door frames in a corridor, open/closed state) — the room 1
      exit is a door texture on a border wall, which is enough for room-to-room exits but not for
      doors you walk through inside a level.
- [ ] More enemy kinds in the world: `OBJ_ENEMY_GROUP` always draws the imp troop prop; other
      groups need their own prop (`objectProp` in dungeon_view.c could key on the encounter).
- [ ] Enemies only move towards the player, greedily (`encounter_tick`): no pathfinding round
      obstacles, no line of sight, no wandering.
- [ ] Strafing (classic EOB/DM control scheme uses a 3x3 or 4x4 button/D-pad layout; Mega Drive's
      3-button pad is cramped — decide on a control scheme early, maybe 6-button pad only).

## Party & characters
- [ ] Letter-grid name entry (D-pad-driven on-screen keyboard) if auto-naming ever feels wrong —
      explicitly deferred when this was built, not forgotten.
- [ ] Recruiting the rest of the party — "Wir" (Room 2) and Lae'zel (Room 3) are in;
      Schattenherz (Room 4) follows the same pattern (`party_addMember` + `uiPanel_initSprites`),
      each with an avatar in `tools/make_avatar.py`. "Wir" is meant to be a temporary companion in
      the doc; nothing removes it yet. What lobotomised changes beyond stats is open too.
- [ ] D&D-derived stat block (STR/DEX/CON/INT/WIS/CHA, AC, saving throws) — the current model is
      class + HP/MP + three small (1-5) skill-check modifiers, not real ability scores. Decide how
      much of real D&D rules to keep vs. simplify.
- [ ] Identified-item inventory (`ItemId` enum + `bool hasItem[]`, additive alongside
      `src/inventory.c`'s stackable counts) — needed once Room 4/5 introduce key items (Eldritch
      Rune, Gold Key).
- [ ] Real inventory/equipment screen — the panel's item block is a live readout, not an
      interactive screen.

## Combat
- [ ] Only one spell (Magier: Geschoss). Schattenherz (Room 4) brings healing; a spell list per
      class is the natural next step.
- [ ] No fleeing, no status effects, no XP/levels; enemies pick targets at random.
- [ ] Balance is a first guess (5e-like level-1 values in `party.c`, `ENEMY_IMP` in combat.c).
- [ ] Room 1's larva pool still never takes the hero below 1 KP (death only happens in combat).

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
      (64x64, palette indices into the 16-colour view palette, organic Nautiloid look). Could load
      hand-drawn indexed PNGs there instead; the rest of the pipeline stays the same.
- [x] Hero avatar (`res/gfx/avatar.png`, `tools/make_avatar.py`) — one generic 24x24 cloaked-figure
      placeholder shared by all 3 classes. Replace with real art, and/or split into per-class
      avatars, whenever that's worth the extra tile budget.
- [x] Props (larva pool + burst, corpse, chest + open, shrine, clone pod open/broken) and the
      sphincter door texture — placeholders in
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
