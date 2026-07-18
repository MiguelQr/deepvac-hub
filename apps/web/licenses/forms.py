from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import DateTimeLocalField, IntegerField, SelectField
from wtforms.validators import DataRequired, NumberRange


class LicenseForm(FlaskForm):
    product_edition = SelectField("Product / edition", validators=[DataRequired()])
    device_limit_per_user = IntegerField(
        "Device limit per user", default=3, validators=[DataRequired(), NumberRange(min=1)]
    )
    starts_at = DateTimeLocalField(
        "Starts at", format="%Y-%m-%dT%H:%M", validators=[DataRequired()]
    )
    expires_at = DateTimeLocalField(
        "Expires at", format="%Y-%m-%dT%H:%M", validators=[DataRequired()]
    )
    offline_validity_days = IntegerField(
        "Certificate validity (days)",
        default=36500,
        validators=[DataRequired(), NumberRange(min=1)],
    )
