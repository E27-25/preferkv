from preferkv import load_trace, trace_stats, reuse_recency_corr


def test_load_trace_accepts_all_formats(tmp_path):
    p = tmp_path / "t.jsonl"
    p.write_text('[1, 2, 3]\n{"blocks": [1, 2, 4]}\n{"hash_ids": [1, 2, 5]}\n\n',
                 encoding="utf-8")
    assert load_trace(str(p)) == [[1, 2, 3], [1, 2, 4], [1, 2, 5]]


def test_trace_stats_working_set_and_reuse():
    tr = [[1, 2], [1, 2], [1, 3]]        # blocks 1,2 reused; 3 seen once
    st = trace_stats(tr)
    assert st["requests"] == 3
    assert st["unique_blocks"] == 3
    assert st["working_set"] == 2        # only reused blocks count
    assert 0.0 < st["reuse_rate_blocks"] < 1.0


def test_reuse_recency_corr_bounds():
    assert reuse_recency_corr([[1], [2], [3]]) == 0.0          # no reuse
    assert reuse_recency_corr([[1], [1], [1]], window=8) == 1.0  # immediate reuse
