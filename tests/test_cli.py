import json

from preferkv.cli import main
from preferkv.synth import make_multitenant


def test_cli_demo_runs():
    assert main(["demo"]) == 0


def _write(tmp_path):
    p = tmp_path / "t.jsonl"
    with open(p, "w", encoding="utf-8") as f:
        for r in make_multitenant(n_requests=300, seed=0):
            f.write(json.dumps(r) + "\n")
    return str(p)


def test_cli_advise_runs(tmp_path):
    assert main(["advise", _write(tmp_path)]) == 0


def test_cli_bench_runs(tmp_path):
    assert main(["bench", _write(tmp_path), "--cap", "16", "--cap", "32"]) == 0
