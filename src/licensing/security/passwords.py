"""Argon2id password hashing for management-portal accounts.

Never store or return plaintext/reversible passwords. Hashing parameters
are the argon2-cffi defaults (time_cost=3, memory_cost=64MB, parallelism=4
as of argon2-cffi 23.x), which are reasonable for a login endpoint; revisit
under docs/threat-model.md if profiling shows otherwise.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(plaintext_password: str) -> str:
    return _hasher.hash(plaintext_password)


def verify_password(plaintext_password: str, password_hash: str) -> bool:
    try:
        _hasher.verify(password_hash, plaintext_password)
    except VerifyMismatchError:
        return False
    return True


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)
