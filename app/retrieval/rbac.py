from dataclasses import dataclass

from pgvector.psycopg import register_vector

from app.db.pool import get_connection
from app.embeddings.huggingface import embed_query


@dataclass(frozen=True)
class Principal:
    user_id: str


def retrieve(
    query: str,
    principal: Principal,
    top_k: int,
) -> list[dict]:
    """Cosine distance (<=>); always filter by user_id."""
    qvec = embed_query(query)
    sql = """
        SELECT chunk_id, doc_id, content, metadata,
               (embedding <=> %(q)s::vector) AS distance
        FROM rag_chunks
        WHERE user_id = %(uid)s
        ORDER BY embedding <=> %(q)s::vector
        LIMIT %(k)s;
    """
    with get_connection() as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(
                sql,
                {"q": qvec, "uid": principal.user_id, "k": top_k},
            )
            cols = [c.name for c in cur.description or []]
            return [dict(zip(cols, row)) for row in cur.fetchall()]