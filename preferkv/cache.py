"""PrefixCache: a prefix-aware cache with pluggable eviction and persistent
frequency --- the reusable core of the paper.

Model. Each request is a sequence of *blocks* (hashable ids: KV-block ids, token
ids, prompt-chunk hashes...). The cache stores blocks in a radix tree and reuses the
longest cached prefix of each request. When it exceeds ``capacity`` cached blocks it
evicts cached leaves by the chosen policy, keeping the set prefix-closed.

Two ways to use it:

* Serving / measurement --- ``access(blocks)`` replays a request and returns how many
  leading blocks hit the cache (the prefix-cache hit length). This is what the
  simulator and advisor use.
* Application cache --- ``put(key, value)`` / ``get(key)`` treat the block sequence
  as a key and store a value at its leaf (e.g. a computed prefix state or response).

Complexity note: eviction uses a lazy min-heap of cached leaves, so each eviction is
amortized O(log n). Stale entries --- a node that was evicted, is no longer a leaf, or
whose priority rose since it was pushed --- are validated out on pop; because
priorities are monotone non-decreasing, the lazy re-push is exact.
"""
from __future__ import annotations

import heapq
from typing import Iterable, Optional, Tuple

from .node import Node
from .persist import PersistentFrequency, OFFSET, fnv1a
from .policies import get_policy


class PrefixCache:
    def __init__(self, capacity: int, policy="prefer", persist_cap: int = 1_000_000):
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        self.capacity = capacity
        self.policy = get_policy(policy)
        self.persist = PersistentFrequency(cap=persist_cap)
        self.root = Node(block_id=None, parent=None, depth=0)
        self._cached: set[Node] = set()
        self._heap: list = []          # lazy min-heap of (priority, seq, node)
        self._seq = 0
        self.tick = 0
        # lifetime stats
        self.total_blocks = 0
        self.hit_blocks = 0

    # ---- core primitive -----------------------------------------------------
    def access(self, blocks: Iterable, value=None) -> int:
        """Replay a request for ``blocks``; insert its path; evict to capacity.

        Returns the number of leading blocks that were already cached (the
        prefix-cache hit length for this request).
        """
        self.tick += 1
        node = self.root
        h = OFFSET
        hit = 0
        counting = True
        path = []
        for bid in blocks:
            h = fnv1a(h, bid if isinstance(bid, int) else hash(bid))
            child = node.children.get(bid)
            if child is None:
                child = Node(bid, node, node.depth + 1, h)
                node.children[bid] = child
                node.children_ever += 1
            if counting and child.cached:
                hit += 1
            else:
                counting = False
            child.phash = h
            self.persist.bump(h)
            node = child
            path.append(child)

        for nd in path:
            if not nd.cached:
                nd.cached = True
                self._cached.add(nd)
            nd.last_access = self.tick
        if value is not None and path:
            path[-1].value = value
        if path:
            self._push(path[-1])        # the request's endpoint is a cached leaf

        self._evict_to_capacity()

        self.total_blocks += len(path)
        self.hit_blocks += hit
        return hit

    # ---- application-cache convenience --------------------------------------
    def put(self, key: Iterable, value) -> None:
        self.access(key, value=value)

    def get(self, key: Iterable) -> Optional[object]:
        """Return the value stored at the exact key if fully cached, else None.
        Refreshes recency/frequency on a hit (a real cache read counts as use)."""
        blocks = list(key)
        node, ok = self._walk_existing(blocks)
        if ok and node.cached and all(n.cached for n in self._path_nodes(blocks)):
            self.access(blocks)  # touch
            return node.value
        return None

    def longest_prefix(self, blocks: Iterable) -> int:
        """Read-only: length of the longest cached prefix of ``blocks``."""
        node = self.root
        hit = 0
        for bid in blocks:
            child = node.children.get(bid)
            if child is None or not child.cached:
                break
            hit += 1
            node = child
        return hit

    # ---- eviction -----------------------------------------------------------
    def _push(self, node: Node) -> None:
        heapq.heappush(self._heap, (self.policy.priority(node, self), self._seq, node))
        self._seq += 1

    def _evict_to_capacity(self) -> None:
        while len(self._cached) > self.capacity:
            victim = self._pick_victim()
            if victim is None:                    # safety: rebuild from scratch
                self._rebuild_heap()
                victim = self._pick_victim()
                if victim is None:
                    break
            parent = victim.parent
            victim.cached = False
            victim.value = None
            self._cached.discard(victim)
            if parent is not None and parent.is_cached_leaf():
                self._push(parent)                # parent may now be evictable

    def _pick_victim(self) -> Optional[Node]:
        """Pop the lowest-priority valid cached leaf from the lazy heap.

        Heap entries can be stale (node evicted, no longer a leaf, or its priority
        rose since it was pushed). Priorities are monotone non-decreasing (frequency,
        branchiness and recency only grow), so a stale key is always <= the current
        one: we re-push the refreshed key and keep popping, never evicting wrongly.
        """
        h = self._heap
        while h:
            key, _, node = heapq.heappop(h)
            if not node.cached or not node.is_cached_leaf():
                continue
            cur = self.policy.priority(node, self)
            if cur != key:
                heapq.heappush(h, (cur, self._seq, node))
                self._seq += 1
                continue
            return node
        return None

    def _rebuild_heap(self) -> None:
        self._heap = []
        self._seq = 0
        for n in self._cached:
            if n.is_cached_leaf():
                self._push(n)

    # ---- helpers ------------------------------------------------------------
    def freq(self, node: Node) -> int:
        """Persistent access frequency of ``node``'s prefix (survives eviction)."""
        return self.persist.get(node.phash)

    def _walk_existing(self, blocks) -> Tuple[Node, bool]:
        node = self.root
        for bid in blocks:
            child = node.children.get(bid)
            if child is None:
                return node, False
            node = child
        return node, True

    def _path_nodes(self, blocks):
        node = self.root
        out = []
        for bid in blocks:
            node = node.children[bid]
            out.append(node)
        return out

    @property
    def hit_rate(self) -> float:
        return self.hit_blocks / self.total_blocks if self.total_blocks else 0.0

    @property
    def size(self) -> int:
        return len(self._cached)
