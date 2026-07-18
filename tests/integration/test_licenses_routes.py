from __future__ import annotations

from datetime import UTC, datetime

from tests.factories import make_organization, make_product_and_edition, make_vendor_super_admin

from licensing.models.licenses import OrganizationLicense
from licensing.models.users import User


def _login_as(client, user: User) -> None:  # type: ignore[no-untyped-def]
    with client.session_transaction() as session:
        session["user_id"] = str(user.id)
        session["last_seen"] = datetime.now(UTC).isoformat()


def test_vendor_can_create_license(flask_client, db_session) -> None:  # type: ignore[no-untyped-def]
    admin = make_vendor_super_admin(db_session)
    org = make_organization(db_session)
    product, edition = make_product_and_edition(db_session)
    _login_as(flask_client, admin)

    response = flask_client.post(
        f"/organizations/{org.id}/licenses/new",
        data={
            "product_edition": f"{product.id}:{edition.id}",
            "device_limit_per_user": "3",
            "starts_at": "2026-01-01T00:00",
            "expires_at": "2027-01-01T00:00",
            "offline_validity_days": "14",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    license_ = (
        db_session.query(OrganizationLicense)
        .filter(OrganizationLicense.organization_id == org.id)
        .one()
    )
    assert license_.device_limit_per_user == 3
