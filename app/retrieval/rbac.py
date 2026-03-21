from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    user_id: str


def retrieve(
    query: str,
    principal: Principal,
    top_k: int,
) -> list[dict]:
    """Cosine / pgvector search filtered by user_id."""
    ...
