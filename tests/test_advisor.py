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


def test_select_policy_auto_selection():
    from preferkv import select_policy, PrefixCache
    assert select_policy(make_multitenant(seed=0)) == "prefer"
    assert select_policy(make_burst(seed=0)) == "lru"
    # the returned string is directly deployable
    cache = PrefixCache(capacity=8, policy=select_policy(make_multitenant(seed=0)))
    assert cache.access([1, 2, 3]) == 0


def test_recommended_policy_matches_recommend_prefer():
    rec = advise(make_multitenant(seed=0))
    assert rec.recommended_policy == ("prefer" if rec.recommend_prefer else "lru")
