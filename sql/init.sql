CREATE EXTENSION IF NOT EXISTS vector;

-- 1536 dims: must match OpenRouter embedding model output (see app/config.py embedding_dim)
-- Isolation: one user_id per row; retrieval must always filter by authenticated user_id.
CREATE TABLE IF NOT EXISTS rag_chunks (
    id              BIGSERIAL PRIMARY KEY,
    chunk_id        TEXT NOT NULL UNIQUE,
    user_id         TEXT NOT NULL,
    doc_id          TEXT NOT NULL,
    content         TEXT NOT NULL,
    embedding       vector(1536) NOT NULL,
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS rag_chunks_embedding_idx
    ON rag_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS rag_chunks_user_id_idx
    ON rag_chunks (user_id);
