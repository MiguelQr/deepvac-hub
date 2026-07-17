"""Confirm the license-signing private key is never returned through the
public API surface or embedded in anything that would end up in logs/output
(section 11 / docs/privacy.md: "private signing keys are never returned
through APIs").
"""

from __future__ import annotations

import dataclasses
import json

from licensing.security.signing import (
    SignedEnvelope,
    generate_keypair,
    private_key_to_raw_bytes,
    sign_payload,
)

_PAYLOAD = {
    "schema_version": 1,
    "license_id": "b6f2b8b0-1111-4a11-8a11-000000000001",
    "user_id": "b6f2b8b0-1111-4a11-8a11-000000000002",
    "organization_id": "b6f2b8b0-1111-4a11-8a11-000000000003",
    "device_id": "b6f2b8b0-1111-4a11-8a11-000000000004",
    "device_public_key_hash": "dGVzdC1oYXNoLXZhbHVl",
    "product_code": "deepvac-insight",
    "edition_code": "professional",
    "features": ["reports"],
    "issued_at": "2026-01-01T00:00:00Z",
    "not_before": "2026-01-01T00:00:00Z",
    "expires_at": "2027-01-01T00:00:00Z",
    "key_id": "k1",
    "license_version": 1,
}


def test_signed_envelope_has_no_private_key_field() -> None:
    field_names = {f.name for f in dataclasses.fields(SignedEnvelope)}
    assert field_names == {"envelope_version", "payload", "signature_b64", "key_id"}


def test_serialized_envelope_never_contains_raw_private_key_bytes() -> None:
    private_key, _ = generate_keypair()
    raw_private = private_key_to_raw_bytes(private_key)
    envelope = sign_payload(_PAYLOAD, private_key, key_id="k1")
    serialized = json.dumps(envelope.to_dict())
    assert raw_private.hex() not in serialized
    assert raw_private not in serialized.encode("utf-8", errors="ignore")


def test_private_key_repr_does_not_expose_raw_bytes() -> None:
    private_key, _ = generate_keypair()
    raw_private = private_key_to_raw_bytes(private_key)
    assert raw_private.hex() not in repr(private_key)
    assert raw_private.hex() not in str(private_key)
