from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from tests.factories import (
    make_license,
    make_membership,
    make_organization,
    make_product_and_edition,
    make_user,
    make_vendor_super_admin,
)

from licensing.exceptions import ConflictError, PermissionDeniedError
from licensing.models.enums import MembershipRole
from licensing.services import licenses as licenses_service


def test_create_license_requires_vendor_write(db_session) -> None:  # type: ignore[no-untyped-def]
    org = make_organization(db_session)
    product, edition = make_product_and_edition(db_session)
    non_vendor = make_user(db_session)
    now = datetime.now(UTC)
    with pytest.raises(PermissionDeniedError):
        licenses_service.create_license(
            db_session,
            actor=non_vendor,
            organization_id=org.id,
            product_id=product.id,
            edition_id=edition.id,
            seat_limit=5,
            device_limit_per_user=3,
            starts_at=now,
            expires_at=now + timedelta(days=365),
            offline_validity_days=14,
        )


def test_create_license_rejects_expiry_before_start(db_session) -> None:  # type: ignore[no-untyped-def]
    admin = make_vendor_super_admin(db_session)
    org = make_organization(db_session)
    product, edition = make_product_and_edition(db_session)
    now = datetime.now(UTC)
    with pytest.raises(ConflictError):
        licenses_service.create_license(
            db_session,
            actor=admin,
            organization_id=org.id,
            product_id=product.id,
            edition_id=edition.id,
            seat_limit=5,
            device_limit_per_user=3,
            starts_at=now,
            expires_at=now - timedelta(days=1),
            offline_validity_days=14,
        )


def test_assign_seat_requires_org_admin(db_session) -> None:  # type: ignore[no-untyped-def]
    org = make_organization(db_session)
    product, edition = make_product_and_edition(db_session)
    license_ = make_license(db_session, organization=org, product=product, edition=edition)
    plain_member = make_user(db_session)
    make_membership(
        db_session, organization=org, user=plain_member, role=MembershipRole.ORGANIZATION_MEMBER
    )
    with pytest.raises(PermissionDeniedError):
        licenses_service.assign_seat_to_member(
            db_session, actor=plain_member, license_id=license_.id, user_email="someone@example.com"
        )


def test_assign_seat_requires_target_to_be_org_member(db_session) -> None:  # type: ignore[no-untyped-def]
    org = make_organization(db_session)
    product, edition = make_product_and_edition(db_session)
    license_ = make_license(db_session, organization=org, product=product, edition=edition)
    admin = make_vendor_super_admin(db_session)
    make_user(db_session, email="outsider@example.com")
    with pytest.raises(ConflictError):
        licenses_service.assign_seat_to_member(
            db_session, actor=admin, license_id=license_.id, user_email="outsider@example.com"
        )


def test_assign_seat_succeeds_for_org_member(db_session) -> None:  # type: ignore[no-untyped-def]
    org = make_organization(db_session)
    product, edition = make_product_and_edition(db_session)
    license_ = make_license(
        db_session, organization=org, product=product, edition=edition, seat_limit=1
    )
    admin = make_vendor_super_admin(db_session)
    member = make_user(db_session, email="member@example.com")
    make_membership(
        db_session, organization=org, user=member, role=MembershipRole.ORGANIZATION_MEMBER
    )
    seat = licenses_service.assign_seat_to_member(
        db_session, actor=admin, license_id=license_.id, user_email="member@example.com"
    )
    assert seat.user_id == member.id
