"""Load block traces and characterize their reuse structure.

A trace is a sequence of requests; each request is a sequence of block ids (ints or
any hashable). Accepted file formats (JSON Lines), one request per line:

    [12, 45, 9, 88]
    {"blocks": [12, 45, 9, 88]}
    {"hash_ids": [12, 45, 9]}          # Mooncake-style field name

The key diagnostic is the *reuse-recency correlation*: the fraction of block reuses
whose previous use was within the last ``window`` requests. High means recency
predicts reuse (LRU is already good); low means popular blocks come back after long
gaps (frequency wins).
"""
from __future__ import annotations

import json
from typing import List, Sequence


def load_trace(path: str) -> List[list]:
    out: List[list] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                obj = obj.get("blocks") or obj.get("hash_ids") or obj.get("block_ids")
            if obj:
                out.append(list(obj))
    return out


def reuse_recency_corr(trace: Sequence[Sequence], window: int = 8) -> float:
    """Fraction of block reuses whose previous use was <= ``window`` requests ago.

    ~1.0 => recency-heavy (prefer LRU); ~0.0 => gap-heavy (prefer frequency).
    Returns 0.0 if there are no reuses.
    """
    last_seen: dict = {}
    near = total = 0
    for i, blocks in enumerate(trace):
        touched = set()
        for b in blocks:
            if b in touched:
                continue
            touched.add(b)
            if b in last_seen:
                total += 1
                if i - last_seen[b] <= window:
                    near += 1
            last_seen[b] = i
    return near / total if total else 0.0


def trace_stats(trace: Sequence[Sequence], window: int = 8) -> dict:
    from collections import Counter
    counts: Counter = Counter()
    block_refs = 0
    reuse_refs = 0
    for blocks in trace:
        for b in blocks:
            block_refs += 1
            if counts[b]:
                reuse_refs += 1
            counts[b] += 1
    # working set = blocks that are actually reused (referenced >=2 times). This is
    # the scale at which cache pressure matters; one-shot blocks never help.
    working_set = sum(1 for c in counts.values() if c >= 2)
    return {
        "requests": len(trace),
        "unique_blocks": len(counts),
        "working_set": working_set,
        "block_refs": block_refs,
        "reuse_rate_blocks": reuse_refs / block_refs if block_refs else 0.0,
        "reuse_recency_corr": reuse_recency_corr(trace, window),
    }
