"""Command-line interface: ``preferkv advise|bench|demo``."""
from __future__ import annotations

import argparse
import sys

from .advisor import advise
from .sim import simulate, simulate_belady, reuse_ceiling
from .trace import load_trace, trace_stats


def _cmd_advise(args) -> int:
    trace = load_trace(args.trace)
    if not trace:
        print("empty trace", file=sys.stderr)
        return 2
    rec = advise(trace, capacities=args.cap or None, window=args.window)
    print(rec)
    return 0


def _cmd_bench(args) -> int:
    trace = load_trace(args.trace)
    st = trace_stats(trace)
    caps = args.cap or sorted({max(1, int(f * max(4, st["unique_blocks"])))
                               for f in (0.05, 0.1, 0.25)})
    print(f"requests={st['requests']} unique={st['unique_blocks']} "
          f"reuse={st['reuse_rate_blocks']:.2f} corr={st['reuse_recency_corr']:.2f}")
    print(f"{'cap':>8} {'lru':>7} {'lfu':>7} {'prefer':>7} {'oracle':>7} {'ceil':>7}")
    ceil = reuse_ceiling(trace)
    for cap in caps:
        print(f"{cap:>8} {simulate(trace, cap, 'lru'):>7.3f} "
              f"{simulate(trace, cap, 'lfu'):>7.3f} "
              f"{simulate(trace, cap, 'prefer'):>7.3f} "
              f"{simulate_belady(trace, cap):>7.3f} {ceil:>7.3f}")
    return 0


def _cmd_demo(args) -> int:
    from .synth import make_multitenant, make_burst
    print("Built-in demo: PREFER vs LRU on two workloads at the same relative pressure\n")
    for name, trace in (("multi-tenant (frequency-favorable)", make_multitenant()),
                        ("agent burst  (recency-favorable)  ", make_burst())):
        rec = advise(trace)
        best = rec.rows[0]
        tag = "USE PREFER" if rec.recommend_prefer else "STICK WITH LRU"
        print(f"{name}: corr={rec.stats['reuse_recency_corr']:.2f}  "
              f"gain={rec.best_gain_pct:+5.1f}%  -> {tag}")
    print("\n(run `preferkv advise <trace.jsonl>` on your own workload)")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="preferkv",
                                description="Prefix-aware caching with PREFER eviction + a workload advisor.")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("advise", help="recommend LRU vs PREFER for a trace")
    a.add_argument("trace")
    a.add_argument("--cap", type=int, action="append", help="cache capacity (repeatable)")
    a.add_argument("--window", type=int, default=8)
    a.set_defaults(fn=_cmd_advise)

    b = sub.add_parser("bench", help="compare all policies on a trace")
    b.add_argument("trace")
    b.add_argument("--cap", type=int, action="append")
    b.set_defaults(fn=_cmd_bench)

    d = sub.add_parser("demo", help="built-in synthetic demo (no data needed)")
    d.set_defaults(fn=_cmd_demo)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
