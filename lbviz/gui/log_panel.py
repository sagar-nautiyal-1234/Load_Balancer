"""Terminal-style scrolling log."""

import time
import tkinter as tk

from ..config import BG, BRIGHT, DEAD, DIM, FONT_S, MID


class LogPanel(tk.Text):
    MAX_LINES = 300

    def __init__(self, parent):
        super().__init__(parent, height=9, bg=BG, fg=MID, font=FONT_S, bd=0,
                         highlightthickness=1, highlightbackground=DIM,
                         insertbackground=BRIGHT, state="disabled")
        self.tag_config("bad", foreground=DEAD)
        self.tag_config("hi", foreground=BRIGHT)

    def write(self, msg, tag=None):
        self.config(state="normal")
        self.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}\n", tag)
        if int(self.index("end-1c").split(".")[0]) > self.MAX_LINES:
            self.delete("1.0", "50.0")
        self.see("end")
        self.config(state="disabled")