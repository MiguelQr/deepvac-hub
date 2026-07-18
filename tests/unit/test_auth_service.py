from __future__ import annotations

import pytest
from tests.factories import make_membership, make_organization, make_user, make_vendor_super_admin

from licensing.exceptions import PermissionDeniedError
from licensing.models.enums import MembershipRole
from licensing.services import auth as auth_service


def test_require_vendor_rejects_non_vendor(db_session) -> None:  # type: ignore[no-untyped-def]
    user = make_user(db_session)
    with pytest.raises(PermissionDeniedError):
        auth_service.require_vendor(user)


def test_require_vendor_write_rejects_support(db_session) -> None:  # type: ignore[no-untyped-def]
    from licensing.models.enums import VendorRole

    support = make_user(db_session, vendor_role=VendorRole.VENDOR_SUPPORT)
    auth_service.require_vendor(support)  # read is fine
    with pytest.raises(PermissionDeniedError):
        auth_service.require_vendor(support, write=True)


def test_require_vendor_write_allows_super_admin(db_session) -> None:  # type: ignore[no-untyped-def]
    admin = make_vendor_super_admin(db_session)
    auth_service.require_vendor(admin, write=True)  # should not raise


def test_require_org_view_allows_vendor_for_any_org(db_session) -> None:  # type: ignore[no-untyped-def]
    admin = make_vendor_super_admin(db_session)
    org = make_organization(db_session)
    assert auth_service.require_org_view(db_session, admin, org.id) is None


def test_require_org_view_rejects_non_member(db_session) -> None:  # type: ignore[no-untyped-def]
    user = make_user(db_session)
    org = make_organization(db_session)
    with pytest.raises(PermissionDeniedError):
        auth_service.require_org_view(db_session, user, org.id)


def test_require_org_view_allows_active_member(db_session) -> None:  # type: ignore[no-untyped-def]
    user = make_user(db_session)
    org = make_organization(db_session)
    make_membership(
        db_session, organization=org, user=user, role=MembershipRole.ORGANIZATION_MEMBER
    )
    membership = auth_service.require_org_view(db_session, user, org.id)
    assert membership is not None
    assert membership.role == MembershipRole.ORGANIZATION_MEMBER


def test_require_org_admin_rejects_plain_member(db_session) -> None:  # type: ignore[no-untyped-def]
    user = make_user(db_session)
    org = make_organization(db_session)
    make_membership(
        db_session, organization=org, user=user, role=MembershipRole.ORGANIZATION_MEMBER
    )
    with pytest.raises(PermissionDeniedError):
        auth_service.require_org_admin(db_session, user, org.id)


def test_require_org_admin_allows_org_admin(db_session) -> None:  # type: ignore[no-untyped-def]
    user = make_user(db_session)
    org = make_organization(db_session)
    make_membership(db_session, organization=org, user=user, role=MembershipRole.ORGANIZATION_ADMIN)
    auth_service.require_org_admin(db_session, user, org.id)  # should not raise


def test_require_org_admin_rejects_admin_of_a_different_org(db_session) -> None:  # type: ignore[no-untyped-def]
    user = make_user(db_session)
    own_org = make_organization(db_session)
    other_org = make_organization(db_session)
    make_membership(
        db_session, organization=own_org, user=user, role=MembershipRole.ORGANIZATION_ADMIN
    )
    with pytest.raises(PermissionDeniedError):
        auth_service.require_org_admin(db_session, user, other_org.id)


def test_can_org_admin_is_non_raising(db_session) -> None:  # type: ignore[no-untyped-def]
    user = make_user(db_session)
    org = make_organization(db_session)
    assert auth_service.can_org_admin(db_session, user, org.id) is False
    make_membership(db_session, organization=org, user=user, role=MembershipRole.ORGANIZATION_ADMIN)
    assert auth_service.can_org_admin(db_session, user, org.id) is True
