# Chatbot RAG (skeleton)

This repository is a **starter layout** for a retrieval-augmented generation (RAG) pipeline in Python: documents are parsed (intended for [Docling](https://github.com/docling-project/docling)), chunked, embedded with **Hugging Face** models, stored in **PostgreSQL** with the **[pgvector](https://github.com/pgvector/pgvector)** extension, and retrieved with **per-user isolation**. [LangChain](https://python.langchain.com/) types are used where helpful (`Document`, `Embeddings`, optional chains).

Most application functions are **stubs** (`...`) so you can implement ingestion, retrieval, and orchestration yourself.

## What is included

- **Docker Compose** — PostgreSQL 16 with pgvector; optional Python `app` service (see below).
- **SQL schema** — `rag_chunks` table with 768-dimensional vectors and `user_id` for scoping queries.
- **Python package** — `app/` modules for config, DB access, embeddings, ingest, retrieval, and an optional RAG chain.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose (Compose V2).
- For local development without the `app` container: Python 3.12+ and dependencies from `requirements.txt`.

## Quick start

1. Copy environment template and adjust if needed:

   ```bash
   cp .env.example .env
   ```

2. Start only the database (recommended while you implement the Python code locally):

   ```bash
   docker compose up -d
   ```

   On the **first** run with an empty volume, `sql/init.sql` is applied automatically via `docker-entrypoint-initdb.d`.

3. Optional: build and run the placeholder app container (uses profile `app`):

   ```bash
   docker compose --profile app up -d --build
   ```

   The `app` service expects a `.env` file (see `.env.example`) and mounts `./app` read-only plus `./data` for file uploads.

To reset the database in development (destroys the Postgres volume):

```bash
docker compose down -v
docker compose up -d
```

## Environment variables

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string. From the host, use `localhost` and the mapped port; from the `app` service, use host `db`. |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT` | Used by Compose for the `db` service. |
| `HUGGINGFACE_HUB_TOKEN` | Optional; required for some gated models on Hugging Face. |
| `EMBEDDING_MODEL_NAME` | Pydantic Settings maps this to `embedding_model_name` in `app/config.py` (default: `BAAI/bge-base-en-v1.5`). |

See `.env.example` for a minimal template.

## Project layout

```
chatbot/
├── docker-compose.yml    # Postgres + optional app service
├── Dockerfile            # Python runtime for the app service
├── requirements.txt
├── sql/
│   └── init.sql          # pgvector extension + rag_chunks schema
├── app/
│   ├── config.py         # Settings (DB URL, embedding model, dim 768)
│   ├── main.py           # Entry point (stub)
│   ├── db/pool.py        # psycopg connection helpers (stubs)
│   ├── embeddings/
│   │   └── huggingface.py  # LangChain Embeddings + helpers (stubs)
│   ├── ingest/
│   │   ├── docling_loader.py  # Docling → text (stub)
│   │   └── pipeline.py        # chunk + upsert to DB (stubs)
│   ├── retrieval/
│   │   └── rbac.py       # Principal(user_id) + retrieve (stub)
│   └── chains/
│       └── rag.py        # Optional LCEL chain (stub)
├── data/                 # Mounted volume for uploads (gitignored)
└── tests/
```

## Database model

Table **`rag_chunks`** (see `sql/init.sql`):

- **`chunk_id`** — Stable unique id per chunk (your application should define how this is generated).
- **`user_id`** — **Required for isolation**: every vector search must filter by the authenticated user’s id so one user cannot read another’s chunks.
- **`doc_id`** — Logical source document identifier.
- **`content`** — Chunk text.
- **`embedding`** — `vector(768)`; must match the output dimension of your embedding model.
- **`metadata`** — JSONB for extra fields (e.g. page, filename).

Indexes: **IVFFlat** on `embedding` for cosine distance, and **B-tree** on `user_id` for filtering.

If you change the embedding model dimension, update **`sql/init.sql`**, **`app/config.py`** (`embedding_dim`), and recreate or migrate the database accordingly.

## Implementation notes

1. **`get_settings()`** in `app/config.py` — Return a `Settings` instance (typically `Settings()`), optionally validating env at startup.
2. **`app/db/pool.py`** — Wire `psycopg` connections or a pool; register pgvector types if you pass vectors as Python lists.
3. **`app/embeddings/huggingface.py`** — Instantiate `langchain_huggingface` / `sentence_transformers` embeddings with output dimension **768** unless you change the schema.
4. **`app/ingest/`** — Docling converts files to text; split with LangChain text splitters; attach `user_id` and `doc_id` in `Document.metadata` before upserting.
5. **`app/retrieval/rbac.py`** — Embed the query, run SQL with `WHERE user_id = %s` **and** `ORDER BY embedding <=> query_vector` (or equivalent), never omit the user filter.
6. **`app/chains/rag.py`** — Optional: build an LCEL chain that calls your retriever and your chosen LLM.

## Testing

`tests/` contains a placeholder test. Add tests that assert retrieval never crosses `user_id` boundaries once you implement `retrieve`.

## License

Add a license file if you distribute this project.
