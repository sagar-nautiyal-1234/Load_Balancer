"""Simulated clients (random IPv4 addresses) and a Poisson traffic generator."""

import ipaddress
import random
import threading
import time

from .config import CLIENT_COUNT, CLIENT_SUBNET_BASE, DEFAULT_RPS


def make_clients(n=CLIENT_COUNT):
    base = int(ipaddress.IPv4Address(CLIENT_SUBNET_BASE))
    return [ipaddress.IPv4Address(base + random.randint(0, 200)) for _ in range(n)]


class TrafficGenerator:
    def __init__(self, balancer, clients):
        self.balancer = balancer
        self.clients = clients
        self.rate = float(DEFAULT_RPS)      # requests per second
        self.running = False

    def fire(self):
        ci = random.randrange(len(self.clients))
        threading.Thread(target=self.balancer.handle_request,
                         args=(ci, self.clients[ci]), daemon=True).start()

    def burst(self, n=25):
        for _ in range(n):
            self.fire()

    def start(self):
        if self.running:
            return
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self.running = False

    def _loop(self):
        while self.running:
            self.fire()
            time.sleep(random.expovariate(max(self.rate, 1.0)))