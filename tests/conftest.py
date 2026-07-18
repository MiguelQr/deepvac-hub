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

import licensing.database as database_module
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


@pytest.fixture
def flask_client(db_session: Session, monkeypatch):  # type: ignore[no-untyped-def]
    """A Flask test client whose app talks to the exact same per-test
    transactional connection as db_session -- so routes can be exercised
    over HTTP while still asserting against db_session directly, and
    everything rolls back together at teardown like the rest of the suite.

    apps/web routes call db.commit() (see apps/web/activate/routes.py for
    the established pattern); join_transaction_mode="create_savepoint"
    makes those commits release a SAVEPOINT instead of ending the outer
    per-test transaction db_session's rollback relies on.
    """
    connection = db_session.connection()
    test_sessionmaker = sessionmaker(
        bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )

    monkeypatch.setattr(database_module, "get_sessionmaker", lambda: test_sessionmaker)
    database_module.get_scoped_session.cache_clear()

    from apps.web.app import create_app

    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    with app.test_client() as client:
        yield client

    database_module.get_scoped_session().remove()
    database_module.get_scoped_session.cache_clear()
