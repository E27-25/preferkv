"""Synthetic workloads spanning the recency--frequency axis, for demos and tests.

* :func:`make_multitenant` --- many one-shot requests share a few Zipf-popular
  templates reused across distant, interleaved requests (frequency-favorable).
* :func:`make_burst` --- agents step in tight bursts, each step reusing the context
  it just created (recency-favorable).
"""
from __future__ import annotations

import random
from typing import List


def make_multitenant(n_templates: int = 12, n_requests: int = 2000,
                     zipf_a: float = 1.1, seed: int = 0) -> List[list]:
    rng = random.Random(seed)
    nb = 0
    templates = []
    for _ in range(n_templates):
        L = rng.randint(2, 6)
        templates.append(list(range(nb, nb + L)))
        nb += L
    w = [1.0 / ((i + 1) ** zipf_a) for i in range(n_templates)]
    trace = []
    for _ in range(n_requests):
        t = rng.choices(range(n_templates), weights=w)[0]
        path = list(templates[t])
        for _ in range(rng.randint(1, 2)):      # unique one-shot tail
            path.append(nb)
            nb += 1
        trace.append(path)
    return trace


def make_burst(n_sessions: int = 40, steps_each: int = 8, burst: int = 4,
               zipf_a: float = 1.1, seed: int = 0) -> List[list]:
    rng = random.Random(seed)
    nb = 1                                        # block 0 is the shared system prefix
    paths = [[0] for _ in range(n_sessions)]
    remaining = [steps_each] * n_sessions
    w = [1.0 / ((i + 1) ** zipf_a) for i in range(n_sessions)]
    trace = []
    while sum(remaining) > 0:
        live = [i for i in range(n_sessions) if remaining[i] > 0]
        s = rng.choices(live, weights=[w[i] for i in live])[0]
        for _ in range(min(burst, remaining[s])):  # consecutive steps => recency
            paths[s].append(nb)
            nb += 1
            trace.append(list(paths[s]))
            remaining[s] -= 1
    return trace
