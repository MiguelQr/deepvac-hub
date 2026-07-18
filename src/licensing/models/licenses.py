from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from licensing.database import Base
from licensing.models.enums import OrganizationLicenseStatus
from licensing.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin, pg_enum

if TYPE_CHECKING:
    from licensing.models.organizations import Organization
    from licensing.models.products import Edition, Product


class OrganizationLicense(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Entitles every active member of `organization_id` to the given
    product/edition for the license's validity window -- there is no
    per-user seat limit or seat-assignment step. Any active org member can
    activate a device directly, up to `device_limit_per_user` devices each
    (see services/activation.py)."""

    __tablename__ = "organization_licenses"
    __table_args__ = (
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
    device_limit_per_user: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    offline_validity_days: Mapped[int] = mapped_column(Integer, nullable=False, default=36500)
    """Certificate validity window from issuance, independent of this
    license's own expires_at (see services/issuance.py). Defaults to
    ~100 years: licenses in this product are lifetime grants with no
    renewal flow, so this is intentionally not a short check-in interval
    -- an admin can still set a shorter value per-license if ever needed."""

    organization: Mapped[Organization] = relationship()
    product: Mapped[Product] = relationship()
    edition: Mapped[Edition] = relationship()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<OrganizationLicense {self.id} org={self.organization_id} status={self.status}>"
