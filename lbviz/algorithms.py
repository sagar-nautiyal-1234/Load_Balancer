"""Load-balancing strategies.

Every strategy implements pick(pool, lb, client_ip) and returns the index of a
backend taken from `pool` (indices of currently healthy backends).
`lb` gives access to lb.backends and lb.inflight (in-flight requests per backend).
"""

import random
import zlib


class Algorithm:
    name = "base"

    def pick(self, pool, lb, client_ip):
        raise NotImplementedError


class RoundRobin(Algorithm):
    name = "Round Robin"

    def __init__(self):
        self.counter = 0

    def pick(self, pool, lb, client_ip):
        self.counter += 1
        return pool[self.counter % len(pool)]


class WeightedRoundRobin(Algorithm):
    """Smooth weighted round robin (the nginx variant)."""
    name = "Weighted Round Robin"

    def __init__(self):
        self.current = {}

    def pick(self, pool, lb, client_ip):
        total = sum(lb.backends[i].weight for i in pool)
        for i in pool:
            self.current[i] = self.current.get(i, 0) + lb.backends[i].weight
        best = max(pool, key=lambda i: self.current[i])
        self.current[best] -= total
        return best


class LeastConnections(Algorithm):
    name = "Least Connections"

    def pick(self, pool, lb, client_ip):
        return min(pool, key=lambda i: (lb.inflight[i], i))


class LeastResponseTime(Algorithm):
    """Prefers the backend with the lowest smoothed latency, penalising load."""
    name = "Least Response Time"

    def pick(self, pool, lb, client_ip):
        return min(pool, key=lambda i: (lb.backends[i].ewma_ms * (1 + lb.inflight[i]), i))


class IPHash(Algorithm):
    name = "IP Hash"

    def pick(self, pool, lb, client_ip):
        return pool[zlib.crc32(client_ip.packed) % len(pool)]


class RandomChoice(Algorithm):
    name = "Random"

    def pick(self, pool, lb, client_ip):
        return random.choice(pool)


_ALL = [RoundRobin, WeightedRoundRobin, LeastConnections,
        LeastResponseTime, IPHash, RandomChoice]

ALGORITHM_NAMES = [cls.name for cls in _ALL]


def make(name):
    """Create a fresh strategy instance by display name."""
    for cls in _ALL:
        if cls.name == name:
            return cls()
    raise KeyError(name)