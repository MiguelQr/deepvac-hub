"""Seat assignment, with transactional seat-limit enforcement.

Concurrency: the parent OrganizationLicense row is locked with
SELECT ... FOR UPDATE before counting active assignments and inserting a
new one, so two concurrent requests for the last available seat cannot both
succeed (see tests/unit/test_seats.py for the concurrency test).
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from licensing.exceptions import SeatLimitExceededError
from licensing.models.enums import SeatAssignmentStatus
from licensing.models.licenses import LicenseSeatAssignment, OrganizationLicense


def ensure_seat_assigned(
    session: Session,
    *,
    organization_license_id: uuid.UUID,
    user_id: uuid.UUID,
    assigned_by_user_id: uuid.UUID,
) -> LicenseSeatAssignment:
    """Return the user's active seat assignment on this license, creating one
    if they don't have one yet and a seat is available.

    Must be called within an active transaction; the caller's session commit
    releases the row lock taken here.
    """
    locked_license = session.execute(
        select(OrganizationLicense)
        .where(OrganizationLicense.id == organization_license_id)
        .with_for_update()
    ).scalar_one()

    existing = session.execute(
        select(LicenseSeatAssignment).where(
            LicenseSeatAssignment.organization_license_id == organization_license_id,
            LicenseSeatAssignment.user_id == user_id,
            LicenseSeatAssignment.status == SeatAssignmentStatus.ACTIVE,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    active_seat_count = session.execute(
        select(func.count()).where(
            LicenseSeatAssignment.organization_license_id == organization_license_id,
            LicenseSeatAssignment.status == SeatAssignmentStatus.ACTIVE,
        )
    ).scalar_one()
    if active_seat_count >= locked_license.seat_limit:
        raise SeatLimitExceededError(
            f"Organization license {organization_license_id} has no available seats "
            f"({active_seat_count}/{locked_license.seat_limit})"
        )

    assignment = LicenseSeatAssignment(
        organization_license_id=organization_license_id,
        user_id=user_id,
        status=SeatAssignmentStatus.ACTIVE,
        assigned_by_user_id=assigned_by_user_id,
    )
    session.add(assignment)
    session.flush()
    return assignment


def remove_seat(session: Session, seat_assignment: LicenseSeatAssignment) -> None:
    from datetime import UTC, datetime

    seat_assignment.status = SeatAssignmentStatus.REMOVED
    seat_assignment.removed_at = datetime.now(UTC)
    session.flush()
