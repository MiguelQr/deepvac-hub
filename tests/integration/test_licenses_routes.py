from __future__ import annotations

from datetime import UTC, datetime

from tests.factories import (
    make_license,
    make_membership,
    make_organization,
    make_product_and_edition,
    make_user,
    make_vendor_super_admin,
)

from licensing.models.enums import (
    MembershipRole,
    OrganizationLicenseStatus,
    SeatAssignmentStatus,
)
from licensing.models.licenses import LicenseSeatAssignment, OrganizationLicense
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
            "seat_limit": "10",
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
    assert license_.seat_limit == 10


def test_vendor_can_suspend_and_reactivate_license(flask_client, db_session) -> None:  # type: ignore[no-untyped-def]
    admin = make_vendor_super_admin(db_session)
    org = make_organization(db_session)
    product, edition = make_product_and_edition(db_session)
    license_ = make_license(db_session, organization=org, product=product, edition=edition)
    _login_as(flask_client, admin)

    response = flask_client.post(f"/licenses/{license_.id}/suspend", follow_redirects=False)
    assert response.status_code == 302
    db_session.refresh(license_)
    assert license_.status == OrganizationLicenseStatus.SUSPENDED

    response = flask_client.post(f"/licenses/{license_.id}/reactivate", follow_redirects=False)
    assert response.status_code == 302
    db_session.refresh(license_)
    assert license_.status == OrganizationLicenseStatus.ACTIVE


def test_org_admin_can_assign_and_remove_seat(flask_client, db_session) -> None:  # type: ignore[no-untyped-def]
    org = make_organization(db_session)
    product, edition = make_product_and_edition(db_session)
    license_ = make_license(
        db_session, organization=org, product=product, edition=edition, seat_limit=2
    )
    org_admin = make_user(db_session)
    make_membership(
        db_session, organization=org, user=org_admin, role=MembershipRole.ORGANIZATION_ADMIN
    )
    teammate = make_user(db_session, email="teammate@example.com")
    make_membership(
        db_session, organization=org, user=teammate, role=MembershipRole.ORGANIZATION_MEMBER
    )
    _login_as(flask_client, org_admin)

    response = flask_client.post(
        f"/licenses/{license_.id}/seats",
        data={"email": "teammate@example.com"},
        follow_redirects=False,
    )
    assert response.status_code == 302

    seat = (
        db_session.query(LicenseSeatAssignment)
        .filter(
            LicenseSeatAssignment.organization_license_id == license_.id,
            LicenseSeatAssignment.user_id == teammate.id,
        )
        .one()
    )
    assert seat.status == SeatAssignmentStatus.ACTIVE

    response = flask_client.post(
        f"/licenses/{license_.id}/seats/{seat.id}/remove", follow_redirects=False
    )
    assert response.status_code == 302
    db_session.refresh(seat)
    assert seat.status == SeatAssignmentStatus.REMOVED


def test_plain_member_cannot_assign_seat(flask_client, db_session) -> None:  # type: ignore[no-untyped-def]
    org = make_organization(db_session)
    product, edition = make_product_and_edition(db_session)
    license_ = make_license(db_session, organization=org, product=product, edition=edition)
    member = make_user(db_session)
    make_membership(
        db_session, organization=org, user=member, role=MembershipRole.ORGANIZATION_MEMBER
    )
    _login_as(flask_client, member)

    response = flask_client.post(
        f"/licenses/{license_.id}/seats",
        data={"email": member.email},
        follow_redirects=True,
    )
    assert response.status_code == 403
