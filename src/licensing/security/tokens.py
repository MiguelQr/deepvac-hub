"""Random token generation and constant-time hashed lookup helpers, used for
activation user codes and refresh-challenge nonces.

Argon2id is deliberately NOT used here: these values are high-entropy,
server-generated random tokens (not user-chosen passwords), looked up at
high frequency during polling. Argon2id's intentional slowness would be a
self-inflicted denial-of-service; the actual defenses are token entropy,
short TTL, and rate limiting (see docs/threat-model.md #4).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from licensing.config import get_settings

# Crockford-safe alphabet: excludes 0/O and 1/I/L to avoid user transcription
# errors when reading the code off a desktop-app screen.
_USER_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_user_code() -> str:
    """8 characters, displayed as XXXX-XXXX."""
    raw = "".join(secrets.choice(_USER_CODE_ALPHABET) for _ in range(8))
    return f"{raw[:4]}-{raw[4:]}"


def generate_nonce() -> str:
    return secrets.token_urlsafe(32)


def _pepper() -> bytes:
    # Reuses the Flask secret key as an HMAC pepper for these lookup hashes.
    # Rationale: both are "if leaked, attacker gains a modest edge, not a
    # full compromise" secrets; not worth managing as a third distinct value
    # in Phase A. Revisit if that stops being true.
    return get_settings().flask_secret_key.encode("utf-8")


def hash_lookup_token(raw_token: str) -> str:
    return hmac.new(_pepper(), raw_token.encode("utf-8"), hashlib.sha256).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)
