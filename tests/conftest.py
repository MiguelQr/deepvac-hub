"""Shared pytest fixtures.

Uses a real PostgreSQL database (TEST_DATABASE_URL / DATABASE_URL), not
SQLite, per the project's testing requirements — SQLite doesn't support
partial unique indexes, native enums, or JSONB the way the models rely on.

Each test runs inside an outer transaction that is rolled back afterward, so
tests don't need to clean up after themselves and can run in any order.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import licensing.models  # noqa: F401  ensures all tables are registered
from licensing.config import get_settings
from licensing.database import Base


@pytest.fixture(scope="session")
def db_url() -> str:
    settings = get_settings()
    return settings.test_database_url or settings.database_url


@pytest.fixture(scope="session")
def engine(db_url: str):  # type: ignore[no-untyped-def]
    eng = create_engine(db_url, future=True)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db_session(engine) -> Generator[Session, None, None]:  # type: ignore[no-untyped-def]
    connection = engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection, expire_on_commit=False)
    session = session_factory()

    yield session

    session.close()
    # A test that deliberately triggers an IntegrityError (constraint tests)
    # leaves the DBAPI connection's transaction already aborted/deassociated
    # by the driver, so the outer transaction handle may no longer be active
    # here — that's expected, not an error, hence the guard.
    if transaction.is_active:
        transaction.rollback()
    connection.close()
