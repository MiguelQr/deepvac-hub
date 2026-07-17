from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column


def pg_enum[E: StrEnum](enum_cls: type[E], name: str) -> Enum:
    """Native Postgres ENUM that stores the StrEnum's *value* (e.g. "active")
    rather than SQLAlchemy's default of the member *name* (e.g. "ACTIVE").

    Without this, partial unique indexes and raw SQL written against the
    lowercase values (see organizations.py, licenses.py) would never match
    what's actually stored, silently defeating the constraint.
    """
    return Enum(
        enum_cls,
        name=name,
        native_enum=True,
        values_callable=lambda obj: [e.value for e in obj],
    )


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
