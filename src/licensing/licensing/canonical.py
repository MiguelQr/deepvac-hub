"""Canonical serialization for signed license payloads.

See docs/license-format.md. The rule: sorted keys, no insignificant
whitespace, UTF-8 bytes, no trailing newline. This is the ONLY function
that may produce bytes for signing or verification — both the server and
any future reference verifier must call this, never hand-roll JSON dumping,
or signatures will silently stop matching across implementations.
"""

from __future__ import annotations

import json
from typing import Any

# The exact, exhaustive set of keys a license payload may contain. Kept here
# (not just in the Pydantic schema) so canonicalization itself refuses to
# silently sign an unexpected shape.
REQUIRED_PAYLOAD_KEYS = frozenset(
    {
        "schema_version",
        "license_id",
        "user_id",
        "organization_id",
        "device_id",
        "device_public_key_hash",
        "product_code",
        "edition_code",
        "features",
        "issued_at",
        "not_before",
        "expires_at",
        "key_id",
        "license_version",
    }
)


def canonicalize(payload: dict[str, Any]) -> bytes:
    """Return the exact byte sequence that must be signed/verified for a
    license payload.

    Raises ValueError if the payload's keys don't exactly match
    REQUIRED_PAYLOAD_KEYS — a deliberately strict guard against
    accidentally signing (or accepting as valid) a payload with extra or
    missing fields.
    """
    payload_keys = frozenset(payload.keys())
    if payload_keys != REQUIRED_PAYLOAD_KEYS:
        missing = REQUIRED_PAYLOAD_KEYS - payload_keys
        extra = payload_keys - REQUIRED_PAYLOAD_KEYS
        raise ValueError(
            f"License payload has invalid shape (missing={sorted(missing)}, "
            f"extra={sorted(extra)})"
        )
    canonical_json = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return canonical_json.encode("utf-8")
