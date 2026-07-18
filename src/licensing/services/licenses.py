"""Organization license creation, plus the license-scoped certificate view
used by the licenses/organizations blueprints.

Licenses in this product are lifetime grants: there is no suspend/revoke/
renew lifecycle (deliberately dropped -- see README.md's Phase D notes),
and no per-user seat limit -- every active member of the organization is
entitled to the licensed product/edition (see services/activation.py and
README.md's Phase D notes for the "no seats" decision). Once created, a
license's only state is what's set at creation time; the issued device
certificates (services/issuance.py) carry their own long validity window
independent of this record.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from licensing.exceptions import ConflictError, NotFoundError
from licensing.models.certificates import IssuedLicenseCertificate
from licensing.models.devices import DeviceActivation
from licensing.models.enums import OrganizationLicenseStatus
from licensing.models.licenses import OrganizationLicense
from licensing.models.users import User
from licensing.services import auth as auth_service


def create_license(
    session: Session,
    *,
    actor: User,
    organization_id: uuid.UUID,
    product_id: uuid.UUID,
    edition_id: uuid.UUID,
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
