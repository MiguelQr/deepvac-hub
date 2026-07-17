from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from licensing.database import Base
from licensing.models.enums import IssuedCertificateStatus, SigningKeyStatus
from licensing.models.mixins import UUIDPrimaryKeyMixin, pg_enum


class SigningKey(Base):
    """Public metadata only. The private key never lives in this table or
    anywhere else in the database — it is loaded from deployment secret
    storage at process start (see config.py, docs/license-format.md).
    """

    __tablename__ = "signing_keys"

    key_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    algorithm: Mapped[str] = mapped_column(String(50), nullable=False, default="ed25519")
    public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    status: Mapped[SigningKeyStatus] = mapped_column(
        pg_enum(SigningKeyStatus, name="signing_key_status"),
        nullable=False,
        default=SigningKeyStatus.ACTIVE,
    )
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SigningKey {self.key_id!r} status={self.status}>"


class IssuedLicenseCertificate(UUIDPrimaryKeyMixin, Base):
    """Record of a signed license payload having been issued. Used for audit,
    revocation, and to answer "what did we sign and when" without needing to
    re-derive it — the payload itself is not duplicated here, only its hash.
    """

    __tablename__ = "issued_license_certificates"

    license_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    device_activation_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("device_activations.id"), nullable=False, index=True
    )
    license_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    signing_key_id: Mapped[str] = mapped_column(
        String(200), ForeignKey("signing_keys.key_id"), nullable=False
    )
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    not_before: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[IssuedCertificateStatus] = mapped_column(
        pg_enum(IssuedCertificateStatus, name="issued_certificate_status"),
        nullable=False,
        default=IssuedCertificateStatus.ACTIVE,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<IssuedLicenseCertificate {self.id} "
            f"license={self.license_id} status={self.status}>"
        )
