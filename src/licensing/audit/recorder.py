"""The only sanctioned way to write an AuditEvent row.

Routes/services must call record_event() rather than constructing
AuditEvent directly, so the metadata allow-list guard in allowlist.py is
always applied.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from licensing.audit.allowlist import assert_allowed_metadata
from licensing.models.audit import AuditEvent


def record_event(
    session: Session,
    *,
    event_type: str,
    actor_user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    request_id: str | None = None,
    source_ip: str | None = None,
    user_agent: str | None = None,
    metadata: dict[str, object] | None = None,
) -> AuditEvent:
    assert_allowed_metadata(metadata)
    event = AuditEvent(
        event_type=event_type,
        actor_user_id=actor_user_id,
        organization_id=organization_id,
        target_type=target_type,
        target_id=target_id,
        request_id=request_id,
        source_ip=source_ip,
        user_agent=user_agent,
        event_metadata=metadata,
    )
    session.add(event)
    return event
