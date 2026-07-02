"""Replay a block trace through the cache under a policy, plus a prefix-aware Belady
oracle used as an achievable reference by the advisor."""
from __future__ import annotations

import bisect
from typing import List, Sequence

from .cache import PrefixCache
from .persist import OFFSET, fnv1a
from .policies import LRU


def _bid(b):
    return b if isinstance(b, int) else hash(b)


def simulate(trace: Sequence[Sequence], capacity: int, policy="prefer") -> float:
    """Block-weighted prefix-cache hit rate of ``policy`` on ``trace``."""
    cache = PrefixCache(capacity, policy=policy)
    for blocks in trace:
        cache.access(blocks)
    return cache.hit_rate


class _BeladyCache(PrefixCache):
    """PrefixCache whose eviction removes the cached leaf reused farthest in the
    future (Belady's rule, restricted to the prefix-closed set)."""

    def __init__(self, capacity: int, occ: dict):
        super().__init__(capacity, policy=LRU())
        self.occ = occ
        self.cur = 0

    def access_at(self, blocks, i: int) -> int:
        self.cur = i
        return self.access(blocks)

    def _next_use(self, phash: int) -> float:
        lst = self.occ.get(phash)
        if not lst:
            return float("inf")
        j = bisect.bisect_right(lst, self.cur)
        return lst[j] if j < len(lst) else float("inf")

    def _pick_victim(self):
        best = None
        best_key = None
        for n in self._cached:
            if not n.is_cached_leaf():
                continue
            key = (-self._next_use(n.phash),)  # farthest / never -> evicted first
            if best_key is None or key < best_key:
                best_key, best = key, n
        return best


def simulate_belady(trace: Sequence[Sequence], capacity: int) -> float:
    """Achievable-reference hit rate under a prefix-aware Belady oracle."""
    occ: dict = {}
    for i, blocks in enumerate(trace):
        h = OFFSET
        for b in blocks:
            h = fnv1a(h, _bid(b))
            occ.setdefault(h, []).append(i)
    cache = _BeladyCache(capacity, occ)
    for i, blocks in enumerate(trace):
        cache.access_at(blocks, i)
    return cache.hit_rate


def reuse_ceiling(trace: Sequence[Sequence]) -> float:
    """Infinite-cache hit rate: a loose upper bound on any finite cache."""
    return simulate(trace, capacity=10 ** 9, policy="lru")
