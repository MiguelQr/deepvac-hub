from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from tests.factories import (
    make_organization,
    make_product_and_edition,
    make_user,
    make_vendor_super_admin,
)

from licensing.exceptions import ConflictError, PermissionDeniedError
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
            device_limit_per_user=3,
            starts_at=now,
            expires_at=now - timedelta(days=1),
            offline_validity_days=14,
        )


def test_create_license_succeeds_for_vendor_super_admin(db_session) -> None:  # type: ignore[no-untyped-def]
    admin = make_vendor_super_admin(db_session)
    org = make_organization(db_session)
    product, edition = make_product_and_edition(db_session)
    now = datetime.now(UTC)
    license_ = licenses_service.create_license(
        db_session,
        actor=admin,
        organization_id=org.id,
        product_id=product.id,
        edition_id=edition.id,
        device_limit_per_user=3,
        starts_at=now,
        expires_at=now + timedelta(days=365),
        offline_validity_days=14,
    )
    assert license_.organization_id == org.id
