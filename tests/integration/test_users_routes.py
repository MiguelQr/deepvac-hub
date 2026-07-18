from __future__ import annotations

from datetime import UTC, datetime

from tests.factories import make_user, make_vendor_super_admin, make_vendor_support

from licensing.models.enums import UserStatus, VendorRole
from licensing.models.users import User
from licensing.security.passwords import verify_password


def _login_as(client, user: User) -> None:  # type: ignore[no-untyped-def]
    with client.session_transaction() as session:
        session["user_id"] = str(user.id)
        session["last_seen"] = datetime.now(UTC).isoformat()


def test_non_vendor_cannot_list_users(flask_client, db_session) -> None:  # type: ignore[no-untyped-def]
    user = make_user(db_session)
    _login_as(flask_client, user)
    response = flask_client.get("/users")
    assert response.status_code == 403


def test_vendor_can_create_user(flask_client, db_session) -> None:  # type: ignore[no-untyped-def]
    admin = make_vendor_super_admin(db_session)
    _login_as(flask_client, admin)

    response = flask_client.post(
        "/users/new",
        data={
            "email": "created@example.com",
            "display_name": "Created User",
            "password": "correct-horse-battery",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    created = db_session.query(User).filter(User.normalized_email == "created@example.com").one()
    assert created.display_name == "Created User"
    assert created.status == UserStatus.ACTIVE


def test_vendor_support_cannot_create_user(flask_client, db_session) -> None:  # type: ignore[no-untyped-def]
    support = make_vendor_support(db_session)
    _login_as(flask_client, support)

    response = flask_client.post(
        "/users/new",
        data={
            "email": "blocked@example.com",
            "display_name": "Blocked",
            "password": "correct-horse-battery",
        },
        follow_redirects=False,
    )
    assert response.status_code == 403
    blocked_count = (
        db_session.query(User).filter(User.normalized_email == "blocked@example.com").count()
    )
    assert blocked_count == 0


def test_vendor_can_disable_and_reactivate_user(flask_client, db_session) -> None:  # type: ignore[no-untyped-def]
    admin = make_vendor_super_admin(db_session)
    target = make_user(db_session)
    _login_as(flask_client, admin)

    response = flask_client.post(f"/users/{target.id}/disable", follow_redirects=False)
    assert response.status_code == 302
    db_session.refresh(target)
    assert target.status == UserStatus.DISABLED

    response = flask_client.post(f"/users/{target.id}/reactivate", follow_redirects=False)
    assert response.status_code == 302
    db_session.refresh(target)
    assert target.status == UserStatus.ACTIVE


def test_vendor_can_set_user_password(flask_client, db_session) -> None:  # type: ignore[no-untyped-def]
    admin = make_vendor_super_admin(db_session)
    target = make_user(db_session, password="old-password")
    _login_as(flask_client, admin)

    response = flask_client.post(
        f"/users/{target.id}/password",
        data={"new_password": "a-brand-new-password"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    db_session.refresh(target)
    assert verify_password("a-brand-new-password", target.password_hash)


def test_vendor_can_grant_vendor_role(flask_client, db_session) -> None:  # type: ignore[no-untyped-def]
    admin = make_vendor_super_admin(db_session)
    target = make_user(db_session)
    _login_as(flask_client, admin)

    response = flask_client.post(
        f"/users/{target.id}/vendor-role",
        data={"vendor_role": "vendor_support"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    db_session.refresh(target)
    assert target.vendor_role == VendorRole.VENDOR_SUPPORT
