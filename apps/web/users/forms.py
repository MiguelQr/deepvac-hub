from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, Email, Length


class UserForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    display_name = StringField("Display name", validators=[DataRequired(), Length(max=200)])
    password = PasswordField("Initial password", validators=[DataRequired(), Length(min=12)])


class SetPasswordForm(FlaskForm):
    new_password = PasswordField("New password", validators=[DataRequired(), Length(min=12)])
