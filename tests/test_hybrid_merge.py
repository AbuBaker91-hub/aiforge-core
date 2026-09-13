from aiforge_core.vectorstore import Chunk, merge_results


def c(id_, text="t", score=0.5):
    return Chunk(id=id_, doc="d", page=1, section="s", text=text, score=score)


def test_shared_chunk_yields_one_result():
    merged = merge_results([c(1), c(2)], [c(1), c(3)], k=10)
    assert sorted(ch.id for ch in merged) == [1, 2, 3]


def test_shared_chunk_ranks_first():
    merged = merge_results([c(1), c(2)], [c(3), c(1)], k=10)
    assert merged[0].id == 1


def test_k_limits_results():
    merged = merge_results([c(i) for i in range(1, 6)], [c(i) for i in range(6, 11)], k=4)
    assert len(merged) == 4
