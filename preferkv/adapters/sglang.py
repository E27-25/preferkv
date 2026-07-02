"""SGLang adapter for PREFER.

SGLang selects an eviction strategy via ``--radix-eviction-policy`` and each strategy
implements ``get_priority(node)`` (lower = evicted first). :func:`enable_prefer`
monkeypatches SGLang's ``LFUStrategy.get_priority`` to the PREFER score, so launching
with ``--radix-eviction-policy lfu`` uses PREFER --- no fork, no rebuild.

Two levels of the win:

* **Scoring only (this monkeypatch).** PREFER scores each node by
  ``log(1+freq) + 0.9*log(1+branchiness)``. It reads ``node.persist_freq`` if the
  engine exposes it, else falls back to the per-node ``hit_count``. Works out of the
  box; gives the smaller "stock-engine" gain.
* **Full win (persistent frequency).** The larger, robust gain needs frequency that
  survives eviction. That is a small change to the radix cache's insert path (a
  global prefix->count map); see the project's ``radix_cache.py`` patch. Without it,
  PREFER still runs, just with less signal.

This targets SGLang's ``srt.mem_cache.evict_policy`` layout; if that module moves,
:func:`enable_prefer` raises a clear error rather than silently doing nothing.
"""
from __future__ import annotations

import math


def prefer_priority(node, w_freq: float = 1.0, w_branch: float = 0.9):
    """PREFER priority for an SGLang radix ``node`` (lower is evicted first).

    Branchiness is the node's own fan-out (distinct continuations of this prefix) ---
    the signal that this is a shared, worth-keeping prefix rather than a one-shot leaf.
    """
    freq = getattr(node, "persist_freq", 0) or getattr(node, "hit_count", 0)
    own = getattr(node, "children", None)
    branch = len(own) if own else 1
    score = w_freq * math.log1p(freq) + w_branch * math.log1p(branch)
    return (score, getattr(node, "last_access_time", 0.0))


def enable_prefer(w_freq: float = 1.0, w_branch: float = 0.9) -> bool:
    """Patch SGLang's LFU strategy to use PREFER scoring. Returns True on success.

    Call before launching the server (or before the scheduler builds its cache).
    Raises ImportError/AttributeError if the SGLang eviction API is not found.
    """
    try:
        from sglang.srt.mem_cache import evict_policy as ep  # type: ignore
    except Exception as e:  # pragma: no cover - depends on sglang install
        raise ImportError(
            "Could not import sglang.srt.mem_cache.evict_policy; ensure SGLang is "
            "installed and its eviction API matches this adapter version."
        ) from e

    strategy = getattr(ep, "LFUStrategy", None)
    if strategy is None or not hasattr(strategy, "get_priority"):
        raise AttributeError("sglang LFUStrategy.get_priority not found; adapter needs update.")

    def get_priority(self, node):
        return prefer_priority(node, w_freq, w_branch)

    strategy.get_priority = get_priority
    return True


def persistent_frequency_available() -> bool:
    """True if the running SGLang radix nodes expose ``persist_freq`` (the patch)."""
    try:
        from sglang.srt.mem_cache.radix_cache import TreeNode  # type: ignore
    except Exception:
        return False
    slots = set(getattr(TreeNode, "__slots__", ()) or ())
    return "persist_freq" in slots or "persist_freq" in vars(TreeNode)
