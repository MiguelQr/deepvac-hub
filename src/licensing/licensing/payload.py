"""Builds the trusted, canonical license payload dict for signing.

This is the single place where a license payload is assembled from
server-side truth. Called once, at activation completion (no renewal
service exists -- licenses are lifetime grants). Callers pass only values
already validated against the database in the same transaction — never raw
client input. See docs/license-format.md "Field trust rules".
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise ValueError("Naive datetime passed to license payload builder; must be UTC-aware")
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_payload_dict(
    *,
    license_id: uuid.UUID,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    device_id: uuid.UUID,
    device_public_key_hash: str,
    product_code: str,
    edition_code: str,
    features: list[str],
    issued_at: datetime,
    not_before: datetime,
    expires_at: datetime,
    key_id: str,
    license_version: int = 1,
    schema_version: int = 1,
) -> dict[str, object]:
    return {
        "schema_version": schema_version,
        "license_id": str(license_id),
        "user_id": str(user_id),
        "organization_id": str(organization_id),
        "device_id": str(device_id),
        "device_public_key_hash": device_public_key_hash,
        "product_code": product_code,
        "edition_code": edition_code,
        "features": sorted(features),
        "issued_at": _iso(issued_at),
        "not_before": _iso(not_before),
        "expires_at": _iso(expires_at),
        "key_id": key_id,
        "license_version": license_version,
    }
