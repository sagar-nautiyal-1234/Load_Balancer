"""Active health checker: PINGs every backend over TCP on an interval.

Pushes ("health", backend_name, is_up) onto the event queue on state changes.
"""

import socket
import threading
import time

from .config import HEALTH_INTERVAL, HOST


class HealthChecker(threading.Thread):
    def __init__(self, backends, events, interval=HEALTH_INTERVAL):
        super().__init__(daemon=True)
        self.backends = backends
        self.events = events
        self.interval = interval
        self.running = True

    def run(self):
        while self.running:
            for b in self.backends:
                up = self._ping(b)
                if up != b.healthy:
                    b.healthy = up
                    self.events.put(("health", b.name, up))
            time.sleep(self.interval)

    @staticmethod
    def _ping(backend):
        try:
            with socket.create_connection((HOST, backend.port), timeout=0.4) as s:
                s.sendall(b"PING\n")
                return s.recv(16).startswith(b"PONG")
        except OSError:
            return False

    def stop(self):
        self.running = False