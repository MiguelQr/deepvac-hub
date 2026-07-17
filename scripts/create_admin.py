#!/usr/bin/env python
"""Create (or promote) a vendor_super_admin user for the management portal.

Usage:
    python scripts/create_admin.py --email admin@example.com --display-name "Admin" [--password ...]

If --password is omitted, you will be prompted (input hidden). The password
is hashed with Argon2id before being written to the database — never stored
or logged in plaintext.

Idempotent: running this against an email that already exists updates its
display name, sets status=active and vendor_role=vendor_super_admin, and
resets the password if --password/--reset-password is given.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from licensing.database import session_scope  # noqa: E402
from licensing.models.enums import UserStatus, VendorRole  # noqa: E402
from licensing.models.users import User  # noqa: E402
from licensing.security.passwords import hash_password  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--password", default=None, help="Omit to be prompted securely.")
    args = parser.parse_args()

    password = args.password or getpass.getpass("Password: ")
    if len(password) < 12:
        raise SystemExit("Password must be at least 12 characters.")

    normalized_email = args.email.strip().lower()

    with session_scope() as session:
        user = (
            session.query(User)
            .filter(User.normalized_email == normalized_email)
            .one_or_none()
        )
        if user is None:
            user = User(
                email=args.email.strip(),
                normalized_email=normalized_email,
                display_name=args.display_name,
                password_hash=hash_password(password),
                status=UserStatus.ACTIVE,
                vendor_role=VendorRole.VENDOR_SUPER_ADMIN,
                email_verified_at=datetime.now(UTC),
            )
            session.add(user)
            action = "Created"
        else:
            user.display_name = args.display_name
            user.password_hash = hash_password(password)
            user.status = UserStatus.ACTIVE
            user.vendor_role = VendorRole.VENDOR_SUPER_ADMIN
            action = "Updated"
        session.flush()
        print(f"{action} vendor_super_admin user: {user.normalized_email} (id={user.id})")


if __name__ == "__main__":
    main()
