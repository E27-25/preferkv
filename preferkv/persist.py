"""Persistent prefix-frequency map --- the key systems idea.

A prefix cache tracks how often each prefix is used. If that count lives *on the
cache node*, it is destroyed when the node is evicted, so a frequently-evicted but
popular prefix can never accumulate frequency and never gets protected (a
chicken-and-egg that makes frequency-based eviction ineffective on real engines).

`PersistentFrequency` keeps the counts in a side table keyed by a rolling hash of
the prefix's block ids, so the count *survives* eviction. This is what turns
frequency eviction from "no better than LRU" into a real win on the workloads where
frequency matters (see the advisor).

The table is bounded: when it exceeds ``cap`` entries all counts are halved and the
zeros dropped (exponential decay), so memory stays O(cap) regardless of stream
length while recent popularity still dominates.
"""
from __future__ import annotations

_FNV_OFFSET = 0xCBF29CE484222325
_FNV_PRIME = 0x100000001B3
_MASK = 0xFFFFFFFFFFFFFFFF


def fnv1a(h: int, block_id: int) -> int:
    """One FNV-1a step folding ``block_id`` into the running hash ``h``.

    Start a fresh hash from :data:`OFFSET`. Chaining these over a block-id
    sequence yields a stable per-prefix key.
    """
    return ((h ^ (block_id & 0xFFFFFFFF)) * _FNV_PRIME) & _MASK


OFFSET = _FNV_OFFSET


class PersistentFrequency:
    """Global prefix -> access-count table that outlives cache eviction."""

    def __init__(self, cap: int = 1_000_000):
        self._c: dict[int, int] = {}
        self.cap = cap

    def bump(self, prefix_hash: int) -> int:
        """Record one access of the prefix with hash ``prefix_hash``; return count."""
        n = self._c.get(prefix_hash, 0) + 1
        self._c[prefix_hash] = n
        if len(self._c) > self.cap:
            self._decay()
        return n

    def get(self, prefix_hash: int) -> int:
        return self._c.get(prefix_hash, 0)

    def _decay(self) -> None:
        self._c = {k: v >> 1 for k, v in self._c.items() if v > 1}

    def __len__(self) -> int:
        return len(self._c)
