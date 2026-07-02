from preferkv import PrefixCache


def test_prefix_hit_and_reuse():
    c = PrefixCache(capacity=100, policy="lru")
    assert c.access([1, 2, 3]) == 0        # cold miss
    assert c.access([1, 2, 3]) == 3        # fully cached now
    assert c.access([1, 2, 4]) == 2        # shares prefix [1, 2]


def test_capacity_is_respected():
    c = PrefixCache(capacity=3, policy="lru")
    for i in range(0, 30, 3):
        c.access([i, i + 1, i + 2])
    assert c.size <= 3


def test_eviction_keeps_prefix_closed():
    c = PrefixCache(capacity=3, policy="prefer")
    c.access([1, 2, 3])
    c.access([4, 5, 6])
    c.access([1, 2, 7])
    for n in c._cached:                    # every cached node's parent is cached
        assert n.parent is c.root or n.parent.cached


def test_persistent_frequency_survives_eviction():
    c = PrefixCache(capacity=2, policy="lru")
    for _ in range(5):
        c.access([1])                      # popular, but tiny cache churns it out
        c.access([8])
        c.access([9])
    node = c.root.children[1]
    assert c.freq(node) >= 5               # count kept even after evictions


def test_put_get_value():
    c = PrefixCache(capacity=100, policy="prefer")
    c.put([1, 2, 3], "hello")
    assert c.get([1, 2, 3]) == "hello"
    assert c.get([1, 2, 9]) is None
