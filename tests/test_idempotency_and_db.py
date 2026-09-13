"""DB-backed tests. Skipped automatically when the test Postgres is unreachable
(see aiforge_core.testing.test_db)."""

from aiforge_core import audit, vectorstore
from aiforge_core.idempotency import key, once


def test_once_runs_only_on_first_call(test_db):
    calls = []

    def action():
        calls.append(1)
        return {"written": True}

    k = key("email-123", "create_contact")
    result1, ran1 = once(test_db, k, action)
    result2, ran2 = once(test_db, k, action)
    assert ran1 is True and ran2 is False
    assert calls == [1]
    assert result1 == {"written": True}
    assert result2 == {"written": True}


def test_hybrid_dedups_shared_chunk(test_db, stub_embedder):
    chunks = [
        {"doc": "manual", "page": 1, "section": "returns", "text": "returns accepted within 30 days"},
        {"doc": "manual", "page": 2, "section": "shipping", "text": "shipping takes five days"},
    ]
    assert vectorstore.upsert(test_db, chunks, stub_embedder) == 2
    results = vectorstore.hybrid(test_db, "returns accepted days", k=5, embedder=stub_embedder)
    ids = [c.id for c in results]
    assert len(ids) == len(set(ids))
    assert results, "expected at least one hit"


def test_upsert_same_chunk_twice_inserts_once(test_db, stub_embedder):
    chunk = [{"doc": "d", "page": 1, "section": "s", "text": "identical text"}]
    assert vectorstore.upsert(test_db, chunk, stub_embedder) == 1
    assert vectorstore.upsert(test_db, chunk, stub_embedder) == 0


def test_audit_record_and_fetch(test_db):
    audit.record(test_db, "classify", ref="email-1", prompt_version="classify.v1", ok=True)
    audit.record(test_db, "extract", ref="email-1", ok=False, detail="validation error")
    rows = audit.rows_for(test_db, "email-1")
    assert [r["stage"] for r in rows] == ["classify", "extract"]
    assert rows[1]["ok"] is False
