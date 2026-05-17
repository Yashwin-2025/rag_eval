def _relevant_ids(
    retrieved_chunk_ids: list[str],
    retrieved_doc_ids: list[str],
    expected_chunk_ids: set[str],
    expected_doc_ids: set[str],
) -> set[str]:
    """Chunk ids take precedence; otherwise treat doc_id hits as relevant."""
    if expected_chunk_ids:
        return expected_chunk_ids
    if expected_doc_ids:
        return {d for d in retrieved_doc_ids if d in expected_doc_ids}
    return set()


def hit_at_k(
    retrieved_chunk_ids: list[str],
    retrieved_doc_ids: list[str],
    expected_chunk_ids: set[str],
    expected_doc_ids: set[str],
    k: int,
) -> float:
    relevant = _relevant_ids(
        retrieved_chunk_ids, retrieved_doc_ids, expected_chunk_ids, expected_doc_ids
    )
    if not relevant:
        return 1.0
    top_chunks = retrieved_chunk_ids[:k]
    top_docs = retrieved_doc_ids[:k]
    if expected_chunk_ids:
        return 1.0 if any(cid in relevant for cid in top_chunks) else 0.0
    return 1.0 if any(did in relevant for did in top_docs) else 0.0


def recall_at_k(
    retrieved_chunk_ids: list[str],
    retrieved_doc_ids: list[str],
    expected_chunk_ids: set[str],
    expected_doc_ids: set[str],
    k: int,
) -> float:
    if expected_chunk_ids:
        top = set(retrieved_chunk_ids[:k])
        return len(top & expected_chunk_ids) / len(expected_chunk_ids)
    if expected_doc_ids:
        top = set(retrieved_doc_ids[:k])
        return len(top & expected_doc_ids) / len(expected_doc_ids)
    return 1.0


def reciprocal_rank(
    retrieved_chunk_ids: list[str],
    retrieved_doc_ids: list[str],
    expected_chunk_ids: set[str],
    expected_doc_ids: set[str],
) -> float:
    if expected_chunk_ids:
        for rank, cid in enumerate(retrieved_chunk_ids, start=1):
            if cid in expected_chunk_ids:
                return 1.0 / rank
        return 0.0
    if expected_doc_ids:
        for rank, did in enumerate(retrieved_doc_ids, start=1):
            if did in expected_doc_ids:
                return 1.0 / rank
        return 0.0
    return 1.0
