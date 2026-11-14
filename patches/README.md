# Engine patches

These are the patches used for the live results in the paper. Each is a small `git apply`-able diff against
the engine release named in its file name.

| patch | engine | what it changes |
|:--|:--|:--|
| [`sglang-v0.5.18-prefer.patch`](sglang-v0.5.18-prefer.patch) | SGLang v0.5.18 | `radix_cache.py`: adds a global prefix-to-count map (FNV-1a rolling hash of the prefix tokens), updated on the insert path. Its counts **survive eviction** and are exposed as `node.persist_freq`.<br>`evict_policy.py`: `LFUStrategy` scores nodes with `preferkv.adapters.sglang.prefer_priority` when `preferkv` is importable, and otherwise keeps stock LFU. |
| [`vllm-v0.24.0-block-pool-prefer.patch`](vllm-v0.24.0-block-pool-prefer.patch) | vLLM v0.24.0 (V1 engine) | `v1/core/block_pool.py`: keeps a process-wide persistent-frequency table keyed by block hash. When prefix caching is on, eviction victims are chosen by lowest `log1p(freq)`, with queue (LRU) order breaking ties. |

## SGLang

```bash
pip install "sglang==0.5.18" git+https://github.com/E27-25/preferkv
cd "$(python -c 'import sglang, os; print(os.path.dirname(os.path.dirname(sglang.__file__)))')"   # site-packages
git apply -p2 /path/to/preferkv/patches/sglang-v0.5.18-prefer.patch

python -m sglang.launch_server --model-path Qwen/Qwen2.5-1.5B-Instruct \
       --radix-eviction-policy lfu             # LFU slot now runs PREFER
```

Without the patch, `--radix-eviction-policy lfu` is SGLang's built-in LFU. Its per-node count resets when a
node is evicted. At short reuse distances it already gets most of the gain (paper, Table IV).

## vLLM

```bash
pip install "vllm==0.24.0" git+https://github.com/E27-25/preferkv
cd "$(python -c 'import vllm, os; print(os.path.dirname(os.path.dirname(vllm.__file__)))')"   # site-packages
git apply -p1 /path/to/preferkv/patches/vllm-v0.24.0-block-pool-prefer.patch

vllm serve Qwen/Qwen2.5-0.5B-Instruct --enable-prefix-caching
```

On startup the patched block pool prints `[preferkv-vllm] using shipped preferkv library`, or prints that it fell
back to an identical inline scorer.

## Notes

- In the paper, both engines ran in their official Docker images (`lmsysorg/sglang:v0.5.18-cu129`, and vLLM's
  `vllm-openai` image), with the patched file bind-mounted over the original.
- Other releases may move these files. If a hunk fails, port the change by hand; each patch is under 130 lines.
- SGLang and vLLM are Apache-2.0 projects. These diffs modify their source and keep that license for the
  modified lines.
