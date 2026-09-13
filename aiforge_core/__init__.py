"""aiforge-core: shared plumbing for the AI portfolio projects.

Modules:
    llm         Router with ordered providers, fallback and JSON-schema outputs
    embed       local sentence-transformers embedder + deterministic stub
    vectorstore chunks table, vector + keyword + hybrid search
    audit       one audit row per pipeline stage
    idempotency run-once keys backed by a processed_keys table
    app         FastAPI app factory with /health, JSON logs and a rate limit
    testing     pytest fixtures: mock_router, stub_embedder, test_db
"""

__version__ = "0.1.0"
