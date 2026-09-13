# aiforge-core

Shared plumbing for my AI portfolio projects. Every project installs this package and
gets the same battle-tested pieces: an LLM router with provider fallback and strict
JSON-schema outputs, versioned prompts, a pgvector store with hybrid search, an audit
log, idempotent write keys, and a FastAPI app factory with a rate limit.

```
┌─────────────────────────── project (FastAPI app) ───────────────────────────┐
│  domain code, prompts/, migrations/, static UI                              │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │ imports
┌──────────────────────────────────▼──────────────────────────────────────────┐
│ aiforge_core                                                                │
│  llm.Router ──► providers: gemini → groq (ordered, timeout, fallback)       │
│      generate_json(prompt_name, variables, PydanticSchema)                  │
│  llm.prompts    versioned files  <name>.v<N>.md                             │
│  embed          MiniLM local embedder (384d)  +  StubEmbedder for tests     │
│  vectorstore    chunks table: vector + full-text + hybrid()                 │
│  audit          one row per pipeline stage                                  │
│  idempotency    once(key) — a write can never happen twice                  │
│  app            create_app(): /health, JSON logs, per-IP rate limit         │
│  testing        pytest fixtures: mock_router, stub_embedder, test_db        │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   ▼
                     PostgreSQL 16 + pgvector (one DB for rows, vectors, text)
```

## Used by

| Project | What it builds on top | Live demo |
|---|---|---|
| [inbox-to-actions](https://github.com/AbuBaker91-hub/inbox-to-actions) | Router + audit + idempotency for email → CRM writes | [try it](https://inbox-to-actions.vercel.app) |
| [docchat](https://github.com/AbuBaker91-hub/docchat) | vectorstore hybrid search + citation verification | [try it](https://docchat-mu-three.vercel.app) |
| [safesql](https://github.com/AbuBaker91-hub/safesql) | Router + audit around a SQL guard | [try it](https://safesql.vercel.app) |
| [shopsage](https://github.com/AbuBaker91-hub/shopsage) | vectorstore + Router for catalog-grounded answers | [try it](https://shopsage-two.vercel.app) |

## Key behaviors

- `Router.generate_json(prompt_name, variables, schema)` renders the versioned prompt,
  asks provider 1, on timeout or error asks provider 2, parses the JSON into `schema`.
  If parsing or validation fails it raises `ValidationFailed`. It never returns half data.
- Each call returns the model instance plus metadata: provider used, prompt_version, latency.
- `once(conn, key, fn)` runs `fn` only if the key was never processed; a second call is a
  silent no-op that returns the stored result.
- `audit.record()` writes one row per stage: stage, input_hash, prompt_version, ok, detail.
- `vectorstore.hybrid(query, k)` runs vector search and Postgres full-text search, merges
  with reciprocal-rank fusion, dedups by chunk id, returns top k with scores.
- `create_app()` adds a per-IP rate limit (protects free quotas on public demos) and `/health`.

All AI used is free tier: Gemini 2.5 Flash primary, Groq llama-3.3-70b fallback, and a
local CPU embedding model (MiniLM, no key at all). Tests never call any API.

## Install (from a project)

```
aiforge-core @ git+https://github.com/AbuBaker91-hub/aiforge-core@v0.1.0
```

Add the `[embeddings]` extra where real embeddings are needed (docchat, shopsage);
tests always use the built-in `StubEmbedder` and stay offline.

## Environment (same names in every project)

```
DATABASE_URL=postgresql://app:app@localhost:5432/app
GEMINI_API_KEY=            # required to run a demo with a real model
GROQ_API_KEY=              # optional fallback
LLM_PROVIDER_ORDER=gemini,groq
APP_RATE_LIMIT_PER_MIN=30
```

## Develop

```
make setup   # venv + deps + start the test Postgres (docker compose)
make test    # pytest — MockProvider and StubEmbedder, no keys, no network
make lint    # ruff check
```

DB-backed tests use `TEST_DATABASE_URL` (default `postgresql://postgres:postgres@localhost:5433/postgres`,
provided by `docker compose up -d`); they skip cleanly if Postgres is not reachable.

One-time manual smoke tests with a real free key:

```
python -m aiforge_core.llm.smoke     # one JSON answer via Gemini (or Groq with LLM_PROVIDER_ORDER=groq)
python -m aiforge_core.embed.smoke   # embeds three sentences, prints the nearest pair
```

## Keywords

LLM router, provider fallback, structured outputs, Pydantic validation, prompt versioning,
pgvector, hybrid search, RAG infrastructure, audit trail, idempotency, FastAPI, Gemini API, Groq.
