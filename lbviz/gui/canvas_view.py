"""Animated diagram: clients -> load balancer -> backends."""

import tkinter as tk

from ..config import (BG, BRIGHT, DEAD, DIM, FONT_B, FONT_S, FONT_XS, GLOW, GRID,
                      MID, WARN)


def _lerp(a, b, t):
    return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t


class NetworkCanvas(tk.Canvas):
    W, H = 840, 540
    PACKET_TIME = 0.8

    def __init__(self, parent, balancer, backends, clients):
        super().__init__(parent, width=self.W, height=self.H, bg=BG,
                         highlightthickness=1, highlightbackground=DIM)
        self.lb = balancer
        self.backends = backends
        self.clients = clients
        self.packets = []
        self.client_pulse = [0.0] * len(clients)
        self.server_pulse = [0.0] * len(backends)

        n, m = len(clients), len(backends)
        self.client_pos = [(80, 70 + i * (self.H - 140) / max(n - 1, 1)) for i in range(n)]
        self.lb_pos = (self.W / 2 - 20, self.H / 2)
        self.server_pos = [(self.W - 120, 75 + i * (self.H - 150) / max(m - 1, 1))
                           for i in range(m)]

    def add_packet(self, client_idx, backend_idx, now):
        self.client_pulse[client_idx] = now
        self.packets.append({"t0": now, "ci": client_idx, "si": backend_idx})

    # ------------------------------------------------------------------
    def draw(self, now):
        self.delete("all")
        self._draw_grid()
        self._draw_links(now)
        self._draw_clients(now)
        self._draw_balancer()
        self._draw_servers(now)
        self._draw_packets(now)
        self.create_text(10, self.H - 10, anchor="sw", fill=DIM, font=FONT_XS,
                         text="packets: client -> LB -> backend (real TCP sockets on 127.0.0.1)")

    def _draw_grid(self):
        for x in range(0, self.W, 40):
            self.create_line(x, 0, x, self.H, fill=GRID)
        for y in range(0, self.H, 40):
            self.create_line(0, y, self.W, y, fill=GRID)

    def _draw_links(self, now):
        lx, ly = self.lb_pos
        for i, (cx, cy) in enumerate(self.client_pos):
            hot = now - self.client_pulse[i] < 0.5
            self.create_line(cx + 40, cy, lx - 60, ly, fill=MID if hot else GLOW,
                             width=2 if hot else 1)
        for i, (sx, sy) in enumerate(self.server_pos):
            b = self.backends[i]
            color = DEAD if not b.healthy else (MID if self.lb.inflight[i] else GLOW)
            self.create_line(lx + 60, ly, sx - 100, sy, fill=color,
                             width=1 + min(self.lb.inflight[i], 4),
                             dash=(4, 4) if not b.healthy else None)

    def _draw_clients(self, now):
        for i, (cx, cy) in enumerate(self.client_pos):
            hot = now - self.client_pulse[i] < 0.3
            self.create_rectangle(cx - 40, cy - 18, cx + 40, cy + 18,
                                  outline=BRIGHT if hot else DIM,
                                  fill=GLOW if hot else BG, width=2)
            self.create_text(cx, cy - 5, text=f"CLIENT {i + 1}", fill=MID, font=FONT_S)
            self.create_text(cx, cy + 8, text=str(self.clients[i]), fill=DIM, font=FONT_XS)

    def _draw_balancer(self):
        lx, ly = self.lb_pos
        self.create_rectangle(lx - 60, ly - 55, lx + 60, ly + 55, outline=BRIGHT,
                              width=3, fill=BG)
        self.create_rectangle(lx - 54, ly - 49, lx + 54, ly + 49, outline=GLOW)
        self.create_text(lx, ly - 28, text="LOAD", fill=BRIGHT, font=("Consolas", 12, "bold"))
        self.create_text(lx, ly - 12, text="BALANCER", fill=BRIGHT,
                         font=("Consolas", 12, "bold"))
        self.create_text(lx, ly + 10, text=self.lb.algorithm, fill=MID, font=FONT_XS)
        self.create_text(lx, ly + 28, text=f"in-flight: {sum(self.lb.inflight)}",
                         fill=DIM, font=FONT_S)

    def _draw_servers(self, now):
        for i, (sx, sy) in enumerate(self.server_pos):
            b = self.backends[i]
            flash = now - self.server_pulse[i] < 0.3
            col = DEAD if not b.healthy else BRIGHT
            self.create_rectangle(sx - 100, sy - 46, sx + 100, sy + 46, outline=col,
                                  width=2, fill=GLOW if flash else BG)
            self.create_text(sx - 92, sy - 32, anchor="w", text=b.name, fill=col, font=FONT_B)
            self.create_text(sx + 92, sy - 32, anchor="e", text=f":{b.port}", fill=DIM,
                             font=FONT_S)
            state = "ONLINE" if b.healthy else ("DOWN" if not b.alive else "UNHEALTHY")
            self.create_text(sx - 92, sy - 14, anchor="w", text=f"{state}  w={b.weight}",
                             fill=MID if b.healthy else DEAD, font=FONT_S)
            self.create_text(sx - 92, sy + 2, anchor="w",
                             text=f"active {self.lb.inflight[i]}   total {b.total}",
                             fill=MID, font=FONT_S)
            bx0, bx1, by = sx - 92, sx + 92, sy + 28
            self.create_rectangle(bx0, by - 6, bx1, by + 6, outline=DIM)
            frac = min(self.lb.inflight[i] / 8, 1)
            if frac and b.healthy:
                self.create_rectangle(bx0 + 1, by - 5, bx0 + 1 + (bx1 - bx0 - 2) * frac,
                                      by + 5, fill=BRIGHT if frac < 0.75 else WARN,
                                      outline="")

    def _draw_packets(self, now):
        lx, ly = self.lb_pos
        alive = []
        for p in self.packets:
            e = (now - p["t0"]) / self.PACKET_TIME
            if e >= 1:
                self.server_pulse[p["si"]] = now
                continue
            alive.append(p)
            cx, cy = self.client_pos[p["ci"]]
            sx, sy = self.server_pos[p["si"]]
            if e < 0.5:
                x, y = _lerp((cx + 40, cy), (lx - 60, ly), e * 2)
            else:
                x, y = _lerp((lx + 60, ly), (sx - 100, sy), (e - 0.5) * 2)
            self.create_oval(x - 8, y - 8, x + 8, y + 8, fill=GLOW, outline="")
            self.create_oval(x - 4, y - 4, x + 4, y + 4, fill=BRIGHT, outline="")
        self.packets = alive