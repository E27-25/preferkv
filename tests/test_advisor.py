from preferkv import advise, reuse_recency_corr
from preferkv.synth import make_multitenant, make_burst


def test_advisor_recommends_prefer_on_multitenant():
    rec = advise(make_multitenant(seed=0))
    assert rec.recommend_prefer
    assert rec.best_gain_pct > 5.0
    assert "USE PREFER" in rec.verdict


def test_advisor_recommends_lru_on_burst():
    rec = advise(make_burst(seed=0))
    assert not rec.recommend_prefer
    assert "LRU" in rec.verdict


def test_reuse_recency_corr_orders_workloads():
    burst = reuse_recency_corr(make_burst(seed=0))
    multi = reuse_recency_corr(make_multitenant(seed=0))
    assert burst > multi                   # burst is the recency-heavy extreme
