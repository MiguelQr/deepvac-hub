from __future__ import annotations

from flask import Blueprint, redirect, render_template, request, url_for

from apps.web.auth.session import login_required, login_user, logout_user
from licensing.database import get_scoped_session
from licensing.models.enums import UserStatus
from licensing.models.users import User
from licensing.security.passwords import verify_password

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        db = get_scoped_session()
        user = db.query(User).filter(User.normalized_email == email).one_or_none()
        # Deliberately generic message for both "no such user" and "wrong
        # password" -- see docs/threat-model.md, never distinguish the two.
        if user is None or not verify_password(password, user.password_hash):
            error = "Incorrect email or password."
        elif user.status != UserStatus.ACTIVE:
            error = "This account is disabled."
        else:
            login_user(user.id)
            next_url = request.args.get("next") or url_for("activate.confirm")
            return redirect(next_url)
    return render_template("auth/login.html", error=error)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
