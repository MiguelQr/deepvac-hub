# Sequence Diagrams

## First-launch activation

```mermaid
sequenceDiagram
    participant D as Desktop App
    participant A as api (FastAPI)
    participant U as User's Browser
    participant W as web (Flask)
    participant DB as PostgreSQL

    D->>A: POST /api/v1/activations {product_code, edition_code}
    A->>DB: INSERT activation_requests (status=pending, user_code_hash, expires_at)
    A-->>D: {activation_id, user_code, verification_url, expires_at, polling_interval}
    D->>U: Open verification_url in default browser
    U->>W: GET /activate?user_code=XXXX-XXXX
    W->>U: Login form (if not already authenticated)
    U->>W: Submit credentials
    W->>DB: Verify password (Argon2id), load memberships
    W-->>U: Show organization + product/edition confirmation screen
    U->>W: Confirm activation (choose organization)
    W->>DB: UPDATE activation_requests SET status=approved, approved_by_user_id, approved_organization_id
    W->>DB: INSERT audit_events (event_type=activation_approved)
    loop until approved/expired, every polling_interval
        D->>A: GET /api/v1/activations/{activation_id}
        A-->>D: {status: pending|approved|denied|expired}
    end
    D->>D: Generate Ed25519 device keypair locally
    D->>A: POST /api/v1/activations/{activation_id}/complete {device_public_key}
    A->>DB: Re-validate user status, membership, device limit, entitlement
    A->>DB: INSERT device_activations (status=active)
    A->>A: Build canonical license payload, sign with Ed25519 private key
    A->>DB: INSERT issued_license_certificates
    A->>DB: UPDATE activation_requests SET status=consumed, consumed_at=now()
    A-->>D: {license_payload, signature, key_id}
```

Key properties: the user code is single-use and short-lived; the browser
session used for approval is never handed to the desktop app — only a signed
license certificate is returned.

## No renewal flow (by design)

Licenses in this product are lifetime grants: `complete_activation` issues a
certificate valid for `OrganizationLicense.offline_validity_days` (defaults
to ~100 years — see README.md's Phase D notes), and the desktop app
(`insight`) never calls back for a fresh one. There is deliberately no
challenge-response renewal endpoint and no device revoke/replace endpoint —
an earlier design draft of this doc described one; it was dropped before
being built once the product decision landed on "lifetime license per
organization, no renewal or revocation." `refresh_challenges` remains in the
schema as inert, unused scaffolding rather than being migrated out.

The practical consequence, stated plainly: once a device activates, there is
no live channel for the vendor to revoke that device's access before its
certificate's own `expires_at` (effectively never, given the default). See
`docs/threat-model.md` threat #13 for the accepted risk this implies.
