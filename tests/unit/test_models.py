from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from licensing.models.devices import DeviceActivation
from licensing.models.enums import (
    DeviceActivationStatus,
    MembershipRole,
    MembershipStatus,
    OrganizationLicenseStatus,
    OrganizationStatus,
    SeatAssignmentStatus,
    UserStatus,
)
from licensing.models.licenses import LicenseSeatAssignment, OrganizationLicense
from licensing.models.organizations import Organization, OrganizationMembership
from licensing.models.products import Edition, Product
from licensing.models.users import User


def _make_user(session, email: str) -> User:  # type: ignore[no-untyped-def]
    user = User(
        email=email,
        normalized_email=email.lower(),
        password_hash="argon2id$dummy",
        display_name="Test User",
        status=UserStatus.ACTIVE,
    )
    session.add(user)
    session.flush()
    return user


def _make_org(session, slug: str) -> Organization:  # type: ignore[no-untyped-def]
    org = Organization(name=slug, slug=slug, status=OrganizationStatus.ACTIVE)
    session.add(org)
    session.flush()
    return org


def _make_license(  # type: ignore[no-untyped-def]
    session, org: Organization, product: Product, edition: Edition
) -> OrganizationLicense:
    now = datetime.now(UTC)
    lic = OrganizationLicense(
        organization_id=org.id,
        product_id=product.id,
        edition_id=edition.id,
        status=OrganizationLicenseStatus.ACTIVE,
        seat_limit=1,
        device_limit_per_user=3,
        starts_at=now,
        expires_at=now + timedelta(days=365),
        offline_validity_days=14,
    )
    session.add(lic)
    session.flush()
    return lic


def _make_catalog(session):  # type: ignore[no-untyped-def]
    product = Product(code=f"prod-{uuid.uuid4()}", name="Test Product")
    session.add(product)
    session.flush()
    edition = Edition(product_id=product.id, code="professional", name="Professional")
    session.add(edition)
    session.flush()
    return product, edition


def test_normalized_email_uniqueness(db_session) -> None:  # type: ignore[no-untyped-def]
    _make_user(db_session, "dup@example.com")
    db_session.flush()
    with pytest.raises(IntegrityError):
        _make_user(db_session, "dup@example.com")


def test_duplicate_active_membership_rejected(db_session) -> None:  # type: ignore[no-untyped-def]
    user = _make_user(db_session, f"{uuid.uuid4()}@example.com")
    org = _make_org(db_session, f"org-{uuid.uuid4()}")
    now = datetime.now(UTC)
    db_session.add(
        OrganizationMembership(
            organization_id=org.id,
            user_id=user.id,
            role=MembershipRole.ORGANIZATION_MEMBER,
            status=MembershipStatus.ACTIVE,
            joined_at=now,
        )
    )
    db_session.flush()
    with pytest.raises(IntegrityError):
        db_session.add(
            OrganizationMembership(
                organization_id=org.id,
                user_id=user.id,
                role=MembershipRole.ORGANIZATION_ADMIN,
                status=MembershipStatus.ACTIVE,
                joined_at=now,
            )
        )
        db_session.flush()


def test_removed_membership_does_not_block_new_active_one(db_session) -> None:  # type: ignore[no-untyped-def]
    user = _make_user(db_session, f"{uuid.uuid4()}@example.com")
    org = _make_org(db_session, f"org-{uuid.uuid4()}")
    now = datetime.now(UTC)
    db_session.add(
        OrganizationMembership(
            organization_id=org.id,
            user_id=user.id,
            role=MembershipRole.ORGANIZATION_MEMBER,
            status=MembershipStatus.REMOVED,
            joined_at=now,
            removed_at=now,
        )
    )
    db_session.flush()
    db_session.add(
        OrganizationMembership(
            organization_id=org.id,
            user_id=user.id,
            role=MembershipRole.ORGANIZATION_MEMBER,
            status=MembershipStatus.ACTIVE,
            joined_at=now,
        )
    )
    db_session.flush()  # should not raise


def test_duplicate_active_seat_assignment_rejected(db_session) -> None:  # type: ignore[no-untyped-def]
    user = _make_user(db_session, f"{uuid.uuid4()}@example.com")
    org = _make_org(db_session, f"org-{uuid.uuid4()}")
    product, edition = _make_catalog(db_session)
    lic = _make_license(db_session, org, product, edition)

    db_session.add(
        LicenseSeatAssignment(
            organization_license_id=lic.id,
            user_id=user.id,
            status=SeatAssignmentStatus.ACTIVE,
            assigned_by_user_id=user.id,
        )
    )
    db_session.flush()
    with pytest.raises(IntegrityError):
        db_session.add(
            LicenseSeatAssignment(
                organization_license_id=lic.id,
                user_id=user.id,
                status=SeatAssignmentStatus.ACTIVE,
                assigned_by_user_id=user.id,
            )
        )
        db_session.flush()


def test_duplicate_device_public_key_hash_rejected(db_session) -> None:  # type: ignore[no-untyped-def]
    user = _make_user(db_session, f"{uuid.uuid4()}@example.com")
    org = _make_org(db_session, f"org-{uuid.uuid4()}")
    product, edition = _make_catalog(db_session)
    lic = _make_license(db_session, org, product, edition)

    shared_hash = f"hash-{uuid.uuid4()}"
    db_session.add(
        DeviceActivation(
            organization_license_id=lic.id,
            user_id=user.id,
            device_public_key=b"key-bytes-1",
            device_public_key_hash=shared_hash,
            status=DeviceActivationStatus.ACTIVE,
        )
    )
    db_session.flush()
    with pytest.raises(IntegrityError):
        db_session.add(
            DeviceActivation(
                organization_license_id=lic.id,
                user_id=user.id,
                device_public_key=b"key-bytes-2",
                device_public_key_hash=shared_hash,
                status=DeviceActivationStatus.PENDING,
            )
        )
        db_session.flush()


def test_organization_license_seat_limit_check_constraint(db_session) -> None:  # type: ignore[no-untyped-def]
    org = _make_org(db_session, f"org-{uuid.uuid4()}")
    product, edition = _make_catalog(db_session)
    now = datetime.now(UTC)
    with pytest.raises(IntegrityError):
        db_session.add(
            OrganizationLicense(
                organization_id=org.id,
                product_id=product.id,
                edition_id=edition.id,
                status=OrganizationLicenseStatus.ACTIVE,
                seat_limit=-1,
                device_limit_per_user=3,
                starts_at=now,
                expires_at=now + timedelta(days=30),
                offline_validity_days=14,
            )
        )
        db_session.flush()
