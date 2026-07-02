"""The advisor: given a workload, decide whether PREFER will actually help.

This operationalizes the paper's central, honest finding --- frequency-based eviction
is *workload-dependent*. Blindly switching a recency-heavy workload (e.g. a tight
agent loop) to frequency eviction makes it worse. The advisor measures the workload's
reuse-recency correlation, simulates LRU vs PREFER vs a Belady oracle at realistic
cache pressure, and returns a go / no-go with the expected gain --- so you only deploy
PREFER where it wins.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from .sim import simulate, simulate_belady
from .trace import trace_stats

GAIN_THRESHOLD_PCT = 5.0     # recommend PREFER only if it clears this


@dataclass
class CapRow:
    capacity: int
    lru: float
    prefer: float
    oracle: float

    @property
    def gain_pct(self) -> float:
        return 100.0 * (self.prefer - self.lru) / self.lru if self.lru else 0.0

    @property
    def frac_oracle_lru(self) -> float:
        return self.lru / self.oracle if self.oracle else 0.0

    @property
    def frac_oracle_prefer(self) -> float:
        return self.prefer / self.oracle if self.oracle else 0.0


@dataclass
class Recommendation:
    stats: dict
    rows: List[CapRow] = field(default_factory=list)

    @property
    def best_gain_pct(self) -> float:
        cand = [r.gain_pct for r in self.rows if r.lru > 0]
        return max(cand) if cand else 0.0

    @property
    def recommend_prefer(self) -> bool:
        return self.best_gain_pct >= GAIN_THRESHOLD_PCT

    @property
    def verdict(self) -> str:
        if self.stats["reuse_rate_blocks"] < 0.05:
            return ("LOW REUSE -- prefix caching barely matters here; policy choice is "
                    "second-order.")
        if self.recommend_prefer:
            return (f"USE PREFER -- expected up to {self.best_gain_pct:+.0f}% hit rate "
                    f"over LRU on this workload.")
        return ("STICK WITH LRU -- this workload is recency-heavy; PREFER would not "
                "help (and could hurt).")

    @property
    def sglang_hint(self) -> str:
        if self.recommend_prefer:
            return ("SGLang: from preferkv.adapters.sglang import enable_prefer; "
                    "enable_prefer()  then launch with --radix-eviction-policy lfu")
        return "SGLang: keep the default --radix-eviction-policy lru"

    def __str__(self) -> str:
        s = self.stats
        fav = "frequency-favorable" if self.recommend_prefer else "recency-favorable"
        lines = [
            "preferkv advisor",
            "=" * 52,
            f"requests={s['requests']}  unique_blocks={s['unique_blocks']}  "
            f"working_set={s.get('working_set', '?')}  reuse_rate={s['reuse_rate_blocks']:.2f}",
            f"reuse-recency correlation = {s['reuse_recency_corr']:.2f}  "
            f"(0=gappy .. 1=recency-predictable)",
            f"verdict from simulation below: workload looks {fav}.",
            "",
            f"{'cap':>8} {'LRU':>7} {'PREFER':>7} {'oracle':>7} {'gain':>8}  frac-of-oracle",
        ]
        for r in self.rows:
            lines.append(
                f"{r.capacity:>8} {r.lru:>7.3f} {r.prefer:>7.3f} {r.oracle:>7.3f} "
                f"{r.gain_pct:>+7.1f}%  {r.frac_oracle_lru:.2f} -> {r.frac_oracle_prefer:.2f}")
        lines += ["", "-> " + self.verdict, "   " + self.sglang_hint]
        return "\n".join(lines)


def _default_caps(stats: dict) -> List[int]:
    # Probe the pressured regime: fractions of the *reusable working set*, not of
    # total unique blocks (which is dominated by one-shot content that never helps).
    ws = max(4, stats.get("working_set") or stats["unique_blocks"])
    caps = sorted({max(1, int(f * ws)) for f in (0.2, 0.4, 0.7)})
    return caps


def advise(trace: Sequence[Sequence], capacities: Optional[Sequence[int]] = None,
           window: int = 8) -> Recommendation:
    """Analyze ``trace`` and recommend LRU vs PREFER with expected gains."""
    stats = trace_stats(trace, window=window)
    caps = list(capacities) if capacities else _default_caps(stats)
    rows = []
    for cap in caps:
        rows.append(CapRow(
            capacity=cap,
            lru=simulate(trace, cap, "lru"),
            prefer=simulate(trace, cap, "prefer"),
            oracle=simulate_belady(trace, cap),
        ))
    return Recommendation(stats=stats, rows=rows)
