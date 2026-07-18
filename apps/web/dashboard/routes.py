from __future__ import annotations

from flask import Blueprint, render_template

from apps.web.auth.session import load_current_user, login_required, vendor_required
from licensing.database import get_scoped_session
from licensing.services import dashboard as dashboard_service

bp = Blueprint("dashboard", __name__)


@bp.route("/dashboard", methods=["GET"])
@login_required
@vendor_required()
def index():
    db = get_scoped_session()
    user = load_current_user()
    summary = dashboard_service.get_summary(db, actor=user)
    return render_template("dashboard/index.html", summary=summary)
