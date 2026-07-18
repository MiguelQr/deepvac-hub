from __future__ import annotations

from datetime import UTC, datetime

from tests.factories import make_membership, make_organization, make_user, make_vendor_super_admin

from licensing.models.enums import MembershipRole, MembershipStatus
from licensing.models.organizations import Organization, OrganizationMembership
from licensing.models.users import User


def _login_as(client, user: User) -> None:  # type: ignore[no-untyped-def]
    with client.session_transaction() as session:
        session["user_id"] = str(user.id)
        session["last_seen"] = datetime.now(UTC).isoformat()


def test_non_vendor_cannot_list_organizations(flask_client, db_session) -> None:  # type: ignore[no-untyped-def]
    user = make_user(db_session)
    _login_as(flask_client, user)
    response = flask_client.get("/organizations")
    assert response.status_code == 403


def test_vendor_can_create_organization(flask_client, db_session) -> None:  # type: ignore[no-untyped-def]
    admin = make_vendor_super_admin(db_session)
    _login_as(flask_client, admin)

    response = flask_client.post(
        "/organizations/new",
        data={"name": "Acme Corp", "slug": "acme-corp"},
        follow_redirects=False,
    )
    assert response.status_code == 302

    org = db_session.query(Organization).filter(Organization.slug == "acme-corp").one()
    assert org.name == "Acme Corp"


def test_org_admin_can_view_own_organization(flask_client, db_session) -> None:  # type: ignore[no-untyped-def]
    org = make_organization(db_session)
    admin_user = make_user(db_session)
    make_membership(
        db_session, organization=org, user=admin_user, role=MembershipRole.ORGANIZATION_ADMIN
    )
    _login_as(flask_client, admin_user)

    response = flask_client.get(f"/organizations/{org.id}")
    assert response.status_code == 200
    assert org.name.encode() in response.data


def test_org_admin_can_add_and_remove_membership(flask_client, db_session) -> None:  # type: ignore[no-untyped-def]
    org = make_organization(db_session)
    admin_user = make_user(db_session)
    make_membership(
        db_session, organization=org, user=admin_user, role=MembershipRole.ORGANIZATION_ADMIN
    )
    teammate = make_user(db_session, email="teammate@example.com")
    _login_as(flask_client, admin_user)

    response = flask_client.post(
        f"/organizations/{org.id}/memberships",
        data={"email": "teammate@example.com", "role": "organization_member"},
        follow_redirects=False,
    )
    assert response.status_code == 302

    membership = (
        db_session.query(OrganizationMembership)
        .filter(
            OrganizationMembership.organization_id == org.id,
            OrganizationMembership.user_id == teammate.id,
        )
        .one()
    )
    assert membership.status == MembershipStatus.ACTIVE

    response = flask_client.post(
        f"/organizations/{org.id}/memberships/{membership.id}/remove", follow_redirects=False
    )
    assert response.status_code == 302
    db_session.refresh(membership)
    assert membership.status == MembershipStatus.REMOVED


def test_plain_member_cannot_add_membership(flask_client, db_session) -> None:  # type: ignore[no-untyped-def]
    org = make_organization(db_session)
    member_user = make_user(db_session)
    make_membership(
        db_session, organization=org, user=member_user, role=MembershipRole.ORGANIZATION_MEMBER
    )
    make_user(db_session, email="other@example.com")
    _login_as(flask_client, member_user)

    response = flask_client.post(
        f"/organizations/{org.id}/memberships",
        data={"email": "other@example.com", "role": "organization_member"},
        follow_redirects=True,
    )
    assert response.status_code == 403
