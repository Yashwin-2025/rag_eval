# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository overview

This repo contains **two separate applications** that share a Python environment but do not
import from each other:

1. **`app/`** — a multi-tenant RAG chatbot. Docling ingestion → HuggingFace/OpenRouter
   embeddings → Postgres + pgvector (`rag_chunks` table, per-`user_id` isolation) → LangChain
   LCEL retrieval chain → FastAPI (`app/api.py`). Includes a Responsible-AI guardrail layer
   (`app/responsible_ai_router.py`, `app/services/guardrails.py`).
2. **`aether_ot/`** — AETHER-OT, a cyber-physical digital twin of a warehouse (physics sim +
   Modbus PLC server + ML anomaly detector + LangGraph "AI detective" agent + FastAPI/WebSocket
   3D dashboard), used to demonstrate OT/ICS attack detection and investigation. See
   [PROJECT.md](PROJECT.md) for its full architecture and a recommended reading order.

When working on one, you generally don't need to touch the other.

## Commands

### RAG chatbot (`app/`)
```bash
cp .env.example .env               # set OPENROUTER_API_KEY at minimum
docker compose up -d                # starts Postgres+pgvector only; sql/init.sql auto-applies on first run
docker compose --profile app up -d --build   # also builds/runs the app container on :8000
docker compose down -v              # reset dev DB (destroys the Postgres volume)
```
Run the app locally without Docker (Postgres must be reachable via `DATABASE_URL`):
```bash
uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
```

### AETHER-OT (`aether_ot/`)
```bash
pip install -r requirements.txt
python run_system.py                # dashboard on :8000, Modbus TCP PLC on 127.0.0.1:5020
python -m aether_ot.attacks.attack_harness   # fire a simulated ICS attack against the running PLC
```

### Tests
```bash
pytest                              # runs everything under tests/
pytest tests/test_warehouse_sim.py  # single file
pytest tests/test_warehouse_sim.py::test_name -v   # single test
```
There is no linter/formatter configured in this repo (no ruff/black/mypy config present).

## Architecture notes

### `app/` — RAG chatbot
- **Isolation is the core invariant**: every row in `rag_chunks` carries a `user_id`
  (`sql/init.sql`), and every retrieval call must filter by the authenticated user's id
  (`app/retrieval/rbac.py`). `app/api.py` derives identity from a dev-only `X-User-Id` header
  (`require_user_id`) — replace with real auth before this leaves dev.
- Settings are centralized in `app/config.py` (`Settings`, pydantic-settings, `.env`-driven).
  `DATABASE_URL` and `OPENROUTER_API_KEY` have no defaults and are required.
- **Embedding dimension is a cross-cutting constant**: `sql/init.sql`'s `vector(N)`, `Settings.embedding_dim`,
  and the `dimensions` param passed to `OpenAIEmbeddings` in `app/embeddings/openrouter.py` must all
  agree, or ingestion/retrieval breaks silently. Currently 1024 (truncated from `text-embedding-3-small`'s
  native 1536 via OpenAI's `dimensions` param). If you change it, update all three plus `.env`'s
  `EMBEDDING_DIM`, and reset the DB (`docker compose down -v`) since existing rows won't match the new
  column width.
- Guardrails (`app/services/guardrails.py`: PII scrubbing, prompt-injection checks, verbatim-overlap
  checks, medical-safety checks) run in the request path before/around the LLM call, not just as
  an eval-time check — see `app/responsible_ai_router.py` for how they're wired into the API.
- `eval/*.jsonl` + `eval_benchmark_report.json` are the ground-truth QA sets this pipeline is
  scored against (FinanceBench, enterprise handbook, regulatory compliance, AI safety).

### `aether_ot/` — AETHER-OT digital twin
Full breakdown, data flow diagram, and a suggested file-by-file reading order are in
[PROJECT.md](PROJECT.md). Key structural point: `aether_ot/dashboard/backend/main.py` runs a
single asyncio event loop (`simulation_tick_loop`, 10Hz) that drives physics, Modbus sync, anomaly
detection, SQLite logging, and WebSocket broadcast all in one place — anything blocking added to
that loop stalls the whole simulation/dashboard. The LangGraph investigation
(`aether_ot/agent/ai_detective.py`) is deliberately offloaded via `asyncio.to_thread` so it never
blocks physics ticks; follow that pattern for any other slow/blocking work added to the loop.
`docs/industrial_ai_ot_cybersecurity_blueprint.md` has the OT/ICS domain model (Purdue levels,
protocols, MITRE ATT&CK for ICS) the simulator and attack harness are built against.
