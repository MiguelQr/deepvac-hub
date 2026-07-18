# Deepvac Hub

This app is the cloud licensing control plane for the deepvac-insight
desktop application: identity, organizations, device activation, and
cryptographic license issuance. A license is a lifetime grant to an
organization — every active member is entitled to the licensed
product/edition, with no per-seat limit, and no renewal or revocation flow
once a device has activated.

This service never stores experiment files, names, metadata, measurements,
channels, annotations, or customer project data.

Full design docs: [architecture](docs/architecture.md) ·
[database ERD](docs/database-erd.md) · [sequences](docs/sequences.md) ·
[license format](docs/license-format.md) · [threat model](docs/threat-model.md) ·
[privacy](docs/privacy.md) · [deployment](docs/deployment.md)

## Repository layout

```text
hub/
├── apps/
│   ├── api/                  # FastAPI — desktop-facing
│   │   ├── main.py
│   │   ├── dependencies.py
│   │   ├── middleware.py
│   │   └── routers/{health,activation,licenses}.py
│   └── web/                  # Flask — admin portal
│       ├── app.py
│       ├── extensions.py  errors.py  audit.py
│       ├── auth/ dashboard/ organizations/ users/ licenses/
│       ├── templates/ static/
├── src/licensing/            # shared domain package, imported by both apps
│   ├── config.py database.py exceptions.py pagination.py
│   ├── models/ schemas/ services/ security/ licensing/ audit/
├── migrations/                # Alembic
├── tests/{unit,integration,security}/
├── scripts/{create_admin,generate_signing_key,seed_development}.py
├── docker/  nginx/  docs/
├── alembic.ini  compose.yaml  pyproject.toml  .env.example
```

## API endpoint table (`/api/v1`, FastAPI)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health/live` | none | liveness |
| GET | `/health/ready` | none | readiness (checks DB) |
| POST | `/activations` | none | start activation, returns user code + verification URL |
| GET | `/activations/{id}` | none | poll status; does not leak unrelated org/user existence |
| POST | `/activations/{id}/complete` | activation must be `approved` | submit device public key, receive signed license |
| GET | `/licensing/public-keys` | none | active + still-needed retired public keys |

## Flask management-portal page map

| Section | Routes |
|---|---|
| Auth | `/login`, `/logout`, `/account/password` |
| Dashboard | `/` — active org/license/device counts, licenses expiring soon |
| Organizations | `/organizations`, `/organizations/new`, `/organizations/<id>` (edit/disable/memberships/licenses/devices) |
| Users | `/users`, `/users/new`, `/users/<id>` (disable/reactivate/reset-password/memberships/devices/security) |
| Licenses | `/organizations/<id>/licenses/new`, `/licenses/<id>` (read-only overview, certificates) |
| Devices | read-only, inline on organization/user detail pages |

## Sequence diagrams

See [`docs/sequences.md`](docs/sequences.md) for the full Mermaid activation
sequence: browser-based device-code activation flow, single-use short-lived
user code, no password re-entry after the initial device keypair is
registered.

## Cryptographic format

**Ed25519**, canonical JSON (sorted keys, no whitespace, UTF-8) as the signed
byte string, versioned envelope `{envelope_version, payload, signature,
key_id}`. Full rationale and test-vector strategy: [`docs/license-format.md`](docs/license-format.md).

## Threat model summary

Covers license-file copying, device-key copying/duplicate registration,
activation-code guessing/replay, payload tampering, stolen admin sessions,
cross-org access, DB compromise, signing-key compromise, malicious clients,
and the honest limits of long-lived offline license validity. Full table:
[`docs/threat-model.md`](docs/threat-model.md).

## Domain model (`src/licensing`)

* `config.py` — environment-based settings, fails fast on missing critical
  secrets outside local development.
* `database.py` — SQLAlchemy 2.x engine/session (Psycopg 3) against
  PostgreSQL.
* `models/*` — users, organizations, memberships, products, editions,
  features, edition_features, organization_licenses, device_activations,
  activation_requests, issued_license_certificates, signing_keys,
  audit_events, with the DB-level constraints described in
  `docs/database-erd.md`.
* `licensing/canonical.py` + `security/signing.py` — canonical payload
  serialization and Ed25519 sign/verify, with pinned test vectors.
* `services/{auth,organizations,users,licenses,dashboard,activation,devices,issuance,signing_keys}.py`
  — all business logic lives here. `auth.py` is the authorization core
  (`require_vendor`, `require_org_view`, `require_org_admin`); every
  org/user/license service function calls into it before touching data
  (see `docs/threat-model.md` threat #9, cross-organization access).
* `audit/recorder.py` + `audit/allowlist.py` — the only sanctioned way to
  write an `audit_events` row; metadata keys are allow-listed so nothing
  outside the licensing/identity/administrative domain can be logged (see
  `docs/privacy.md`).

## Desktop activation API (`apps/api`)

* `POST /activations`, `GET /activations/{id}`, `POST /activations/{id}/complete`
  implement the full device-code activation flow (see sequence diagram
  above). `GET /licensing/public-keys` serves the trusted signing keys the
  desktop client verifies certificates against.
* Entitlement at activation time: the requesting user must have an active
  membership in the approving organization, and that organization must
  have an active license for the requested product/edition — no seat
  limit, every active member qualifies. `device_limit_per_user` (default
  3) is the only per-user cap.
* Issued certificates are valid for `OrganizationLicense.offline_validity_days`
  from issuance (default ~36500 days) — a lifetime grant, independent of
  the organization license's own `expires_at`.
* `apps/api/error_handlers.py` maps domain exceptions
  (`src/licensing/exceptions.py`) to HTTP status codes via a status map
  shared with the Flask side, so the two surfaces can't drift.

## Admin portal (`apps/web`)

* **Auth** — email/password login (Argon2id hashing), CSRF via Flask-WTF,
  signed-cookie sessions with an 8h absolute lifetime and a sliding idle
  timeout (`SESSION_IDLE_TIMEOUT_MINUTES`, default 60). Self-service
  password change at `/account/password`.
* **RBAC** — `vendor_super_admin` has full write access across every
  organization; `vendor_support` is read-only everywhere;
  `organization_admin`/`organization_member` can only view/manage their
  own organization(s), enforced in the service layer and tested explicitly
  in `tests/security/test_cross_org_access.py`.
* **Organizations** — list/search/create, edit name/slug, disable/reactivate,
  membership management (add/remove/change role).
* **Users** — vendor-managed global directory: list/search/create,
  disable/reactivate, admin-set password reset, vendor-role grant.
* **Licenses** — create under an organization; the detail page is
  read-only (overview plus the list of certificates issued under it).
* **Devices** — read-only, shown inline on organization and user detail
  pages.
* **Dashboard** — active organization/license/device counts, licenses
  expiring within 30 days.
* `apps/web/errors.py` centrally maps `PermissionDeniedError`/`NotFoundError`
  to 403/404; validation and conflict errors are flashed inline on the
  form that triggered them.
* Every write action is recorded via `licensing.audit.record_event()`.

## Running it locally

```powershell
docker compose up -d
docker compose run --rm tools alembic upgrade head
docker compose run --rm tools python scripts/generate_signing_key.py --key-id dev-key-2026 --out-dir ./secrets
docker compose run --rm tools python scripts/seed_development.py --key-id dev-key-2026 --public-key-file secrets/dev-key-2026.public.b64
```

This seeds a demo org (`demo-org`) with an active `deepvac-insight`
professional license (every active member entitled, no seat limit) and a
portal login: `demo@example.com` / `DemoPass123!` at
`http://localhost:8080/login`. Run the sibling `insight` app
(`python main.py` there) — its **Activate this installation** window opens
`http://localhost:8080/activate?user_code=...`; sign in with the demo login
and approve. The desktop app finishes activation automatically and caches a
verified license under `data/license/`. See `../insight/README.md`
("Cloud licensing (device activation)") for the desktop side.

`docker compose run --rm tools pytest` runs the full suite (needs a
reachable PostgreSQL via `TEST_DATABASE_URL`/`DATABASE_URL`);
`docker compose run --rm tools ruff check .` and
`docker compose run --rm tools mypy` for linting/typing.

## Notable design decisions

* User-code format for activation: 8 uppercase-alphanumeric characters
  (Crockford-safe alphabet, excludes ambiguous characters), grouped
  `XXXX-XXXX`, hashed with HMAC-SHA256 + server-side pepper — not Argon2id,
  since its deliberate slowness is counterproductive for a high-volume
  polling lookup. Guessing defense today is code entropy plus a short TTL;
  request rate limiting is not implemented (see `docs/threat-model.md`
  threat #4).
* Flask session storage uses signed cookies (Flask's built-in,
  itsdangerous-based) rather than server-side sessions.
* Admin-initiated password reset sets the new password directly — no
  forced-change flow, no email dependency (this app has no mail sender).
* Certificate validity (`offline_validity_days`) is independent of the
  organization license's own `expires_at` — a lifetime grant shouldn't
  retroactively shrink if an admin later edits the license record.
