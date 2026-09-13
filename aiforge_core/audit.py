"""audit_log: one row per pipeline stage."""

import hashlib

import psycopg


def input_hash(data) -> str:
    text = data if isinstance(data, str) else repr(data)
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def record(
    conn: psycopg.Connection,
    stage: str,
    *,
    ref: str = "",
    input_hash: str = "",
    prompt_version: str = "",
    ok: bool = True,
    detail: str = "",
) -> None:
    conn.execute(
        """INSERT INTO audit_log (stage, ref, input_hash, prompt_version, ok, detail)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (stage, ref, input_hash, prompt_version, ok, detail[:2000]),
    )


def rows_for(conn: psycopg.Connection, ref: str) -> list[dict]:
    rows = conn.execute(
        """SELECT stage, input_hash, prompt_version, ok, detail, created_at
           FROM audit_log WHERE ref = %s ORDER BY id""",
        (ref,),
    ).fetchall()
    return [
        {
            "stage": r[0],
            "input_hash": r[1],
            "prompt_version": r[2],
            "ok": r[3],
            "detail": r[4],
            "created_at": r[5].isoformat(),
        }
        for r in rows
    ]
