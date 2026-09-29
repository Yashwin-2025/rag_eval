CREATE EXTENSION IF NOT EXISTS vector;

-- 1024 dims: must match OpenRouter embedding model output (see app/config.py embedding_dim)
-- Isolation: one user_id per row; retrieval must always filter by authenticated user_id.
CREATE TABLE IF NOT EXISTS rag_chunks (
    id              BIGSERIAL PRIMARY KEY,
    chunk_id        TEXT NOT NULL UNIQUE,
    user_id         TEXT NOT NULL,
    doc_id          TEXT NOT NULL,
    content         TEXT NOT NULL,
    embedding       vector(1024) NOT NULL,
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS rag_chunks_embedding_idx
    ON rag_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS rag_chunks_user_id_idx
    ON rag_chunks (user_id);

CREATE TABLE IF NOT EXISTS audit_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    question TEXT NOT NULL,
    retrieved_chunks JSONB,
    answer TEXT NOT NULL,
    guardrail_results JSONB,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id);

-- GDPR / CCPA Consent logs
CREATE TABLE IF NOT EXISTS consent_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    consent_given BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_consent_user ON consent_logs(user_id);

-- Human Appeals Queue for Automated Decisions
CREATE TABLE IF NOT EXISTS appeals_queue (
    appeal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    decision_type TEXT NOT NULL, -- e.g. "loan_application", "service_access"
    original_decision JSONB NOT NULL,
    user_appeal_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
    reviewer_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_appeals_user ON appeals_queue(user_id);

-- Incident Reports and Blameless Post-Mortems
CREATE TABLE IF NOT EXISTS incident_reports (
    incident_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    containment_status TEXT NOT NULL, -- 'active', 'contained', 'resolved'
    kill_switch_active BOOLEAN NOT NULL DEFAULT FALSE,
    post_mortem TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


