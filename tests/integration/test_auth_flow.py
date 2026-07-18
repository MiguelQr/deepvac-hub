from __future__ import annotations

from datetime import UTC, datetime, timedelta

from tests.factories import make_user

from licensing.security.passwords import verify_password


def test_login_success_redirects_and_sets_session(flask_client, db_session) -> None:  # type: ignore[no-untyped-def]
    make_user(db_session, email="login@example.com", password="correct-horse-battery")

    response = flask_client.post(
        "/login",
        data={"email": "login@example.com", "password": "correct-horse-battery"},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with flask_client.session_transaction() as session:
        assert session.get("user_id") is not None


def test_login_wrong_password_shows_generic_error(flask_client, db_session) -> None:  # type: ignore[no-untyped-def]
    make_user(db_session, email="login2@example.com", password="correct-horse-battery")

    response = flask_client.post(
        "/login",
        data={"email": "login2@example.com", "password": "wrong-password"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert b"Incorrect email or password" in response.data


def test_logout_clears_session(flask_client, db_session) -> None:  # type: ignore[no-untyped-def]
    user = make_user(db_session, email="logout@example.com", password="correct-horse-battery")
    with flask_client.session_transaction() as session:
        session["user_id"] = str(user.id)
        session["last_seen"] = datetime.now(UTC).isoformat()

    response = flask_client.post("/logout", follow_redirects=False)
    assert response.status_code == 302
    with flask_client.session_transaction() as session:
        assert session.get("user_id") is None


def test_idle_session_is_logged_out(flask_client, db_session) -> None:  # type: ignore[no-untyped-def]
    user = make_user(db_session, email="idle@example.com", password="correct-horse-battery")
    with flask_client.session_transaction() as session:
        session["user_id"] = str(user.id)
        session["last_seen"] = (datetime.now(UTC) - timedelta(hours=2)).isoformat()

    response = flask_client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    with flask_client.session_transaction() as session:
        assert session.get("user_id") is None


def test_account_password_change_updates_hash(flask_client, db_session) -> None:  # type: ignore[no-untyped-def]
    user = make_user(db_session, email="pwchange@example.com", password="original-password")
    with flask_client.session_transaction() as session:
        session["user_id"] = str(user.id)
        session["last_seen"] = datetime.now(UTC).isoformat()

    response = flask_client.post(
        "/account/password",
        data={
            "current_password": "original-password",
            "new_password": "a-brand-new-password",
            "confirm_password": "a-brand-new-password",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    db_session.refresh(user)
    assert verify_password("a-brand-new-password", user.password_hash)


def test_account_password_change_rejects_wrong_current(flask_client, db_session) -> None:  # type: ignore[no-untyped-def]
    user = make_user(db_session, email="pwchange2@example.com", password="original-password")
    with flask_client.session_transaction() as session:
        session["user_id"] = str(user.id)
        session["last_seen"] = datetime.now(UTC).isoformat()

    response = flask_client.post(
        "/account/password",
        data={
            "current_password": "totally-wrong",
            "new_password": "a-brand-new-password",
            "confirm_password": "a-brand-new-password",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Current password is incorrect" in response.data
