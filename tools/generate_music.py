#!/usr/bin/env python3
"""Composes the music of the Nautiloid prologue as VGM files for the SN76489 (the Mega Drive's PSG)
in res/music/. rescomp turns each .vgm into an XGM2 song (`XGM2 name "music/x.vgm"`, see
res/resources.res); src/sfx.c plays them. The framework (Track, write_vgm, note strings) comes
from the Wanderburg project; the songs are new, except the title theme.

    title    Baldur's Gate's opening theme, imported from a MIDI (res/music/src/, a fan arrangement
             for guitar and recorder from vgmusic.com). The composition is not ours: fine for this
             private project, to be replaced by an own piece before anything is published.
    dungeon  eerie: a pulsing low drone, a sparse minor melody with an echo, a heartbeat
    combat   driving D minor riff with drums
    bridge   hectic E minor, fast, for the countdown on the bridge
    ending   slow and solemn, from minor into major

The PSG has three square-wave voices and one noise voice:
    voice 0  melody     voice 1  harmony (arpeggios / echo)     voice 2  bass     noise  drums
The songs are written as note strings: "A4:2 C5:1 R:1" = note name and octave, then the length in
eighth notes; R is a rest, `#` after the letter sharpens (G#5).

Usage:
    generate_music.py            write the VGM files
"""
import math
import os
import struct

PSG_CLOCK = 3579545
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "res", "music")
SAMPLES_PER_TICK = 735                      # one video frame at 44.1 kHz (60 Hz)
NOTES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi(name):
    n = NOTES[name[0]]
    i = 1
    if name[i] == "#":
        n += 1
        i += 1
    octave = int(name[i:])
    return 12 * (octave + 1) + n


def parse(text, eighth):
    """'A4:2 R:1' -> [(midi or None, ticks)]"""
    out = []
    for tok in text.split():
        name, length = tok.split(":")
        out.append((None if name == "R" else midi(name), int(float(length) * eighth)))
    return out


def freq(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def divider(m):
    f = freq(m)
    while PSG_CLOCK / (32 * f) > 1023:      # below the PSG's range: one octave up
        f *= 2
    return max(1, int(round(PSG_CLOCK / (32 * f))))


class Track:
    """Per-tick state of the four voices, then written out as PSG commands."""

    def __init__(self):
        self.voice = [[], [], []]           # per tick: (divider, attenuation) or None
        self.drum = []                      # per tick: (noise control byte, attenuation) or None

    def add_voice(self, v, notes, vol=2, fall=1.0, staccato=1):
        ticks = []
        for m, length in notes:
            for t in range(length):
                if m is None or t >= length - staccato:
                    ticks.append(None)
                else:
                    ticks.append((divider(m), min(15, int(vol + t * fall))))
        self.voice[v] = ticks

    def add_voice_sections(self, v, sections, fall=1.0, staccato=1):
        """Like add_voice, but the volume can change between sections: [(notes, vol), ...]."""
        ticks = []
        for notes, vol in sections:
            self.add_voice(v, notes, vol=vol, fall=fall, staccato=staccato)
            ticks += self.voice[v]
        self.voice[v] = ticks

    def add_drums(self, pattern, eighth):
        """pattern: one string per eighth note, e.g. 'k h s h', k = kick, s = snare, h = hat, . = none."""
        ticks = []
        for c in pattern.split():
            # (noise control: bit 2 = white noise, bits 0-1 = pitch, start attenuation, length in ticks)
            hit = {"k": (0b110, 1, 5), "s": (0b101, 3, 6), "h": (0b100, 8, 3)}.get(c)
            for t in range(eighth):
                if hit and t < hit[2]:
                    ticks.append((hit[0], min(15, hit[1] + t * 2)))
                else:
                    ticks.append(None)
        self.drum = ticks

    def length(self):
        return max(len(v) for v in self.voice + [self.drum])

    def render(self):
        n = self.length()
        data = bytearray()
        cur_div = [None] * 3
        cur_att = [15, 15, 15, 15]
        cur_noise = None
        for tick in range(n):
            for v in range(3):
                st = self.voice[v][tick] if tick < len(self.voice[v]) else None
                if st is None:
                    att = 15
                else:
                    d, att = st
                    if d != cur_div[v]:
                        data += bytes([0x50, 0x80 | (v << 5) | (d & 0x0F), 0x50, (d >> 4) & 0x3F])
                        cur_div[v] = d
                if att != cur_att[v]:
                    data += bytes([0x50, 0x90 | (v << 5) | att])
                    cur_att[v] = att
            st = self.drum[tick] if tick < len(self.drum) else None
            att = 15 if st is None else st[1]
            if st is not None and st[0] != cur_noise:
                data += bytes([0x50, 0xE0 | (st[0] & 0x07)])
                cur_noise = st[0]
            if att != cur_att[3]:
                data += bytes([0x50, 0xF0 | att])
                cur_att[3] = att
            data.append(0x62)               # wait one frame
        data += bytes([0x50, 0x9F, 0x50, 0xBF, 0x50, 0xDF, 0x50, 0xFF])   # silence at the loop point
        data.append(0x66)
        return bytes(data), n * SAMPLES_PER_TICK


def write_vgm(path, track):
    data, total = track.render()
    header = bytearray(0x40)
    header[0:4] = b"Vgm "
    struct.pack_into("<I", header, 0x08, 0x150)
    struct.pack_into("<I", header, 0x0C, PSG_CLOCK)
    struct.pack_into("<I", header, 0x18, total)
    struct.pack_into("<I", header, 0x1C, 0x40 - 0x1C)          # loop back to the start of the data
    struct.pack_into("<I", header, 0x20, total)
    struct.pack_into("<I", header, 0x24, 60)
    struct.pack_into("<H", header, 0x28, 0x0009)
    header[0x2A] = 16
    struct.pack_into("<I", header, 0x2C, 7670453)              # YM2612 clock (unused, marks a Mega Drive)
    struct.pack_into("<I", header, 0x34, 0x40 - 0x34)
    blob = bytes(header) + data
    blob = blob[:4] + struct.pack("<I", len(blob) - 4) + blob[8:]
    with open(path, "wb") as f:
        f.write(blob)
    return len(blob), total / 44100


def chord_arp(chords, eighth):
    """Arpeggio in eighths over one chord per bar: root, third, fifth, third, ..."""
    out = []
    for c in chords:
        a, b, d = c
        out += [(a, 1), (b, 1), (d, 1), (b, 1), (a, 1), (b, 1), (d, 1), (b, 1)]
    return [(m, l * eighth) for m, l in out]


def m(*names):
    return tuple(midi(n) for n in names)




# ------------------------------------------------------------------ MIDI import (the title theme)

SRC_DIR = os.path.join(OUT_DIR, "src")


def varlen(data, p):
    v = 0
    while True:
        b = data[p]
        p += 1
        v = (v << 7) | (b & 0x7F)
        if not b & 0x80:
            return v, p


def read_midi(path):
    """A minimal type-0/1 MIDI reader: (ticks per quarter, tempo map, [notes per track]) with a note
    being (start tick, end tick, pitch). Tracks without notes are dropped."""
    data = open(path, "rb").read()
    assert data[:4] == b"MThd", "not a MIDI file"
    _fmt, ntrk, div = struct.unpack(">HHH", data[8:14])
    pos, tempos, tracks = 14, [(0, 500000)], []
    for _ in range(ntrk):
        assert data[pos:pos + 4] == b"MTrk"
        length = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        p, end, t, status, on, notes = pos + 8, pos + 8 + length, 0, 0, {}, []
        while p < end:
            delta, p = varlen(data, p)
            t += delta
            if data[p] & 0x80:
                status = data[p]
                p += 1
            if status == 0xFF:                                  # meta event
                kind = data[p]
                n, p = varlen(data, p + 1)
                if kind == 0x51:
                    tempos.append((t, int.from_bytes(data[p:p + 3], "big")))
                p += n
                continue
            if status in (0xF0, 0xF7):                          # sysex
                n, p = varlen(data, p)
                p += n
                continue
            hi = status & 0xF0
            if hi in (0x80, 0x90):
                note, vel = data[p], data[p + 1]
                p += 2
                if hi == 0x90 and vel:
                    on[note] = t
                elif note in on:
                    notes.append((on.pop(note), t, note))
            elif hi in (0xA0, 0xB0, 0xE0):
                p += 2
            else:                                               # 0xC0, 0xD0
                p += 1
        if notes:
            tracks.append(notes)
        pos = end
    return div, sorted(tempos), tracks


def frames_of(tick, div, tempos):
    """MIDI tick -> video frame (60 Hz), following the tempo map."""
    sec, last_t, last_tempo = 0.0, 0, tempos[0][1]
    for t, tempo in tempos:
        if t > tick:
            break
        sec += (t - last_t) / div * last_tempo / 1e6
        last_t, last_tempo = t, tempo
    sec += (tick - last_t) / div * last_tempo / 1e6
    return int(round(sec * 60))


def line(notes, div, tempos, total, pick):
    """A monophonic line from (possibly polyphonic) notes: per frame the highest (pick=max) or
    lowest (pick=min) sounding note, as [(pitch or None, frames)] with notes kept apart."""
    frame = [None] * total
    start = [False] * total
    for s, e, n in notes:
        fs, fe = frames_of(s, div, tempos), frames_of(e, div, tempos)
        for f in range(fs, min(fe, total)):
            if frame[f] is None or pick(frame[f], n) == n:
                if frame[f] != n:
                    start[f] = f == fs
                frame[f] = n
        if fs < total:
            start[fs] = True
    out = []
    for f in range(total):
        if out and out[-1][0] == frame[f] and not (start[f] and frame[f] is not None):
            out[-1] = (frame[f], out[-1][1] + 1)
        else:
            out.append((frame[f], 1))
    return out


def song_title():
    """Baldur's Gate's opening theme from res/music/src/baldurs_gate_opening.mid: the track with the
    fewest notes (recorder) is the melody, the other (guitar) gives the harmony (its top note) and
    the bass (its bottom note)."""
    div, tempos, tracks = read_midi(os.path.join(SRC_DIR, "baldurs_gate_opening.mid"))
    tracks.sort(key=len)                                    # the melody has the fewest notes
    melody, accomp = tracks[0], (tracks[-1] if len(tracks) > 1 else tracks[0])
    melody = [(st, en, n + 12) for st, en, n in melody]     # an octave up: clearer on the PSG
    bass = [(st, en, n - 12) for st, en, n in accomp]       # the guitar's bottom, an octave down
    total = max(frames_of(e, div, tempos) for tr in tracks for _, e, _ in tr) + 30
    t = Track()
    t.add_voice(0, line(melody, div, tempos, total, max), vol=2, fall=0.15)
    t.add_voice(1, line(accomp, div, tempos, total, max), vol=6, fall=0.2)
    t.add_voice(2, line(bass, div, tempos, total, min), vol=4, fall=0.15)
    return t


# ------------------------------------------------------------------ own songs

def song_dungeon():
    """Eerie: a slowly pulsing drone, a sparse A minor melody and its echo, a faint heartbeat."""
    e = 26
    mel = ("R:8 E5:4 F5:2 E5:2 C5:8 R:8 D5:4 E5:2 D5:2 B4:8 "
           "R:8 A4:4 C5:4 B4:4 G#4:4 A4:12 R:4")
    bass = []
    for root in ("A2", "A2", "F2", "F2", "D2", "E2", "A2", "A2"):
        bass += parse(f"{root}:3 {root}:1 R:4", e)
    t = Track()
    t.add_voice(0, parse(mel, e), vol=4, fall=0.12, staccato=2)
    t.add_voice(1, parse("R:2 " + mel.replace("A4:12 R:4", "A4:12 R:2"), e), vol=11, fall=0.1, staccato=2)
    t.add_voice(2, bass, vol=6, fall=0.1, staccato=4)
    t.add_drums(" ".join(["k . k . . . . ."] * 8), e)
    return t


def song_combat():
    """Driving: a D minor riff in the bass, an arpeggio above it, a fighting melody, drums."""
    e = 12
    riff = {"D": "D3:1 D3:1 D4:1 D3:1 C4:1 D3:1 A3:1 D3:1 ",
            "Bb": "A#2:1 A#2:1 A#3:1 A#2:1 A3:1 A#2:1 F3:1 A#2:1 ",
            "C": "C3:1 C3:1 C4:1 C3:1 A#3:1 C3:1 G3:1 C3:1 ",
            "A": "A2:1 A2:1 A3:1 A2:1 G3:1 A2:1 E3:1 A2:1 "}
    order = ["D", "D", "Bb", "C", "D", "D", "Bb", "A"] * 2
    lead = ("D5:2 F5:2 A5:3 G5:1 F5:2 E5:2 D5:4 C5:2 D5:2 E5:2 F5:2 E5:4 A4:4 "
            "A#4:2 D5:2 F5:2 A#5:2 A5:2 G5:2 F5:2 E5:2 D5:3 E5:1 F5:2 E5:2 C#5:8 "
            "A5:2 A5:1 G5:1 F5:2 A5:2 G5:2 F5:1 E5:1 D5:4 F5:2 F5:1 E5:1 D5:2 F5:2 E5:2 D5:1 C5:1 A4:4 "
            "A#4:2 C5:2 D5:2 F5:2 E5:2 F5:2 G5:2 A5:2 A5:4 G5:2 E5:2 D5:8")
    chords = {"D": m("D4", "F4", "A4"), "Bb": m("A#3", "D4", "F4"), "C": m("C4", "E4", "G4"), "A": m("A3", "C#4", "E4")}
    t = Track()
    t.add_voice(0, parse(lead, e), vol=2, fall=0.5)
    t.add_voice(1, chord_arp([chords[c] for c in order], e), vol=9, fall=0.5)
    t.add_voice(2, parse("".join(riff[c] for c in order), e), vol=3, fall=0.3)
    t.add_drums(" ".join(["k h s h k h s h"] * 16), e)
    return t


def song_bridge():
    """Hectic: E minor, fast, an alarm-like figure over a pounding bass -- the ship is falling."""
    e = 9
    riff1 = "E3:1 E3:1 E4:1 E3:1 G4:1 E3:1 F#4:1 E3:1 "
    riff2 = "C3:1 C3:1 C4:1 C3:1 D4:1 C3:1 B3:1 C3:1 "
    riff3 = "D3:1 D3:1 D4:1 D3:1 A3:1 D3:1 F#3:1 D3:1 "
    riff4 = "B2:1 B2:1 B3:1 B2:1 D#4:1 B2:1 F#3:1 B2:1 "
    alarm = "B5:1 E6:1 B5:1 E6:1 B5:1 E6:1 B5:1 E6:1 "
    lead = (alarm * 2 + "G5:2 F#5:2 E5:2 D5:2 E5:2 F#5:2 G5:2 A5:2 B5:4 A5:2 F#5:2 D#5:8 "
            + alarm * 2 + "C6:2 B5:2 A5:2 G5:2 F#5:2 G5:2 A5:2 F#5:2 E5:4 D#5:4 E5:8")
    t = Track()
    t.add_voice(0, parse(lead, e), vol=2, fall=0.6)
    t.add_voice(1, parse("R:4 " + lead.replace("E5:8", "E5:4"), e), vol=10, fall=0.6)
    t.add_voice(2, parse((riff1 + riff2 + riff3 + riff4) * 4, e), vol=3, fall=0.3)
    t.add_drums(" ".join(["k k s h k k s s"] * 16), e)
    return t


def song_ending():
    """Solemn: from A minor into C major -- the ship is down, the party alive."""
    e = 24
    mel = ("A4:4 C5:4 E5:4 D5:4 C5:4 B4:4 A4:8 "
           "F4:4 A4:4 C5:4 E5:4 D5:4 B4:4 G4:8 "
           "C5:4 E5:4 G5:8 F5:4 E5:4 D5:8 "
           "E5:4 D5:4 C5:4 B4:4 C5:16")
    chords = [m("A3", "C4", "E4"), m("A3", "C4", "E4"), m("F3", "A3", "C4"), m("G3", "B3", "D4"),
              m("C4", "E4", "G4"), m("F3", "A3", "C4"), m("G3", "B3", "D4"), m("C4", "E4", "G4")]
    bass = []
    for root in ("A2", "A2", "F2", "G2", "C3", "F2", "G2", "C3"):
        bass += parse(f"{root}:8", e)
    t = Track()
    t.add_voice(0, parse(mel, e), vol=3, fall=0.1, staccato=2)
    t.add_voice(1, chord_arp(chords, e), vol=10, fall=0.3)
    t.add_voice(2, bass, vol=5, fall=0.08, staccato=3)
    return t


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, fn in (("title", song_title), ("dungeon", song_dungeon), ("combat", song_combat),
                     ("bridge", song_bridge), ("ending", song_ending)):
        path = os.path.join(OUT_DIR, name + ".vgm")
        size, seconds = write_vgm(path, fn())
        print(f"wrote {os.path.relpath(path)}  {size} bytes, {seconds:.1f} s loop")


if __name__ == "__main__":
    main()
