"""Run-once keys backed by the processed_keys table.

once(conn, key, fn) runs fn only if the key was never processed; a second call
with the same key is a silent no-op that returns the stored result.
"""

import hashlib
import json
from typing import Any

import psycopg


def key(*parts) -> str:
    joined = "|".join(str(p) for p in parts)
    return hashlib.sha256(joined.encode()).hexdigest()[:32]


def once(conn: psycopg.Connection, k: str, fn) -> tuple[Any, bool]:
    """Returns (result, ran). ran is False when the key was already processed,
    in which case result is the stored value (JSON round-tripped)."""
    existing = conn.execute(
        "SELECT result_json FROM processed_keys WHERE key = %s", (k,)
    ).fetchone()
    if existing is not None:
        return existing[0], False
    result = fn()
    conn.execute(
        """INSERT INTO processed_keys (key, result_json) VALUES (%s, %s)
           ON CONFLICT (key) DO NOTHING""",
        (k, json.dumps(result, default=str)),
    )
    return result, True
