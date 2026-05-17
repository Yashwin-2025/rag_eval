from app.evaluation.metrics import hit_at_k, recall_at_k, reciprocal_rank


def test_hit_at_k_by_chunk_id() -> None:
    chunks = ["a", "b", "c"]
    docs = ["d1", "d1", "d2"]
    assert hit_at_k(chunks, docs, {"b"}, set(), 3) == 1.0
    assert hit_at_k(chunks, docs, {"z"}, set(), 3) == 0.0


def test_recall_at_k_chunks() -> None:
    chunks = ["a", "b"]
    assert recall_at_k(chunks, [], {"a", "c"}, set(), 5) == 0.5


def test_mrr_doc_id() -> None:
    chunks = ["x", "y"]
    docs = ["d1", "d2"]
    assert reciprocal_rank(chunks, docs, set(), {"d2"}) == 0.5
