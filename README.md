<p align="center">
  <img src="assets/banner.png" width="880" alt="preferkv: persistent-frequency KV-cache eviction for LLM prefix caching. SGLang v0.5.18, vLLM v0.24.0, iSAI-NLP 2026">
</p>

<p align="center">
| <a href="paper/PREFER_iSAI-NLP2026.pdf"><b>Paper</b></a>
| <a href="docs/RESULTS.md"><b>Results</b></a>
| <a href="patches/README.md"><b>SGLang &amp; vLLM</b></a>
| <a href="#citation"><b>Citation</b></a> |
</p>

<p align="center">
  <a href="paper/PREFER_iSAI-NLP2026.pdf"><img src="https://img.shields.io/badge/iSAI--NLP-2026-6A4C93?style=flat-square" alt="iSAI-NLP 2026"></a>
  <a href="https://www.python.org"><img src="https://img.shields.io/badge/python-3.8%2B-8E6CC0?style=flat-square" alt="Python 3.8+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-3B2A5A?style=flat-square" alt="MIT license"></a>
</p>

---

**Latest News**

- [2026/11] Paper and engine patches released. PREFER will be presented at iSAI-NLP 2026 (IEEE, Nov 19–21).
- [2026/10] PREFER was accepted at iSAI-NLP 2026.

---

## About

vLLM and SGLang cache the KV state of shared prompt prefixes, and evict the least recently used (LRU) block when memory runs out. On real traffic most blocks are used only once, so LRU often evicts a popular prefix just to keep a block nobody will ask for again.

**PREFER** evicts by how often a prefix is used instead. It keeps those counts even after the block is evicted, which is the detail that makes the difference.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/features_dark.png">
    <img src="assets/features_light.png" width="880" alt="Engine patches for SGLang v0.5.18 and vLLM v0.24.0; a workload advisor that recommends PREFER only where it beats LRU; a simulator with a Belady reference and an infinite-cache ceiling; a pure-Python core with no dependencies">
  </picture>
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/hero_dark.png">
    <img src="assets/hero_light.png" width="880" alt="Left: on the Mooncake conversation trace at a 2k-block cache, PREFER reaches 1.8 times LRU's hit rate, versus 1.06 for ARC and in-cache LFU and 1.19 for LIRS. Right: live on SGLang, PREFER gains +30.5% hit rate on multi-tenant serving and +27.3% on session resumption, and loses 15.3% on a tight agent loop">
  </picture>
</p>

On production traces PREFER reaches **1.8× LRU's hit rate**, where classic policies (ARC, in-cache LFU, LIRS) reach at most 1.19×. Live on SGLang it raises the hit rate by **25–31%** over LRU. It also gains **+6.3%** on vLLM and up to **+10.5% throughput** on an 8B model under load. On tight agent loops it loses, and the advisor keeps LRU there. See [full results](docs/RESULTS.md).

## Getting Started

```bash
pip install git+https://github.com/E27-25/preferkv
```

<img src="assets/mascot/mascot-curious.png" align="right" width="110" alt="Mascot with a question mark (fan art)">

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

<img src="assets/mascot/mascot-cheer.png" align="right" width="120" alt="Cheering mascot (fan art)">

| Engine | Patch | Live gain vs LRU |
|:--|:--|:--|
| SGLang v0.5.18 | [`sglang-v0.5.18-prefer.patch`](patches/sglang-v0.5.18-prefer.patch) | +25–31% hit rate |
| vLLM v0.24.0 | [`vllm-v0.24.0-block-pool-prefer.patch`](patches/vllm-v0.24.0-block-pool-prefer.patch) | +6.3% hit rate |

Apply the patch inside `site-packages`, then start the server as usual. For SGLang, add `--radix-eviction-policy lfu`. Step-by-step instructions are in [`patches/README.md`](patches/README.md).

## Contributing

Issues and pull requests are welcome, especially ports of the patches to newer engine releases. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Citation

If you use preferkv or PREFER in your research, please cite:

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

The mascot images in `assets/mascot/`, the banner, and the social preview card are fan art of Fern from *Frieren: Beyond Journey's End* (© Kanehito Yamada, Tsukasa Abe / Shogakukan). They are not covered by the MIT License, and this project is not affiliated with or endorsed by the rights holders.

<p align="center">
  <img src="assets/mascot/mascot-reading.png" width="110" alt="preferkv mascot reading a book (fan art)"><br>
  <sub>Thanks for reading.</sub>
</p>
