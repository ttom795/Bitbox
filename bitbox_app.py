import tkinter as tk
from tkinter import ttk, filedialog
import numpy as np
import threading, queue, random, os, shutil, subprocess, tempfile, time, traceback
from bitbox_core import *
try:
    import sounddevice as sdev
except Exception:
    sdev = None
try:
    import winsound
except Exception:
    winsound = None
BG = "#1e1f29"
FG = "#e6e6f0"
ACC = "#7aa2f7"
WAVE_INFO = {
    "random": "Picks a different timbre each time this channel is regenerated.",
    "square": "Hard square wave, hollow and buzzy, classic NES lead tone.",
    "pulse25": "Narrower pulse wave, thinner and reedier than a plain square.",
    "pulse12": "Very narrow pulse, thin and nasal, good for fast arpeggios.",
    "triangle": "Soft rounded wave, mellow, the classic chiptune bass tone.",
    "saw": "Bright, buzzy wave rich in harmonics, good for leads and basses.",
    "sine": "Pure smooth tone with no extra harmonics, very soft and clean.",
    "wavetable": "Randomised custom waveform, somewhere between organ and bell.",
    "fm": "Metallic, bell-like tone produced by frequency modulation.",
    "supersaw": "Three detuned saw waves stacked together, thick and wide.",
    "noise": "Hissy static, mainly used for percussion and texture.",
}
KIT_INFO = {
    "8-bit": "Tight, punchy retro kit close to NES / Game Boy drums.",
    "punchy": "Bigger, rounder drums with more low end and snap.",
    "lofi": "Grungier, sample-held drums for a dirtier SNES-ish feel.",
}
MOOD_DESC = {
    "Relaxed": "Slow, gentle, major-leaning, background feel.",
    "Happy": "Upbeat major key, bouncy and bright.",
    "Sad": "Slow minor key, sparse and wistful.",
    "Tense": "Mid-tempo, edgy, on-guard feel.",
    "Action": "Fast, driving, minor-key energy.",
    "Mysterious": "Moody modal scale, loose floating rhythm.",
    "Heroic": "Bright, bold, march-like feel.",
    "Playful": "Bouncy pentatonic runs with loose swing.",
}
GENRE_DESC = {
    "RPG Overworld": "Warm, wandering major-key travel theme.",
    "RPG Battle": "Fast aggressive minor-key combat theme.",
    "Dungeon": "Dark, sparse, echoing modal theme.",
    "Platformer": "Bouncy, energetic major-key action theme.",
    "Puzzle": "Calm, repetitive, gently melodic theme.",
    "Menu": "Simple, unobtrusive title or menu theme.",
    "Boss Battle": "Intense, fast, maximal energy combat theme.",
}
SLIDERS = [
    ("vol", tk.DoubleVar, 0, 1, 0.01, "mix", "How loud this channel is in the mix."),
    ("pan", tk.DoubleVar, -1, 1, 0.05, "mix", "Stereo position, left to right."),
    ("oct", tk.IntVar, -2, 2, 1, "voice", "Shifts this channel up or down by octaves."),
    ("a", tk.DoubleVar, 0, 0.5, 0.005, "voice", "Attack time, how fast a note fades in."),
    ("d", tk.DoubleVar, 0.01, 1, 0.01, "voice", "Decay time, how fast it settles after attack."),
    ("s", tk.DoubleVar, 0, 1, 0.01, "voice", "Sustain level while a note is held."),
    ("r", tk.DoubleVar, 0.01, 1, 0.01, "voice", "Release time, how fast a note fades out."),
    ("vib", tk.DoubleVar, 0, 1, 0.05, "voice", "Amount of pitch vibrato."),
]
HEADERS = ["", "On", "Solo", "Wave / Kit", "Vol", "Pan", "Oct", "Atk", "Dec", "Sus", "Rel", "Vib", "Seed", "Lock", "", ""]
FX = [
    ("Delay", "delay", tk.DoubleVar, 0.24, 0.03, 0.6, 0.01, "Time between echo repeats."),
    ("Feedback", "fb", tk.DoubleVar, 0.45, 0, 0.85, 0.01, "How much each echo repeat feeds into the next."),
    ("Wet", "emix", tk.DoubleVar, 0.35, 0, 1, 0.01, "How much echo is mixed into the final sound."),
    ("Bits", "bits", tk.IntVar, 16, 3, 16, 1, "Bit depth, lower sounds crunchier and more retro."),
    ("Hold", "hold", tk.IntVar, 1, 1, 12, 1, "Sample and hold amount, lower sample rate feel."),
    ("Soft", "soft", tk.IntVar, 25, 0, 100, 1, "Smooths harsh edges, like an old DAC filter."),
    ("Master", "master", tk.DoubleVar, 1.0, 0.3, 2.5, 0.05, "Overall output volume before limiting."),
]
PLAYERS = [["afplay"], ["paplay"], ["aplay", "-q"], ["play", "-q"], ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]]
class Tooltip:
    def __init__(self, widget, textfunc):
        self.w = widget
        self.f = textfunc
        self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)
    def show(self, e):
        text = self.f()
        if not text:
            return
        self.tip = tk.Toplevel(self.w)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{e.x_root + 12}+{e.y_root + 10}")
        tk.Label(self.tip, text=text, bg="#2b2d3d", fg=FG, bd=1, relief="solid", wraplength=220, justify="left", padx=6, pady=4).pack()
    def hide(self, e):
        if self.tip:
            self.tip.destroy()
            self.tip = None
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bitbox, procedural chiptune generator")
        self.configure(bg=BG)
        self.geometry("1600x960")
        self.setup_style()
        self.jobs = queue.Queue()
        self.results = queue.Queue()
        self.engine = Engine()
        self.pend = {"ev": set(), "rn": set(), "song": False, "play": False}
        self.timer = None
        self.audio = None
        self.events = {}
        self.steps = 0
        self.playing = False
        self.t0 = 0.0
        self.proc = None
        self.counter = 0
        self.tmp = []
        self.g = {}
        self.cv = {}
        self.sections = [tuple(x) for x in STRUCT_PRESETS["Verse/Chorus"]]
        self.style_waves = {name: DEFAULTS[name]["wave"] for name in CHANNELS}
        self.vis = {name: tk.BooleanVar(value=True) for name in CHANNELS}
        self.motifs = {}
        self.motif_cache = {}
        self.motif_rects = []
        self.motif_drag_state = None
        self.note_rects = []
        self.drag_state = None
        self.status = tk.StringVar(value="Starting...")
        self.build()
        self.protocol("WM_DELETE_WINDOW", self.close)
        threading.Thread(target=self.worker, daemon=True).start()
        self.after(17, self.poll)
        self.regenerate_all(play=False)
    def setup_style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=FG, fieldbackground="#2b2d3d", bordercolor="#3a3c50", lightcolor=BG, darkcolor=BG)
        s.configure("TButton", padding=4)
        s.map("TButton", background=[("active", "#3a3c50")])
        s.map("TCombobox", fieldbackground=[("readonly", "#2b2d3d")], foreground=[("readonly", FG)])
        s.configure("TCheckbutton", indicatorbackground="#2b2d3d", indicatorforeground=ACC)
        s.map("TCheckbutton", background=[("active", BG)])
        s.configure("TNotebook.Tab", padding=(10, 4), background="#cfcfd6", foreground="black")
        s.map("TNotebook.Tab", background=[("selected", "#e9e9ee")], foreground=[("selected", "black"), ("!selected", "black")])
        self.option_add("*TCombobox*Listbox.background", "#2b2d3d")
        self.option_add("*TCombobox*Listbox.foreground", FG)
    def mk(self, cls, name, value, kind=None):
        v = cls(value=value)
        self.g[name] = v
        if kind:
            v.trace_add("write", lambda *a: self.changed(kind))
        return v
    def combo(self, parent, var, values, width):
        return ttk.Combobox(parent, textvariable=var, values=values, state="readonly", width=width)
    def slider(self, parent, var, lo, hi, res, length, show=False):
        return tk.Scale(parent, variable=var, from_=lo, to=hi, resolution=res, orient="horizontal", length=length, showvalue=show,
                        sliderlength=14, width=10, bd=0, highlightthickness=0, bg=BG, fg=FG, troughcolor="#2b2d3d", activebackground=ACC)
    def field(self, parent, text, var, lo, hi, res, length, tip=""):
        f = ttk.Frame(parent)
        lab = ttk.Label(f, text=text)
        lab.pack(side="left")
        sl = self.slider(f, var, lo, hi, res, length, True)
        sl.pack(side="left")
        if tip:
            self.tip(lab, tip)
            self.tip(sl, tip)
        return f
    def tip(self, widget, text):
        Tooltip(widget, lambda t=text: t)
    def build(self):
        top_split = ttk.Frame(self)
        top_split.pack(fill="x", padx=8, pady=(8, 2))
        nb = ttk.Notebook(top_split)
        nb.pack(side="left", fill="both", expand=True)
        controls_tab = ttk.Frame(nb)
        struct_tab = ttk.Frame(nb)
        motif_tab = ttk.Frame(nb)
        nb.add(controls_tab, text="Controls")
        nb.add(struct_tab, text="Structure")
        nb.add(motif_tab, text="Motif")
        self.build_controls_tab(controls_tab)
        self.build_structure_tab(struct_tab)
        self.build_motif_tab(motif_tab)
        wave_frame = ttk.Frame(top_split)
        wave_frame.pack(side="right", padx=(8, 0))
        ttk.Label(wave_frame, text="Live waveforms").pack()
        wave_grid = tk.Frame(wave_frame, bg=BG)
        wave_grid.pack()
        self.wave_canvases = {}
        cols = 3
        for i, name in enumerate(CHANNELS):
            rr, cc = divmod(i, cols)
            cell = tk.Frame(wave_grid, bg="black")
            cell.grid(row=rr, column=cc, padx=2, pady=2)
            cv = tk.Canvas(cell, width=108, height=100, bg="black", highlightthickness=1, highlightbackground=COLORS[name])
            cv.pack()
            self.wave_canvases[name] = cv
            self.tip(cv, f"Live waveform for {name}, white on black.")
        visbar = ttk.Frame(self)
        visbar.pack(fill="x", padx=8)
        ttk.Label(visbar, text="Show in display:").pack(side="left", padx=(0, 6))
        for name in CHANNELS:
            cb = ttk.Checkbutton(visbar, text=name, variable=self.vis[name], command=self.draw)
            cb.pack(side="left", padx=3)
            self.tip(cb, f"Show or hide {name} notes below.")
        self.canvas = tk.Canvas(self, height=180, bg="#12131a", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=8, pady=4)
        self.canvas.bind("<Configure>", lambda e: self.draw())
        self.canvas.bind("<ButtonPress-1>", self.canvas_press)
        self.canvas.bind("<B1-Motion>", self.canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.canvas_release)
        self.tip(self.canvas, "Drag a note to move it in time or pitch.")
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=8, pady=(2, 8))
        b1 = ttk.Button(bar, text="Generate All", command=self.regenerate_all)
        b1.pack(side="left")
        self.tip(b1, "Reroll everything and make a new song.")
        b2 = ttk.Button(bar, text="Play", command=self.play)
        b2.pack(side="left", padx=4)
        self.tip(b2, "Play the current loop.")
        b3 = ttk.Button(bar, text="Stop", command=self.stop)
        b3.pack(side="left")
        self.tip(b3, "Stop playback.")
        c1 = ttk.Checkbutton(bar, text="Loop", variable=self.mk(tk.BooleanVar, "loop", True))
        c1.pack(side="left", padx=8)
        self.tip(c1, "Repeat the song when it reaches the end.")
        c2 = ttk.Checkbutton(bar, text="Auto-play on regenerate", variable=self.mk(tk.BooleanVar, "autoplay", True))
        c2.pack(side="left")
        self.tip(c2, "Start playing automatically after changes.")
        b4 = ttk.Button(bar, text="Export WAV", command=self.export)
        b4.pack(side="left", padx=8)
        self.tip(b4, "Save the current loop as a WAV file.")
        ttk.Label(bar, textvariable=self.status).pack(side="right")
    def build_controls_tab(self, parent):
        self.build_song_tab(parent)
        ttk.Separator(parent).pack(fill="x", pady=4)
        ch_frame = ttk.LabelFrame(parent, text="Channels")
        ch_frame.pack(fill="x", padx=4, pady=4)
        self.build_channels_tab(ch_frame)
        ttk.Separator(parent).pack(fill="x", pady=4)
        out_frame = ttk.LabelFrame(parent, text="Output")
        out_frame.pack(fill="x", padx=4, pady=4)
        self.build_output_tab(out_frame)
    def build_song_tab(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill="x", pady=(4, 2))
        lab = ttk.Label(top, text="Style")
        lab.pack(side="left")
        self.tip(lab, "Overall retro sound profile.")
        cb = self.combo(top, self.mk(tk.StringVar, "preset", "SNES"), list(PRESETS), 13)
        cb.pack(side="left", padx=(4, 10))
        cb.bind("<<ComboboxSelected>>", lambda e: self.apply_preset())
        self.tip(cb, "Console style, sets echo, bit depth and waveforms.")
        lab2 = ttk.Label(top, text="Mood")
        lab2.pack(side="left")
        self.tip(lab2, "Overall emotional feel.")
        self.g["mood"] = tk.StringVar(value="-")
        mc = self.combo(top, self.g["mood"], ["-"] + list(MOODS), 11)
        mc.pack(side="left", padx=(4, 10))
        mc.bind("<<ComboboxSelected>>", self.apply_mood)
        Tooltip(mc, lambda: MOOD_DESC.get(self.g["mood"].get(), "Sets scale, tempo and feel at random."))
        lab3 = ttk.Label(top, text="Genre")
        lab3.pack(side="left")
        self.tip(lab3, "Game music style.")
        self.g["genre"] = tk.StringVar(value="-")
        gc = self.combo(top, self.g["genre"], ["-"] + list(GENRES), 13)
        gc.pack(side="left", padx=(4, 10))
        gc.bind("<<ComboboxSelected>>", self.apply_genre)
        Tooltip(gc, lambda: GENRE_DESC.get(self.g["genre"].get(), "Sets scale, tempo, feel and waveforms."))
        self.field(top, "BPM", self.mk(tk.IntVar, "bpm", 120, "timing"), 60, 200, 1, 120, "Speed of the song in beats per minute.").pack(side="left", padx=6)
        r2 = ttk.Frame(parent)
        r2.pack(fill="x", pady=2)
        tips = {"key": "Root note of the song.", "scale": "Scale used for melodies and chords.", "time": "Time signature, how beats are grouped."}
        for label, name, vals, w, default in (("Key", "key", NOTE_NAMES, 4, "C"), ("Scale", "scale", list(SCALES), 15, "Natural Minor"), ("Time", "time", list(TIME_SIGS), 6, "4/4")):
            lb = ttk.Label(r2, text=label)
            lb.pack(side="left", padx=(0, 2))
            self.tip(lb, tips[name])
            cb2 = self.combo(r2, self.mk(tk.StringVar, name, default, "music"), vals, w)
            cb2.pack(side="left", padx=(0, 10))
            self.tip(cb2, tips[name])
        lab4 = ttk.Label(r2, text="Seed")
        lab4.pack(side="left", padx=(4, 2))
        self.tip(lab4, "Master random seed for the whole song.")
        me = ttk.Entry(r2, textvariable=self.mk(tk.IntVar, "master_seed", random.randrange(1, 2 ** 31)), width=11)
        me.pack(side="left")
        me.bind("<Return>", lambda e: self.request(ev=CHANNELS, song=True, play=self.g["autoplay"].get(), delay=0))
        self.tip(me, "Press enter to apply this seed.")
        r3 = ttk.Frame(parent)
        r3.pack(fill="x", pady=2)
        self.field(r3, "Complexity", self.mk(tk.IntVar, "complexity", 50, "music"), 0, 100, 1, 220, "How busy and ornamented the music is.").pack(side="left", padx=6)
        self.field(r3, "Swing", self.mk(tk.DoubleVar, "swing", 0.0, "timing"), 0, 1, 0.05, 90, "Shuffles off-beat notes for a groovier feel.").pack(side="left", padx=6)
        toggles = (("Extended chords", "extended", True, "Adds richer 7th and 9th style chords."),
                   ("Ornaments", "ornaments", True, "Adds grace notes and short trills."),
                   ("Syncopation", "sync", True, "Allows notes off the main beat."),
                   ("Drum fills", "fills", True, "Adds drum fills every few bars."),
                   ("Key change", "modulate", False, "Shifts key up near the end of the song."))
        for text, name, val, tp in toggles:
            cb3 = ttk.Checkbutton(r3, text=text, variable=self.mk(tk.BooleanVar, name, val, "music"))
            cb3.pack(side="left", padx=5)
            self.tip(cb3, tp)
    def build_structure_tab(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill="x", pady=6)
        lab = ttk.Label(top, text="Preset")
        lab.pack(side="left")
        self.tip(lab, "Quick song layout templates.")
        self.g["structpreset"] = tk.StringVar(value="Verse/Chorus")
        cb = self.combo(top, self.g["structpreset"], list(STRUCT_PRESETS), 20)
        cb.pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", self.load_struct_preset)
        self.tip(cb, "Load a ready made section layout.")
        ttk.Label(top, text="Same label sections reuse the same motif automatically.").pack(side="left", padx=10)
        mid = ttk.Frame(parent)
        mid.pack(fill="both", expand=True, pady=6)
        self.seclist = tk.Listbox(mid, height=8, bg="#2b2d3d", fg=FG, selectbackground=ACC, highlightthickness=0, bd=0)
        self.seclist.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.tip(self.seclist, "The current section order, top to bottom.")
        ctl = ttk.Frame(mid)
        ctl.pack(side="left", fill="y")
        self.g["sec_label"] = tk.StringVar(value="A")
        lc = ttk.Combobox(ctl, textvariable=self.g["sec_label"], values=SECTION_TYPES, width=10)
        lc.pack(pady=2)
        self.tip(lc, "Label for the next section to add.")
        self.g["sec_bars"] = tk.IntVar(value=8)
        sb = ttk.Spinbox(ctl, from_=1, to=64, textvariable=self.g["sec_bars"], width=6)
        sb.pack(pady=2)
        self.tip(sb, "Length of the next section in bars.")
        b1 = ttk.Button(ctl, text="Add", command=self.add_section)
        b1.pack(fill="x", pady=2)
        self.tip(b1, "Add this section to the end.")
        b2 = ttk.Button(ctl, text="Remove", command=self.remove_section)
        b2.pack(fill="x", pady=2)
        self.tip(b2, "Remove the selected section.")
        b3 = ttk.Button(ctl, text="Move Up", command=lambda: self.move_section(-1))
        b3.pack(fill="x", pady=2)
        self.tip(b3, "Move the selected section earlier.")
        b4 = ttk.Button(ctl, text="Move Down", command=lambda: self.move_section(1))
        b4.pack(fill="x", pady=2)
        self.tip(b4, "Move the selected section later.")
        self.sec_total = tk.StringVar()
        ttk.Label(parent, textvariable=self.sec_total).pack(anchor="w")
        self.refresh_sections()
    def build_motif_tab(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill="x", pady=6)
        lab = ttk.Label(top, text="Section")
        lab.pack(side="left")
        self.tip(lab, "Which section's core melody to view or edit.")
        self.g["motif_label"] = tk.StringVar(value="")
        self.motif_combo = ttk.Combobox(top, textvariable=self.g["motif_label"], values=[], state="readonly", width=14)
        self.motif_combo.pack(side="left", padx=4)
        self.motif_combo.bind("<<ComboboxSelected>>", lambda e: self.draw_motif())
        self.tip(self.motif_combo, "Pick a section label to view its motif.")
        b1 = ttk.Button(top, text="Regenerate Motif", command=self.regen_motif)
        b1.pack(side="left", padx=6)
        self.tip(b1, "Roll a brand new core melody for this label.")
        ttk.Label(top, text="Drag a note to move it, drag empty space to add one, right click to delete.").pack(side="left", padx=10)
        self.motifcanvas = tk.Canvas(parent, bg="#12131a", height=220, highlightthickness=0)
        self.motifcanvas.pack(fill="x", padx=4, pady=4)
        self.motifcanvas.bind("<Configure>", lambda e: self.draw_motif())
        self.motifcanvas.bind("<ButtonPress-1>", self.motif_press)
        self.motifcanvas.bind("<B1-Motion>", self.motif_drag)
        self.motifcanvas.bind("<ButtonRelease-1>", self.motif_release)
        self.motifcanvas.bind("<Button-3>", self.motif_delete)
        self.tip(self.motifcanvas, "The one bar motif used by this section label.")
    def build_channels_tab(self, parent):
        for i, h in enumerate(HEADERS):
            ttk.Label(parent, text=h).grid(row=0, column=i)
        for i, name in enumerate(CHANNELS):
            self.channel_row(parent, i + 1, name)
    def build_output_tab(self, parent):
        c1 = ttk.Checkbutton(parent, text="Echo", variable=self.mk(tk.BooleanVar, "echo", True, "mix"))
        c1.pack(side="left", padx=4, pady=6)
        self.tip(c1, "Turns the delay effect on or off.")
        c2 = ttk.Checkbutton(parent, text="Ping-pong", variable=self.mk(tk.BooleanVar, "pp", True, "mix"))
        c2.pack(side="left", padx=4)
        self.tip(c2, "Bounces the echo between left and right.")
        for text, name, cls, val, lo, hi, res, tp in FX:
            self.field(parent, text, self.mk(cls, name, val, "mix"), lo, hi, res, 85, tp).pack(side="left", padx=4)
    def channel_row(self, cf, row, name):
        d = DEFAULTS[name]
        v = {}
        self.cv[name] = v
        def mk(key, cls, val, kind=None):
            var = cls(value=val)
            v[key] = var
            if kind:
                var.trace_add("write", lambda *a: self.changed(kind, name))
            return var
        tk.Label(cf, text=name, bg=COLORS[name], fg="#111111", width=8).grid(row=row, column=0, padx=3, pady=2)
        on = ttk.Checkbutton(cf, variable=mk("on", tk.BooleanVar, True, "mix"))
        on.grid(row=row, column=1)
        self.tip(on, f"Mutes or unmutes {name}.")
        solo = ttk.Checkbutton(cf, variable=mk("solo", tk.BooleanVar, False, "mix"))
        solo.grid(row=row, column=2)
        self.tip(solo, f"Solos {name}, muting the rest.")
        wc = self.combo(cf, mk("wave", tk.StringVar, d["wave"], "voice"), KITS if name == "Drums" else WAVES, 10)
        wc.grid(row=row, column=3, padx=3)
        Tooltip(wc, lambda nm=name: (KIT_INFO if nm == "Drums" else WAVE_INFO).get(v["wave"].get(), ""))
        for i, (key, cls, lo, hi, res, kind, tp) in enumerate(SLIDERS):
            var = mk(key, cls, d.get(key, 0), kind)
            if name == "Drums" and kind == "voice":
                continue
            sl = self.slider(cf, var, lo, hi, res, 66)
            sl.grid(row=row, column=4 + i)
            self.tip(sl, tp)
        k = len(SLIDERS)
        e = ttk.Entry(cf, textvariable=mk("seed", tk.IntVar, random.randrange(1, 2 ** 31)), width=11)
        e.grid(row=row, column=4 + k, padx=3)
        e.bind("<Return>", lambda ev: self.request(ev=[name], play=self.g["autoplay"].get(), delay=0))
        self.tip(e, f"Random seed for {name}, press enter to apply.")
        lock = ttk.Checkbutton(cf, variable=mk("lock", tk.BooleanVar, False))
        lock.grid(row=row, column=5 + k)
        self.tip(lock, f"Keeps {name} unchanged when using Generate All.")
        rg = ttk.Button(cf, text="Regen", width=7, command=lambda: self.regen(name))
        rg.grid(row=row, column=6 + k, padx=3)
        self.tip(rg, f"Reroll only {name}.")
        rs = ttk.Button(cf, text="Reset", width=7, command=lambda: self.reset_channel(name))
        rs.grid(row=row, column=7 + k, padx=3)
        self.tip(rs, f"Reset {name} waveform to the current style.")
    def changed(self, kind, name=None):
        if kind == "music":
            self.request(ev=CHANNELS, song=True, delay=450)
        elif kind == "timing":
            self.request(rn=CHANNELS, delay=300)
        elif kind == "voice":
            self.request(rn=[name], delay=250)
        else:
            self.request(delay=120)
    def apply_preset(self):
        for k, val in PRESETS[self.g["preset"].get()].items():
            if k == "waves":
                self.style_waves = dict(val)
                for name, wv in val.items():
                    self.cv[name]["wave"].set(wv)
            else:
                self.g[k].set(val)
    def apply_mood(self, e=None):
        name = self.g["mood"].get()
        if name not in MOODS:
            return
        m = MOODS[name]
        rr = random.Random()
        self.g["scale"].set(rr.choice(m["scales"]))
        self.g["bpm"].set(rr.randint(*m["bpm"]))
        self.g["complexity"].set(rr.randint(*m["cx"]))
        self.g["swing"].set(round(rr.uniform(*m["swing"]), 2))
        self.g["time"].set(rr.choice(m["time"]))
        for k, val in m["flags"].items():
            self.g[k].set(val)
    def apply_genre(self, e=None):
        name = self.g["genre"].get()
        if name not in GENRES:
            return
        m = GENRES[name]
        rr = random.Random()
        self.g["scale"].set(rr.choice(m["scales"]))
        self.g["bpm"].set(rr.randint(*m["bpm"]))
        self.g["complexity"].set(rr.randint(*m["cx"]))
        self.g["swing"].set(round(rr.uniform(*m["swing"]), 2))
        self.g["time"].set(rr.choice(m["time"]))
        for k, val in m["flags"].items():
            self.g[k].set(val)
        self.style_waves = dict(m["waves"])
        for cname, wv in m["waves"].items():
            self.cv[cname]["wave"].set(wv)
    def reset_channel(self, name):
        wv = self.style_waves.get(name, DEFAULTS[name]["wave"])
        self.cv[name]["wave"].set(wv)
    def refresh_sections(self):
        self.seclist.delete(0, "end")
        for label, bars in self.sections:
            self.seclist.insert("end", f"{label}  ({bars} bars)")
        total = sum(b for _, b in self.sections)
        self.sec_total.set(f"Total: {total} bars")
        self.refresh_motif_labels()
    def refresh_motif_labels(self):
        labels = []
        for l, _ in self.sections:
            if l not in labels:
                labels.append(l)
        if hasattr(self, "motif_combo"):
            self.motif_combo["values"] = labels
            if self.g["motif_label"].get() not in labels and labels:
                self.g["motif_label"].set(labels[0])
            self.draw_motif()
    def load_struct_preset(self, e=None):
        self.sections = [tuple(x) for x in STRUCT_PRESETS[self.g["structpreset"].get()]]
        self.refresh_sections()
        self.request(ev=CHANNELS, song=True, play=self.g["autoplay"].get(), delay=0)
    def add_section(self):
        label = self.g["sec_label"].get().strip() or "A"
        bars = max(1, self.g["sec_bars"].get())
        self.sections.append((label, bars))
        self.refresh_sections()
        self.request(ev=CHANNELS, song=True, play=self.g["autoplay"].get(), delay=0)
    def remove_section(self):
        sel = self.seclist.curselection()
        if not sel or len(self.sections) <= 1:
            return
        del self.sections[sel[0]]
        self.refresh_sections()
        self.request(ev=CHANNELS, song=True, play=self.g["autoplay"].get(), delay=0)
    def move_section(self, delta):
        sel = self.seclist.curselection()
        if not sel:
            return
        i = sel[0]
        j = i + delta
        if 0 <= j < len(self.sections):
            self.sections[i], self.sections[j] = self.sections[j], self.sections[i]
            self.refresh_sections()
            self.seclist.selection_set(j)
            self.request(ev=CHANNELS, song=True, play=self.g["autoplay"].get(), delay=0)
    def motif_spb(self):
        return sum(TIME_SIGS[self.g["time"].get()])
    def motif_pattern(self):
        label = self.g["motif_label"].get()
        if not label:
            return []
        if label not in self.motif_cache:
            if label in self.motifs:
                self.motif_cache[label] = list(self.motifs[label])
            else:
                seed = abs(hash((label, self.g["master_seed"].get()))) % (2 ** 31)
                self.motif_cache[label] = generate_motif(self.g["scale"].get(), self.g["complexity"].get(), self.g["time"].get(), seed)
        return self.motif_cache[label]
    def commit_motif(self, label, pattern):
        self.motif_cache[label] = pattern
        self.motifs[label] = list(pattern)
        self.request(ev=["Lead"], song=True, delay=0)
    def regen_motif(self):
        label = self.g["motif_label"].get()
        if not label:
            return
        seed = random.randrange(1, 2 ** 31)
        pat = generate_motif(self.g["scale"].get(), self.g["complexity"].get(), self.g["time"].get(), seed)
        self.commit_motif(label, pat)
        self.draw_motif()
    def draw_motif(self):
        if not hasattr(self, "motifcanvas"):
            return
        c = self.motifcanvas
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if w < 10:
            return
        spb = self.motif_spb()
        pat = self.motif_pattern()
        sx = w / max(1, spb)
        lo, hi = -6, 6
        ph = h / (hi - lo)
        for s in range(0, spb + 1):
            x = s * sx
            c.create_line(x, 0, x, h, fill="#2a2c3d")
        self.motif_rects = []
        for i, (s, d, deg) in enumerate(pat):
            x0, x1 = s * sx, (s + d) * sx
            y0 = (hi - deg) * ph
            y1 = y0 + max(2, ph)
            c.create_rectangle(x0, y0, x1, y1, fill=COLORS.get("Lead", "#f7768e"), outline="")
            self.motif_rects.append((x0, y0, x1, y1, i))
    def motif_geom(self):
        w, h = self.motifcanvas.winfo_width(), self.motifcanvas.winfo_height()
        spb = self.motif_spb()
        sx = w / max(1, spb)
        lo, hi = -6, 6
        ph = h / (hi - lo)
        return sx, ph, hi, lo
    def motif_press(self, e):
        self.motif_drag_state = None
        for x0, y0, x1, y1, i in reversed(self.motif_rects):
            if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                self.motif_drag_state = dict(idx=i, sx=e.x, sy=e.y, orig=(x0, y0, x1, y1))
                return
        self.motif_drag_state = dict(idx=None, sx=e.x, sy=e.y, orig=None)
    def motif_drag(self, e):
        st = self.motif_drag_state
        if not st:
            return
        sx, ph, hi, lo = self.motif_geom()
        self.motifcanvas.delete("dragpreview")
        if st["idx"] is not None and st["orig"]:
            x0, y0, x1, y1 = st["orig"]
            dstep = round((e.x - st["sx"]) / sx)
            ddeg = -round((e.y - st["sy"]) / ph)
            nx0, nx1 = x0 + dstep * sx, x1 + dstep * sx
            ny0, ny1 = y0 - ddeg * ph, y1 - ddeg * ph
            self.motifcanvas.create_rectangle(nx0, ny0, nx1, ny1, outline="white", width=2, dash=(4, 2), tags="dragpreview")
        else:
            x0, x1 = min(st["sx"], e.x), max(st["sx"], e.x)
            deg = round(hi - e.y / ph)
            y0 = (hi - deg) * ph
            y1 = y0 + max(2, ph)
            self.motifcanvas.create_rectangle(x0, y0, x1, y1, outline="white", width=2, dash=(4, 2), tags="dragpreview")
    def motif_release(self, e):
        st = self.motif_drag_state
        self.motif_drag_state = None
        if not st:
            return
        sx, ph, hi, lo = self.motif_geom()
        spb = self.motif_spb()
        label = self.g["motif_label"].get()
        if not label:
            return
        pat = list(self.motif_pattern())
        if st["idx"] is not None:
            s0, d0, deg0 = pat[st["idx"]]
            dstep = round((e.x - st["sx"]) / sx)
            ddeg = -round((e.y - st["sy"]) / ph)
            ns = max(0, min(spb - 1, s0 + dstep))
            pat[st["idx"]] = (ns, d0, deg0 + ddeg)
        else:
            s0 = max(0, min(spb - 1, int(st["sx"] / sx)))
            s1 = max(0, min(spb - 1, int(e.x / sx)))
            step = min(s0, s1)
            dur = max(1, abs(s1 - s0) + 1)
            deg = round(hi - e.y / ph)
            pat.append((step, dur, deg))
        self.commit_motif(label, pat)
        self.draw_motif()
        self.motif_drag_state = None
    def motif_delete(self, e):
        label = self.g["motif_label"].get()
        if not label:
            return
        pat = list(self.motif_pattern())
        for x0, y0, x1, y1, i in reversed(self.motif_rects):
            if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                del pat[i]
                self.commit_motif(label, pat)
                self.draw_motif()
                return
    def request(self, ev=(), rn=(), song=False, play=False, delay=150):
        p = self.pend
        p["ev"] |= set(ev)
        p["rn"] |= set(rn)
        p["song"] |= song
        p["play"] |= play
        if self.timer:
            self.after_cancel(self.timer)
        self.timer = self.after(delay, self.dispatch)
    def seedval(self, var):
        try:
            return int(var.get()) % (2 ** 31)
        except (tk.TclError, ValueError):
            return 0
    def snapshot(self):
        g = self.g
        P = {k: g[k].get() for k in ("bpm", "key", "scale", "time", "complexity", "swing", "extended", "ornaments", "sync", "fills", "modulate", "echo", "delay", "fb", "emix", "pp", "bits", "hold", "soft", "master")}
        P["master_seed"] = self.seedval(g["master_seed"])
        P["sections"] = list(self.sections)
        P["motifs"] = dict(self.motifs)
        P["ch"] = {}
        for name in CHANNELS:
            c = {k: v.get() for k, v in self.cv[name].items() if k != "seed"}
            c["seed"] = self.seedval(self.cv[name]["seed"])
            P["ch"][name] = c
        return P
    def dispatch(self):
        self.timer = None
        job = dict(self.pend)
        job["P"] = self.snapshot()
        self.pend = {"ev": set(), "rn": set(), "song": False, "play": False}
        self.jobs.put(job)
        self.status.set("Rendering...")
    def regen(self, name):
        self.cv[name]["seed"].set(random.randrange(1, 2 ** 31))
        self.request(ev=[name], play=self.g["autoplay"].get(), delay=0)
    def regenerate_all(self, play=True):
        self.g["master_seed"].set(random.randrange(1, 2 ** 31))
        for name in CHANNELS:
            if not self.cv[name]["lock"].get():
                self.cv[name]["seed"].set(random.randrange(1, 2 ** 31))
        self.request(ev=CHANNELS, song=True, play=play and self.g["autoplay"].get(), delay=0)
    def worker(self):
        while True:
            job = self.jobs.get()
            if job is None:
                return
            try:
                while True:
                    nxt = self.jobs.get_nowait()
                    if nxt is None:
                        return
                    nxt["ev"] |= job["ev"]
                    nxt["rn"] |= job["rn"]
                    nxt["song"] |= job["song"]
                    nxt["play"] |= job["play"]
                    job = nxt
            except queue.Empty:
                pass
            try:
                t = time.time()
                audio, ev, steps = self.engine.run(job)
                self.results.put(("ok", audio, ev, steps, job["play"], time.time() - t))
            except Exception as e:
                traceback.print_exc()
                self.results.put(("err", repr(e)))
    def poll(self):
        last = None
        while True:
            try:
                last = self.results.get_nowait()
            except queue.Empty:
                break
        if last:
            if last[0] == "ok":
                _, self.audio, self.events, self.steps, play, dt = last
                self.status.set(f"Ready: {len(self.audio) / SR:.1f}s loop, rendered in {dt:.2f}s")
                self.draw()
                if play or (self.playing and self.g["autoplay"].get()):
                    self.play()
            else:
                self.status.set("Error: " + last[1])
        self.tick()
        self.draw_wave()
        self.after(17, self.poll)
    def draw(self):
        c = self.canvas
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        song = self.engine.song
        if not self.events or self.steps == 0 or w < 10 or song is None:
            return
        mel = [e for k, ev in self.events.items() if k != "Drums" for e in ev]
        lo = min((e[2] for e in mel), default=40) - 1
        hi = max((e[2] for e in mel), default=80) + 2
        hm = h * 0.78
        ph = hm / (hi - lo)
        sx = w / self.steps
        for b in range(0, self.steps, song.spb):
            c.create_line(b * sx, 0, b * sx, h, fill="#2a2c3d")
        x = 0
        for label, bars in song.sections:
            c.create_line(x * sx, 0, x * sx, h, fill="#454866", width=2)
            c.create_text(x * sx + 4, 8, text=label, fill="#8a8dab", anchor="nw", font=("TkDefaultFont", 8))
            x += bars * song.spb
        self.note_rects = []
        for k in CHANNELS:
            if not self.vis[k].get():
                continue
            for idx, (s, d, m, v) in enumerate(self.events.get(k, ())):
                if k == "Drums":
                    y = hm + (m % 7) * (h - hm) / 7
                    c.create_rectangle(s * sx, y, s * sx + max(2, sx), y + (h - hm) / 7 - 1, fill=COLORS[k], outline="")
                else:
                    y0 = (hi - m) * ph
                    x0, x1 = s * sx, (s + d) * sx
                    y1 = y0 + max(2, ph)
                    c.create_rectangle(x0, y0, x1, y1, fill=COLORS[k], outline="")
                    self.note_rects.append((x0, y0, x1, y1, k, idx))
        c.create_line(-5, 0, -5, h, fill="#ffffff", tag="ph")
    def note_geom(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        mel = [ev for kk, evl in self.events.items() if kk != "Drums" for ev in evl]
        lo = min((ev[2] for ev in mel), default=40) - 1
        hi = max((ev[2] for ev in mel), default=80) + 2
        hm = h * 0.78
        ph = hm / (hi - lo) if hi > lo else 1.0
        sx = w / self.steps if self.steps else 1.0
        return sx, ph, hi, lo, hm
    def canvas_press(self, e):
        self.drag_state = None
        for x0, y0, x1, y1, k, idx in reversed(self.note_rects):
            if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                self.drag_state = dict(ch=k, idx=idx, sx=e.x, sy=e.y, orig=(x0, y0, x1, y1))
                return
    def canvas_drag(self, e):
        st = self.drag_state
        if not st:
            return
        sx, ph, hi, lo, hm = self.note_geom()
        dstep = round((e.x - st["sx"]) / sx)
        ddeg = -round((e.y - st["sy"]) / ph)
        x0, y0, x1, y1 = st["orig"]
        nx0, nx1 = x0 + dstep * sx, x1 + dstep * sx
        ny0, ny1 = y0 - ddeg * ph, y1 - ddeg * ph
        self.canvas.delete("dragpreview")
        self.canvas.create_rectangle(nx0, ny0, nx1, ny1, outline="white", width=2, dash=(4, 2), tags="dragpreview")
    def canvas_release(self, e):
        st = self.drag_state
        self.drag_state = None
        self.canvas.delete("dragpreview")
        if not st or self.steps == 0:
            return
        sx, ph, hi, lo, hm = self.note_geom()
        dstep = round((e.x - st["sx"]) / sx)
        ddeg = -round((e.y - st["sy"]) / ph)
        evs = self.engine.ev.get(st["ch"])
        if not evs or st["idx"] >= len(evs):
            return
        s, d, m, v = evs[st["idx"]]
        ns = max(0, s + dstep)
        nm = m + ddeg
        evs[st["idx"]] = (ns, d, nm, v)
        if st["ch"] in self.events:
            lst = list(self.events[st["ch"]])
            if st["idx"] < len(lst):
                lst[st["idx"]] = (ns, d, nm, v)
                self.events[st["ch"]] = lst
        self.request(rn=[st["ch"]], delay=0)
        self.draw()
    def draw_wave(self):
        if not hasattr(self, "wave_canvases"):
            return
        aud = self.audio
        n = len(aud) if aud is not None else 0
        idx = int((time.time() - self.t0) * SR) if (self.playing and n) else 0
        for name, cv in self.wave_canvases.items():
            cv.delete("wave")
            if not self.cv[name]["on"].get():
                continue
            w = int(cv["width"])
            h = int(cv["height"])
            buf = self.engine.buf.get(name)
            if buf is None or len(buf) == 0:
                cv.create_text(4, 4, text=name, fill=COLORS[name], anchor="nw", font=("TkDefaultFont", 7), tags="wave")
                continue
            bn = len(buf)
            i2 = idx % bn
            span = min(bn, max(200, w * 4))
            end = i2 + span
            if end <= bn:
                seg = buf[i2:end]
            else:
                seg = np.concatenate([buf[i2:bn], buf[0:end - bn]])
            step = max(1, len(seg) // w)
            seg = seg[::step][:w]
            mx = float(np.max(np.abs(seg))) if len(seg) else 0.0
            seg = seg / mx if mx > 1e-6 else seg
            pts = []
            for i, val in enumerate(seg):
                pts.append(float(i))
                pts.append(h / 2 - val * (h / 2 - 6))
            if len(pts) >= 4:
                cv.create_line(*pts, fill="white", tags="wave")
            cv.create_line(0, h / 2, w, h / 2, fill="#333333", tags="wave")
            cv.create_text(4, 4, text=name, fill=COLORS[name], anchor="nw", font=("TkDefaultFont", 7), tags="wave")
    def tick(self):
        if not self.playing or self.audio is None:
            return
        dur = len(self.audio) / SR
        el = time.time() - self.t0
        loop = self.g["loop"].get()
        if self.proc is not None and self.proc.poll() is not None:
            if loop:
                self.play()
                return
            self.stop()
            return
        if el > dur and not loop:
            self.stop()
            return
        x = (el % dur) / dur * self.canvas.winfo_width()
        self.canvas.coords("ph", x, 0, x, self.canvas.winfo_height())
    def play(self):
        if self.audio is None:
            return
        self.stop()
        loop = self.g["loop"].get()
        try:
            if sdev is not None:
                sdev.play(self.audio, SR, loop=loop)
            else:
                self.counter += 1
                path = os.path.join(tempfile.gettempdir(), f"bitbox_{os.getpid()}_{self.counter}.wav")
                save_wav(path, self.audio)
                self.tmp.append(path)
                if winsound:
                    winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC | (winsound.SND_LOOP if loop else 0))
                else:
                    cmd = next((c for c in PLAYERS if shutil.which(c[0])), None)
                    if cmd is None:
                        self.status.set("No audio backend found. Try: pip install sounddevice")
                        return
                    self.proc = subprocess.Popen(cmd + [path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            self.status.set(f"Playback error: {e}")
            return
        self.t0 = time.time()
        self.playing = True
    def stop(self):
        self.playing = False
        try:
            if sdev is not None:
                sdev.stop()
            if winsound:
                winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass
        if self.proc is not None:
            try:
                self.proc.terminate()
            except Exception:
                pass
            self.proc = None
        for p in self.tmp:
            try:
                os.remove(p)
            except OSError:
                pass
        self.tmp = []
        self.canvas.coords("ph", -5, 0, -5, 0)
    def export(self):
        if self.audio is None:
            return
        path = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV audio", "*.wav")])
        if path:
            save_wav(path, self.audio)
            self.status.set("Saved " + os.path.basename(path))
    def close(self):
        self.stop()
        self.jobs.put(None)
        self.destroy()
if __name__ == "__main__":
    App().mainloop()
