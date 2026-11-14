"""A real TCP backend server that simulates work with a weight-scaled delay."""

import random
import socketserver
import threading
import time

from .config import HOST


class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class Backend:
    def __init__(self, name, weight):
        self.name = name
        self.weight = weight        # "power": higher = faster responses
        self.port = 0
        self.alive = False          # is the server process actually running
        self.healthy = True         # what the load balancer believes
        self.active = 0
        self.total = 0
        self.ewma_ms = 0.0          # smoothed response time seen by the LB
        self.lock = threading.Lock()
        self.server = None
        self.start()

    def start(self):
        backend = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                line = self.rfile.readline()
                if line.startswith(b"PING"):
                    self.wfile.write(b"PONG\n")
                    return
                with backend.lock:
                    backend.active += 1
                try:
                    time.sleep(random.uniform(0.3, 0.9) / backend.weight)
                    self.wfile.write(f"200 OK from {backend.name}\n".encode())
                finally:
                    with backend.lock:
                        backend.active -= 1
                        backend.total += 1

        try:                                    # try to reuse the old port
            self.server = _Server((HOST, self.port), Handler)
        except OSError:
            self.server = _Server((HOST, 0), Handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.alive = True

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        self.alive = False