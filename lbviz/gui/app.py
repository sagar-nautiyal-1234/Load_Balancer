"""Main window: wires backends, balancer, health checker, traffic and widgets."""

import queue
import time
import tkinter as tk

from ..backend import Backend
from ..balancer import LoadBalancer
from ..config import BG, BRIGHT, DEFAULT_WEIGHTS, DIM, FONT_S, FONT_T, CLIENT_COUNT
from ..health import HealthChecker
from ..traffic import TrafficGenerator, make_clients
from .canvas_view import NetworkCanvas
from .control_panel import ControlPanel
from .log_panel import LogPanel


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LB//VIZ - Load Balancer Visualizer")
        self.configure(bg=BG)
        self.resizable(False, False)

        # --- back end (real sockets) ---
        self.events = queue.Queue()
        self.backends = [Backend(f"SRV-{i + 1}", w) for i, w in enumerate(DEFAULT_WEIGHTS)]
        self.balancer = LoadBalancer(self.backends, self.events)
        self.health = HealthChecker(self.backends, self.events)
        self.health.start()
        self.clients = make_clients(CLIENT_COUNT)
        self.traffic = TrafficGenerator(self.balancer, self.clients)

        # --- widgets ---
        head = tk.Frame(self, bg=BG)
        head.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(head, text="LB//VIZ", font=FONT_T, fg=BRIGHT, bg=BG).pack(side="left")
        tk.Label(head, text="  real TCP backends - live health checks",
                 font=FONT_S, fg=DIM, bg=BG).pack(side="left", pady=(6, 0))

        body = tk.Frame(self, bg=BG)
        body.pack(padx=12)
        self.view = NetworkCanvas(body, self.balancer, self.backends, self.clients)
        self.view.pack(side="left")
        self.panel = ControlPanel(
            body, self.backends,
            on_algorithm=self._on_algorithm, on_rate=self._on_rate,
            on_toggle_traffic=self._on_toggle_traffic, on_burst=self.traffic.burst,
            on_weight=self._on_weight, on_kill=self._on_kill)
        self.panel.pack(side="left", fill="y", padx=(10, 0))
        self.log = LogPanel(self)
        self.log.pack(fill="x", padx=12, pady=(8, 12))

        self.log.write("system ready - backends listening on localhost", "hi")
        for b in self.backends:
            self.log.write(f"{b.name} listening on 127.0.0.1:{b.port}  weight={b.weight}")

        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(33, self._tick)

    # ---- control callbacks ----
    def _on_algorithm(self, name):
        self.balancer.set_algorithm(name)
        self.log.write(f"algorithm -> {name}", "hi")

    def _on_rate(self, rps):
        self.traffic.rate = rps

    def _on_toggle_traffic(self):
        if self.traffic.running:
            self.traffic.stop()
        else:
            self.traffic.start()
        self.panel.set_traffic_running(self.traffic.running)

    def _on_weight(self, i, w):
        self.backends[i].weight = w

    def _on_kill(self, i):
        b = self.backends[i]
        if b.alive:
            b.stop()
            self.log.write(f"{b.name} process killed - port {b.port} closed", "bad")
        else:
            b.start()
            self.log.write(f"{b.name} restarted on :{b.port}", "hi")
        self.panel.set_server_alive(i, b.alive)

    # ---- main loop ----
    def _tick(self):
        now = time.time()
        try:
            while True:
                self._handle_event(self.events.get_nowait(), now)
        except queue.Empty:
            pass
        self.panel.update_stats(self.balancer.snapshot())
        self.view.draw(now)
        self.after(33, self._tick)

    def _handle_event(self, ev, now):
        kind = ev[0]
        if kind == "dispatch":
            _, ci, si, ip = ev
            self.view.add_packet(ci, si, now)
            b = self.backends[si]
            self.log.write(f"{ip:<15} -> {b.name} (:{b.port})  [{self.balancer.algorithm}]")
        elif kind == "done":
            _, si, ms, ok = ev
            if ok:
                self.log.write(f"{self.backends[si].name} replied 200 in {ms:.0f} ms")
            else:
                self.log.write(f"{self.backends[si].name} connection FAILED", "bad")
        elif kind == "health":
            _, name, up = ev
            self.log.write(f"health-check: {name} is {'UP' if up else 'DOWN'}",
                           "hi" if up else "bad")
        elif kind == "drop":
            self.log.write(f"{ev[2]} dropped - no healthy backends!", "bad")

    def _close(self):
        self.traffic.stop()
        self.health.stop()
        for b in self.backends:
            if b.alive:
                b.stop()
        self.destroy()