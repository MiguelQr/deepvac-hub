"""Explicit test for docs/threat-model.md threat #9: every management-portal
query must be scoped by the acting user's organization memberships and
role. organization_admin/organization_member of one org must not be able
to query or act on another organization's data, and a plain member must
not be able to perform admin-only actions even within their own org.
"""

from __future__ import annotations

from datetime import UTC, datetime

from tests.factories import (
    make_license,
    make_membership,
    make_organization,
    make_product_and_edition,
    make_user,
)

from licensing.models.enums import MembershipRole
from licensing.models.users import User


def _login_as(client, user: User) -> None:  # type: ignore[no-untyped-def]
    with client.session_transaction() as session:
        session["user_id"] = str(user.id)
        session["last_seen"] = datetime.now(UTC).isoformat()


def test_org_admin_cannot_view_a_different_organization(flask_client, db_session) -> None:  # type: ignore[no-untyped-def]
    org_a = make_organization(db_session)
    org_b = make_organization(db_session)
    admin_a = make_user(db_session)
    make_membership(
        db_session, organization=org_a, user=admin_a, role=MembershipRole.ORGANIZATION_ADMIN
    )
    _login_as(flask_client, admin_a)

    response = flask_client.get(f"/organizations/{org_b.id}")
    assert response.status_code in (403, 404)


def test_org_admin_cannot_manage_membership_of_a_different_org(flask_client, db_session) -> None:  # type: ignore[no-untyped-def]
    org_a = make_organization(db_session)
    org_b = make_organization(db_session)
    admin_a = make_user(db_session)
    make_membership(
        db_session, organization=org_a, user=admin_a, role=MembershipRole.ORGANIZATION_ADMIN
    )
    make_user(db_session, email="outsider@example.com")
    _login_as(flask_client, admin_a)

    response = flask_client.post(
        f"/organizations/{org_b.id}/memberships",
        data={"email": "outsider@example.com", "role": "organization_member"},
        follow_redirects=True,
    )
    assert response.status_code in (403, 404)


def test_org_admin_cannot_view_a_different_orgs_license(flask_client, db_session) -> None:  # type: ignore[no-untyped-def]
    org_a = make_organization(db_session)
    org_b = make_organization(db_session)
    product, edition = make_product_and_edition(db_session)
    license_b = make_license(db_session, organization=org_b, product=product, edition=edition)
    admin_a = make_user(db_session)
    make_membership(
        db_session, organization=org_a, user=admin_a, role=MembershipRole.ORGANIZATION_ADMIN
    )
    _login_as(flask_client, admin_a)

    response = flask_client.get(f"/licenses/{license_b.id}")
    assert response.status_code in (403, 404)


def test_plain_member_cannot_disable_own_organization(flask_client, db_session) -> None:  # type: ignore[no-untyped-def]
    org = make_organization(db_session)
    member = make_user(db_session)
    make_membership(
        db_session, organization=org, user=member, role=MembershipRole.ORGANIZATION_MEMBER
    )
    _login_as(flask_client, member)

    response = flask_client.post(f"/organizations/{org.id}/disable", follow_redirects=True)
    assert response.status_code == 403


def test_plain_member_cannot_remove_a_membership_in_own_org(flask_client, db_session) -> None:  # type: ignore[no-untyped-def]
    org = make_organization(db_session)
    member = make_user(db_session)
    membership = make_membership(
        db_session, organization=org, user=member, role=MembershipRole.ORGANIZATION_MEMBER
    )
    _login_as(flask_client, member)

    response = flask_client.post(
        f"/organizations/{org.id}/memberships/{membership.id}/remove", follow_redirects=True
    )
    assert response.status_code == 403
