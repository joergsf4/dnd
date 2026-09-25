#!/usr/bin/env python3
"""Drives the ROM in BlastEm's debugger to inspect it without a human -- same technique as
tools/emutest.py in the Wanderburg (megadriveplay) project: BlastEm's debugger (-d) runs frames,
simulates key presses and takes screenshots via its own UI hotkey, so no OS-level screen capture
is needed (and none is available in this sandbox).

    python3 tools/emutest.py create              # just the character creation screen
    python3 tools/emutest.py look                # Room 1: look around from the spawn point
    python3 tools/emutest.py tour                # Room 1: views from two opposite corners
    python3 tools/emutest.py room1               # Room 1: interact with every object
    python3 tools/emutest.py room2               # through the door: Room 2, Myrnath, back to Room 1
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


def start_game(b, cls_down=0):
    """Creates the hero and dismisses Room 1's two intro textboxes."""
    create_hero(b, cls_down)
    act(b, "gamepads.1.a")
    act(b, "gamepads.1.a")


def walk(b, n):
    for _ in range(n):
        act(b, "gamepads.1.up")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scenario", choices=["create", "look", "tour", "room1", "room2"])
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
            # Room 1 (the Klonkammer, src/room1.c): spawn in front of the open pod, look around.
            start_game(b, args.cls)
            b.shot("room1_spawn")              # (3,3) facing south, larva pool two cells ahead
            for name in ("west", "north", "east"):
                act(b, "gamepads.1.right")     # turn clockwise
                b.shot(f"room1_look_{name}")   # north: the open pod right behind the start
            return

        if args.scenario == "tour":
            # Views from two opposite corners of Room 1 (interior x 1-6, y 1-5): walls from
            # everywhere, props standing free in the room and hidden behind nearer walls.
            start_game(b, args.cls)
            act(b, "gamepads.1.right")         # south -> west
            walk(b, 2)                         # (1,3)
            act(b, "gamepads.1.right")         # west -> north
            walk(b, 2)                         # (1,1), north-west corner
            act(b, "gamepads.1.right")
            b.shot("tour_nw_e")                # broken pod right ahead, chest far away
            act(b, "gamepads.1.right")
            b.shot("tour_nw_s")                # down the west side: broken pod
            walk(b, 2)                         # (1,3)
            act(b, "gamepads.1.left")          # south -> east
            walk(b, 4)                         # (5,3), shrine ahead
            act(b, "gamepads.1.right")         # east -> south
            walk(b, 1)                         # (5,4)
            act(b, "gamepads.1.left")          # south -> east
            walk(b, 1)                         # (6,4), south-east corner
            act(b, "gamepads.1.right")
            b.shot("tour_se_s")                # corpse right ahead
            act(b, "gamepads.1.right")
            b.shot("tour_se_w")                # across the room: broken pods, pool
            act(b, "gamepads.1.right")
            b.shot("tour_se_n")                # shrine ahead, chest behind it
            return

        if args.scenario == "room1":
            # Plays through Room 1: intro, both larva-pool branches (INT check, then reaching
            # in), corpse, shrine, chest, a broken pod and the open pod.
            create_hero(b, args.cls)
            b.shot("r1_intro1")
            act(b, "gamepads.1.a")
            b.shot("r1_intro2")
            act(b, "gamepads.1.a")
            b.shot("r1_spawn")

            # --- larva pool, (3,5) ---
            walk(b, 1)                         # (3,4)
            act(b, "gamepads.1.a", 10)
            b.shot("r1_pool_menu")             # Hineinfassen / Untersuchen [INT] / Weggehen
            act(b, "gamepads.1.down", 6)       # cursor -> Untersuchen [INT]
            act(b, "gamepads.1.a", 90)         # runs the skill-check roll animation
            b.shot("r1_pool_rolling")
            b.frames(90)
            b.shot("r1_pool_result")           # "Gefahr erkannt" or "nichts Besonderes"
            act(b, "gamepads.1.a")
            act(b, "gamepads.1.a", 10)
            b.shot("r1_pool_menu2")            # marked variant if the check succeeded
            act(b, "gamepads.1.a")             # Hineinfassen
            b.shot("r1_pool_boom")             # -3 KP, panel updated
            act(b, "gamepads.1.a")
            b.shot("r1_pool_broken")           # burst pool

            # --- corpse, (6,5) ---
            act(b, "gamepads.1.left")          # south -> east
            walk(b, 3)                         # (6,4)
            act(b, "gamepads.1.right")         # east -> south
            act(b, "gamepads.1.a")
            b.shot("r1_corpse")
            act(b, "gamepads.1.a")

            # --- restoration station, (6,3) ---
            act(b, "gamepads.1.left")          # south -> east
            act(b, "gamepads.1.left")          # east -> north
            b.shot("r1_at_shrine")
            act(b, "gamepads.1.a")
            b.shot("r1_shrine")                # KP back to full
            act(b, "gamepads.1.a")

            # --- chest, (6,1) ---
            act(b, "gamepads.1.left")          # north -> west
            walk(b, 1)                         # (5,4)
            act(b, "gamepads.1.right")         # west -> north
            walk(b, 2)                         # (5,2)
            act(b, "gamepads.1.right")         # north -> east
            walk(b, 1)                         # (6,2)
            act(b, "gamepads.1.left")          # east -> north
            act(b, "gamepads.1.a")
            b.shot("r1_chest")
            act(b, "gamepads.1.a")
            b.shot("r1_chest_open")            # opened chest, panel: potion + gear

            # --- past the door, west wall (0,1) ---
            act(b, "gamepads.1.left")          # north -> west
            walk(b, 1)                         # (5,2)
            act(b, "gamepads.1.left")          # west -> south
            walk(b, 1)                         # (5,3)
            act(b, "gamepads.1.right")         # south -> west
            walk(b, 4)                         # (1,3)
            act(b, "gamepads.1.right")         # west -> north
            walk(b, 2)                         # (1,1)
            act(b, "gamepads.1.left")          # north -> west
            b.shot("r1_at_door")               # the door itself leads to Room 2: see "room2"

            # --- broken pod, (2,1) ---
            act(b, "gamepads.1.right")         # west -> north
            act(b, "gamepads.1.right")         # north -> east
            act(b, "gamepads.1.a")
            b.shot("r1_pod_broken")
            act(b, "gamepads.1.a")

            # --- the open pod, (3,2) ---
            act(b, "gamepads.1.right")         # east -> south
            walk(b, 1)                         # (1,2)
            act(b, "gamepads.1.left")          # south -> east
            walk(b, 1)                         # (2,2)
            act(b, "gamepads.1.a")
            b.shot("r1_pod_open")
            act(b, "gamepads.1.a")
            b.shot("r1_final")

        if args.scenario == "room2":
            # Room 1 -> door -> Room 2: Myrnath (STR check; the path below assumes it succeeds,
            # check r2_check_result), "Wir" joins, the lore objects, the shut exit to Room 3,
            # then back through the door to Room 1.
            start_game(b, args.cls)
            act(b, "gamepads.1.right")         # south -> west
            walk(b, 2)                         # (1,3)
            act(b, "gamepads.1.right")         # west -> north
            walk(b, 2)                         # (1,1)
            act(b, "gamepads.1.left")          # north -> west, the door
            act(b, "gamepads.1.a", 20)
            b.shot("r2_intro")                 # Room 2, first-visit text
            act(b, "gamepads.1.a")
            b.shot("r2_arrive")                # (4,6) facing north, Myrnath in the middle

            # --- Myrnath, (4,3) ---
            walk(b, 2)                         # (4,4)
            act(b, "gamepads.1.a", 10)
            b.shot("r2_myrnath_menu")
            act(b, "gamepads.1.a", 90)         # Schädel aufbrechen [STÄ]
            b.frames(90)
            b.shot("r2_check_result")          # "... auf vier Beinen!" (or the brain died)
            act(b, "gamepads.1.a")
            b.shot("r2_recruit_menu")
            act(b, "gamepads.1.down", 6)       # Als Begleiter aufnehmen
            act(b, "gamepads.1.a")
            b.shot("r2_joined")                # panel: WIR in slot 2
            act(b, "gamepads.1.a")
            b.shot("r2_myrnath_dead")

            # --- desk, (2,5) ---
            act(b, "gamepads.1.left")          # north -> west
            walk(b, 1)                         # (3,4)
            act(b, "gamepads.1.left")          # west -> south
            walk(b, 1)                         # (3,5)
            act(b, "gamepads.1.right")         # south -> west
            act(b, "gamepads.1.a")
            b.shot("r2_desk")
            act(b, "gamepads.1.a")
            b.shot("r2_desk2")
            act(b, "gamepads.1.a")

            # --- vivisection table, (2,2) ---
            act(b, "gamepads.1.right")         # west -> north
            walk(b, 3)                         # (3,2)
            act(b, "gamepads.1.left")          # north -> west
            act(b, "gamepads.1.a")
            b.shot("r2_table")
            act(b, "gamepads.1.a")

            # --- tablet, west wall (0,2) ---
            act(b, "gamepads.1.right")         # west -> north
            walk(b, 1)                         # (3,1)
            act(b, "gamepads.1.left")          # north -> west
            walk(b, 2)                         # (1,1)
            act(b, "gamepads.1.left")          # west -> south
            walk(b, 1)                         # (1,2)
            act(b, "gamepads.1.right")         # south -> west
            act(b, "gamepads.1.a")
            b.shot("r2_tablet")
            act(b, "gamepads.1.a")

            # --- exit to Room 3, north wall (4,0) ---
            act(b, "gamepads.1.right")         # west -> north
            walk(b, 1)                         # (1,1)
            act(b, "gamepads.1.right")         # north -> east
            walk(b, 3)                         # (4,1)
            act(b, "gamepads.1.left")          # east -> north
            act(b, "gamepads.1.a")
            b.shot("r2_exit_shut")
            act(b, "gamepads.1.a")

            # --- back to Room 1 through the south door ---
            act(b, "gamepads.1.right")         # north -> east
            walk(b, 1)                         # (5,1)
            act(b, "gamepads.1.right")         # east -> south
            walk(b, 5)                         # (5,6)
            act(b, "gamepads.1.right")         # south -> west
            walk(b, 1)                         # (4,6)
            act(b, "gamepads.1.left")          # west -> south
            b.shot("r2_at_door_back")
            act(b, "gamepads.1.a", 20)
            b.shot("r2_back_in_room1")         # (1,1) facing east, no intro again
    finally:
        b.close()


if __name__ == "__main__":
    main()
