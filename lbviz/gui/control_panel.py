"""Right-hand control panel: algorithm, traffic, per-server controls, stats."""

import tkinter as tk

from .. import algorithms
from ..config import (BG, BRIGHT, DEFAULT_RPS, DIM, FONT, FONT_B, FONT_S, GLOW,
                      MID, PANEL)


class ControlPanel(tk.Frame):
    def __init__(self, parent, backends, *, on_algorithm, on_rate, on_toggle_traffic,
                 on_burst, on_weight, on_kill):
        super().__init__(parent, bg=PANEL, highlightthickness=1,
                         highlightbackground=DIM, width=260)
        self.pack_propagate(False)
        self.algo_var = tk.StringVar(value=algorithms.ALGORITHM_NAMES[0])
        self.stat_vars = {k: tk.StringVar(value="0")
                          for k in ("sent", "ok", "failed", "dropped", "avg")}
        self.kill_btns = []

        self._section("ALGORITHM")
        menu = tk.OptionMenu(self, self.algo_var, *algorithms.ALGORITHM_NAMES,
                             command=on_algorithm)
        menu.config(bg=BG, fg=BRIGHT, activebackground=GLOW, activeforeground=BRIGHT,
                    font=FONT, highlightthickness=1, highlightbackground=DIM,
                    relief="flat", bd=0, width=22, anchor="w")
        menu["menu"].config(bg=BG, fg=BRIGHT, activebackground=GLOW,
                            activeforeground=BRIGHT, font=FONT)
        menu.pack(padx=10, pady=(0, 6), fill="x")

        self._section("TRAFFIC")
        scale = tk.Scale(self, from_=1, to=30, resolution=1, orient="horizontal",
                         label="requests / sec", bg=PANEL, fg=BRIGHT, troughcolor=BG,
                         highlightthickness=0, font=FONT_S, activebackground=BRIGHT,
                         command=lambda v: on_rate(float(v)))
        scale.set(DEFAULT_RPS)
        scale.pack(padx=10, fill="x")
        row = tk.Frame(self, bg=PANEL)
        row.pack(fill="x", padx=10, pady=4)
        self.start_btn = self._button(row, "> START", on_toggle_traffic)
        self.start_btn.pack(side="left", expand=True, fill="x", padx=(0, 3))
        self._button(row, "! BURST", on_burst).pack(side="left", expand=True,
                                                    fill="x", padx=(3, 0))

        self._section("SERVERS  (weight / power)")
        for i, b in enumerate(backends):
            r = tk.Frame(self, bg=PANEL)
            r.pack(fill="x", padx=10, pady=1)
            tk.Label(r, text=b.name, font=FONT_S, fg=MID, bg=PANEL, width=6).pack(side="left")
            sc = tk.Scale(r, from_=1, to=5, orient="horizontal", length=90,
                          bg=PANEL, fg=BRIGHT, troughcolor=BG, highlightthickness=0,
                          font=FONT_S, activebackground=BRIGHT,
                          command=lambda v, i=i: on_weight(i, int(v)))
            sc.set(b.weight)
            sc.pack(side="left")
            kb = self._button(r, "KILL", lambda i=i: on_kill(i), small=True)
            kb.pack(side="right")
            self.kill_btns.append(kb)

        self._section("STATS")
        for label, key in (("sent", "sent"), ("success", "ok"), ("failed", "failed"),
                           ("dropped", "dropped"), ("avg latency", "avg")):
            r = tk.Frame(self, bg=PANEL)
            r.pack(fill="x", padx=12)
            tk.Label(r, text=label, font=FONT_S, fg=DIM, bg=PANEL).pack(side="left")
            tk.Label(r, textvariable=self.stat_vars[key], font=FONT_B, fg=BRIGHT,
                     bg=PANEL).pack(side="right")

    # ---- helpers ----
    def _section(self, text):
        tk.Label(self, text=f"-- {text} --", font=FONT_B, fg=DIM, bg=PANEL,
                 anchor="w").pack(fill="x", padx=10, pady=(10, 4))

    def _button(self, parent, text, cmd, small=False):
        return tk.Button(parent, text=text, command=cmd, bg=BG, fg=BRIGHT,
                         activebackground=BRIGHT, activeforeground=BG, relief="flat",
                         bd=0, font=FONT_S if small else FONT_B, cursor="hand2",
                         highlightthickness=1, highlightbackground=DIM, padx=6, pady=2)

    # ---- called by the app ----
    def set_traffic_running(self, running):
        self.start_btn.config(text="[] STOP" if running else "> START")

    def set_server_alive(self, i, alive):
        self.kill_btns[i].config(text="KILL" if alive else "REVIVE")

    def update_stats(self, snap):
        self.stat_vars["sent"].set(str(snap["sent"]))
        self.stat_vars["ok"].set(str(snap["ok"]))
        self.stat_vars["failed"].set(str(snap["failed"]))
        self.stat_vars["dropped"].set(str(snap["dropped"]))
        self.stat_vars["avg"].set(f"{snap['avg']:.0f} ms")