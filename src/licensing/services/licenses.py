"""Organization license creation, plus the license-scoped seat and
certificate views used by the licenses/organizations blueprints.

Licenses in this product are lifetime grants: there is no suspend/revoke/
renew lifecycle (deliberately dropped -- see README.md's Phase D notes).
Once created, a license's only state is what's set at creation time; the
issued device certificates (services/issuance.py) carry their own long
validity window independent of this record.

Seat assignment delegates its locking/limit logic to services/seats.py
rather than duplicating it -- this module only adds the membership
precondition (a seat can only go to an active member of the license's org)
and authorization.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from licensing.exceptions import ConflictError, NotFoundError
from licensing.models.certificates import IssuedLicenseCertificate
from licensing.models.devices import DeviceActivation
from licensing.models.enums import OrganizationLicenseStatus, SeatAssignmentStatus
from licensing.models.licenses import LicenseSeatAssignment, OrganizationLicense
from licensing.models.users import User
from licensing.services import auth as auth_service
from licensing.services import seats as seats_service


def create_license(
    session: Session,
    *,
    actor: User,
    organization_id: uuid.UUID,
    product_id: uuid.UUID,
    edition_id: uuid.UUID,
    seat_limit: int,
    device_limit_per_user: int,
    starts_at: datetime,
    expires_at: datetime,
    offline_validity_days: int,
) -> OrganizationLicense:
    auth_service.require_vendor(actor, write=True)
    if expires_at <= starts_at:
        raise ConflictError("Expiry date must be after the start date.")
    status = (
        OrganizationLicenseStatus.ACTIVE
        if starts_at <= datetime.now(UTC)
        else OrganizationLicenseStatus.PENDING
    )
    license_ = OrganizationLicense(
        organization_id=organization_id,
        product_id=product_id,
        edition_id=edition_id,
        status=status,
        seat_limit=seat_limit,
        device_limit_per_user=device_limit_per_user,
        starts_at=starts_at,
        expires_at=expires_at,
        offline_validity_days=offline_validity_days,
    )
    session.add(license_)
    session.flush()
    return license_


def get_license(
    session: Session, *, actor: User, license_id: uuid.UUID
) -> OrganizationLicense:
    license_ = session.get(OrganizationLicense, license_id)
    if license_ is None:
        raise NotFoundError(f"License {license_id} not found.")
    auth_service.require_org_view(session, actor, license_.organization_id)
    return license_


def list_licenses_for_org(
    session: Session, *, actor: User, organization_id: uuid.UUID
) -> list[OrganizationLicense]:
    auth_service.require_org_view(session, actor, organization_id)
    return list(
        session.execute(
            select(OrganizationLicense)
            .where(OrganizationLicense.organization_id == organization_id)
            .order_by(OrganizationLicense.created_at.desc())
        ).scalars()
    )


def list_seats_for_license(
    session: Session, *, actor: User, license_id: uuid.UUID
) -> list[LicenseSeatAssignment]:
    license_ = get_license(session, actor=actor, license_id=license_id)
    return list(
        session.execute(
            select(LicenseSeatAssignment)
            .where(
                LicenseSeatAssignment.organization_license_id == license_.id,
                LicenseSeatAssignment.status == SeatAssignmentStatus.ACTIVE,
            )
            .order_by(LicenseSeatAssignment.assigned_at)
        ).scalars()
    )


def assign_seat_to_member(
    session: Session, *, actor: User, license_id: uuid.UUID, user_email: str
) -> LicenseSeatAssignment:
    license_ = session.get(OrganizationLicense, license_id)
    if license_ is None:
        raise NotFoundError(f"License {license_id} not found.")
    auth_service.require_org_admin(session, actor, license_.organization_id)

    normalized_email = user_email.strip().lower()
    target_user = session.execute(
        select(User).where(User.normalized_email == normalized_email)
    ).scalar_one_or_none()
    if target_user is None:
        raise NotFoundError(f"No user found with email {user_email!r}.")

    membership = auth_service.get_active_membership(
        session, user_id=target_user.id, organization_id=license_.organization_id
    )
    if membership is None:
        raise ConflictError(
            f"{user_email} must be a member of this organization before being assigned a seat."
        )

    return seats_service.ensure_seat_assigned(
        session,
        organization_license_id=license_.id,
        user_id=target_user.id,
        assigned_by_user_id=actor.id,
    )


def remove_seat_from_license(
    session: Session, *, actor: User, license_id: uuid.UUID, seat_assignment_id: uuid.UUID
) -> None:
    license_ = session.get(OrganizationLicense, license_id)
    if license_ is None:
        raise NotFoundError(f"License {license_id} not found.")
    auth_service.require_org_admin(session, actor, license_.organization_id)

    seat_assignment = session.get(LicenseSeatAssignment, seat_assignment_id)
    if seat_assignment is None or seat_assignment.organization_license_id != license_.id:
        raise NotFoundError(f"Seat assignment {seat_assignment_id} not found on this license.")
    seats_service.remove_seat(session, seat_assignment)


def list_certificates_for_license(
    session: Session, *, actor: User, license_id: uuid.UUID
) -> list[IssuedLicenseCertificate]:
    license_ = get_license(session, actor=actor, license_id=license_id)
    return list(
        session.execute(
            select(IssuedLicenseCertificate)
            .join(
                DeviceActivation,
                IssuedLicenseCertificate.device_activation_id == DeviceActivation.id,
            )
            .where(DeviceActivation.organization_license_id == license_.id)
            .order_by(IssuedLicenseCertificate.issued_at.desc())
        ).scalars()
    )
