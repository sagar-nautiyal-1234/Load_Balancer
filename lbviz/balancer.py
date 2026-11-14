"""The load balancer: choose a backend, open a real socket, relay, record stats.

Events pushed to the queue (consumed by the GUI):
    ("dispatch", client_idx, backend_idx, client_ip_str)
    ("done", backend_idx, latency_ms, ok)
    ("drop", client_idx, client_ip_str)
"""

import socket
import threading
import time

from . import algorithms
from .config import CONNECT_TIMEOUT, HOST


class LoadBalancer:
    def __init__(self, backends, events):
        self.backends = backends
        self.events = events
        self.lock = threading.Lock()
        self.inflight = [0] * len(backends)
        self.strategy = algorithms.make(algorithms.ALGORITHM_NAMES[0])
        self.sent = self.ok = self.failed = self.dropped = 0
        self.latencies = []

    @property
    def algorithm(self):
        return self.strategy.name

    def set_algorithm(self, name):
        with self.lock:
            self.strategy = algorithms.make(name)

    def pick(self, client_ip):
        with self.lock:
            pool = [i for i, b in enumerate(self.backends) if b.healthy]
            if not pool:
                return None
            return self.strategy.pick(pool, self, client_ip)

    def handle_request(self, client_idx, client_ip):
        """Runs in its own thread, one per request."""
        idx = self.pick(client_ip)
        with self.lock:
            self.sent += 1
        if idx is None:
            with self.lock:
                self.dropped += 1
            self.events.put(("drop", client_idx, str(client_ip)))
            return

        backend = self.backends[idx]
        with self.lock:
            self.inflight[idx] += 1
        self.events.put(("dispatch", client_idx, idx, str(client_ip)))
        t0 = time.time()
        try:
            with socket.create_connection((HOST, backend.port), timeout=CONNECT_TIMEOUT) as s:
                s.sendall(f"GET / {client_ip}\n".encode())
                s.recv(256)
            ms = (time.time() - t0) * 1000
            with self.lock:
                self.ok += 1
                self.latencies = (self.latencies + [ms])[-200:]
                backend.ewma_ms = ms if backend.ewma_ms == 0 else 0.7 * backend.ewma_ms + 0.3 * ms
            self.events.put(("done", idx, ms, True))
        except OSError:
            backend.healthy = False          # passive health check
            with self.lock:
                self.failed += 1
            self.events.put(("done", idx, 0, False))
        finally:
            with self.lock:
                self.inflight[idx] -= 1

    def snapshot(self):
        with self.lock:
            avg = sum(self.latencies) / len(self.latencies) if self.latencies else 0
            return {"sent": self.sent, "ok": self.ok, "failed": self.failed,
                    "dropped": self.dropped, "avg": avg}