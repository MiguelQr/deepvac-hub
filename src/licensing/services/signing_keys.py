"""Read-side queries for signing-key metadata (public keys only -- never the
private key, which lives outside the database entirely).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from licensing.models.certificates import IssuedLicenseCertificate, SigningKey
from licensing.models.enums import IssuedCertificateStatus, SigningKeyStatus


def list_public_keys(session: Session) -> list[SigningKey]:
    """Active keys, plus retired keys that still have a non-expired active
    certificate outstanding -- so clients holding older certificates can
    still verify them through natural expiry (see docs/license-format.md).
    """
    active = list(
        session.execute(
            select(SigningKey).where(SigningKey.status == SigningKeyStatus.ACTIVE)
        ).scalars()
    )
    now = datetime.now(UTC)
    still_needed_retired = list(
        session.execute(
            select(SigningKey)
            .join(
                IssuedLicenseCertificate,
                IssuedLicenseCertificate.signing_key_id == SigningKey.key_id,
            )
            .where(
                SigningKey.status == SigningKeyStatus.RETIRED,
                IssuedLicenseCertificate.status == IssuedCertificateStatus.ACTIVE,
                IssuedLicenseCertificate.expires_at > now,
            )
            .distinct()
        ).scalars()
    )
    return active + still_needed_retired
