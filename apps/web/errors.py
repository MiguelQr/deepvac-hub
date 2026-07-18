"""Centralized handling for domain exceptions raised by src/licensing
services -- covers "you're not allowed here" / "that doesn't exist" so
individual routes don't need their own try/except for authorization.

Form-submission errors (validation, conflicts, seat limits) stay inline per
route instead, using flash() + re-rendering the same form -- see
apps/web/organizations/routes.py for that pattern. Reuses the same
exception -> status mapping apps/api/error_handlers.py uses, so the two
surfaces can't drift out of sync.
"""

from __future__ import annotations

from flask import Flask, render_template

from licensing.exceptions import NotFoundError, PermissionDeniedError, status_for


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(PermissionDeniedError)
    def _handle_permission_denied(exc: PermissionDeniedError) -> tuple[str, int]:
        return render_template("shared/error.html", message=str(exc)), status_for(exc)

    @app.errorhandler(NotFoundError)
    def _handle_not_found(exc: NotFoundError) -> tuple[str, int]:
        return render_template("shared/error.html", message=str(exc)), status_for(exc)

    @app.errorhandler(404)
    def _handle_404(exc: object) -> tuple[str, int]:
        return render_template("shared/error.html", message="Page not found."), 404
