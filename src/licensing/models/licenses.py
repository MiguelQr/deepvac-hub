from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from licensing.database import Base
from licensing.models.enums import OrganizationLicenseStatus, SeatAssignmentStatus
from licensing.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin, pg_enum

if TYPE_CHECKING:
    from licensing.models.organizations import Organization
    from licensing.models.products import Edition, Product
    from licensing.models.users import User


class OrganizationLicense(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organization_licenses"
    __table_args__ = (
        CheckConstraint("seat_limit >= 0", name="ck_org_license_seat_limit_nonneg"),
        CheckConstraint(
            "device_limit_per_user >= 1", name="ck_org_license_device_limit_positive"
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True
    )
    edition_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("editions.id"), nullable=False, index=True
    )
    status: Mapped[OrganizationLicenseStatus] = mapped_column(
        pg_enum(OrganizationLicenseStatus, name="organization_license_status"),
        nullable=False,
        default=OrganizationLicenseStatus.PENDING,
    )
    seat_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    device_limit_per_user: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    offline_validity_days: Mapped[int] = mapped_column(Integer, nullable=False, default=36500)
    """Certificate validity window from issuance, independent of this
    license's own expires_at (see services/issuance.py). Defaults to
    ~100 years: licenses in this product are lifetime grants with no
    renewal flow, so this is intentionally not a short check-in interval
    -- an admin can still set a shorter value per-license if ever needed."""

    seat_assignments: Mapped[list[LicenseSeatAssignment]] = relationship(
        back_populates="organization_license"
    )
    organization: Mapped[Organization] = relationship()
    product: Mapped[Product] = relationship()
    edition: Mapped[Edition] = relationship()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<OrganizationLicense {self.id} org={self.organization_id} status={self.status}>"


class LicenseSeatAssignment(UUIDPrimaryKeyMixin, Base):
    """A single user's claim on one seat of an organization license.

    Concurrency: seat-limit enforcement is done in
    services/seats.py by taking a row lock
    (`SELECT ... FOR UPDATE`) on the parent OrganizationLicense before
    counting active assignments and inserting a new one, in the same
    transaction — this table's partial unique index only prevents *duplicate*
    assignment, not over-allocation, which is a distinct requirement.
    """

    __tablename__ = "license_seat_assignments"
    __table_args__ = (
        Index(
            "ix_seat_assignments_active_unique",
            "organization_license_id",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    organization_license_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organization_licenses.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    status: Mapped[SeatAssignmentStatus] = mapped_column(
        pg_enum(SeatAssignmentStatus, name="seat_assignment_status"),
        nullable=False,
        default=SeatAssignmentStatus.ACTIVE,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    organization_license: Mapped[OrganizationLicense] = relationship(
        back_populates="seat_assignments"
    )
    user: Mapped[User] = relationship(foreign_keys=[user_id])

    def __repr__(self) -> str:  # pragma: no cover
        return f"<LicenseSeatAssignment {self.id} user={self.user_id} status={self.status}>"
