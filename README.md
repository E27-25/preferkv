<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo/preferkv-logo-dark.svg">
    <img alt="preferkv" src="assets/logo/preferkv-logo-light.svg" width="400">
  </picture>
</p>

<h3 align="center">Persistent-frequency KV-cache eviction for LLM prefix caching</h3>

<p align="center">
| <a href="paper/PREFER_iSAI-NLP2026.pdf"><b>Paper</b></a>
| <a href="docs/RESULTS.md"><b>Results</b></a>
| <a href="patches/README.md"><b>SGLang &amp; vLLM</b></a>
| <a href="#citation"><b>Citation</b></a> |
</p>

<p align="center">
  <a href="paper/PREFER_iSAI-NLP2026.pdf"><img src="https://img.shields.io/badge/iSAI--NLP-2026-4338CA?style=flat-square" alt="iSAI-NLP 2026"></a>
  <a href="https://www.python.org"><img src="https://img.shields.io/badge/python-3.8%2B-3776AB?style=flat-square" alt="Python 3.8+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-64748B?style=flat-square" alt="MIT license"></a>
</p>

---

**Latest News**

- [2026/11] Paper and engine patches released. PREFER will be presented at iSAI-NLP 2026 (IEEE, Nov 19–21).
- [2026/10] PREFER was accepted at iSAI-NLP 2026.

---

## About

vLLM and SGLang cache the KV state of shared prompt prefixes, and evict the least recently used (LRU) block when memory runs out. On real traffic most blocks are used only once, so LRU often evicts a popular prefix just to keep a block nobody will ask for again.

**PREFER** evicts by how often a prefix is used instead. It keeps those counts even after the block is evicted, which is the detail that makes the difference. preferkv provides:

- **Engine patches** for SGLang v0.5.18 and vLLM v0.24.0
- **A workload advisor** that recommends PREFER only where it beats LRU
- **A simulator** with a Belady reference, to measure how much hit rate a policy leaves on the table
- **A pure-Python core** with no dependencies

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/live_sglang_dark.png">
    <img src="assets/live_sglang_light.png" width="760" alt="Live SGLang results: frequency eviction gains about +25 to +31% hit rate over LRU on multi-tenant and resumption workloads, and loses 7 to 15% on a tight agent loop">
  </picture>
</p>

Live on SGLang, frequency eviction raises the prefix-cache hit rate by **25–31%** over LRU, and loses on tight agent loops, where the advisor keeps LRU. It also reaches **+6.3%** on vLLM and up to **+10.5% throughput** on an 8B model under load. See [full results](docs/RESULTS.md).

## Getting Started

```bash
pip install git+https://github.com/E27-25/preferkv
```

Check whether PREFER helps your workload. The trace is JSON Lines, one list of block ids per request:

```bash
preferkv advise your_trace.jsonl     # USE PREFER  or  STICK WITH LRU
```

Use it in Python:

```python
from preferkv import PrefixCache, select_policy, load_trace

trace = load_trace("your_trace.jsonl")
cache = PrefixCache(capacity=2048, policy=select_policy(trace))
hit_len = cache.access([12, 45, 9, 88])      # leading blocks served from cache
```

## SGLang and vLLM

| Engine | Patch | Live gain vs LRU |
|:--|:--|:--|
| SGLang v0.5.18 | [`sglang-v0.5.18-prefer.patch`](patches/sglang-v0.5.18-prefer.patch) | +25–31% hit rate |
| vLLM v0.24.0 | [`vllm-v0.24.0-block-pool-prefer.patch`](patches/vllm-v0.24.0-block-pool-prefer.patch) | +6.3% hit rate |

Apply the patch inside `site-packages`, then start the server as usual. For SGLang, add `--radix-eviction-policy lfu`. Step-by-step instructions are in [`patches/README.md`](patches/README.md).

## Contributing

Issues and pull requests are welcome, especially ports of the patches to newer engine releases. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Citation

```bibtex
@inproceedings{promfiy2026prefer,
  title     = {{PREFER}: Persistent-Frequency {KV}-Cache Eviction for {LLM} Prefix Caching},
  author    = {Promfiy, Watin and Sirikayon, Chaloemphon and Tuwanut, Panwit and Poomrittigul, Suvit},
  booktitle = {Proceedings of the International Joint Symposium on Artificial Intelligence and Natural Language Processing (iSAI-NLP)},
  publisher = {IEEE},
  year      = {2026}
}
```

## License

The code is released under the [MIT License](LICENSE). The files in `patches/` modify Apache-2.0 sources of SGLang and vLLM. The [paper](paper/PREFER_iSAI-NLP2026.pdf) is © 2026 IEEE: personal use is permitted, and any other use requires permission from IEEE.
