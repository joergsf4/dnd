#!/usr/bin/env python3
"""Drives the ROM in BlastEm's debugger to inspect it without a human -- same technique as
tools/emutest.py in the Wanderburg (megadriveplay) project: BlastEm's debugger (-d) runs frames,
simulates key presses and takes screenshots via its own UI hotkey, so no OS-level screen capture
is needed (and none is available in this sandbox).

    python3 tools/emutest.py create              # just the character creation screen
    python3 tools/emutest.py look                # Room 1: look around from the spawn point
    python3 tools/emutest.py tour                # Room 1: views from the middle and a corner
    python3 tools/emutest.py room1               # Room 1: interact with every object
    python3 tools/emutest.py look --class 2       # any scenario, but pick Mage instead of Fighter

Screenshots go to out/emutest/ (gitignored). Needs a built out/rom.bin (./build.sh).

Notes on the debugger: commands are read from a terminal, hence the pty. Key names are strings
("gamepads.1.up"). binddown/bindup only take effect while frames run. The screenshot binding
(ui.screenshot) writes blastem_*.png into $HOME, which is moved here.
"""
import argparse
import glob
import os
import pty
import re
import select
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
ROM = os.path.join(ROOT, "out", "rom.bin")
OUT = os.path.join(ROOT, "out", "emutest")


class Blastem:
    """The emulator in debugger mode, driven over a pty."""

    def __init__(self, rom=ROM):
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.execvp("blastem", ["blastem", rom, "-d"])
        self.read(3.0)
        self.held = set()

    def read(self, wait=0.6, prompt=False):
        """Collect output for wait seconds; with prompt=True return as soon as the
        debugger shows its "> " prompt again (wait is then the timeout)."""
        out, end = "", time.time() + wait
        while time.time() < end:
            ready, _, _ = select.select([self.fd], [], [], 0.05)
            if ready:
                try:
                    data = os.read(self.fd, 65536).decode("utf-8", "replace")
                except OSError:
                    break
                if not data:
                    break
                out += data
                if prompt and out.rstrip().endswith(">"):
                    break
                if not prompt:
                    end = max(end, time.time() + 0.25)
        return out

    def cmd_fast(self, text, timeout=5.0):
        """Send a command and wait only for the next prompt."""
        os.write(self.fd, (text + "\n").encode())
        return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", self.read(timeout, prompt=True))

    def frames(self, n, patient=60.0):
        out = self.cmd_fast(f"frames {n}", 3.0 + n / 30)
        waited = 0.0
        while not out.rstrip().endswith(">") and waited < patient:
            out += re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", self.read(5.0, prompt=True))
            waited += 5.0

    def keys(self, names):
        """Hold exactly these keys, e.g. {"gamepads.1.up"}."""
        names = set(names)
        for k in self.held - names:
            self.cmd_fast(f'bindup "{k}"')
        for k in names - self.held:
            self.cmd_fast(f'binddown "{k}"')
        self.held = names

    def press(self, name, n=3):
        self.keys({name})
        self.frames(n)
        self.keys(set())

    def shot(self, tag):
        home = os.path.expanduser("~")
        os.makedirs(OUT, exist_ok=True)
        before = set(glob.glob(home + "/blastem_*.png"))
        self.cmd_fast('binddown "ui.screenshot"')
        self.frames(3)
        self.cmd_fast('bindup "ui.screenshot"')
        self.frames(2)
        time.sleep(1.0)
        new = sorted(set(glob.glob(home + "/blastem_*.png")) - before)
        for extra in new[1:]:
            os.remove(extra)
        if not new:
            print(f"{tag}: no screenshot")
            return None
        dst = os.path.join(OUT, tag + ".png")
        os.replace(new[0], dst)
        print(f"{tag}: {dst}")
        return dst

    def close(self):
        try:
            os.write(self.fd, b"quit\n")
            time.sleep(0.4)
            os.kill(self.pid, 9)
        except OSError:
            pass


def act(b, key, settle=15):
    """One button press, then enough frames for the ROM to redraw the view (a redraw takes up
    to ~5 frames, see src/dungeon_view.c) and for the release to register -- consecutive
    presses of the same button without a gap can land inside one polled frame, and the ROM's
    edge-detection (pressed = joy & ~prevJoy) then never sees the second press."""
    b.press(key)
    b.frames(settle)


def create_hero(b, cls_down=0):
    """Drives the character-creation screen: cursor starts on Fighter (index 0);
    cls_down Down-presses move it (1=Rogue, 2=Mage), then Start confirms."""
    b.frames(30)
    for _ in range(cls_down):
        act(b, "gamepads.1.down", 6)
    act(b, "gamepads.1.start", 30)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scenario", choices=["create", "look", "tour", "room1"])
    ap.add_argument("--class", dest="cls", type=int, default=0, choices=[0, 1, 2],
                     help="0 fighter (default), 1 rogue, 2 mage")
    args = ap.parse_args()

    if not os.path.exists(ROM):
        raise SystemExit("build first: ./build.sh")

    b = Blastem()
    try:
        if args.scenario == "create":
            b.frames(30)
            b.shot("create_screen")
            create_hero(b, args.cls)
            b.shot("after_create")
            return

        if args.scenario == "look":
            # Room 1 (the Klonkammer, src/room1.c): spawn facing the larva tank, look around.
            create_hero(b, args.cls)
            b.shot("room1_spawn")              # (3,1) facing north, larva tank one step ahead
            for name in ("east", "south", "west"):
                act(b, "gamepads.1.right")     # turn clockwise
                b.shot(f"room1_look_{name}")
            return

        if args.scenario == "tour":
            # Views from the middle and the corners of Room 1 (interior x 1-6, y 1-4): every wall
            # should be visible from everywhere, with side walls, corners and objects in place.
            create_hero(b, args.cls)
            act(b, "gamepads.1.down")          # back off the tank: (3,1) -> (3,2), still facing north
            b.shot("tour_center_n")
            for name in ("e", "s", "w"):
                act(b, "gamepads.1.right")
                b.shot(f"tour_center_{name}")
            act(b, "gamepads.1.up")            # facing west: (3,2) -> (2,2)
            act(b, "gamepads.1.left")          # west -> south
            act(b, "gamepads.1.up")            # (2,3)
            act(b, "gamepads.1.up")            # (2,4), south-west part of the room
            act(b, "gamepads.1.left")          # south -> east
            b.shot("tour_sw_e")                # looking along the south wall
            act(b, "gamepads.1.left")          # east -> north
            b.shot("tour_sw_n")                # looking diagonally across towards the tank
            return

        if args.scenario == "room1":
            # Walks up to and interacts with every object kind in Room 1: the larva tank's
            # skill-check branch, a one-shot loot pickup, and a door whose target room isn't
            # built yet (the "still sealed" stub).
            create_hero(b, args.cls)
            b.shot("r1_spawn")

            # --- larva tank (north wall, one step ahead) ---
            act(b, "gamepads.1.a", 10)
            b.shot("r1_larva_menu")            # 3-option textbox: REACH IN / INVESTIGATE / LEAVE
            act(b, "gamepads.1.down", 6)       # cursor -> INVESTIGATE [INT]
            b.shot("r1_larva_cursor")
            act(b, "gamepads.1.a", 90)         # confirm: runs the skill-check roll animation
            b.shot("r1_larva_rolling")
            b.frames(90)
            b.shot("r1_larva_result")          # result textbox behind the roll's pause
            act(b, "gamepads.1.a")             # dismiss
            b.shot("r1_larva_done")

            # --- walk to the mindflayer corpse (west wall, (0,2)) ---
            act(b, "gamepads.1.right")         # north -> east
            act(b, "gamepads.1.right")         # east -> south
            act(b, "gamepads.1.up")            # step south: (3,1) -> (3,2)
            act(b, "gamepads.1.right")         # south -> west
            act(b, "gamepads.1.up")            # step west: (3,2) -> (2,2)
            act(b, "gamepads.1.up")            # (2,2) -> (1,2), adjacent to the corpse
            b.shot("r1_at_corpse")
            act(b, "gamepads.1.a")
            b.shot("r1_corpse_loot")           # loot textbox + panel should show GOLD/GEM updated
            act(b, "gamepads.1.a")

            # --- walk to the door (west wall, (0,3)) ---
            act(b, "gamepads.1.left")          # west -> south
            act(b, "gamepads.1.up")            # step south: (1,2) -> (1,3)
            act(b, "gamepads.1.right")         # south -> west
            b.shot("r1_at_door")
            act(b, "gamepads.1.a")
            b.shot("r1_door_stub")             # "still sealed" -- ROOM_2 isn't registered yet
            act(b, "gamepads.1.a")
            b.shot("r1_panel_final")           # final panel state: gold/gem up
    finally:
        b.close()


if __name__ == "__main__":
    main()
