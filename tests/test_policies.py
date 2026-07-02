from preferkv import simulate, simulate_belady
from preferkv.synth import make_multitenant, make_burst


def test_prefer_beats_lru_on_multitenant():
    tr = make_multitenant(seed=0)
    lru = simulate(tr, 20, "lru")
    prefer = simulate(tr, 20, "prefer")
    assert prefer > lru * 1.05             # frequency-favorable: PREFER wins


def test_lru_not_beaten_on_burst():
    tr = make_burst(seed=0)
    lru = simulate(tr, 40, "lru")
    prefer = simulate(tr, 40, "prefer")
    assert lru >= prefer * 0.98            # recency-favorable: PREFER must not help


def test_oracle_upper_bounds_online_policies():
    tr = make_multitenant(seed=1)
    orc = simulate_belady(tr, 20)
    assert orc + 1e-9 >= simulate(tr, 20, "lru")
    assert orc + 1e-9 >= simulate(tr, 20, "prefer")


def test_lfu_and_prefer_reduce_correctly():
    # PREFER with branch weight 0 and freq weight 1 should track LFU closely
    tr = make_multitenant(seed=2)
    from preferkv.policies import Prefer
    only_freq = simulate(tr, 20, Prefer(w_freq=1.0, w_branch=0.0))
    lfu = simulate(tr, 20, "lfu")
    assert abs(only_freq - lfu) < 0.05
