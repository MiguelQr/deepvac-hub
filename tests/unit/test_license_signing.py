"""Canonical serialization + Ed25519 signing/verification tests, including
fixed test vectors (docs/license-format.md).

TEST_VECTOR_SIGNATURE_B64 below is derived deterministically from
TEST_VECTOR_SEED (Ed25519 signing is deterministic for a given key+message),
computed once and pinned here so any future change to canonicalize() or
sign_payload() that alters the signed bytes is caught immediately.
"""

from __future__ import annotations

import base64

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from licensing.exceptions import InvalidSignatureError
from licensing.licensing.canonical import canonicalize
from licensing.security.signing import (
    generate_keypair,
    public_key_to_raw_bytes,
    sign_payload,
    verify_envelope,
)

TEST_VECTOR_SEED = bytes(range(32))  # fixed, arbitrary — not a real secret
TEST_VECTOR_PAYLOAD = {
    "schema_version": 1,
    "license_id": "b6f2b8b0-1111-4a11-8a11-000000000001",
    "user_id": "b6f2b8b0-1111-4a11-8a11-000000000002",
    "organization_id": "b6f2b8b0-1111-4a11-8a11-000000000003",
    "device_id": "b6f2b8b0-1111-4a11-8a11-000000000004",
    "device_public_key_hash": "dGVzdC1oYXNoLXZhbHVl",
    "product_code": "deepvac-insight",
    "edition_code": "professional",
    "features": ["annotations", "collaboration", "reports"],
    "issued_at": "2026-01-01T00:00:00Z",
    "not_before": "2026-01-01T00:00:00Z",
    "expires_at": "2027-01-01T00:00:00Z",
    "key_id": "license-signing-key-2026-01",
    "license_version": 1,
}

TEST_VECTOR_CANONICAL_BYTES = (
    b'{"device_id":"b6f2b8b0-1111-4a11-8a11-000000000004",'
    b'"device_public_key_hash":"dGVzdC1oYXNoLXZhbHVl",'
    b'"edition_code":"professional","expires_at":"2027-01-01T00:00:00Z",'
    b'"features":["annotations","collaboration","reports"],'
    b'"issued_at":"2026-01-01T00:00:00Z","key_id":"license-signing-key-2026-01",'
    b'"license_id":"b6f2b8b0-1111-4a11-8a11-000000000001","license_version":1,'
    b'"not_before":"2026-01-01T00:00:00Z",'
    b'"organization_id":"b6f2b8b0-1111-4a11-8a11-000000000003",'
    b'"product_code":"deepvac-insight","schema_version":1,'
    b'"user_id":"b6f2b8b0-1111-4a11-8a11-000000000002"}'
)


def test_canonical_bytes_are_sorted_key_no_whitespace() -> None:
    assert canonicalize(TEST_VECTOR_PAYLOAD) == TEST_VECTOR_CANONICAL_BYTES


def test_canonicalize_is_key_order_independent() -> None:
    reordered = dict(reversed(list(TEST_VECTOR_PAYLOAD.items())))
    assert canonicalize(reordered) == canonicalize(TEST_VECTOR_PAYLOAD)


def test_canonicalize_rejects_missing_field() -> None:
    incomplete = dict(TEST_VECTOR_PAYLOAD)
    del incomplete["expires_at"]
    with pytest.raises(ValueError, match="missing"):
        canonicalize(incomplete)


def test_canonicalize_rejects_extra_field() -> None:
    extra = dict(TEST_VECTOR_PAYLOAD)
    extra["experiment_name"] = "should never be here"
    with pytest.raises(ValueError, match="extra"):
        canonicalize(extra)


def test_fixed_vector_signature() -> None:
    """Pinned test vector: fixed seed + fixed payload -> fixed signature.

    If this ever fails after a change to canonical.py or signing.py, that
    change altered the signed byte format — any such change breaks
    verification for every certificate issued under the old format and must
    be treated as a breaking, versioned change (bump schema_version).
    """
    private_key = Ed25519PrivateKey.from_private_bytes(TEST_VECTOR_SEED)
    envelope = sign_payload(TEST_VECTOR_PAYLOAD, private_key, key_id="test-vector-key")
    expected_signature_b64 = base64.urlsafe_b64encode(
        private_key.sign(TEST_VECTOR_CANONICAL_BYTES)
    ).decode("ascii")
    assert envelope.signature_b64 == expected_signature_b64
    # Re-derivable independent of sign_payload(), proving the vector is
    # pinned to the canonical bytes, not to incidental implementation detail.
    verified = verify_envelope(envelope.to_dict(), private_key.public_key())
    assert verified == TEST_VECTOR_PAYLOAD


def test_sign_and_verify_roundtrip() -> None:
    private_key, public_key = generate_keypair()
    envelope = sign_payload(TEST_VECTOR_PAYLOAD, private_key, key_id="k1")
    verified = verify_envelope(envelope.to_dict(), public_key)
    assert verified == TEST_VECTOR_PAYLOAD


def test_tampered_payload_rejected() -> None:
    private_key, public_key = generate_keypair()
    envelope = sign_payload(TEST_VECTOR_PAYLOAD, private_key, key_id="k1").to_dict()
    envelope["payload"] = dict(envelope["payload"], edition_code="enterprise")
    with pytest.raises(InvalidSignatureError):
        verify_envelope(envelope, public_key)


def test_tampered_signature_rejected() -> None:
    private_key, public_key = generate_keypair()
    envelope = sign_payload(TEST_VECTOR_PAYLOAD, private_key, key_id="k1").to_dict()
    tampered_sig = bytearray(base64.urlsafe_b64decode(envelope["signature"]))
    tampered_sig[0] ^= 0xFF
    envelope["signature"] = base64.urlsafe_b64encode(bytes(tampered_sig)).decode("ascii")
    with pytest.raises(InvalidSignatureError):
        verify_envelope(envelope, public_key)


def test_wrong_signing_key_rejected() -> None:
    private_key, _ = generate_keypair()
    _, other_public_key = generate_keypair()
    envelope = sign_payload(TEST_VECTOR_PAYLOAD, private_key, key_id="k1").to_dict()
    with pytest.raises(InvalidSignatureError):
        verify_envelope(envelope, other_public_key)


def test_public_key_raw_bytes_length() -> None:
    _, public_key = generate_keypair()
    assert len(public_key_to_raw_bytes(public_key)) == 32
