# D&D Dungeon Crawler (Mega Drive)

A grid-based first-person dungeon crawler for the Sega Mega Drive / Genesis, in the vein of
*Eye of the Beholder* and *Dungeon Master* (step movement, 90°-turns, no free-look), built with
[SGDK](https://github.com/Stephane-D/SGDK). Currently building a narrative vertical slice
("Nautiloid Prologue", a Baldur's Gate 3-inspired opening — see
[BeschreibungInhaltVerticalSlice.md](BeschreibungInhaltVerticalSlice.md)) adapted onto this
first-person engine: the source document was written for a top-down view, the content is being
reinterpreted for ours, not the other way around.

## Toolchain

Same setup as the other Mega Drive projects in this workspace:

- **SGDK 2.11** via the [doragasu/docker-sgdk](https://gitlab.com/doragasu/docker-sgdk) Docker image — no local SGDK install needed.
- **BlastEm** to run the ROM (`brew install blastem` or similar).
- `./build.sh` — builds `out/rom.bin` in the container (`./build.sh clean` to clean).
- `./run.sh` — runs the last build in BlastEm.
- `.vscode/tasks.json` — the same two as build/run tasks (Cmd+Shift+B to build).
- `tools/emutest.py` — drives BlastEm's debugger (`-d`) to play the ROM headlessly and save
  screenshots (`python3 tools/emutest.py room1`; screenshots land in `out/emutest/`, gitignored).
  BlastEm's own `ui.screenshot` binding writes the PNG, so no OS-level screen capture is needed —
  use this instead of trying to read pixels off the live window. Scenarios: `create` (character
  creation only), `look` (Room 1, look around), `room1` (walks up to and interacts with every
  object in Room 1). Note: consecutive `press()` calls for the *same* button need a `frames()` gap
  between them or the ROM's edge-detection can miss the second press entirely (see TODO.md).

## Rendering approach

The Mega Drive VDP has no hardware scaling or texture mapping, so — like the original EOB/DM-style
engines — the 3D view is not raycast; it's built from pre-shaded wall/floor/ceiling *tiles*
composited onto the BG_B plane as nested, mitred rings (near → mid → far → vanishing point), based
on a 3-cell lookahead into the map grid from the player's position and facing. Every tile in a ring
is classified into the left/right wall band or the ceiling/floor band by comparing its horizontal
vs. vertical offset from the ring's centre (the same construction a picture frame's mitred corners
use) — this tapers the wall/ceiling/floor boundary into a diagonal that actually recedes, which is
what makes it read as a tunnel instead of nested rectangles. This is cheap (a few hundred
`VDP_setTileMapXY` writes, only on movement, not per frame) and keeps the view entirely on BG_B,
leaving BG_A free for HUD text.

See `src/dungeon_view.c` for the ring/depth geometry and compositing logic.

## Screen layout

320x224px = 40x28 tiles, split 28/12: the dungeon view fills the left 28x28 tiles (224x224px,
BG_B), the party/inventory panel fills the right 12 columns (96x224px, all 28 rows, BG_A text).
Since the view uses the full screen height, **no text may be drawn left of column 28 during normal
gameplay rendering** — BG_A composites in front of BG_B on real hardware, so it would cut into the
view. A modal textbox (`src/textbox.c`) is the one deliberate exception: it pauses the world and
draws a full-width overlay over the lower rows on purpose. See the comment above `UI_PANEL_COL` in
`src/ui_panel.h`.

## Project structure

```
src/
  main.c                Init, character creation, room load, input, game loop
  dungeon_map.c/.h       RoomDef/RoomObject data model, player position/facing, movement rules
  dungeon_view.c/.h      First-person renderer: BG_B tile compositing by depth ring
  dungeon_objects.c/.h   Interactive-object sprite (always the ring-0 front wall when faced)
  textbox.c/.h           Modal textbox/menu overlay (BG_A rows 19-27, full width)
  skill_check.c/.h       d20 + attribute vs. threshold, with a "rolling" animation
  inventory.c/.h         Party-wide gold/gems/potions/gear (placeholder scope, see TODO.md)
  party.c/.h             Party data model (up to 4 members: class, name, HP/MP, str/dex/int)
  char_create.c/.h       Full-screen class-select loop, runs once before the dungeon starts
  room1.c/.h             Room 1 ("Klonkammer") content: map, objects, interaction handlers
  ui_panel.c/.h          Right-hand panel: party slots, item block, status line
  game.h                 Shared includes/constants
  boot/                  SGDK boot files (ROM header, startup assembly)
res/
  resources.res          Asset manifest, compiled by SGDK's rescomp
  resources.h            Declares the compiled asset symbols (generated, but committed for IDE use)
  gfx/dungeon_tiles.png    Placeholder wall/floor/ceiling tileset, from tools/make_dungeon_tiles.py
  gfx/avatar.png           Placeholder hero avatar (one generic sprite, shared by all classes)
  gfx/dungeon_objects.png  Placeholder interactive-object icons, from tools/make_dungeon_objects.py
tools/
  make_dungeon_tiles.py    Regenerates the placeholder tileset (16 tiles, indexed PNG)
  make_avatar.py           Regenerates the placeholder avatar sprite (24x24, indexed PNG)
  make_dungeon_objects.py  Regenerates the placeholder object icons (5x 64x64, indexed PNG)
```

## Current state

Boots into a class-select screen (Fighter/Rogue/Mage, D-pad + Start) that creates the one starting
party member, auto-named after the class — then into Room 1 (the "Klonkammer"): a small room with
four interactive objects (a larva tank with a damage/skill-check/leave choice, a lootable corpse, a
lootable chest, a reusable full-party heal shrine) and an exit door that correctly stubs "still
sealed" since Room 2 doesn't exist yet. D-Pad Up/Down walks forward/back, Left/Right turns 90°, A
interacts with whatever's directly ahead. The right panel shows the live party (avatar + name/
HP or MP, empty slots as "---EMPTY---"), live inventory (gold/gems/potions/gear), and a facing/
coordinates status line.

All placeholder art is procedurally generated (see `tools/`) — tile/sprite *slot order* is indexed
directly by the C code (see each generator script's docstring), so keep that order if you replace
the art.

See [TODO.md](TODO.md) for what's next (Room 2 onward, combat, real D&D stats, real art).
