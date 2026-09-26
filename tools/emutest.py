#!/usr/bin/env python3
"""Drives the ROM in BlastEm's debugger to inspect it without a human -- same technique as
tools/emutest.py in the Wanderburg (megadriveplay) project: BlastEm's debugger (-d) runs frames,
simulates key presses and takes screenshots via its own UI hotkey, so no OS-level screen capture
is needed (and none is available in this sandbox).

    python3 tools/emutest.py create              # just the character creation screen
    python3 tools/emutest.py look                # Room 1: look around from the spawn point
    python3 tools/emutest.py tour                # Room 1: views from two opposite corners
    python3 tools/emutest.py title               # club logo, title screen, then the creation screen
    python3 tools/emutest.py portraits           # creation screen: all 9 hero portraits, then in game
    python3 tools/emutest.py room1               # Room 1: interact with every object
    python3 tools/emutest.py room2               # through the door: Room 2, Myrnath, back to Room 1
    python3 tools/emutest.py room3               # on to Room 3: Lae'zel joins, fight against 3 imps
    python3 tools/emutest.py room45              # through Room 3 to Rooms 4 and 5: rune, Schattenherz
    python3 tools/emutest.py room6               # the bridge: sneak past to the transponder, the ending
    python3 tools/emutest.py zhalk               # the bridge: walk up to Zhalk and fight him
    python3 tools/emutest.py crash               # the bridge: dawdle until the countdown runs out
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


def skip_title(b):
    """Past the club logo and the title screen (START each) onto the creation screen. Booting takes
    a while (the XGM2 sound driver loads first), so wait before pressing."""
    b.frames(150)
    act(b, "gamepads.1.start", 60)          # skips the logo intro
    act(b, "gamepads.1.start", 30)          # the title


def create_hero(b, cls_down=0):
    """Drives the character-creation screen: cursor starts on Fighter (index 0);
    cls_down Down-presses move it (1=Rogue, 2=Mage), then Start confirms."""
    skip_title(b)
    for _ in range(cls_down):
        act(b, "gamepads.1.down", 6)
    act(b, "gamepads.1.start", 30)


def start_game(b, cls_down=0):
    """Creates the hero and dismisses Room 1's two intro textboxes."""
    create_hero(b, cls_down)
    act(b, "gamepads.1.a")
    act(b, "gamepads.1.a")


def to_room3(b, cls_down=0):
    """New game, straight through Rooms 1 and 2 (Myrnath left alone) to Room 3's door."""
    start_game(b, cls_down)
    act(b, "gamepads.1.right")                 # south -> west
    walk(b, 2)                                 # (1,3)
    act(b, "gamepads.1.right")                 # west -> north
    walk(b, 2)                                 # (1,1)
    act(b, "gamepads.1.left")                  # north -> west, door to Room 2
    act(b, "gamepads.1.a", 20)
    act(b, "gamepads.1.a")                     # Room 2 intro
    act(b, "gamepads.1.right")                 # north -> east
    walk(b, 1)                                 # (5,6)
    act(b, "gamepads.1.left")                  # east -> north
    walk(b, 5)                                 # (5,1)
    act(b, "gamepads.1.left")                  # north -> west
    walk(b, 1)                                 # (4,1)
    act(b, "gamepads.1.right")                 # west -> north, door to Room 3
    act(b, "gamepads.1.a", 20)


def to_room6(b, cls_down=0):
    """New game, through Room 3's fight and Room 4, the rune from Room 5, Schattenherz freed, then
    through the gate onto the bridge (its intro still showing)."""
    to_room3(b, cls_down)
    for _ in range(9):                         # Lae'zel's scene, the imps' entrance
        act(b, "gamepads.1.a", 40)
    b.frames(150)
    for _ in range(40):                        # the fight
        act(b, "gamepads.1.a", 45)
    walk(b, 7)                                 # (2,1)
    act(b, "gamepads.1.a", 20)                 # Room 4
    act(b, "gamepads.1.a")                     # intro
    act(b, "gamepads.1.right")                 # north -> east
    walk(b, 2)                                 # (6,7)
    act(b, "gamepads.1.left")                  # east -> north
    walk(b, 3)                                 # (6,4), past the pod at (7,6)
    act(b, "gamepads.1.right")                 # north -> east
    walk(b, 1)                                 # (7,4), passage to Room 5 ahead
    act(b, "gamepads.1.a", 20)
    act(b, "gamepads.1.a")
    act(b, "gamepads.1.a")                     # Room 5 intro
    walk(b, 1)                                 # (2,2)
    act(b, "gamepads.1.right")                 # east -> south
    walk(b, 1)                                 # (2,3)
    act(b, "gamepads.1.left")                  # south -> east, the cleric
    act(b, "gamepads.1.a")
    act(b, "gamepads.1.a")                     # rune + key
    act(b, "gamepads.1.left")                  # east -> north
    walk(b, 1)                                 # (2,2)
    act(b, "gamepads.1.left")                  # north -> west
    walk(b, 1)                                 # (1,2)
    act(b, "gamepads.1.a", 20)                 # back to Room 4, (7,4) facing west
    act(b, "gamepads.1.right")                 # west -> north
    walk(b, 1)                                 # (7,3)
    act(b, "gamepads.1.left")                  # north -> west
    walk(b, 4)                                 # (3,3)
    act(b, "gamepads.1.a")                     # pod console
    act(b, "gamepads.1.a", 20)                 # Rune einsetzen
    for _ in range(4):                         # Puff!, her thanks, joining
        act(b, "gamepads.1.a", 40)
    act(b, "gamepads.1.right")                 # west -> north
    walk(b, 1)                                 # (3,2); a pod stands at (3,1)
    act(b, "gamepads.1.right")                 # north -> east
    walk(b, 1)                                 # (4,2)
    act(b, "gamepads.1.left")                  # east -> north
    walk(b, 1)                                 # (4,1), the gate ahead
    act(b, "gamepads.1.a", 30)                 # onto the bridge


def walk(b, n):
    for _ in range(n):
        act(b, "gamepads.1.up")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scenario", choices=["title", "create", "portraits", "look", "tour", "room1", "room2", "room3", "room45", "room6", "zhalk", "crash"])
    ap.add_argument("--class", dest="cls", type=int, default=0, choices=[0, 1, 2],
                     help="0 fighter (default), 1 rogue, 2 mage")
    args = ap.parse_args()

    if not os.path.exists(ROM):
        raise SystemExit("build first: ./build.sh")

    b = Blastem()
    try:
        if args.scenario == "create":
            skip_title(b)
            b.shot("create_screen")
            create_hero(b, args.cls)
            b.shot("after_create")
            return

        if args.scenario == "title":
            b.frames(60)
            b.shot("intro_sweep")               # the club logo sweeping in
            b.frames(120)
            b.shot("intro_logo")
            b.frames(150)                       # the intro ends by itself
            b.shot("title")
            act(b, "gamepads.1.start", 30)
            b.shot("title_to_create")
            return

        if args.scenario == "portraits":
            # Creation screen: every class with each of its three portraits (right cycles them),
            # then start as the last one (mage, portrait 3) to see its avatar in the panel.
            skip_title(b)
            for cls in range(3):
                for n in range(3):
                    b.shot(f"portrait_{cls}_{n}")
                    act(b, "gamepads.1.right", 8)
                act(b, "gamepads.1.down", 8)     # next class (portrait stays at 1 after 3 rights)
            act(b, "gamepads.1.up", 8)           # back to the mage
            act(b, "gamepads.1.left", 8)         # portrait 3
            b.shot("portrait_chosen")
            act(b, "gamepads.1.start", 30)
            b.shot("portrait_in_game")           # Room 1 intro, avatar in the panel
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
            b.shot("r1_equip_ask")             # "Gleich anlegen?"
            act(b, "gamepads.1.a", 20)         # Ja: the equipment screen
            b.shot("r1_equip_screen")
            act(b, "gamepads.1.a")             # slot Waffe
            b.shot("r1_equip_pick")
            act(b, "gamepads.1.a")             # the first candidate
            for _ in range(2):                 # Rüstung, then Schild
                act(b, "gamepads.1.down", 8)
                act(b, "gamepads.1.a")
                act(b, "gamepads.1.a")
            b.shot("r1_equipped")              # AC and damage from the gear
            act(b, "gamepads.1.b", 20)
            b.shot("r1_chest_open")            # opened chest, panel: potion, backpack

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
            # check r2_check_result), "Wir" joins, the lore objects, then back through the door
            # to Room 1.
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

            # --- lectern, (2,5) ---
            act(b, "gamepads.1.left")          # north -> west
            walk(b, 1)                         # (3,4)
            act(b, "gamepads.1.left")          # west -> south
            walk(b, 1)                         # (3,5)
            act(b, "gamepads.1.right")         # south -> west
            act(b, "gamepads.1.a")
            b.shot("r2_lectern")
            act(b, "gamepads.1.a")
            b.shot("r2_lectern2")
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

            # --- past the exit to Room 3, north wall (4,0) ---
            act(b, "gamepads.1.right")         # west -> north
            walk(b, 1)                         # (1,1)
            act(b, "gamepads.1.right")         # north -> east
            walk(b, 3)                         # (4,1)
            act(b, "gamepads.1.left")          # east -> north
            b.shot("r2_at_exit")               # the door to Room 3: see the "room3" scenario

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

        if args.scenario == "room3":
            # Room 1 -> Room 2 (Myrnath left alone) -> Room 3: the ambush scene, Lae'zel joins,
            # the imps close in, the fight. The fight is dice-driven: A is pressed repeatedly
            # (Angriff, first target), screenshots show how it went.
            start_game(b, args.cls)
            act(b, "gamepads.1.right")         # south -> west
            walk(b, 2)                         # (1,3)
            act(b, "gamepads.1.right")         # west -> north
            walk(b, 2)                         # (1,1)
            act(b, "gamepads.1.left")          # north -> west, door to Room 2
            act(b, "gamepads.1.a", 20)
            act(b, "gamepads.1.a")             # Room 2 intro
            act(b, "gamepads.1.right")         # north -> east
            walk(b, 1)                         # (5,6)
            act(b, "gamepads.1.left")          # east -> north
            walk(b, 5)                         # (5,1)
            act(b, "gamepads.1.left")          # north -> west
            walk(b, 1)                         # (4,1)
            act(b, "gamepads.1.right")         # west -> north, door to Room 3
            act(b, "gamepads.1.a", 20)
            b.shot("r3_arrive")                # "Wind heult durch einen Riss..."
            act(b, "gamepads.1.a")
            act(b, "gamepads.1.a", 40)         # "Da! Über dir..." -> Lae'zel lands
            b.shot("r3_laezel")
            act(b, "gamepads.1.a")
            b.shot("r3_laezel_menu")
            act(b, "gamepads.1.a")             # "Gemeinsam kämpfen!"
            act(b, "gamepads.1.a")             # "Erst schlagen wir uns..."
            b.shot("r3_joined")                # panel: LAE'ZEL
            act(b, "gamepads.1.a")
            b.shot("r3_imps")                  # imps revealed in the corridor
            act(b, "gamepads.1.a", 150)        # they close in -> fight starts
            b.shot("r3_fight_start")
            for i in range(40):
                act(b, "gamepads.1.a", 45)
                if i % 3 == 2:
                    b.shot(f"r3_fight_{i:02d}")
            b.shot("r3_after")

        if args.scenario == "room45":
            # Straight through Rooms 1-3 (fight by pressing A), then Room 4: button 3, the empty
            # socket, Schattenherz knocking; Room 5: cleric (rune + key), chest, the
            # transformation; back to Room 4 to free Schattenherz.
            to_room3(b, args.cls)
            for _ in range(7):                 # Lae'zel's scene
                act(b, "gamepads.1.a", 40)
            b.frames(150)                      # imps close in
            for _ in range(40):                # the fight
                act(b, "gamepads.1.a", 45)
            b.shot("r45_after_fight")
            walk(b, 7)                         # (2,1)
            act(b, "gamepads.1.a", 20)         # door to Room 4
            b.shot("r4_arrive")
            act(b, "gamepads.1.a")
            b.shot("r4_view")

            walk(b, 2)                         # (4,5), button console ahead
            act(b, "gamepads.1.a", 10)
            b.shot("r4_buttons")
            act(b, "gamepads.1.down", 6)
            act(b, "gamepads.1.down", 6)       # Taste 3
            act(b, "gamepads.1.a", 20)
            b.shot("r4_button3")
            act(b, "gamepads.1.a")

            act(b, "gamepads.1.left")          # north -> west
            walk(b, 1)                         # (3,5)
            act(b, "gamepads.1.right")         # west -> north
            walk(b, 2)                         # (3,3)
            act(b, "gamepads.1.left")          # north -> west, pod console
            act(b, "gamepads.1.a")
            b.shot("r4_socket_empty")
            act(b, "gamepads.1.a")
            act(b, "gamepads.1.right")         # west -> north
            walk(b, 1)                         # (3,2)
            act(b, "gamepads.1.left")          # north -> west
            walk(b, 2)                         # (1,2)
            act(b, "gamepads.1.left")          # west -> south, Schattenherz's pod
            act(b, "gamepads.1.a", 30)
            b.shot("r4_shadowheart_pod")
            act(b, "gamepads.1.a")
            act(b, "gamepads.1.a")

            act(b, "gamepads.1.left")          # south -> east
            walk(b, 6)                         # (7,2)
            act(b, "gamepads.1.right")         # east -> south
            walk(b, 2)                         # (7,4)
            act(b, "gamepads.1.left")          # south -> east, passage to Room 5
            act(b, "gamepads.1.a", 20)
            b.shot("r5_arrive")
            act(b, "gamepads.1.a")
            act(b, "gamepads.1.a")
            b.shot("r5_view")

            walk(b, 1)                         # (2,2)
            act(b, "gamepads.1.right")         # east -> south
            walk(b, 1)                         # (2,3)
            act(b, "gamepads.1.left")          # south -> east, the cleric
            act(b, "gamepads.1.a")
            b.shot("r5_cleric")                # rune + key, panel shows both
            act(b, "gamepads.1.a")
            act(b, "gamepads.1.left")          # east -> north
            walk(b, 1)                         # (2,2)
            act(b, "gamepads.1.right")         # north -> east
            walk(b, 2)                         # (4,2), the chest ahead
            act(b, "gamepads.1.a")
            b.shot("r5_chest")
            act(b, "gamepads.1.a")
            b.shot("r5_chest_open")
            act(b, "gamepads.1.left")          # east -> north, the switch
            act(b, "gamepads.1.a")
            b.shot("r5_switch")
            act(b, "gamepads.1.a", 20)         # Taste 1: Auslösen
            act(b, "gamepads.1.a", 180)        # "Lila Nebel..." -> transformation (~2 s)
            b.shot("r5_transformed")
            act(b, "gamepads.1.a")
            act(b, "gamepads.1.left")          # north -> west
            b.shot("r5_pod_flayer_side")
            walk(b, 1)                         # (3,2)
            act(b, "gamepads.1.right")         # west -> north, the pod
            b.shot("r5_pod_flayer")
            act(b, "gamepads.1.left")          # north -> west
            walk(b, 2)                         # (1,2)
            act(b, "gamepads.1.a", 20)         # door back to Room 4 -> (7,4) facing west
            b.shot("r4_back")

            act(b, "gamepads.1.right")         # west -> north
            walk(b, 1)                         # (7,3)
            act(b, "gamepads.1.left")          # north -> west
            walk(b, 4)                         # (3,3), past the button console at (4,4)
            act(b, "gamepads.1.a")
            b.shot("r4_socket_menu")
            act(b, "gamepads.1.a", 20)         # Rune einsetzen
            b.shot("r4_pod_opens")
            act(b, "gamepads.1.a", 30)
            b.shot("r4_shadowheart")
            act(b, "gamepads.1.a")
            act(b, "gamepads.1.a")
            b.shot("r4_joined")
            act(b, "gamepads.1.a")
            b.shot("r45_final")

        if args.scenario in ("room6", "zhalk", "crash"):
            to_room6(b, args.cls)
            b.shot("r6_arrive")
            for i in range(5):                 # intro: bridge, mind flayer (2), Zhalk, countdown
                act(b, "gamepads.1.a", 40)
                b.shot(f"r6_intro{i}")
            b.shot("r6_start")                 # ABSTURZ: 10 in the panel

        if args.scenario == "room6":
            # Sneak along the east lane past both groups (they only close in within 2 cells).
            act(b, "gamepads.1.right")         # north -> east
            walk(b, 3)                         # (7,12)
            act(b, "gamepads.1.left")          # east -> north
            walk(b, 10)                        # (7,2)
            b.shot("r6_lane")
            act(b, "gamepads.1.left")          # north -> west
            walk(b, 1)                         # (6,2)
            act(b, "gamepads.1.right")         # west -> north
            walk(b, 1)                         # (6,1): step 15 = round 5, the cambions
            b.shot("r6_cambions")
            act(b, "gamepads.1.a")
            act(b, "gamepads.1.left")          # north -> west
            walk(b, 1)                         # (5,1), the transponder ahead
            b.shot("r6_transponder")
            act(b, "gamepads.1.a", 10)
            b.shot("r6_transponder_menu")
            act(b, "gamepads.1.a", 20)         # Nervenstränge verbinden!
            b.shot("r6_end1")
            act(b, "gamepads.1.a", 150)
            b.shot("r6_end2")
            act(b, "gamepads.1.a", 200)
            b.shot("r6_end3")
            act(b, "gamepads.1.a", 30)
            b.shot("r6_end_screen")

        if args.scenario == "zhalk":
            act(b, "gamepads.1.left")          # north -> west
            walk(b, 3)                         # (1,12)
            act(b, "gamepads.1.right")         # west -> north
            walk(b, 5)                         # (1,7): next to Zhalk, the fight starts
            b.frames(60)
            b.shot("zhalk_fight")
            for i in range(60):
                act(b, "gamepads.1.a", 45)
                if i % 6 == 5:
                    b.shot(f"zhalk_{i:02d}")
            b.shot("zhalk_after")

        if args.scenario == "crash":
            act(b, "gamepads.1.right")         # north -> east
            for i in range(40):                # pace back and forth; A through fights and boxes
                act(b, "gamepads.1.up", 10)
                act(b, "gamepads.1.down", 10)
                act(b, "gamepads.1.a", 30)
                if i % 8 == 7:
                    b.shot(f"crash_{i:02d}")
            b.shot("crash_end")
    finally:
        b.close()


if __name__ == "__main__":
    main()
