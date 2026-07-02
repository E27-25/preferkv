"""Eviction policies. A policy maps a cached leaf to a sortable priority; the cache
evicts the leaf with the *smallest* priority.

* :class:`LRU`    -- evict the least recently used (recency only). The reflexive
  default in vLLM and SGLang.
* :class:`LFU`    -- evict the least frequently used (frequency only).
* :class:`Prefer` -- the searched policy: keep prefixes that are *frequent* and
  *branchy*, with recency only as a tie-break. Beats LRU when reuse is not
  recency-correlated (multi-tenant serving, agent session-resumption). Reduces to
  LFU/LRU at the axis-aligned weight vectors.

Frequency is read from the cache's :class:`~preferkv.persist.PersistentFrequency`
table, so it reflects popularity that survived earlier evictions.
"""
from __future__ import annotations

import math
from typing import Protocol, Tuple


class EvictionPolicy(Protocol):
    name: str

    def priority(self, node, cache) -> Tuple:  # smaller == evicted first
        ...


class LRU:
    name = "lru"

    def priority(self, node, cache) -> Tuple:
        return (node.last_access,)


class LFU:
    name = "lfu"

    def priority(self, node, cache) -> Tuple:
        return (cache.freq(node), node.last_access)


class Prefer:
    """score = w_freq * log(1+freq) + w_branch * log(1+branchiness); recency breaks ties.

    Defaults are the values found by the offline search (frequency dominant,
    branchiness a strong secondary). Zero tree-walk: every term is O(1) at the node.
    """

    name = "prefer"

    def __init__(self, w_freq: float = 1.0, w_branch: float = 0.9):
        self.w_freq = w_freq
        self.w_branch = w_branch

    def priority(self, node, cache) -> Tuple:
        freq = cache.freq(node)
        # branchiness = this prefix's own fan-out (distinct continuations seen).
        # A prefix with many continuations is a shared/popular prefix worth keeping;
        # a one-shot endpoint has none.
        branch = len(node.children) if node.children else 1
        score = self.w_freq * math.log1p(freq) + self.w_branch * math.log1p(branch)
        return (score, node.last_access)


# convenient singletons / factory
def get_policy(name_or_policy):
    """Accept a policy instance or a name ('lru'/'lfu'/'prefer') and return a policy."""
    if not isinstance(name_or_policy, str):
        return name_or_policy
    return {"lru": LRU(), "lfu": LFU(), "prefer": Prefer()}[name_or_policy.lower()]
