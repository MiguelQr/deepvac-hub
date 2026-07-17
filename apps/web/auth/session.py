"""Minimal signed-cookie session auth for the management portal.

Full RBAC (vendor_super_admin vs vendor_support vs organization_admin vs
organization_member enforcement per screen) lands in Phase B/C -- this is
just enough identity to gate the activation-approval page added for the
desktop licensing verification loop.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import redirect, request, session, url_for

from licensing.database import get_scoped_session
from licensing.models.users import User

_SESSION_KEY = "user_id"


def login_user(user_id: uuid.UUID) -> None:
    session.clear()
    session[_SESSION_KEY] = str(user_id)
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


def login_required(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if current_user_id() is None:
            return redirect(url_for("auth.login", next=request.full_path))
        return view(*args, **kwargs)

    return wrapped
