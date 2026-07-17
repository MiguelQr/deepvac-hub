#!/usr/bin/env python
"""Generate a new Ed25519 license-signing keypair.

Usage:
    python scripts/generate_signing_key.py --key-id license-signing-key-2026-01 --out-dir ./secrets

Writes two files to --out-dir:
    <key-id>.private (raw 32 bytes — treat as a secret; mount into the API
        container via LICENSE_SIGNING_PRIVATE_KEY_PATH, never commit it)
    <key-id>.public.b64 (base64url-encoded raw public key — safe to commit
        to a signing_keys migration/seed or paste into the database)

This script never prints the private key material to stdout — only the
file paths it wrote and the public key (which is, by design, public).
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from licensing.security.signing import (  # noqa: E402
    generate_keypair,
    private_key_to_raw_bytes,
    public_key_to_raw_bytes,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key-id", required=True)
    parser.add_argument("--out-dir", default="./secrets")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    private_key, public_key = generate_keypair()
    private_path = out_dir / f"{args.key_id}.private"
    public_path = out_dir / f"{args.key_id}.public.b64"

    private_path.write_bytes(private_key_to_raw_bytes(private_key))
    # best-effort on platforms without POSIX permissions (e.g. Windows)
    with contextlib.suppress(NotImplementedError):
        private_path.chmod(0o600)

    public_b64 = base64.urlsafe_b64encode(public_key_to_raw_bytes(public_key)).decode("ascii")
    public_path.write_text(public_b64 + "\n")

    print(f"Wrote private key: {private_path}")
    print(f"Wrote public key:  {public_path}")
    print(f"key_id:            {args.key_id}")
    print(f"public_key (b64url): {public_b64}")
    print()
    print("Next steps:")
    print(f"  1. Set LICENSE_SIGNING_KEY_ID={args.key_id} and")
    print(f"     LICENSE_SIGNING_PRIVATE_KEY_PATH={private_path} in the API's environment.")
    print("  2. Insert a signing_keys row with this key_id/public_key/status=active")
    print("     (via scripts/seed_development.py in dev, or a migration/admin action in prod).")


if __name__ == "__main__":
    main()
