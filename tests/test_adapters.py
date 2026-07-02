from preferkv.adapters.sglang import prefer_priority
from preferkv.adapters.vllm import PreferEvictor, _PERSIST


class _FakeNode:
    def __init__(self, persist_freq, n_children, last):
        self.persist_freq = persist_freq
        self.children = {i: None for i in range(n_children)}
        self.last_access_time = last


def test_sglang_prefer_priority_prefers_frequent_and_branchy():
    hot = _FakeNode(persist_freq=40, n_children=5, last=1.0)   # frequent + branchy
    one_shot = _FakeNode(persist_freq=1, n_children=0, last=9.0)  # recent one-shot
    # lower priority is evicted first -> the one-shot must sort below the hot prefix
    assert prefer_priority(one_shot) < prefer_priority(hot)


def test_vllm_prefer_evictor_evicts_least_frequent():
    _PERSIST._c.clear()
    e = PreferEvictor()
    for t in range(5):                 # prefix A (hash 100) cached repeatedly -> hot
        e.add(1, content_hash=100, num_hashed_tokens=10, last_accessed=float(t))
        e.remove(1)
    e.add(1, content_hash=100, num_hashed_tokens=10, last_accessed=10.0)  # A resident
    e.add(2, content_hash=200, num_hashed_tokens=10, last_accessed=11.0)  # B, one-shot, newer
    bid, chash = e.evict()             # evict least-frequent despite B being newer
    assert bid == 2 and chash == 200
    assert e.num_blocks == 1


def test_vllm_prefer_evictor_interface():
    _PERSIST._c.clear()
    e = PreferEvictor()
    e.add(7, 7, 3, 0.0)
    assert 7 in e
    e.update(7, 5.0)
    e.remove(7)
    assert 7 not in e and e.num_blocks == 0
