# Database Entity Relationship Model

All timestamps UTC (`timestamptz`). All primary keys are UUIDv4 unless noted.

```mermaid
erDiagram
    USERS ||--o{ ORGANIZATION_MEMBERSHIPS : "has"
    ORGANIZATIONS ||--o{ ORGANIZATION_MEMBERSHIPS : "has"
    ORGANIZATIONS ||--o{ ORGANIZATION_LICENSES : "owns"
    PRODUCTS ||--o{ EDITIONS : "has"
    PRODUCTS ||--o{ ORGANIZATION_LICENSES : "licensed as"
    EDITIONS ||--o{ ORGANIZATION_LICENSES : "licensed as"
    EDITIONS ||--o{ EDITION_FEATURES : "grants"
    FEATURES ||--o{ EDITION_FEATURES : "granted by"
    ORGANIZATION_LICENSES ||--o{ LICENSE_SEAT_ASSIGNMENTS : "allocates"
    USERS ||--o{ LICENSE_SEAT_ASSIGNMENTS : "assigned"
    ORGANIZATION_LICENSES ||--o{ DEVICE_ACTIVATIONS : "activates under"
    USERS ||--o{ DEVICE_ACTIVATIONS : "activates"
    DEVICE_ACTIVATIONS ||--o{ ISSUED_LICENSE_CERTIFICATES : "receives"
    DEVICE_ACTIVATIONS ||--o{ REFRESH_CHALLENGES : "renews via"
    SIGNING_KEYS ||--o{ ISSUED_LICENSE_CERTIFICATES : "signs"
    USERS ||--o{ ACTIVATION_REQUESTS : "approves (optional)"
    ORGANIZATIONS ||--o{ ACTIVATION_REQUESTS : "approves into (optional)"
    USERS ||--o{ AUDIT_EVENTS : "actor (optional)"
    ORGANIZATIONS ||--o{ AUDIT_EVENTS : "scoped to (optional)"

    USERS {
        uuid id PK
        string email
        string normalized_email UK
        string password_hash
        string display_name
        string status
        timestamptz email_verified_at
        timestamptz last_login_at
        timestamptz created_at
        timestamptz updated_at
    }

    ORGANIZATIONS {
        uuid id PK
        string name
        string slug UK
        string status
        timestamptz created_at
        timestamptz updated_at
    }

    ORGANIZATION_MEMBERSHIPS {
        uuid id PK
        uuid organization_id FK
        uuid user_id FK
        string role
        string status
        timestamptz joined_at
        timestamptz removed_at
        timestamptz created_at
        timestamptz updated_at
    }

    PRODUCTS {
        uuid id PK
        string code UK
        string name
        string status
    }

    EDITIONS {
        uuid id PK
        uuid product_id FK
        string code
        string name
        string status
    }

    FEATURES {
        uuid id PK
        string code UK
        string name
        string description
    }

    EDITION_FEATURES {
        uuid edition_id FK
        uuid feature_id FK
        jsonb config
    }

    ORGANIZATION_LICENSES {
        uuid id PK
        uuid organization_id FK
        uuid product_id FK
        uuid edition_id FK
        string status
        int seat_limit
        int device_limit_per_user
        timestamptz starts_at
        timestamptz expires_at
        int offline_validity_days
        timestamptz created_at
        timestamptz updated_at
    }

    LICENSE_SEAT_ASSIGNMENTS {
        uuid id PK
        uuid organization_license_id FK
        uuid user_id FK
        string status
        timestamptz assigned_at
        timestamptz removed_at
        uuid assigned_by_user_id FK
    }

    DEVICE_ACTIVATIONS {
        uuid id PK
        uuid organization_license_id FK
        uuid user_id FK
        bytes device_public_key
        string device_public_key_hash UK
        string display_name
        string status
        timestamptz activated_at
        timestamptz last_renewed_at
        timestamptz revoked_at
        uuid revoked_by_user_id FK
        string revocation_reason
        timestamptz created_at
        timestamptz updated_at
    }

    ACTIVATION_REQUESTS {
        uuid id PK
        string user_code_hash
        string status
        string requested_product_code
        string requested_edition_code
        timestamptz requested_at
        timestamptz expires_at
        uuid approved_by_user_id FK
        uuid approved_organization_id FK
        timestamptz approved_at
        timestamptz consumed_at
        int attempt_count
    }

    ISSUED_LICENSE_CERTIFICATES {
        uuid id PK
        uuid license_id
        uuid device_activation_id FK
        int license_version
        string signing_key_id FK
        timestamptz issued_at
        timestamptz not_before
        timestamptz expires_at
        timestamptz revoked_at
        string payload_hash
        string status
    }

    SIGNING_KEYS {
        string key_id PK
        string algorithm
        bytes public_key
        string status
        timestamptz activated_at
        timestamptz retired_at
        timestamptz created_at
    }

    AUDIT_EVENTS {
        uuid id PK
        uuid actor_user_id FK
        uuid organization_id FK
        string event_type
        string target_type
        string target_id
        string request_id
        string source_ip
        string user_agent
        jsonb metadata
        timestamptz created_at
    }

    REFRESH_CHALLENGES {
        uuid id PK
        uuid device_activation_id FK
        string nonce_hash
        timestamptz created_at
        timestamptz expires_at
        timestamptz consumed_at
    }
```

## Key constraints (DB-level, not just app-level)

* `users.normalized_email` — unique index, lower-cased at write time.
* `organization_memberships` — partial unique index on `(organization_id, user_id)`
  `WHERE status = 'active'` to prevent duplicate active memberships.
* `license_seat_assignments` — partial unique index on
  `(organization_license_id, user_id) WHERE status = 'active'`; seat-limit
  enforcement done via `SELECT ... FOR UPDATE` on the parent
  `organization_licenses` row inside the assignment transaction (see
  `services/seats.py`).
* `device_activations.device_public_key_hash` — globally unique; a device key
  can never be registered twice, satisfying the "duplicate device key" threat.
* `device_activations` — active-device-count-per-user enforced transactionally
  against `organization_licenses.device_limit_per_user`.
* `activation_requests.user_code_hash` — the raw user code is never persisted,
  only its hash (Argon2id or HMAC-SHA256 with a server pepper); lookups hash
  the presented code and compare.
* `refresh_challenges` — unused: this table exists in the schema from an
  earlier design draft that planned a renewal flow. That flow was dropped
  before being built (licenses are lifetime grants — see
  `docs/threat-model.md`), so no code ever writes to this table. Left in
  place as inert scaffolding rather than migrated out.
