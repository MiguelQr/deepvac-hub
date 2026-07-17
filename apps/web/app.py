"""web — Flask, browser-facing admin portal. Run under Gunicorn.

Application factory pattern with blueprints, per section 9 of the spec.
Imports domain code from src/licensing only; contains no business logic
itself (see docs/architecture.md layering rules).

Phase A shipped the factory, extensions, security headers, and
session/cookie configuration. The `auth` and `activate` blueprints below
were added to close the loop on desktop device-code activation (section 4)
so the whole flow is verifiable locally; the rest of the admin portal
(dashboard, organizations, users, licenses, devices, audit) still lands in
Phase B/C — see README.md phase plan.
"""

from __future__ import annotations

import logging
import uuid

from flask import Flask, g, request

from apps.web.extensions import csrf
from licensing.config import get_settings
from licensing.database import get_scoped_session


def create_app() -> Flask:
    settings = get_settings()
    settings.validate_for_production()

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=settings.flask_secret_key,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=settings.session_cookie_secure,
        PERMANENT_SESSION_LIFETIME=60 * 60 * 8,  # 8 hours; revisited in Phase B
    )

    logging.basicConfig(level=settings.log_level)

    csrf.init_app(app)

    if settings.trusted_proxy_count > 0:
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(  # type: ignore[method-assign]
            app.wsgi_app,
            x_for=settings.trusted_proxy_count,
            x_proto=settings.trusted_proxy_count,
            x_host=settings.trusted_proxy_count,
        )

    @app.before_request
    def _assign_request_id() -> None:
        g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    @app.after_request
    def _security_headers(response):  # type: ignore[no-untyped-def]
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers["X-Request-ID"] = g.get("request_id", "")
        return response

    @app.teardown_appcontext
    def _remove_session(exception: BaseException | None) -> None:
        get_scoped_session().remove()

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    from apps.web.activate import bp as activate_bp
    from apps.web.auth import bp as auth_bp
    from apps.web.auth.session import load_current_user

    app.register_blueprint(auth_bp)
    app.register_blueprint(activate_bp)

    @app.context_processor
    def _inject_current_user() -> dict[str, object]:
        return {"current_user": load_current_user()}

    @app.get("/")
    def index():
        from flask import redirect, url_for

        return redirect(url_for("auth.login"))

    # Remaining blueprints land in Phase C (dashboard, organizations, users,
    # licenses) / Phase E (devices) / Phase F (audit).

    return app


app = create_app()
