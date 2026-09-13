"""Postgres connection helper and a minimal SQL-file migration runner."""

import os
from importlib.resources import files
from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector


def database_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql://app:app@localhost:5432/app")


def connect(url: str | None = None) -> psycopg.Connection:
    conn = psycopg.connect(url or database_url(), autocommit=True)
    try:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    except psycopg.Error:
        pass  # no permission on managed DBs where the extension is pre-enabled
    register_vector(conn)
    return conn


def core_migrations_dir() -> Path:
    return Path(str(files("aiforge_core").joinpath("migrations")))


def run_migrations(conn: psycopg.Connection, project_dir: str | Path | None = None) -> list[str]:
    """Apply core migrations, then the project's migrations/ folder, in filename
    order. Each file runs once; applied names are tracked in schema_migrations."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations (
               name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"""
    )
    applied: list[str] = []
    dirs = [core_migrations_dir()]
    if project_dir is not None:
        dirs.append(Path(project_dir))
    for d in dirs:
        if not d.is_dir():
            continue
        for sql_file in sorted(d.glob("*.sql")):
            done = conn.execute(
                "SELECT 1 FROM schema_migrations WHERE name = %s", (sql_file.name,)
            ).fetchone()
            if done:
                continue
            conn.execute(sql_file.read_text(encoding="utf-8"))
            conn.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (sql_file.name,))
            applied.append(sql_file.name)
    return applied
