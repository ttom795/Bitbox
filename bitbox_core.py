import numpy as np
import random, wave, math
SR = 32000
TAIL = int(SR * 2.5)
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
SCALES = {
    "Major": [0, 2, 4, 5, 7, 9, 11],
    "Natural Minor": [0, 2, 3, 5, 7, 8, 10],
    "Dorian": [0, 2, 3, 5, 7, 9, 10],
    "Phrygian": [0, 1, 3, 5, 7, 8, 10],
    "Lydian": [0, 2, 4, 6, 7, 9, 11],
    "Mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "Harmonic Minor": [0, 2, 3, 5, 7, 8, 11],
    "Pentatonic Major": [0, 2, 4, 7, 9],
    "Pentatonic Minor": [0, 3, 5, 7, 10],
    "Blues": [0, 3, 5, 6, 7, 10],
}
TIME_SIGS = {
    "4/4": [4, 4, 4, 4],
    "3/4": [4, 4, 4],
    "2/4": [4, 4],
    "6/8": [6, 6],
    "9/8": [6, 6, 6],
    "5/4": [4, 4, 4, 4, 4],
    "7/8": [4, 4, 6],
}
WAVES = ["random", "square", "pulse25", "pulse12", "triangle", "saw", "sine", "noise", "wavetable", "fm", "supersaw"]
KITS = ["8-bit", "punchy", "lofi"]
CHANNELS = ["Lead", "Counter", "Arp", "Bass", "Pad", "Drums"]
COLORS = {"Lead": "#f7768e", "Counter": "#e0af68", "Arp": "#9ece6a", "Bass": "#7dcfff", "Pad": "#bb9af7", "Drums": "#c0caf5"}
POOLS = {
    "Lead": ["pulse25", "square", "pulse12", "saw", "wavetable", "fm", "supersaw"],
    "Counter": ["square", "pulse12", "triangle", "fm", "wavetable"],
    "Arp": ["pulse12", "pulse25", "square", "wavetable", "fm"],
    "Bass": ["triangle", "square", "saw", "sine", "pulse25"],
    "Pad": ["triangle", "wavetable", "supersaw", "sine", "fm"],
}
DEFAULTS = {
    "Lead": dict(wave="pulse25", vol=0.8, pan=0.0, oct=0, a=0.005, d=0.15, s=0.6, r=0.08, vib=0.3),
    "Counter": dict(wave="square", vol=0.5, pan=0.4, oct=0, a=0.01, d=0.2, s=0.5, r=0.1, vib=0.2),
    "Arp": dict(wave="pulse12", vol=0.45, pan=-0.4, oct=0, a=0.002, d=0.1, s=0.3, r=0.05, vib=0.0),
    "Bass": dict(wave="triangle", vol=0.9, pan=0.0, oct=0, a=0.003, d=0.1, s=0.8, r=0.05, vib=0.0),
    "Pad": dict(wave="wavetable", vol=0.4, pan=-0.2, oct=0, a=0.25, d=0.4, s=0.7, r=0.4, vib=0.4),
    "Drums": dict(wave="8-bit", vol=0.8, pan=0.0),
}
MOODS = {
    "Relaxed": dict(scales=["Major", "Dorian", "Pentatonic Major"], bpm=(65, 95), cx=(15, 40), swing=(0.05, 0.2), time=["4/4", "6/8"], flags=dict(sync=False, ornaments=True, fills=False, modulate=False, extended=True)),
    "Happy": dict(scales=["Major", "Lydian", "Pentatonic Major"], bpm=(115, 150), cx=(40, 65), swing=(0.0, 0.15), time=["4/4"], flags=dict(sync=True, ornaments=True, fills=True, modulate=False, extended=True)),
    "Sad": dict(scales=["Natural Minor", "Phrygian"], bpm=(55, 80), cx=(15, 40), swing=(0.0, 0.1), time=["4/4", "3/4"], flags=dict(sync=False, ornaments=True, fills=False, modulate=False, extended=True)),
    "Tense": dict(scales=["Harmonic Minor", "Phrygian"], bpm=(100, 135), cx=(55, 85), swing=(0.0, 0.05), time=["4/4", "7/8"], flags=dict(sync=True, ornaments=False, fills=True, modulate=False, extended=True)),
    "Action": dict(scales=["Phrygian", "Harmonic Minor", "Dorian"], bpm=(150, 185), cx=(70, 95), swing=(0.0, 0.05), time=["4/4"], flags=dict(sync=True, ornaments=False, fills=True, modulate=True, extended=True)),
    "Mysterious": dict(scales=["Dorian", "Phrygian", "Blues"], bpm=(75, 105), cx=(35, 60), swing=(0.1, 0.25), time=["4/4", "6/8"], flags=dict(sync=True, ornaments=True, fills=False, modulate=False, extended=True)),
    "Heroic": dict(scales=["Lydian", "Major"], bpm=(115, 145), cx=(55, 80), swing=(0.0, 0.1), time=["4/4"], flags=dict(sync=True, ornaments=True, fills=True, modulate=True, extended=True)),
    "Playful": dict(scales=["Pentatonic Major", "Mixolydian"], bpm=(130, 165), cx=(45, 70), swing=(0.15, 0.3), time=["4/4", "6/8"], flags=dict(sync=True, ornaments=True, fills=True, modulate=False, extended=False)),
}
GENRES = {
    "RPG Overworld": dict(scales=["Major", "Mixolydian"], bpm=(110, 140), cx=(45, 70), swing=(0.05, 0.15), time=["4/4"], flags=dict(sync=True, ornaments=True, fills=True, modulate=True, extended=True), waves=dict(Lead="pulse25", Counter="fm", Arp="wavetable", Bass="triangle", Pad="supersaw", Drums="8-bit")),
    "RPG Battle": dict(scales=["Phrygian", "Harmonic Minor"], bpm=(150, 180), cx=(75, 95), swing=(0.0, 0.05), time=["4/4"], flags=dict(sync=True, ornaments=False, fills=True, modulate=True, extended=True), waves=dict(Lead="saw", Counter="square", Arp="pulse12", Bass="saw", Pad="supersaw", Drums="punchy")),
    "Dungeon": dict(scales=["Dorian", "Phrygian"], bpm=(85, 110), cx=(40, 65), swing=(0.0, 0.1), time=["4/4", "3/4"], flags=dict(sync=True, ornaments=True, fills=False, modulate=False, extended=True), waves=dict(Lead="fm", Counter="sine", Arp="pulse12", Bass="triangle", Pad="sine", Drums="lofi")),
    "Platformer": dict(scales=["Major", "Pentatonic Major"], bpm=(140, 175), cx=(55, 80), swing=(0.0, 0.1), time=["4/4"], flags=dict(sync=True, ornaments=True, fills=True, modulate=False, extended=False), waves=dict(Lead="square", Counter="pulse25", Arp="pulse12", Bass="square", Pad="triangle", Drums="8-bit")),
    "Puzzle": dict(scales=["Major", "Lydian", "Pentatonic Major"], bpm=(120, 150), cx=(35, 55), swing=(0.1, 0.2), time=["4/4"], flags=dict(sync=False, ornaments=True, fills=False, modulate=False, extended=True), waves=dict(Lead="pulse12", Counter="wavetable", Arp="square", Bass="triangle", Pad="wavetable", Drums="8-bit")),
    "Menu": dict(scales=["Major", "Lydian"], bpm=(95, 125), cx=(20, 40), swing=(0.0, 0.1), time=["4/4", "3/4"], flags=dict(sync=False, ornaments=True, fills=False, modulate=False, extended=True), waves=dict(Lead="sine", Counter="triangle", Arp="wavetable", Bass="sine", Pad="wavetable", Drums="lofi")),
    "Boss Battle": dict(scales=["Harmonic Minor", "Phrygian"], bpm=(160, 190), cx=(80, 100), swing=(0.0, 0.0), time=["4/4"], flags=dict(sync=True, ornaments=False, fills=True, modulate=True, extended=True), waves=dict(Lead="supersaw", Counter="saw", Arp="pulse12", Bass="saw", Pad="fm", Drums="punchy")),
}
PRESETS = {
    "SNES": dict(echo=True, delay=0.24, fb=0.45, emix=0.35, pp=True, bits=16, hold=1, soft=30,
                 waves=dict(Lead="pulse25", Counter="fm", Arp="wavetable", Bass="triangle", Pad="supersaw", Drums="punchy")),
    "GBA": dict(echo=True, delay=0.12, fb=0.25, emix=0.2, pp=False, bits=10, hold=1, soft=10,
                waves=dict(Lead="pulse25", Counter="pulse12", Arp="square", Bass="wavetable", Pad="triangle", Drums="lofi")),
    "NES / Game Boy": dict(echo=False, delay=0.2, fb=0.3, emix=0.2, pp=False, bits=6, hold=2, soft=0,
                           waves=dict(Lead="pulse25", Counter="pulse12", Arp="square", Bass="triangle", Pad="triangle", Drums="8-bit")),
    "Random Timbres": dict(echo=True, delay=0.2, fb=0.35, emix=0.3, pp=True, bits=16, hold=1, soft=20,
                           waves=dict(Lead="random", Counter="random", Arp="random", Bass="random", Pad="random", Drums="punchy")),
}
SECTION_TYPES = ["Intro", "A", "B", "C", "Chorus", "Verse", "Bridge", "Outro"]
ENERGY = {"Intro": 0.6, "Outro": 0.55, "Bridge": 0.9, "Verse": 0.8, "Chorus": 1.05, "A": 0.85, "B": 1.0, "C": 0.95}
STRUCT_PRESETS = {
    "Simple Loop": [("A", 8)],
    "Intro + Loop": [("Intro", 4), ("A", 8), ("B", 8)],
    "Verse/Chorus": [("Intro", 4), ("A", 8), ("B", 8), ("A", 8), ("B", 8), ("Outro", 4)],
    "Verse/Chorus/Bridge": [("Intro", 4), ("A", 8), ("B", 8), ("A", 8), ("B", 8), ("Bridge", 4), ("B", 8), ("Outro", 4)],
    "Long Form": [("Intro", 4), ("A", 8), ("B", 8), ("A", 8), ("B", 8), ("Bridge", 8), ("B", 8), ("B", 8), ("Outro", 4)],
}
TRANS = {
    0: [(3, 3), (4, 4), (5, 2), (1, 1), (2, 1), (6, 1)],
    1: [(4, 4), (6, 1), (3, 1), (0, 1)],
    2: [(5, 3), (3, 2), (1, 1)],
    3: [(4, 4), (0, 3), (1, 1), (5, 1)],
    4: [(0, 5), (5, 2), (3, 1)],
    5: [(3, 3), (1, 2), (4, 2)],
    6: [(0, 4), (2, 1)],
}
KITDEF = {
    "8-bit": dict(sq=True, kd=0.14, kf=160, sd=0.13, hd=0.035, od=0.16, hold=3),
    "punchy": dict(sq=False, kd=0.22, kf=220, sd=0.18, hd=0.05, od=0.28, hold=1),
    "lofi": dict(sq=False, kd=0.18, kf=140, sd=0.16, hd=0.06, od=0.22, hold=6),
}
def beat_strength(groups):
    total = sum(groups)
    arr = [0.3] * total
    pos = 0
    for g in groups:
        arr[pos] = 0.95
        if g % 3 == 0 and g > 3:
            for k in range(3, g, 3):
                arr[pos + k] = 0.55
        elif g % 2 == 0 and g > 2:
            arr[pos + g // 2] = 0.55
        pos += g
    arr[0] = 1.4
    return arr
class Song:
    def __init__(self, P):
        self.p = P
        self.scale = SCALES[P["scale"]]
        self.n = len(self.scale)
        self.root = 48 + NOTE_NAMES.index(P["key"])
        groups = TIME_SIGS[P["time"]]
        self.groups = groups
        self.spb = sum(groups)
        starts = []
        pos = 0
        for g in groups:
            starts.append(pos)
            pos += g
        self.starts = starts
        self.half = starts[(len(starts) + 1) // 2] if len(starts) > 1 else max(1, self.spb // 2)
        self.strength = beat_strength(groups)
        self.c = P["complexity"] / 100.0
        secs = P["sections"] if P["sections"] else [("A", 8)]
        self.sections = secs
        self.bars = sum(b for _, b in secs)
        self.steps = self.bars * self.spb
        r = random.Random(P["master_seed"])
        self.chord_cache = {}
        self.chords = []
        cur = 0
        started = False
        for label, bars in secs:
            slots = bars * 2
            if label in self.chord_cache:
                base = self.chord_cache[label]
                seq = [base[i % len(base)] for i in range(slots)]
                if seq:
                    cur = seq[-1]
            else:
                seq = []
                for i in range(slots):
                    if started:
                        cur = self.nxt(r, cur)
                    started = True
                    seq.append(cur)
                if len(seq) >= 2 and r.random() < 0.5:
                    seq[-2] = seq[-1] = min(4, self.n - 1)
                self.chord_cache[label] = list(seq)
            self.chords += seq
        self.label_of_bar = []
        for label, bars in secs:
            self.label_of_bar += [label] * bars
        self.energy = [ENERGY.get(l, 0.85) for l in self.label_of_bar]
        self.shift = []
        for bi in range(self.bars):
            frac = bi / max(1, self.bars - 1)
            self.shift.append(2 if P["modulate"] and self.bars >= 8 and frac >= 0.75 else 0)
    def nxt(self, r, cur):
        opts = TRANS[cur % 7]
        return r.choices([o[0] for o in opts], [o[1] for o in opts])[0] % self.n
    def midi(self, deg):
        o, i = divmod(deg, self.n)
        return self.root + 12 * o + self.scale[i]
    def tones(self, slot):
        d = self.chords[slot]
        t = [d, d + 2, d + 4]
        bar = slot // 2
        energy = self.energy[bar] if bar < len(self.energy) else 0.85
        eff = self.c * (0.6 + 0.5 * energy)
        if self.p["extended"]:
            if eff > 0.3:
                t.append(d + 6)
            if eff > 0.7:
                t.append(d + 8)
        return t
    def slot_at(self, step):
        bar, local = divmod(step, self.spb)
        return 2 * bar + (1 if local >= self.half else 0)
    def slot_span(self, slot):
        bar = slot // 2
        if slot % 2 == 0:
            return bar * self.spb, self.half
        return bar * self.spb + self.half, self.spb - self.half
def snap(cur, tones, n):
    ts = {t % n for t in tones}
    for o in (0, 1, -1, 2, -2, 3, -3):
        if (cur + o) % n in ts:
            return cur + o
    return cur
def rhythm(r, dens, c, sync, longs, spb, strength):
    out = []
    s = 0
    scale = spb / 16
    durs = [max(1, round(x * scale)) for x in (1, 2, 3, 4, 6, 8)]
    wsel = [c * 3 + 0.2, 4, 1 + c, 3 - c * 1.5 + longs, 1 + longs, 0.5 + longs]
    while s < spb:
        w = strength[s] if sync else min(strength[s], 0.9)
        if (s == 0 and r.random() < 0.8) or r.random() < dens * (0.4 + w):
            d = min(r.choices(durs, wsel)[0], spb - s)
            out.append((s, d))
            s += d
        else:
            s += 1
    return out
def generate_motif(scale_name, complexity, time_sig, seed):
    n = len(SCALES[scale_name])
    groups = TIME_SIGS[time_sig]
    spb = sum(groups)
    strength = beat_strength(groups)
    c = complexity / 100.0
    r = random.Random(seed)
    moves = [0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5]
    wts = [1, 4, 4, 2.5, 2.5, 1 + c * 2, 1 + c * 2, 0.3 + c * 1.5, 0.3 + c * 1.5, c, c]
    dens = 0.3 + 0.45 * c
    pattern = rhythm(r, dens, c, True, 0, spb, strength)
    cur = n + 3
    last_dir = 0
    out = []
    for s, d in pattern:
        mv = r.choices(moves, wts)[0]
        if abs(last_dir) >= 4 and mv != 0 and (mv * last_dir > 0 or abs(mv) > 2):
            mv = -1 if last_dir > 0 else 1
        last_dir = mv
        cur += mv
        out.append((s, d, cur))
    return out
def gen_melody(song, r, lead, motifs=None):
    c, n = song.c, song.n
    lo, hi, center = (n, 2 * n + 5, n + 3) if lead else (0, n + 4, 2)
    sync = song.p["sync"]
    orn = song.p["ornaments"] and c > 0.25
    moves = [0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5]
    wts = [1, 4, 4, 2.5, 2.5, 1 + c * 2, 1 + c * 2, 0.3 + c * 1.5, 0.3 + c * 1.5, c, c]
    cache = {}
    entry_cache = {}
    cur = center
    last_dir = 0
    core = []
    bar0 = 0
    for si, (label, bars) in enumerate(song.sections):
        key0 = (label, lead)
        if key0 in entry_cache:
            cur, last_dir = entry_cache[key0]
        else:
            entry_cache[key0] = (cur, last_dir)
        energy = ENERGY.get(label, 0.85)
        override = motifs.get(label) if (lead and motifs) else None
        if override:
            for lb in range(bars):
                b = bar0 + lb
                for step, dur, deg in override:
                    s = max(0, min(step, song.spb - 1))
                    d = max(1, min(dur, song.spb - s))
                    core.append((b * song.spb + s, d, deg, 0.85 * energy))
            cur = override[-1][2]
            last_dir = 0
            bar0 += bars
            continue
        dens = (0.3 + 0.45 * c if lead else 0.12 + 0.25 * c) * (0.55 + 0.55 * energy)
        longs = 0 if lead else 3
        bias = 0.75 if lead else 0.95
        key = (label, lead)
        first_occurrence = not any(l == label for l, _ in song.sections[:si])
        if key not in cache:
            def template():
                return [(s, d, r.choices(moves, wts)[0]) for s, d in rhythm(r, dens, c, sync, longs, song.spb, song.strength)]
            form = r.choice(["AABA", "ABAB"] if c < 0.4 else ["ABAC", "ABCB", "AABC", "ABAB"])
            tp = {k: template() for k in "ABC"}
            cache[key] = (form, tp)
        form, tp = cache[key]
        for lb in range(bars):
            b = bar0 + lb
            t = list(tp[form[lb % 4]])
            if first_occurrence and lb >= 4 and t and r.random() < c * 0.6:
                i = r.randrange(len(t))
                t[i] = (t[i][0], t[i][1], r.choice(moves))
            if first_occurrence and lb % 4 == 3 and len(t) > 2 and r.random() < 0.5:
                t.pop()
            last = len(t) - 1
            for k, (s, d, mv) in enumerate(t):
                if abs(last_dir) >= 4 and mv != 0 and (mv * last_dir > 0 or abs(mv) > 2):
                    mv = -1 if last_dir > 0 else 1
                last_dir = mv
                cur += mv
                while cur > hi:
                    cur -= n
                while cur < lo:
                    cur += n
                slot = song.slot_at(b * song.spb + s)
                tones = song.tones(slot)
                strong = song.strength[s] >= 0.85
                step_abs = b * song.spb + s
                is_final = (b == song.bars - 1) and (k == last)
                if is_final:
                    cur = snap(cur, tones[:1], n)
                elif strong and r.random() < bias:
                    cur = snap(cur, tones, n)
                v = min(1.0, (0.95 if strong else 0.75) + r.uniform(-0.08, 0.08)) * energy
                core.append((step_abs, d, cur, v))
        bar0 += bars
    ev = []
    last_orn = -99
    for idx, (step, d, deg, v) in enumerate(core):
        if orn and step >= 1 and step - last_orn >= 6 and r.random() < c * 0.1:
            ev.append((step - 1, 1, song.midi(deg + r.choice([-1, 1])), v * 0.45))
            last_orn = step
        if orn and d >= 4 and step - last_orn >= 8 and r.random() < c * 0.1:
            for j in range(d):
                ev.append((step + j, 1, song.midi(deg + j % 2), v * 0.85))
            last_orn = step + d
        else:
            ev.append((step, d, song.midi(deg), v))
        if idx + 1 < len(core):
            nstep, nd, ndeg, nv = core[idx + 1]
            gap = ndeg - deg
            if abs(gap) >= 3 and d >= 2 and nstep <= step + d:
                pdeg = deg + (1 if gap > 0 else -1)
                ev.append((step + d - 1, 1, song.midi(pdeg), v * 0.65))
    return ev
def gen_arp(song, r):
    c, n = song.c, song.n
    rate = 2 if c < 0.35 else r.choice([1, 2, 2])
    style = r.choice(["up", "down", "updown", "random", "skip"])
    span = 1 if c < 0.3 else (2 if c < 0.7 else 3)
    ev = []
    i = 0
    for s in range(0, song.steps, rate):
        slot = song.slot_at(s)
        tones = song.tones(slot)
        pool = sorted(t + n + o * n for o in range(span) for t in tones)
        m = len(pool)
        if style == "up":
            deg = pool[i % m]
        elif style == "down":
            deg = pool[-1 - i % m]
        elif style == "updown":
            q = max(1, 2 * m - 2)
            j = i % q
            deg = pool[j if j < m else q - j]
        elif style == "skip":
            deg = pool[(i * 2) % m]
        else:
            deg = r.choice(pool)
        i += 1
        bar = s // song.spb
        energy = song.energy[bar] if bar < len(song.energy) else 0.85
        if song.p["sync"] and r.random() < 0.05 + 0.2 * c:
            continue
        local = s % song.spb
        strong = song.strength[local] >= 0.85
        ev.append((s, rate, song.midi(deg), (0.9 if strong else 0.6) * energy))
    return ev
def gen_bass(song, r):
    c, n = song.c, song.n
    groups, starts = song.groups, song.starts
    style = r.choice(["quarters", "octave"]) if c < 0.35 else r.choice(["octave", "walk", "sync", "gallop"])
    def split(st, g, parts):
        if g < parts:
            parts = 1
        step = g // parts
        return [(st + i * step, step if i < parts - 1 else g - step * (parts - 1)) for i in range(parts)]
    def bar_pat():
        if style == "quarters":
            return [(st, g, "r") for st, g in zip(starts, groups)]
        if style == "octave":
            out = []
            for st, g in zip(starts, groups):
                for j, (s2, d2) in enumerate(split(st, g, 2)):
                    out.append((s2, d2, "r" if j == 0 else "o"))
            return out
        if style == "gallop":
            out = []
            for st, g in zip(starts, groups):
                parts = split(st, g, 3)
                out.append((parts[0][0], parts[0][1] + parts[1][1], "r"))
                out.append((parts[2][0], parts[2][1], "o"))
            return out
        if style == "walk":
            seq = ["r"] + [r.choice("tfo") for _ in range(len(groups) - 1)]
            return [(st, g, k) for (st, g), k in zip(zip(starts, groups), seq)]
        return [(s, d, "r" if song.strength[s] >= 0.9 else r.choice("rrfo")) for s, d in rhythm(r, 0.3 + 0.3 * c, c, True, 0, song.spb, song.strength)]
    pats = [bar_pat(), bar_pat()]
    off = {"r": 0, "t": 2, "f": 4, "o": n}
    ev = []
    for b in range(song.bars):
        energy = song.energy[b] if b < len(song.energy) else 0.85
        for s, d, k in pats[b % 2]:
            slot = song.slot_at(b * song.spb + s)
            deg = song.chords[slot] + off[k] - n
            if s + d in (song.half, song.spb) and c > 0.3 and style != "quarters" and r.random() < 0.5:
                nx = song.chords[(slot + 1) % len(song.chords)]
                if nx != song.chords[slot]:
                    cand = [nx - n, nx + 2 - n, nx - 2 - n]
                    deg = min(cand, key=lambda x: abs(x - deg))
            ev.append((b * song.spb + s, d, song.midi(deg), (1.0 if song.strength[s] >= 0.9 else 0.8) * energy))
    return ev
def gen_pad(song, r):
    c, n = song.c, song.n
    pulse = c > 0.4 and r.random() < 0.5
    ev = []
    total = len(song.chords)
    slot = 0
    while slot < total:
        run = 1
        while not pulse and slot + run < total and song.chords[slot + run] == song.chords[slot]:
            run += 1
        tones = song.tones(slot)
        bar = slot // 2
        energy = song.energy[bar] if bar < len(song.energy) else 0.85
        start, length = song.slot_span(slot)
        if run > 1:
            last_start, last_len = song.slot_span(slot + run - 1)
            length = (last_start + last_len) - start
        if pulse:
            gap = max(1, length // 4) if c > 0.7 else max(1, length // 2)
            k = 0
            while k < length:
                g = min(gap, length - k)
                for t in tones:
                    ev.append((start + k, g, song.midi(t + n), (0.6 if k == 0 else 0.45) * energy))
                k += g
        else:
            for t in tones:
                ev.append((start, length, song.midi(t + n), 0.6 * energy))
        slot += run
    return ev
def gen_drums(song, r):
    c = song.c
    groups, starts = song.groups, song.starts
    ng = len(groups)
    kick_idx = {0}
    for i in range(1, ng):
        if r.random() < 0.3 + 0.5 * c:
            kick_idx.add(i)
    if ng > 2 and r.random() < 0.5:
        kick_idx.add(ng // 2)
    back = [i for i in range(1, ng, 2)] or [ng - 1 if ng > 1 else 0]
    snare_idx = set(back)
    def subdivs(st, g):
        parts = 3 if g % 3 == 0 and g >= 3 else (2 if g % 2 == 0 else 1)
        step = g // parts
        return [st + k * step for k in range(parts)]
    mode = 0 if c < 0.3 else (1 if c < 0.6 else 2)
    fills_on = song.p["fills"]
    ev = []
    for b in range(song.bars):
        base = b * song.spb
        energy = song.energy[b] if b < len(song.energy) else 0.85
        fill = fills_on and energy >= 0.9 and b % 4 == 3
        fs = starts[max(0, ng - (2 if c > 0.6 else 1))]
        ks, ss = set(kick_idx), set(snare_idx)
        if song.p["sync"] and ng > 1 and r.random() < c * 0.4 * energy:
            ks.add(r.choice(range(1, ng)))
        if fills_on and c > 0.2 and b > 0 and b % 4 == 0 and energy >= 0.8:
            ev.append((base, 1, 5, 0.6 * energy))
        for gi, (st, g) in enumerate(zip(starts, groups)):
            if fill and st >= fs:
                for s in subdivs(st, g):
                    if s < fs:
                        continue
                    ev.append((base + s, 1, r.choice([1, 6, 4]) if s < song.spb - 2 else 1, (0.6 + 0.4 * (s - fs) / max(1, song.spb - fs)) * energy))
                continue
            if gi in ks:
                ev.append((base + st, 1, 0, (1.0 if gi == 0 else 0.8) * energy))
            if gi in ss:
                ev.append((base + st, 1, 1, 1.0 * energy))
            for j, s in enumerate(subdivs(st, g)):
                if mode == 0 and j != 0:
                    continue
                if mode >= 1 and j > 0:
                    kind = 3 if (mode == 2 and r.random() < c * 0.3) else 2
                    v = (0.55 if j == 0 else 0.35 + 0.15 * r.random()) * energy
                    ev.append((base + s, 1, kind, v))
        if song.p["sync"] and c > 0.5 and r.random() < c * 0.3 * energy:
            ev.append((base + r.choice(range(song.spb)), 1, 1, 0.4 * energy))
    return ev
def gen_events(name, song, seed):
    r = random.Random(seed)
    if name == "Drums":
        return gen_drums(song, r)
    if name == "Lead":
        raw = gen_melody(song, r, True, song.p.get("motifs"))
    elif name == "Counter":
        raw = gen_melody(song, r, False)
    elif name == "Arp":
        raw = gen_arp(song, r)
    elif name == "Bass":
        raw = gen_bass(song, r)
    else:
        raw = gen_pad(song, r)
    return [(s, d, m + song.shift[min(s // song.spb, song.bars - 1)], v) for s, d, m, v in raw]
def envelope(dur, a, d, s, r):
    a = max(a, 1e-4)
    d = max(d, 1e-4)
    ng = max(1, int(dur * SR))
    nr = max(1, int(r * SR))
    e = np.interp(np.arange(ng) / SR, [0, a, a + d], [0, 1, s])
    return np.concatenate([e, e[-1] * np.linspace(1, 0, nr)])
def pulse(x, d):
    return (np.where(x < d, 1.0, -1.0) - (2 * d - 1)) * 0.6
def synth(freq, n, wv, vib, aux):
    t = np.arange(n) / SR
    f = freq * (1 + vib * 0.02 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(1.0, t / 0.2))
    ph = np.cumsum(f) / SR
    x = ph % 1.0
    if wv == "square":
        return pulse(x, 0.5)
    if wv == "pulse25":
        return pulse(x, 0.25)
    if wv == "pulse12":
        return pulse(x, 0.125)
    if wv == "triangle":
        return (4 * np.abs(x - 0.5) - 1) * 0.9
    if wv == "saw":
        return (2 * x - 1) * 0.7
    if wv == "sine":
        return np.sin(2 * np.pi * ph) * 0.9
    if wv == "noise":
        idx = np.floor(ph).astype(int)
        return aux["rng"].uniform(-1, 1, idx[-1] + 2)[idx] * 0.7
    if wv == "wavetable":
        return aux["tbl"][(x * len(aux["tbl"])).astype(int) % len(aux["tbl"])] * 0.8
    if wv == "fm":
        return np.sin(2 * np.pi * ph + aux["fmi"] * np.exp(-t * 3) * np.sin(2 * np.pi * ph * aux["fmr"])) * 0.8
    return ((2 * x - 1) + (2 * ((ph * 1.007) % 1.0) - 1) + (2 * ((ph * 0.993) % 1.0) - 1)) / 3 * 0.8
def drum_sound(kind, kit, rng):
    k = KITDEF[kit]
    def noise(n):
        x = rng.uniform(-1, 1, n + 1)
        if k["hold"] > 1:
            x = np.repeat(x[::k["hold"]], k["hold"])[:n + 1]
        return x
    def tone(t, f1, f0, rate):
        y = np.sin(2 * np.pi * np.cumsum(f1 + f0 * np.exp(-t * rate)) / SR)
        return np.sign(y) * 0.7 if k["sq"] else y
    def make(dur):
        n = int(dur * SR)
        return n, np.arange(n) / SR
    if kind == 0:
        n, t = make(k["kd"])
        return tone(t, 45, k["kf"], 30) * (1 - t / k["kd"]) ** 2
    if kind == 1:
        n, t = make(k["sd"])
        e = 1 - t / k["sd"]
        return noise(n)[:n] * 0.7 * e ** 1.5 + tone(t, 160, 100, 40) * 0.5 * e
    if kind in (4, 6):
        n, t = make(0.2)
        return tone(t, 90 if kind == 4 else 130, 150 if kind == 4 else 130, 12) * (1 - t / 0.2) ** 2
    dur, p, amp = {2: (k["hd"], 2, 0.5), 3: (k["od"], 1.5, 0.5), 5: (0.7, 2.5, 0.5)}[kind]
    n, t = make(dur)
    x = noise(n)
    return (x[1:] - x[:-1]) * amp * (1 - t / dur) ** p
def put(buf, y, i):
    e = min(len(buf), i + len(y))
    if e > i:
        buf[i:e] += y[:e - i]
def render_channel(name, ev, P, total):
    cfg = P["ch"][name]
    sdur = 60.0 / P["bpm"] / 4
    sw = P["swing"] * 0.5
    def tm(s):
        return (s + (sw if s % 2 else 0)) * sdur
    buf = np.zeros(total, np.float32)
    rng = np.random.default_rng(cfg["seed"])
    if name == "Drums":
        snd = {k: drum_sound(k, cfg["wave"], rng) for k in range(7)}
        for s, d, kind, v in ev:
            put(buf, snd[kind] * v, int(tm(s) * SR))
        return buf
    wv = cfg["wave"]
    if wv == "random":
        wv = POOLS[name][cfg["seed"] % len(POOLS[name])]
    x = np.arange(32) / 32
    tbl = sum(rng.uniform(0, 1) / (k ** rng.uniform(0.5, 1.5)) * np.sin(2 * np.pi * k * x + rng.uniform(0, 6.28)) for k in range(1, 7))
    tbl = np.round(tbl / np.abs(tbl).max() * 7.5) / 7.5
    aux = {"tbl": tbl, "fmr": float(rng.choice([0.5, 1, 1.5, 2, 3, 4])), "fmi": float(rng.uniform(1, 5)), "rng": rng}
    for s, d, m, v in ev:
        f = 440.0 * 2 ** ((m + 12 * cfg["oct"] - 69) / 12)
        env = envelope((tm(s + d) - tm(s)) * 0.97, cfg["a"], cfg["d"], cfg["s"], cfg["r"])
        put(buf, synth(f, len(env), wv, cfg["vib"], aux) * env * v, int(tm(s) * SR))
    return buf
def echo(x, delay, fb, mix, pp):
    d = max(1, int(delay * SR))
    y = x.copy()
    for i in range(d, len(y), d):
        prev = y[i - d:i]
        prev = 0.5 * prev + 0.25 * (np.roll(prev, 1, 0) + np.roll(prev, -1, 0))
        seg = y[i:i + d]
        m = len(seg)
        if pp:
            c = (i // d) % 2
            s = prev[:m].mean(axis=1) * fb
            seg[:, c] += s
            seg[:, 1 - c] += 0.25 * s
        else:
            seg += fb * prev[:m]
    return x + mix * (y - x)
def mix(buf, P, n):
    ch = P["ch"]
    solo = any(ch[k]["solo"] for k in CHANNELS)
    out = np.zeros((n + TAIL, 2), np.float32)
    for k in CHANNELS:
        c = ch[k]
        if not c["on"] or (solo and not c["solo"]):
            continue
        a = (c["pan"] + 1) * math.pi / 4
        g = c["vol"] * 0.35
        out[:, 0] += buf[k] * (g * math.cos(a))
        out[:, 1] += buf[k] * (g * math.sin(a))
    if P["echo"]:
        out = echo(out, P["delay"], P["fb"], P["emix"], P["pp"])
    out[:TAIL] += out[n:n + TAIL]
    out = out[:n]
    if P["hold"] > 1:
        out = np.repeat(out[::P["hold"]], P["hold"], axis=0)[:n]
    if P["bits"] < 16:
        q = 2.0 ** (P["bits"] - 1)
        out = np.round(out * q) / q
    w = int(P["soft"] * 0.12)
    if w > 0:
        k = np.hanning(2 * w + 3)[1:-1]
        k /= k.sum()
        out = np.stack([np.convolve(out[:, i], k, "same") for i in range(2)], 1)
    out = np.tanh(out * P["master"])
    return (out * 32767).astype(np.int16)
class Engine:
    def __init__(self):
        self.song = None
        self.ev = {}
        self.buf = {}
    def run(self, job):
        P = job["P"]
        if job["song"] or self.song is None:
            self.song = Song(P)
            job["ev"] = set(CHANNELS)
        n = int(self.song.steps * 60.0 / P["bpm"] / 4 * SR)
        total = n + TAIL
        for name in CHANNELS:
            if name in job["ev"] or name not in self.ev:
                self.ev[name] = gen_events(name, self.song, P["ch"][name]["seed"])
                job["rn"].add(name)
            if name in job["rn"] or name not in self.buf or len(self.buf[name]) != total:
                self.buf[name] = render_channel(name, self.ev[name], P, total)
        return mix(self.buf, P, n), dict(self.ev), self.song.steps
def save_wav(path, audio):
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(audio.tobytes())
