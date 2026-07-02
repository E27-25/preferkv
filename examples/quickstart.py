"""End-to-end preferkv example: cache, advisor, and adapters.

Run:  python examples/quickstart.py
"""
from preferkv import PrefixCache, advise, simulate, simulate_belady
from preferkv.synth import make_multitenant, make_burst

# 1) Use the cache directly ---------------------------------------------------
cache = PrefixCache(capacity=64, policy="prefer")
for req in make_multitenant(n_requests=500, seed=0):
    cache.access(req)                       # blocks served from cache tracked internally
print(f"[cache] lifetime prefix-cache hit rate = {cache.hit_rate:.3f} "
      f"(resident blocks: {cache.size})")

# ... or as a keyed application cache
cache.put(["sys-prompt", "fewshot", "q42"], value={"answer": 42})
print("[cache] get exact key ->", cache.get(["sys-prompt", "fewshot", "q42"]))

# 2) Ask the advisor whether PREFER helps YOUR workload -----------------------
for name, trace in [("multi-tenant serving", make_multitenant(seed=1)),
                    ("tight agent loop", make_burst(seed=1))]:
    rec = advise(trace)
    verdict = "USE PREFER" if rec.recommend_prefer else "STICK WITH LRU"
    print(f"[advisor] {name:22s}: gain {rec.best_gain_pct:+5.1f}%  -> {verdict}")

# 3) Compare against the Belady oracle ----------------------------------------
tr = make_multitenant(seed=2)
print(f"[oracle] cap=32  LRU={simulate(tr,32,'lru'):.3f}  "
      f"PREFER={simulate(tr,32,'prefer'):.3f}  Belady={simulate_belady(tr,32):.3f}")

# 4) Engine adapters (see preferkv/adapters/) ---------------------------------
#   SGLang:  from preferkv.adapters.sglang import enable_prefer; enable_prefer()
#   vLLM:    from preferkv.adapters.vllm import PreferEvictor  # use in block manager
print("[adapters] SGLang: enable_prefer()  |  vLLM: PreferEvictor()")
