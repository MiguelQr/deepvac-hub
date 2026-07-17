"""Builds and signs a license certificate, and records it.

The only place that assembles a payload for signing -- callers pass in
values already validated against the database in the same transaction, per
docs/license-format.md "Field trust rules".
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import select
from sqlalchemy.orm import Session

from licensing.licensing.canonical import canonicalize
from licensing.licensing.payload import build_payload_dict
from licensing.models.certificates import IssuedLicenseCertificate
from licensing.models.devices import DeviceActivation
from licensing.models.enums import IssuedCertificateStatus
from licensing.models.products import Edition, EditionFeature, Feature
from licensing.security.signing import SignedEnvelope, sign_payload


def edition_feature_codes(session: Session, edition_id: uuid.UUID) -> list[str]:
    rows = session.execute(
        select(Feature.code)
        .join(EditionFeature, EditionFeature.feature_id == Feature.id)
        .where(EditionFeature.edition_id == edition_id)
    ).scalars()
    return sorted(rows)


def issue_certificate(
    session: Session,
    *,
    device_activation: DeviceActivation,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    product_code: str,
    edition: Edition,
    signing_key_id: str,
    private_key: Ed25519PrivateKey,
    validity_days: int,
) -> SignedEnvelope:
    now = datetime.now(UTC)
    license_id = uuid.uuid4()
    payload = build_payload_dict(
        license_id=license_id,
        user_id=user_id,
        organization_id=organization_id,
        device_id=device_activation.id,
        device_public_key_hash=device_activation.device_public_key_hash,
        product_code=product_code,
        edition_code=edition.code,
        features=edition_feature_codes(session, edition.id),
        issued_at=now,
        not_before=now,
        expires_at=now + timedelta(days=validity_days),
        key_id=signing_key_id,
    )
    envelope = sign_payload(payload, private_key, key_id=signing_key_id)
    payload_hash = hashlib.sha256(canonicalize(payload)).hexdigest()

    certificate = IssuedLicenseCertificate(
        license_id=license_id,
        device_activation_id=device_activation.id,
        license_version=1,
        signing_key_id=signing_key_id,
        issued_at=now,
        not_before=now,
        expires_at=now + timedelta(days=validity_days),
        payload_hash=payload_hash,
        status=IssuedCertificateStatus.ACTIVE,
    )
    session.add(certificate)
    session.flush()
    return envelope
