# Current codebase reference

This document describes the **Python application**, **database schema**, **Docker setup**, and **environment variables** as implemented in this repository. It is meant to stay aligned with the code; update it when you change behavior or layout.

---

## Architecture overview

| Layer | Role |
|--------|------|
| **Config** (`app/config.py`) | Loads settings from environment and optional `.env` via Pydantic Settings. |
| **Database** (`app/db/pool.py`) | Opens `psycopg` connections to PostgreSQL; supports manual `with connection_context()`. |
| **Embeddings** (`app/embeddings/huggingface.py`) | LangChain `HuggingFaceEmbeddings` (sentence-transformers), 768 dimensions, normalized vectors. |
| **Ingest** (`app/ingest/`) | Docling parses files to Markdown; text is split into LangChain `Document`s and upserted with vectors into `rag_chunks`. |
| **Retrieval** (`app/retrieval/rbac.py`) | Query embedding + pgvector cosine distance (`<=>`), **always** filtered by `user_id`. |
| **Chains** (`app/chains/rag.py`) | LCEL RAG template: retriever produces context string + given LLM; **no LLM is instantiated here**. |

**Isolation model:** each stored chunk row includes a **`user_id`**. Retrieval must never omit the `WHERE user_id = …` predicate tied to the authenticated user.

---

## Environment variables

| Variable | Required | Used by |
|----------|----------|---------|
| `DATABASE_URL` | Yes | `Settings.database_url` — PostgreSQL connection URI. |
| `HUGGINGFACE_HUB_TOKEN` | No | If set, copied to `HF_TOKEN` for gated Hugging Face models. |
| `EMBEDDING_MODEL_NAME` | No (default in code) | Maps to `embedding_model_name` (default `BAAI/bge-base-en-v1.5`). |

Docker Compose also defines `POSTGRES_*` for the `db` service. When the optional `app` service runs, it passes `DATABASE_URL` (default points at host `db` inside the network).

See `.env.example` for a template.

---

## Module reference

### `app/config.py`

- **`Settings`** — `BaseSettings` with `env_file=".env"`.
  - **`database_url`** — Required (`Field(...)`). No default in code.
  - **`huggingface_hub_token`** — Optional.
  - **`embedding_model_name`** — Default `BAAI/bge-base-en-v1.5`.
  - **`embedding_dim`** — `768` (must match `sql/init.sql` and the chosen model).
- **`get_settings()`** — Returns `Settings()`.

---

### `app/db/pool.py`

- **`get_connection()`** — Calls `psycopg.connect(settings.database_url)`, sets `autocommit=False`.
- **`connection_context()`** — Context manager: yields a connection and closes it in `finally`.

Connections returned by `get_connection()` can be used as `with get_connection() as conn:` (psycopg connection context manager).

---

### `app/embeddings/huggingface.py`

- **`get_embeddings()`** — Builds `HuggingFaceEmbeddings` with `model_name` from settings, `device: cpu`, `normalize_embeddings: True`.
- **`embed_documents(texts)`** — Delegates to `get_embeddings().embed_documents`.
- **`embed_query(text)`** — Delegates to `get_embeddings().embed_query`.

Embedding dimension must remain **768** for the current SQL schema.

---

### `app/ingest/docling_loader.py`

- **`load_document_text(path)`** — Uses Docling `DocumentConverter`, `convert(path)`, returns `export_to_markdown()`.

---

### `app/ingest/pipeline.py`

- **`_chunk_id(user_id, doc_id, index, text)`** — SHA-256–based stable id with prefix `chk_`.
- **`chunk_documents(raw_text, doc_id, user_id)`** — `RecursiveCharacterTextSplitter` (1200 / 150 overlap); sets metadata `user_id`, `doc_id`, `chunk_index`, `chunk_id`.
- **`upsert_chunks(documents, embeddings)`** — Validates equal lengths; registers pgvector on the connection; `INSERT … ON CONFLICT (chunk_id) DO UPDATE`; stores extra metadata keys (everything except `chunk_id`, `user_id`, `doc_id`) as JSONB.

**Typical ingest flow:** `load_document_text` → `chunk_documents` → `embed_documents([d.page_content for d in docs])` → `upsert_chunks(docs, vectors)`.

---

### `app/retrieval/rbac.py`

- **`Principal`** — Frozen dataclass with **`user_id`** only.
- **`retrieve(query, principal, top_k)`** — Embeds `query`, runs SQL selecting `chunk_id`, `doc_id`, `content`, `metadata`, and cosine distance `(embedding <=> query_vector)` ordered by distance, limited to `top_k`, **`WHERE user_id = principal.user_id`**.

Returns a list of row dicts (column names from the cursor).

---

### `app/chains/rag.py`

- **`_format_docs(docs)`** — Joins `page_content` from LangChain documents (or stringifies items).
- **`build_rag_chain(llm, retriever)`** — Builds an LCEL chain:
  - Input: dict with **`question`**.
  - `context` = formatted results of **`retriever.invoke(x["question"])`**.
  - System prompt instructs to use only context; human message is the question.
  - Pipe through **`llm`** and **`StrOutputParser`**.

**Note:** You must supply a LangChain **`BaseLanguageModel`** (or compatible runnable) and a retriever (for example a `BaseRetriever` that wraps `retrieve` for a fixed `Principal`). OpenRouter / chat models are **not** configured in this module.

---

### `app/main.py`

- Loads settings, opens a connection, runs `SELECT 1`, prints **`config and database connection OK`**. Used as a smoke test and Docker `command` default.

---

## SQL schema (`sql/init.sql`)

- Extension **`vector`**.
- Table **`rag_chunks`**:
  - `chunk_id` (unique), `user_id`, `doc_id`, `content`, `embedding vector(768)`, `metadata` JSONB, timestamps.
- Indexes: **IVFFlat** on `embedding` with `vector_cosine_ops`; **B-tree** on `user_id`.

---

## Docker (`docker-compose.yml`)

- **`db`** — Image `pgvector/pgvector:pg16`, port mapping, volume `pgdata`, mounts `sql/init.sql` into `docker-entrypoint-initdb.d` for first-time init, healthcheck.
- **`app`** (profile **`app`**) — Builds `Dockerfile`, depends on healthy `db`, uses `.env`, overrides `DATABASE_URL` default to `postgresql://rag:rag@db:5432/ragdb`, mounts `./app` read-only and `./data` for uploads, runs `python -m app.main`.

---

## Dependencies (`requirements.txt`)

Core stack: `langchain-core`, `langchain-text-splitters`, `langchain-huggingface`, `sentence-transformers`, `torch`, `psycopg`, `pgvector`, `python-dotenv`, `docling`, `pydantic`, `pydantic-settings`.

There is **no** `langchain-openai` in `requirements.txt`; adding OpenRouter or OpenAI would require that dependency and separate configuration.

---

## Gaps and next steps

1. **End-to-end RAG** — Wire a `BaseRetriever` + LLM (e.g. OpenRouter via `ChatOpenAI`) into `build_rag_chain`; not present in repo yet.
2. **HTTP API** — No FastAPI/Flask app; only `main` smoke test.
3. **Auth** — `Principal.user_id` must come from your session/JWT; never trust client-sent ids without verification.
4. **Pooling** — Single connections per call; consider `psycopg_pool` under load.
5. **Tests** — Add tests that assert retrieval never crosses `user_id` boundaries.

---

## Related docs

- Root **`README.md`** — Quick start, layout summary, and operational notes.
