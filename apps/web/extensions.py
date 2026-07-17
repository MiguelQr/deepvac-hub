"""Flask extension instances, initialized in app.py's create_app().

Kept separate from app.py so blueprint modules can `from apps.web.extensions
import csrf, db_session` without circular imports.
"""

from __future__ import annotations

from flask_wtf import CSRFProtect

csrf = CSRFProtect()
