"""Radix/prefix-tree node for the block cache."""
from __future__ import annotations


class Node:
    """One block in the prefix tree.

    A node is *cached* if its KV block (or cached value) is resident. The cache is
    kept prefix-closed: a node may be cached only while its parent is cached, so the
    only evictable nodes are cached leaves of the cached subtree.
    """

    __slots__ = ("block_id", "parent", "children", "cached", "value",
                 "last_access", "depth", "children_ever", "phash")

    def __init__(self, block_id, parent, depth, phash: int = 0):
        self.block_id = block_id
        self.parent = parent
        self.children: dict = {}
        self.cached = False
        self.value = None
        self.last_access = -1
        self.depth = depth
        self.children_ever = 0     # distinct children ever seen (branchiness signal)
        self.phash = phash         # rolling hash of the root->this prefix

    def is_cached_leaf(self) -> bool:
        """True if cached and no child is currently cached (safe to evict)."""
        if not self.cached:
            return False
        for c in self.children.values():
            if c.cached:
                return False
        return True

    def __repr__(self) -> str:
        return f"Node(id={self.block_id}, depth={self.depth}, cached={self.cached})"
