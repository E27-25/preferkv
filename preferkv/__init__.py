"""preferkv --- a prefix-aware cache with frequency+branchiness eviction (PREFER)
and a workload advisor.

Quick start::

    from preferkv import PrefixCache, advise, load_trace

    cache = PrefixCache(capacity=2048, policy="prefer")
    hit_len = cache.access([12, 45, 9, 88])      # blocks that hit the cache

    rec = advise(load_trace("trace.jsonl"))
    print(rec)                                   # go/no-go + expected gain

    from preferkv import select_policy
    cache = PrefixCache(2048, policy=select_policy(my_trace))   # auto selection

PREFER retains frequently-reused, branchy prefixes and evicts one-shot tails; it wins
over LRU when reuse is not recency-correlated. The advisor tells you whether that is
true for *your* workload before you switch.
"""
from .cache import PrefixCache
from .policies import LRU, LFU, Prefer, get_policy
from .persist import PersistentFrequency
from .sim import simulate, simulate_belady, reuse_ceiling
from .trace import load_trace, trace_stats, reuse_recency_corr
from .advisor import advise, select_policy, Recommendation

__version__ = "0.2.0"

__all__ = [
    "PrefixCache", "LRU", "LFU", "Prefer", "get_policy", "PersistentFrequency",
    "simulate", "simulate_belady", "reuse_ceiling",
    "load_trace", "trace_stats", "reuse_recency_corr",
    "advise", "select_policy", "Recommendation", "__version__",
]
