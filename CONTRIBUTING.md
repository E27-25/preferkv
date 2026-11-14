# Contributing to preferkv

Thanks for your interest in improving preferkv. Bug reports, engine ports, and documentation fixes are all welcome.

## Development setup

```bash
git clone https://github.com/E27-25/preferkv
cd preferkv
pip install -e ".[dev]"
pytest -q
```

The core library has no runtime dependencies and supports Python 3.8+. Please keep it that way: engine-specific code belongs in `preferkv/adapters/` or `patches/`.

## What helps most

- **Engine ports.** Each patch in `patches/` targets one release, SGLang v0.5.18 or vLLM v0.24.0. A port to a newer release should include:
  - the new patch file, named `<engine>-v<version>-....patch`;
  - a line in `patches/README.md`;
  - a short note on how you checked it, for example the engine's hit-rate counters with LRU and with PREFER on the same request stream.
- **Workload traces.** If the advisor gets your workload wrong, please open an issue with trace statistics (`preferkv advise` output). If you can share an anonymized trace, include it too.
- **Bug fixes.** Please include a test that fails without the fix.

## Pull requests

1. Fork the repository and create a branch from `main`.
2. Keep changes focused, and add or update tests in `tests/`.
3. Make sure `pytest -q` passes.
4. Describe what changed and why in the pull request.

By contributing you agree that your contributions are licensed under the MIT License.
