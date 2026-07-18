from __future__ import annotations

import pytest
from tests.factories import make_user, make_vendor_super_admin

from licensing.exceptions import ConflictError, InvalidCredentialsError, PermissionDeniedError
from licensing.models.enums import VendorRole
from licensing.services import users as users_service


def test_create_user_requires_vendor_write(db_session) -> None:  # type: ignore[no-untyped-def]
    non_vendor = make_user(db_session)
    with pytest.raises(PermissionDeniedError):
        users_service.create_user(
            db_session,
            actor=non_vendor,
            email="new@example.com",
            display_name="New User",
            password="correct-horse-battery",
        )


def test_create_user_rejects_short_password(db_session) -> None:  # type: ignore[no-untyped-def]
    admin = make_vendor_super_admin(db_session)
    with pytest.raises(ConflictError):
        users_service.create_user(
            db_session,
            actor=admin,
            email="new@example.com",
            display_name="New User",
            password="short",
        )


def test_create_user_rejects_duplicate_email(db_session) -> None:  # type: ignore[no-untyped-def]
    admin = make_vendor_super_admin(db_session)
    make_user(db_session, email="dup@example.com")
    with pytest.raises(ConflictError):
        users_service.create_user(
            db_session,
            actor=admin,
            email="dup@example.com",
            display_name="Dup",
            password="correct-horse-battery",
        )


def test_set_vendor_role_requires_vendor_write(db_session) -> None:  # type: ignore[no-untyped-def]
    support = make_user(db_session, vendor_role=VendorRole.VENDOR_SUPPORT)
    target = make_user(db_session)
    with pytest.raises(PermissionDeniedError):
        users_service.set_vendor_role(
            db_session, actor=support, user_id=target.id, vendor_role=VendorRole.VENDOR_SUPPORT
        )


def test_set_vendor_role_allows_super_admin(db_session) -> None:  # type: ignore[no-untyped-def]
    admin = make_vendor_super_admin(db_session)
    target = make_user(db_session)
    updated = users_service.set_vendor_role(
        db_session, actor=admin, user_id=target.id, vendor_role=VendorRole.VENDOR_SUPPORT
    )
    assert updated.vendor_role == VendorRole.VENDOR_SUPPORT


def test_change_own_password_rejects_wrong_current_password(db_session) -> None:  # type: ignore[no-untyped-def]
    user = make_user(db_session, password="original-password")
    with pytest.raises(InvalidCredentialsError):
        users_service.change_own_password(
            db_session,
            user=user,
            current_password="wrong-password",
            new_password="a-brand-new-password",
        )


def test_change_own_password_succeeds_with_correct_current_password(db_session) -> None:  # type: ignore[no-untyped-def]
    from licensing.security.passwords import verify_password

    user = make_user(db_session, password="original-password")
    users_service.change_own_password(
        db_session,
        user=user,
        current_password="original-password",
        new_password="a-brand-new-password",
    )
    assert verify_password("a-brand-new-password", user.password_hash)


def test_list_users_requires_vendor(db_session) -> None:  # type: ignore[no-untyped-def]
    non_vendor = make_user(db_session)
    with pytest.raises(PermissionDeniedError):
        users_service.list_users(db_session, actor=non_vendor)
