from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from licensing.database import Base
from licensing.models.enums import UserStatus, VendorRole
from licensing.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin, pg_enum

if TYPE_CHECKING:
    from licensing.models.organizations import OrganizationMembership


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A vendor-cloud identity. Never stores anything experiment-related —
    see docs/privacy.md.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    normalized_email: Mapped[str] = mapped_column(
        String(320), nullable=False, unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[UserStatus] = mapped_column(
        pg_enum(UserStatus, name="user_status"),
        nullable=False,
        default=UserStatus.PENDING,
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    vendor_role: Mapped[VendorRole | None] = mapped_column(
        pg_enum(VendorRole, name="vendor_role"),
        nullable=True,
        default=None,
    )
    """Global vendor-staff role (vendor_super_admin/vendor_support), or NULL
    for ordinary customer users. Distinct from OrganizationMembership.role,
    which is organization-scoped. A vendor_support user having this set does
    NOT imply organization_admin rights over any organization."""

    memberships: Mapped[list[OrganizationMembership]] = relationship(
        back_populates="user", foreign_keys="OrganizationMembership.user_id"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"<User {self.id} {self.normalized_email!r} status={self.status}>"
