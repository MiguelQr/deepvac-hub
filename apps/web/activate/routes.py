"""Browser-side half of desktop device-code activation (section 4 of the
spec / docs/sequences.md): the user signs in here and confirms which
organization's license the requesting device should activate against.
"""

from __future__ import annotations

import uuid

from flask import Blueprint, render_template, request

from apps.web.auth.session import load_current_user, login_required
from licensing.audit import record_event
from licensing.database import get_scoped_session
from licensing.exceptions import LicensingError
from licensing.services import activation as activation_service

bp = Blueprint("activate", __name__)


def _normalize_code(raw: str) -> str:
    return raw.strip().upper()


@bp.route("/activate", methods=["GET"])
@login_required
def confirm():
    db = get_scoped_session()
    user = load_current_user()
    user_code = _normalize_code(request.args.get("user_code", ""))

    request_row = activation_service.find_by_user_code(db, user_code) if user_code else None
    error = None
    organizations = []
    status = None

    if request_row is None:
        error = "Invalid or missing activation code. Check the code shown in the desktop app."
    else:
        status = activation_service.effective_status(request_row).value
        if status != "pending":
            error = f"This activation request is {status} and can no longer be approved."
        else:
            organizations = activation_service.list_eligible_organizations(
                db, user=user, product_code=request_row.requested_product_code
            )
            if not organizations:
                error = (
                    "None of your organizations have an active license for "
                    f"{request_row.requested_product_code!r}."
                )

    return render_template(
        "activate/confirm.html",
        user=user,
        user_code=user_code,
        activation=request_row,
        organizations=organizations,
        error=error,
        status=status,
        approved=False,
    )


@bp.route("/activate", methods=["POST"])
@login_required
def approve():
    db = get_scoped_session()
    user = load_current_user()
    user_code = _normalize_code(request.form.get("user_code", ""))
    organization_id_raw = request.form.get("organization_id", "")

    request_row = activation_service.find_by_user_code(db, user_code) if user_code else None
    error = None
    approved = False

    if request_row is None:
        error = "Invalid activation code."
    else:
        try:
            activation_service.approve_activation(
                db,
                activation_id=request_row.id,
                approving_user=user,
                organization_id=uuid.UUID(organization_id_raw),
            )
            record_event(
                db,
                event_type="activation_approved",
                actor_user_id=user.id,
                organization_id=uuid.UUID(organization_id_raw),
                target_type="activation_request",
                target_id=str(request_row.id),
                request_id=request.headers.get("X-Request-ID"),
                source_ip=request.remote_addr,
                user_agent=request.headers.get("User-Agent"),
            )
            db.commit()
            approved = True
        except LicensingError as exc:
            db.rollback()
            error = str(exc)
        except ValueError:
            db.rollback()
            error = "Choose an organization."

    return render_template(
        "activate/confirm.html",
        user=user,
        user_code=user_code,
        activation=request_row,
        organizations=[],
        error=error,
        status=None,
        approved=approved,
    )
