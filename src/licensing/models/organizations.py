from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from licensing.database import Base
from licensing.models.enums import MembershipRole, MembershipStatus, OrganizationStatus
from licensing.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin, pg_enum

if TYPE_CHECKING:
    from licensing.models.users import User


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    status: Mapped[OrganizationStatus] = mapped_column(
        pg_enum(OrganizationStatus, name="organization_status"),
        nullable=False,
        default=OrganizationStatus.ACTIVE,
    )

    memberships: Mapped[list[OrganizationMembership]] = relationship(
        back_populates="organization"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Organization {self.id} {self.slug!r}>"


class OrganizationMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A user's role within an organization.

    Only one *active* membership per (organization, user) pair is allowed;
    enforced via a partial unique index in the migration
    (WHERE status = 'active'), not just the app layer.
    """

    __tablename__ = "organization_memberships"
    __table_args__ = (
        # Prevents duplicate *active* memberships for the same user/org pair
        # while still allowing historical removed rows to accumulate.
        Index(
            "ix_org_memberships_active_unique",
            "organization_id",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    role: Mapped[MembershipRole] = mapped_column(
        pg_enum(MembershipRole, name="membership_role"), nullable=False
    )
    status: Mapped[MembershipStatus] = mapped_column(
        pg_enum(MembershipStatus, name="membership_status"),
        nullable=False,
        default=MembershipStatus.ACTIVE,
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped[Organization] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships", foreign_keys=[user_id])

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<OrganizationMembership org={self.organization_id} "
            f"user={self.user_id} role={self.role}>"
        )
