from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from licensing.database import Base
from licensing.models.enums import ActivationRequestStatus
from licensing.models.mixins import UUIDPrimaryKeyMixin, pg_enum


class ActivationRequest(UUIDPrimaryKeyMixin, Base):
    """A single device-code activation attempt.

    The raw user code shown to the user is never persisted — only
    `user_code_hash` (HMAC-SHA256 with a server-side pepper). See
    docs/threat-model.md #4 (code guessing) and #5 (replay).
    """

    __tablename__ = "activation_requests"

    user_code_hash: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )
    status: Mapped[ActivationRequestStatus] = mapped_column(
        pg_enum(ActivationRequestStatus, name="activation_request_status"),
        nullable=False,
        default=ActivationRequestStatus.PENDING,
    )
    requested_product_code: Mapped[str] = mapped_column(String(100), nullable=False)
    requested_edition_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_organization_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ActivationRequest {self.id} status={self.status}>"


class RefreshChallenge(UUIDPrimaryKeyMixin, Base):
    """Short-lived, single-use nonce for device-signature license renewal."""

    __tablename__ = "refresh_challenges"

    device_activation_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("device_activations.id"), nullable=False, index=True
    )
    nonce_hash: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RefreshChallenge {self.id} device={self.device_activation_id}>"
