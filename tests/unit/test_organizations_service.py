from __future__ import annotations

import pytest
from tests.factories import make_membership, make_organization, make_user, make_vendor_super_admin

from licensing.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from licensing.models.enums import MembershipRole, OrganizationStatus
from licensing.services import organizations as organizations_service


def test_create_organization_requires_vendor_write(db_session) -> None:  # type: ignore[no-untyped-def]
    user = make_user(db_session)
    with pytest.raises(PermissionDeniedError):
        organizations_service.create_organization(db_session, actor=user, name="Acme", slug="acme")


def test_create_organization_rejects_duplicate_slug(db_session) -> None:  # type: ignore[no-untyped-def]
    admin = make_vendor_super_admin(db_session)
    organizations_service.create_organization(db_session, actor=admin, name="Acme", slug="acme-x")
    with pytest.raises(ConflictError):
        organizations_service.create_organization(
            db_session, actor=admin, name="Acme 2", slug="acme-x"
        )


def test_create_organization_rejects_invalid_slug(db_session) -> None:  # type: ignore[no-untyped-def]
    admin = make_vendor_super_admin(db_session)
    with pytest.raises(ConflictError):
        organizations_service.create_organization(
            db_session, actor=admin, name="Acme", slug="Not A Slug!"
        )


def test_get_organization_not_found(db_session) -> None:  # type: ignore[no-untyped-def]
    import uuid

    admin = make_vendor_super_admin(db_session)
    with pytest.raises(NotFoundError):
        organizations_service.get_organization(
            db_session, actor=admin, organization_id=uuid.uuid4()
        )


def test_get_organization_rejects_non_member(db_session) -> None:  # type: ignore[no-untyped-def]
    org = make_organization(db_session)
    outsider = make_user(db_session)
    with pytest.raises(PermissionDeniedError):
        organizations_service.get_organization(db_session, actor=outsider, organization_id=org.id)


def test_list_organizations_search_filters_by_name_or_slug(db_session) -> None:  # type: ignore[no-untyped-def]
    admin = make_vendor_super_admin(db_session)
    make_organization(db_session, name="Zebra Labs")
    make_organization(db_session, name="Acme Corp")
    page = organizations_service.list_organizations(db_session, actor=admin, q="zebra")
    assert len(page.items) == 1
    assert page.items[0].name == "Zebra Labs"


def test_add_membership_requires_existing_user(db_session) -> None:  # type: ignore[no-untyped-def]
    admin = make_vendor_super_admin(db_session)
    org = make_organization(db_session)
    with pytest.raises(NotFoundError):
        organizations_service.add_membership(
            db_session,
            actor=admin,
            organization_id=org.id,
            user_email="nobody@example.com",
            role=MembershipRole.ORGANIZATION_MEMBER,
        )


def test_add_membership_rejects_duplicate(db_session) -> None:  # type: ignore[no-untyped-def]
    admin = make_vendor_super_admin(db_session)
    org = make_organization(db_session)
    member = make_user(db_session, email="member@example.com")
    make_membership(db_session, organization=org, user=member)
    with pytest.raises(ConflictError):
        organizations_service.add_membership(
            db_session,
            actor=admin,
            organization_id=org.id,
            user_email="member@example.com",
            role=MembershipRole.ORGANIZATION_MEMBER,
        )


def test_remove_membership_guards_last_admin(db_session) -> None:  # type: ignore[no-untyped-def]
    org = make_organization(db_session)
    admin_user = make_user(db_session)
    membership = make_membership(
        db_session, organization=org, user=admin_user, role=MembershipRole.ORGANIZATION_ADMIN
    )
    with pytest.raises(ConflictError):
        organizations_service.remove_membership(
            db_session, actor=admin_user, organization_id=org.id, membership_id=membership.id
        )


def test_remove_membership_allowed_when_another_admin_remains(db_session) -> None:  # type: ignore[no-untyped-def]
    org = make_organization(db_session)
    admin_a = make_user(db_session)
    admin_b = make_user(db_session)
    make_membership(
        db_session, organization=org, user=admin_a, role=MembershipRole.ORGANIZATION_ADMIN
    )
    membership_b = make_membership(
        db_session, organization=org, user=admin_b, role=MembershipRole.ORGANIZATION_ADMIN
    )
    organizations_service.remove_membership(
        db_session, actor=admin_a, organization_id=org.id, membership_id=membership_b.id
    )  # should not raise


def test_change_membership_role_guards_last_admin(db_session) -> None:  # type: ignore[no-untyped-def]
    org = make_organization(db_session)
    admin_user = make_user(db_session)
    membership = make_membership(
        db_session, organization=org, user=admin_user, role=MembershipRole.ORGANIZATION_ADMIN
    )
    with pytest.raises(ConflictError):
        organizations_service.change_membership_role(
            db_session,
            actor=admin_user,
            organization_id=org.id,
            membership_id=membership.id,
            role=MembershipRole.ORGANIZATION_MEMBER,
        )


def test_set_organization_status_requires_vendor_write(db_session) -> None:  # type: ignore[no-untyped-def]
    org = make_organization(db_session)
    member = make_user(db_session)
    make_membership(
        db_session, organization=org, user=member, role=MembershipRole.ORGANIZATION_ADMIN
    )
    with pytest.raises(PermissionDeniedError):
        organizations_service.set_organization_status(
            db_session, actor=member, organization_id=org.id, status=OrganizationStatus.DISABLED
        )
