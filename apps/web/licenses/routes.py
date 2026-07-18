from __future__ import annotations

import uuid
from datetime import UTC

from flask import Blueprint, flash, redirect, render_template, url_for
from sqlalchemy import select

from apps.web.audit import log_event
from apps.web.auth.session import load_current_user, login_required, vendor_required
from apps.web.licenses.forms import AssignSeatForm, LicenseForm
from licensing.database import get_scoped_session
from licensing.exceptions import (
    ConflictError,
    LicensingError,
    NotFoundError,
    SeatLimitExceededError,
)
from licensing.models.enums import EditionStatus, ProductStatus
from licensing.models.products import Edition, Product
from licensing.services import auth as auth_service
from licensing.services import licenses as licenses_service

bp = Blueprint("licenses", __name__)


def _flash_form_errors(form) -> None:  # type: ignore[no-untyped-def]
    for field_errors in form.errors.values():
        for error in field_errors:
            flash(error, "error")


def _product_edition_choices(db) -> list[tuple[str, str]]:  # type: ignore[no-untyped-def]
    editions = db.execute(
        select(Edition)
        .join(Product, Edition.product_id == Product.id)
        .where(Edition.status == EditionStatus.ACTIVE, Product.status == ProductStatus.ACTIVE)
        .order_by(Product.code, Edition.code)
    ).scalars()
    return [(f"{e.product_id}:{e.id}", f"{e.product.code} — {e.name}") for e in editions]


@bp.route("/organizations/<uuid:organization_id>/licenses/new", methods=["GET", "POST"])
@login_required
@vendor_required(write=True)
def new(organization_id: uuid.UUID):
    db = get_scoped_session()
    user = load_current_user()
    form = LicenseForm()
    form.product_edition.choices = _product_edition_choices(db)
    if form.validate_on_submit():
        try:
            product_id_raw, edition_id_raw = form.product_edition.data.split(":")
            license_ = licenses_service.create_license(
                db,
                actor=user,
                organization_id=organization_id,
                product_id=uuid.UUID(product_id_raw),
                edition_id=uuid.UUID(edition_id_raw),
                seat_limit=form.seat_limit.data,
                device_limit_per_user=form.device_limit_per_user.data,
                starts_at=form.starts_at.data.replace(tzinfo=UTC),
                expires_at=form.expires_at.data.replace(tzinfo=UTC),
                offline_validity_days=form.offline_validity_days.data,
            )
            log_event(
                db,
                event_type="license_created",
                actor_user_id=user.id,
                organization_id=organization_id,
                target_type="organization_license",
                target_id=str(license_.id),
                metadata={
                    "seat_limit": license_.seat_limit,
                    "device_limit_per_user": license_.device_limit_per_user,
                },
            )
            db.commit()
            flash("License created.", "success")
            return redirect(url_for("licenses.detail", license_id=license_.id))
        except LicensingError as exc:
            db.rollback()
            flash(str(exc), "error")
    return render_template("licenses/form.html", form=form, organization_id=organization_id)


@bp.route("/licenses/<uuid:license_id>", methods=["GET"])
@login_required
def detail(license_id: uuid.UUID):
    db = get_scoped_session()
    user = load_current_user()
    license_ = licenses_service.get_license(db, actor=user, license_id=license_id)
    seats = licenses_service.list_seats_for_license(db, actor=user, license_id=license_id)
    certificates = licenses_service.list_certificates_for_license(
        db, actor=user, license_id=license_id
    )
    can_admin = auth_service.can_org_admin(db, user, license_.organization_id)
    seat_form = AssignSeatForm()
    return render_template(
        "licenses/detail.html",
        license=license_,
        seats=seats,
        certificates=certificates,
        can_admin=can_admin,
        seat_form=seat_form,
    )


@bp.route("/licenses/<uuid:license_id>/seats", methods=["POST"])
@login_required
def assign_seat(license_id: uuid.UUID):
    db = get_scoped_session()
    user = load_current_user()
    form = AssignSeatForm()
    if form.validate_on_submit():
        try:
            seat = licenses_service.assign_seat_to_member(
                db, actor=user, license_id=license_id, user_email=form.email.data.strip()
            )
            log_event(
                db,
                event_type="seat_assigned",
                actor_user_id=user.id,
                target_type="license_seat_assignment",
                target_id=str(seat.id),
            )
            db.commit()
            flash("Seat assigned.", "success")
        except (ConflictError, NotFoundError, SeatLimitExceededError) as exc:
            db.rollback()
            flash(str(exc), "error")
    else:
        _flash_form_errors(form)
    return redirect(url_for("licenses.detail", license_id=license_id))


@bp.route("/licenses/<uuid:license_id>/seats/<uuid:seat_assignment_id>/remove", methods=["POST"])
@login_required
def remove_seat(license_id: uuid.UUID, seat_assignment_id: uuid.UUID):
    db = get_scoped_session()
    user = load_current_user()
    try:
        licenses_service.remove_seat_from_license(
            db, actor=user, license_id=license_id, seat_assignment_id=seat_assignment_id
        )
        log_event(
            db,
            event_type="seat_removed",
            actor_user_id=user.id,
            target_type="license_seat_assignment",
            target_id=str(seat_assignment_id),
        )
        db.commit()
        flash("Seat removed.", "success")
    except (ConflictError, NotFoundError) as exc:
        db.rollback()
        flash(str(exc), "error")
    return redirect(url_for("licenses.detail", license_id=license_id))
