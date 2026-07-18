"""Signed-cookie session auth for the management portal, plus the RBAC
gate decorators used by every blueprint.

Vendor vs organization-scoped authorization itself lives in
src/licensing/services/auth.py (framework-agnostic, unit-tested); the
decorators here just adapt that to Flask views -- pulling the acting user
from the session and raising via the same domain exceptions apps/web/errors.py
already maps to HTTP responses.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import wraps
from typing import Any

from flask import flash, redirect, request, session, url_for

from licensing.config import get_settings
from licensing.database import get_scoped_session
from licensing.models.users import User
from licensing.services import auth as auth_service

_SESSION_KEY = "user_id"
_LAST_SEEN_KEY = "last_seen"


def login_user(user_id: uuid.UUID) -> None:
    session.clear()
    session[_SESSION_KEY] = str(user_id)
    session[_LAST_SEEN_KEY] = datetime.now(UTC).isoformat()
    session.permanent = True


def logout_user() -> None:
    session.clear()


def current_user_id() -> uuid.UUID | None:
    raw = session.get(_SESSION_KEY)
    return uuid.UUID(raw) if raw else None


def load_current_user() -> User | None:
    user_id = current_user_id()
    if user_id is None:
        return None
    return get_scoped_session().get(User, user_id)


def _idle_timeout_expired() -> bool:
    raw = session.get(_LAST_SEEN_KEY)
    if raw is None:
        return False
    last_seen = datetime.fromisoformat(raw)
    timeout = timedelta(minutes=get_settings().session_idle_timeout_minutes)
    return datetime.now(UTC) - last_seen > timeout


def login_required(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if current_user_id() is None:
            return redirect(url_for("auth.login", next=request.full_path))
        if _idle_timeout_expired():
            logout_user()
            flash("Your session expired due to inactivity. Please sign in again.", "error")
            return redirect(url_for("auth.login", next=request.full_path))
        session[_LAST_SEEN_KEY] = datetime.now(UTC).isoformat()
        return view(*args, **kwargs)

    return wrapped


def vendor_required(*, write: bool = False) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Gate a view to vendor staff (any vendor role for read,
    vendor_super_admin for write). Redirects to login if unauthenticated, so
    it's safe to use standalone, but every route in this codebase stacks it
    under @login_required anyway for the idle-timeout check that lives there."""

    def decorator(view: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            user = load_current_user()
            if user is None:
                return redirect(url_for("auth.login", next=request.full_path))
            auth_service.require_vendor(user, write=write)
            return view(*args, **kwargs)

        return wrapped

    return decorator


__all__ = [
    "current_user_id",
    "load_current_user",
    "login_required",
    "login_user",
    "logout_user",
    "vendor_required",
]
