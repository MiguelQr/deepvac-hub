"""Thin Flask-aware wrapper around licensing.audit.record_event that fills
in request_id/source_ip/user_agent from the current request, so routes
don't repeat that boilerplate on every audited action.
"""

from __future__ import annotations

import uuid

from flask import g, request
from sqlalchemy.orm import Session

from licensing.audit import record_event


def log_event(
    session: Session,
    *,
    event_type: str,
    actor_user_id: uuid.UUID | None,
    organization_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    metadata: dict[str, object] | None = None,
) -> None:
    record_event(
        session,
        event_type=event_type,
        actor_user_id=actor_user_id,
        organization_id=organization_id,
        target_type=target_type,
        target_id=target_id,
        request_id=g.get("request_id"),
        source_ip=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        metadata=metadata,
    )
