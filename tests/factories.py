"""Shared test object builders for Phase B/C tests.

tests/unit/test_models.py has its own older, file-local `_make_*` helpers
predating this module -- left alone since they're only used there. New
tests should use these instead of duplicating similar helpers per file.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from licensing.models.enums import (
    MembershipRole,
    MembershipStatus,
    OrganizationLicenseStatus,
    OrganizationStatus,
    UserStatus,
    VendorRole,
)
from licensing.models.licenses import OrganizationLicense
from licensing.models.organizations import Organization, OrganizationMembership
from licensing.models.products import Edition, Product
from licensing.models.users import User
from licensing.security.passwords import hash_password


def make_user(
    session: Session,
    *,
    email: str | None = None,
    display_name: str = "Test User",
    password: str = "correct-horse-battery",
    status: UserStatus = UserStatus.ACTIVE,
    vendor_role: VendorRole | None = None,
) -> User:
    email = email or f"{uuid.uuid4()}@example.com"
    user = User(
        email=email,
        normalized_email=email.lower(),
        password_hash=hash_password(password),
        display_name=display_name,
        status=status,
        vendor_role=vendor_role,
    )
    session.add(user)
    session.flush()
    return user


def make_vendor_super_admin(session: Session, **kwargs: object) -> User:
    kwargs.setdefault("vendor_role", VendorRole.VENDOR_SUPER_ADMIN)
    return make_user(session, **kwargs)  # type: ignore[arg-type]


def make_vendor_support(session: Session, **kwargs: object) -> User:
    kwargs.setdefault("vendor_role", VendorRole.VENDOR_SUPPORT)
    return make_user(session, **kwargs)  # type: ignore[arg-type]


def make_organization(
    session: Session,
    *,
    name: str | None = None,
    status: OrganizationStatus = OrganizationStatus.ACTIVE,
) -> Organization:
    name = name or f"org-{uuid.uuid4()}"
    org = Organization(name=name, slug=name, status=status)
    session.add(org)
    session.flush()
    return org


def make_membership(
    session: Session,
    *,
    organization: Organization,
    user: User,
    role: MembershipRole = MembershipRole.ORGANIZATION_MEMBER,
    status: MembershipStatus = MembershipStatus.ACTIVE,
) -> OrganizationMembership:
    membership = OrganizationMembership(
        organization_id=organization.id,
        user_id=user.id,
        role=role,
        status=status,
        joined_at=datetime.now(UTC),
    )
    session.add(membership)
    session.flush()
    return membership


def make_product_and_edition(
    session: Session, *, product_code: str | None = None, edition_code: str = "professional"
) -> tuple[Product, Edition]:
    product = Product(code=product_code or f"prod-{uuid.uuid4()}", name="Test Product")
    session.add(product)
    session.flush()
    edition = Edition(product_id=product.id, code=edition_code, name=edition_code.title())
    session.add(edition)
    session.flush()
    return product, edition


def make_license(
    session: Session,
    *,
    organization: Organization,
    product: Product,
    edition: Edition,
    device_limit_per_user: int = 3,
    status: OrganizationLicenseStatus = OrganizationLicenseStatus.ACTIVE,
    expires_in_days: int = 365,
) -> OrganizationLicense:
    now = datetime.now(UTC)
    license_ = OrganizationLicense(
        organization_id=organization.id,
        product_id=product.id,
        edition_id=edition.id,
        status=status,
        device_limit_per_user=device_limit_per_user,
        starts_at=now,
        expires_at=now + timedelta(days=expires_in_days),
        offline_validity_days=14,
    )
    session.add(license_)
    session.flush()
    return license_
