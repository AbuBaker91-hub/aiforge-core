"""Chunks table: upsert, vector search, keyword search, hybrid merge.

hybrid() runs vector search and Postgres full text search, merges, dedups by
chunk id and returns the top k with scores. The merge itself is a pure function
(merge_results) so it is testable without a database.
"""

from dataclasses import dataclass

import psycopg


@dataclass
class Chunk:
    id: int
    doc: str
    page: int | None
    section: str | None
    text: str
    score: float


def upsert(conn: psycopg.Connection, chunks: list[dict], embedder) -> int:
    """chunks: [{doc, page, section, text}]. Returns number of new rows."""
    if not chunks:
        return 0
    vectors = embedder.embed([c["text"] for c in chunks])
    inserted = 0
    for c, v in zip(chunks, vectors, strict=True):
        row = conn.execute(
            """INSERT INTO chunks (doc, page, section, text, embedding)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (doc, page, section, text) DO NOTHING
               RETURNING id""",
            (c["doc"], c.get("page"), c.get("section", ""), c["text"], v),
        ).fetchone()
        if row:
            inserted += 1
    return inserted


def delete_doc(conn: psycopg.Connection, doc: str) -> None:
    conn.execute("DELETE FROM chunks WHERE doc = %s", (doc,))


def vector_search(conn: psycopg.Connection, query: str, k: int, embedder) -> list[Chunk]:
    qvec = embedder.embed_one(query)
    rows = conn.execute(
        """SELECT id, doc, page, section, text, 1 - (embedding <=> %s::vector) AS score
           FROM chunks ORDER BY embedding <=> %s::vector LIMIT %s""",
        (qvec, qvec, k),
    ).fetchall()
    return [Chunk(*r) for r in rows]


def keyword_search(conn: psycopg.Connection, query: str, k: int) -> list[Chunk]:
    rows = conn.execute(
        """SELECT id, doc, page, section, text,
                  ts_rank(tsv, plainto_tsquery('english', %s)) AS score
           FROM chunks
           WHERE tsv @@ plainto_tsquery('english', %s)
           ORDER BY score DESC LIMIT %s""",
        (query, query, k),
    ).fetchall()
    return [Chunk(*r) for r in rows]


def merge_results(vector: list[Chunk], keyword: list[Chunk], k: int) -> list[Chunk]:
    """Reciprocal-rank fusion; dedups by chunk id."""
    K = 60.0
    scores: dict[int, float] = {}
    by_id: dict[int, Chunk] = {}
    for results in (vector, keyword):
        for rank, chunk in enumerate(results):
            scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (K + rank + 1)
            by_id.setdefault(chunk.id, chunk)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:k]
    out = []
    for chunk_id, score in ranked:
        c = by_id[chunk_id]
        out.append(Chunk(c.id, c.doc, c.page, c.section, c.text, round(score, 6)))
    return out


def hybrid(conn: psycopg.Connection, query: str, k: int, embedder) -> list[Chunk]:
    return merge_results(
        vector_search(conn, query, k, embedder), keyword_search(conn, query, k), k
    )
