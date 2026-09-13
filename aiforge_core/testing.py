"""Pytest fixtures shared by every project: mock_provider, mock_router,
stub_embedder, test_db. No network, no keys, no real model anywhere.

Use in a project's conftest.py:

    from aiforge_core.testing import *  # noqa: F401,F403

test_db needs a reachable Postgres with the pgvector extension; set
TEST_DATABASE_URL (default postgresql://postgres:postgres@localhost:5433/postgres).
If it is unreachable the DB-backed tests are skipped, everything else runs.
"""

import os
import uuid

import pytest

from .db import connect, run_migrations
from .embed import StubEmbedder
from .llm.providers.mock import MockProvider
from .llm.router import Router

__all__ = [
    "mock_provider",
    "mock_router",
    "stub_embedder",
    "test_db",
    "project_migrations_dir",
    "prompts_dir",
    "make_router",
]


def make_router(mock: MockProvider, prompts_dir: str) -> Router:
    return Router([mock], prompts_dir=prompts_dir, timeout_s=5.0)


@pytest.fixture
def mock_provider() -> MockProvider:
    return MockProvider()


@pytest.fixture
def prompts_dir(tmp_path):
    """Override in the project conftest to point at the real prompts/ folder."""
    return str(tmp_path / "prompts_missing")


@pytest.fixture
def mock_router(mock_provider, prompts_dir) -> Router:
    return make_router(mock_provider, prompts_dir)


@pytest.fixture
def stub_embedder() -> StubEmbedder:
    return StubEmbedder()


@pytest.fixture
def project_migrations_dir():
    """Override in the project conftest to also apply project migrations."""
    return None


@pytest.fixture
def test_db(project_migrations_dir):
    admin_url = os.getenv(
        "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/postgres"
    )
    sep = "&" if "?" in admin_url else "?"
    try:
        admin = connect(f"{admin_url}{sep}connect_timeout=5")
    except Exception as e:  # pragma: no cover - environment dependent
        pytest.skip(f"test Postgres not reachable at {admin_url}: {e}")
        return
    db_name = f"test_{uuid.uuid4().hex[:12]}"
    admin.execute(f'CREATE DATABASE "{db_name}"')
    base, _, _ = admin_url.rpartition("/")
    conn = connect(f"{base}/{db_name}")
    run_migrations(conn, project_migrations_dir)
    try:
        yield conn
    finally:
        conn.close()
        admin.execute(f'DROP DATABASE "{db_name}" WITH (FORCE)')
        admin.close()
