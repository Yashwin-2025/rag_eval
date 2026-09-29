# Chatbot RAG

This repository is a RAG-oriented Python project: documents are parsed with [Docling](https://github.com/docling-project/docling), chunked, embedded with **Hugging Face** models, stored in **PostgreSQL** with the **[pgvector](https://github.com/pgvector/pgvector)** extension, and retrieved with **per-user** `user_id` filtering. [LangChain](https://python.langchain.com/) is used for documents, embeddings, text splitting, and an LCEL RAG chain helper.

**Code reference (module-by-module):** see [docs/CURRENT_CODE.md](docs/CURRENT_CODE.md).

## What is included

- **Docker Compose** — PostgreSQL 16 with pgvector; optional Python `app` service (see below).
- **SQL schema** — `rag_chunks` table with 1024-dimensional vectors and `user_id` for scoping queries.
- **Python package** — Config, DB pool, Hugging Face embeddings, Docling loader, chunk/upsert pipeline, pgvector retrieval, LCEL `build_rag_chain(llm, retriever)`, and a small `main` DB smoke test.

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
| `OPENROUTER_API_KEY` | Required. Used for both embeddings and chat via OpenRouter's OpenAI-compatible API. |
| `OPENROUTER_EMBEDDING_MODEL`, `OPENROUTER_CHAT_MODEL` | OpenRouter model ids (default: `openai/text-embedding-3-small`, `openai/gpt-4o-mini`). |
| `EMBEDDING_DIM` | Pydantic Settings maps this to `embedding_dim` in `app/config.py` (default: `1024`); passed as the OpenAI `dimensions` param when embedding. |

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
│   ├── config.py         # Settings (DB URL, embedding model, dim 1024)
│   ├── main.py           # DB connectivity smoke test
│   ├── db/pool.py        # psycopg connection helpers
│   ├── embeddings/
│   │   └── huggingface.py  # HuggingFaceEmbeddings + embed helpers
│   ├── ingest/
│   │   ├── docling_loader.py  # Docling → markdown text
│   │   └── pipeline.py        # chunk + upsert into rag_chunks
│   ├── retrieval/
│   │   └── rbac.py       # Principal(user_id) + pgvector retrieve
│   └── chains/
│       └── rag.py        # LCEL RAG chain (requires injected llm + retriever)
├── data/                 # Mounted volume for uploads (gitignored)
└── tests/
```

## Database model

Table **`rag_chunks`** (see `sql/init.sql`):

- **`chunk_id`** — Stable unique id per chunk (your application should define how this is generated).
- **`user_id`** — **Required for isolation**: every vector search must filter by the authenticated user’s id so one user cannot read another’s chunks.
- **`doc_id`** — Logical source document identifier.
- **`content`** — Chunk text.
- **`embedding`** — `vector(1024)`; must match the output dimension of your embedding model.
- **`metadata`** — JSONB for extra fields (e.g. page, filename).

Indexes: **IVFFlat** on `embedding` for cosine distance, and **B-tree** on `user_id` for filtering.

If you change the embedding model dimension, update **`sql/init.sql`**, **`app/config.py`** (`embedding_dim`), and recreate or migrate the database accordingly.

## Implementation notes

1. **`DATABASE_URL`** is required (no default in `Settings`) — set in `.env` or the environment.
2. **`app/chains/rag.py`** does not create an LLM; supply OpenRouter, Ollama, or another model when calling `build_rag_chain`.
3. See **[docs/CURRENT_CODE.md](docs/CURRENT_CODE.md)** for file-by-file behavior and gaps.

## Testing

`tests/` contains a placeholder test. Add tests that assert retrieval never crosses `user_id` boundaries.

## License

Add a license file if you distribute this project.
