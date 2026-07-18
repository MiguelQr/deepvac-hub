from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from licensing.database import Base
from licensing.models.enums import DeviceActivationStatus
from licensing.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin, pg_enum

if TYPE_CHECKING:
    from licensing.models.users import User


class DeviceActivation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One registered installation keypair for one licensed user.

    Stores only the device's public key material and lifecycle metadata —
    never a fingerprint derived from MAC address, CPU/disk serial, or
    hostname (see docs/threat-model.md and section 6 of the spec).
    """

    __tablename__ = "device_activations"

    organization_license_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organization_licenses.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    device_public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    device_public_key_hash: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[DeviceActivationStatus] = mapped_column(
        pg_enum(DeviceActivationStatus, name="device_activation_status"),
        nullable=False,
        default=DeviceActivationStatus.PENDING,
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_renewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    revocation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    user: Mapped[User] = relationship(foreign_keys=[user_id])

    def __repr__(self) -> str:  # pragma: no cover
        return f"<DeviceActivation {self.id} user={self.user_id} status={self.status}>"
