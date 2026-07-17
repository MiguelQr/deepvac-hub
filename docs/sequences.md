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
    A->>DB: Re-validate user status, membership, seat availability, device limit, entitlement
    A->>DB: INSERT device_activations (status=active), UPDATE seat assignment if needed
    A->>A: Build canonical license payload, sign with Ed25519 private key
    A->>DB: INSERT issued_license_certificates
    A->>DB: UPDATE activation_requests SET status=consumed, consumed_at=now()
    A-->>D: {license_payload, signature, key_id}
```

Key properties: the user code is single-use and short-lived; the browser
session used for approval is never handed to the desktop app — only a signed
license certificate is returned.

## Silent license renewal

```mermaid
sequenceDiagram
    participant D as Desktop App
    participant A as api (FastAPI)
    participant DB as PostgreSQL

    D->>A: POST /api/v1/licenses/refresh/challenge {device_id}
    A->>DB: INSERT refresh_challenges (nonce_hash, expires_at)
    A-->>D: {challenge_id, nonce, expires_at}
    D->>D: Sign nonce with device Ed25519 private key
    D->>A: POST /api/v1/licenses/refresh {challenge_id, device_id, signature}
    A->>DB: Load challenge, verify not expired/not consumed
    A->>DB: Load device_activations, verify status=active, load public key
    A->>A: Verify signature over nonce using stored device public key
    A->>DB: UPDATE refresh_challenges SET consumed_at=now() WHERE consumed_at IS NULL (single-use guard)
    A->>DB: Verify user active, membership active, seat active, org license active/not expired
    A->>A: Build fresh canonical payload (new issued_at/expires_at), sign
    A->>DB: INSERT issued_license_certificates, UPDATE device_activations.last_renewed_at
    A-->>D: {license_payload, signature, key_id}
```

No password or browser interaction is required for renewal — trust is rooted
in proof of possession of the device private key plus live server-side status
checks.
