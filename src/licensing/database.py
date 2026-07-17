"""SQLAlchemy 2.x engine/session setup, shared by both apps.

Both apps/api and apps/web call get_engine()/session_scope() from
here rather than constructing their own engines, so pool configuration and
connection handling stay consistent.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, scoped_session, sessionmaker

from licensing.config import get_settings


class Base(DeclarativeBase):
    """Shared declarative base for every model in src/licensing/models."""


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


@lru_cache
def get_scoped_session() -> scoped_session[Session]:
    """Thread-local session factory for the Flask app (one session per
    request thread, torn down in app.py's teardown_appcontext).
    """
    return scoped_session(get_sessionmaker())


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional session; commits on success, rolls back on error."""
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_database_connection() -> bool:
    """Used by the /health/ready endpoint."""
    from sqlalchemy import text

    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
