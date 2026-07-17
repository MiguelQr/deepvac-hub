"""FastAPI dependency providers. Thin wiring only — no business logic.

Management-authenticated endpoints (device revoke/replace/list) will get a
`require_management_session` dependency in Phase C/D once the session
mechanism shared with apps/web is implemented.
"""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from functools import lru_cache

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy.orm import Session

from licensing.config import get_settings
from licensing.database import get_sessionmaker
from licensing.security.signing import load_private_key_from_file


def get_db() -> Generator[Session, None, None]:
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@dataclass(frozen=True)
class SigningContext:
    key_id: str
    private_key: Ed25519PrivateKey


@lru_cache
def get_signing_context() -> SigningContext:
    """Loaded once per process from the deployment secret file -- never from
    the database, never logged (see docs/license-format.md key rotation).
    """
    settings = get_settings()
    key_path = settings.require_signing_key_path()
    private_key = load_private_key_from_file(key_path)
    return SigningContext(key_id=settings.license_signing_key_id, private_key=private_key)
