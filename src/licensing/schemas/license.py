"""Pydantic schemas for the signed license payload and envelope.

Field set here MUST stay in lockstep with
licensing.licensing.canonical.REQUIRED_PAYLOAD_KEYS. A privacy/shape test in
tests/security asserts no additional (and in particular no experiment-shaped)
fields are ever added to this schema.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LicensePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    license_id: uuid.UUID
    user_id: uuid.UUID
    organization_id: uuid.UUID
    device_id: uuid.UUID
    device_public_key_hash: str
    product_code: str
    edition_code: str
    features: list[str]
    issued_at: datetime
    not_before: datetime
    expires_at: datetime
    key_id: str
    license_version: int = 1


class SignedLicenseEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    envelope_version: int = 1
    payload: LicensePayload
    signature: str = Field(description="base64url-encoded Ed25519 signature")
    key_id: str


class PublicSigningKey(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key_id: str
    algorithm: str
    public_key: str = Field(description="base64url-encoded raw public key bytes")
    status: str
    activated_at: datetime
    retired_at: datetime | None = None


class PublicSigningKeysResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    keys: list[PublicSigningKey]
