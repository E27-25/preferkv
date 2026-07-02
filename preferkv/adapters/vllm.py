"""vLLM adapter for PREFER.

vLLM's prefix cache reclaims blocks through an ``Evictor`` (``vllm/core/evictor.py``);
the stock ``LRUEvictor`` evicts by ``last_accessed`` (ties: most hashed tokens).
Unlike SGLang, vLLM's evictor does not see the radix tree, so branchiness is not
available at this layer --- but *frequency* is the dominant term (the paper's ablation:
frequency ~10%, branchiness ~1%), and it is exactly the signal LRU throws away.

:class:`PreferEvictor` mirrors vLLM's ``Evictor`` interface and evicts by
**persistent frequency** (counts keyed by ``content_hash``, surviving eviction),
falling back to recency as a tie-break. Installing it is a one-line swap in vLLM's
block manager; because vLLM's internals move between v0 and v1, this targets the v0
evictor interface and is marked experimental.

    from preferkv.adapters.vllm import PreferEvictor
    # in vllm/core/block_manager: evictor = PreferEvictor()
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Tuple

from ..persist import PersistentFrequency

# One process-wide frequency table shared across evictor instances, so counts
# persist even across cache/block-manager resets.
_PERSIST = PersistentFrequency()


@dataclass
class _Block:
    content_hash: int
    num_hashed_tokens: int
    last_accessed: float


class PreferEvictor:
    """Drop-in replacement for vLLM's ``LRUEvictor`` using persistent-frequency PREFER.

    Priority (evict smallest first): ``(log1p(freq), last_accessed)`` --- least
    frequently used prefix goes first, recency breaks ties. ``freq`` is read from a
    process-wide table keyed by ``content_hash`` and is *not* reset when the block is
    evicted, which is what lets a frequently-evicted-but-popular prefix be protected.
    """

    def __init__(self):
        self.free_table: Dict[int, _Block] = {}

    def __contains__(self, block_id: int) -> bool:
        return block_id in self.free_table

    def add(self, block_id: int, content_hash: int, num_hashed_tokens: int,
            last_accessed: float) -> None:
        self.free_table[block_id] = _Block(content_hash, num_hashed_tokens, last_accessed)
        _PERSIST.bump(content_hash)

    def update(self, block_id: int, last_accessed: float) -> None:
        b = self.free_table.get(block_id)
        if b is not None:
            b.last_accessed = last_accessed
            _PERSIST.bump(b.content_hash)

    def remove(self, block_id: int) -> None:
        self.free_table.pop(block_id, None)

    def evict(self) -> Tuple[int, int]:
        if not self.free_table:
            raise ValueError("no usable cache memory left")
        best_id = None
        best_key = None
        for bid, b in self.free_table.items():
            key = (math.log1p(_PERSIST.get(b.content_hash)), b.last_accessed,
                   -b.num_hashed_tokens)
            if best_key is None or key < best_key:
                best_key, best_id = key, bid
        b = self.free_table.pop(best_id)
        return best_id, b.content_hash

    @property
    def num_blocks(self) -> int:
        return len(self.free_table)


def enable_prefer_vllm() -> bool:
    """Best-effort: register PreferEvictor as vLLM's eviction policy.

    Returns True if the swap was applied. Raises ImportError if vLLM's v0 evictor
    module is not importable. For vLLM v1, install PreferEvictor manually in the
    block manager (the interface is the same).
    """
    try:
        import vllm.core.evictor as ev  # type: ignore
    except Exception as e:  # pragma: no cover - depends on vllm install
        raise ImportError(
            "vllm.core.evictor not importable; this adapter targets vLLM v0's "
            "evictor interface. Install PreferEvictor manually for other versions."
        ) from e
    # make PreferEvictor the default returned by the evictor factory, if present
    if hasattr(ev, "make_evictor"):
        _orig = ev.make_evictor

        def make_evictor(policy=None):  # noqa: ANN001
            return PreferEvictor()
        ev.make_evictor = make_evictor
        ev._preferkv_orig_make_evictor = _orig
    ev.PreferEvictor = PreferEvictor
    return True
