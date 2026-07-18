"""Vendor-console summary counts. No audit-derived widgets here on purpose
-- the filterable /audit page is Phase F's job, not this dashboard's.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from licensing.models.devices import DeviceActivation
from licensing.models.enums import (
    DeviceActivationStatus,
    OrganizationLicenseStatus,
    OrganizationStatus,
    SeatAssignmentStatus,
)
from licensing.models.licenses import LicenseSeatAssignment, OrganizationLicense
from licensing.models.organizations import Organization
from licensing.models.users import User
from licensing.services import auth as auth_service


@dataclass
class DashboardSummary:
    active_organizations: int
    active_licenses: int
    seats_used: int
    seats_available: int
    active_devices: int
    expiring_licenses: list[OrganizationLicense]


def get_summary(
    session: Session, *, actor: User, expiring_within_days: int = 30
) -> DashboardSummary:
    auth_service.require_vendor(actor)

    active_organizations = session.execute(
        select(func.count()).where(Organization.status == OrganizationStatus.ACTIVE)
    ).scalar_one()

    active_licenses = session.execute(
        select(func.count()).where(
            OrganizationLicense.status == OrganizationLicenseStatus.ACTIVE
        )
    ).scalar_one()

    # Scoped to seats on ACTIVE licenses only, so seats_used and the
    # seat_limit total behind seats_available are drawn from the same
    # population of licenses -- otherwise a seat held on a suspended/expired
    # license would count against usage without counting toward the total.
    seats_used = session.execute(
        select(func.count())
        .select_from(LicenseSeatAssignment)
        .join(
            OrganizationLicense,
            LicenseSeatAssignment.organization_license_id == OrganizationLicense.id,
        )
        .where(
            LicenseSeatAssignment.status == SeatAssignmentStatus.ACTIVE,
            OrganizationLicense.status == OrganizationLicenseStatus.ACTIVE,
        )
    ).scalar_one()

    seats_available = (
        session.execute(
            select(func.coalesce(func.sum(OrganizationLicense.seat_limit), 0)).where(
                OrganizationLicense.status == OrganizationLicenseStatus.ACTIVE
            )
        ).scalar_one()
        - seats_used
    )

    active_devices = session.execute(
        select(func.count()).where(DeviceActivation.status == DeviceActivationStatus.ACTIVE)
    ).scalar_one()

    horizon = datetime.now(UTC) + timedelta(days=expiring_within_days)
    expiring_licenses = list(
        session.execute(
            select(OrganizationLicense)
            .where(
                OrganizationLicense.status == OrganizationLicenseStatus.ACTIVE,
                OrganizationLicense.expires_at <= horizon,
            )
            .order_by(OrganizationLicense.expires_at)
        ).scalars()
    )

    return DashboardSummary(
        active_organizations=active_organizations,
        active_licenses=active_licenses,
        seats_used=seats_used,
        seats_available=max(0, seats_available),
        active_devices=active_devices,
        expiring_licenses=expiring_licenses,
    )
