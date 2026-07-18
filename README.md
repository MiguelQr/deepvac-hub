# Deepvac Hub

This app is the cloud service for **identity, organizations, seats,
device activation, and cryptographic license issuance/renewal/revocation**
for the deepvac-insight desktop application.

This service
never stores experiment files, names, metadata, measurements, channels,
annotations, or customer project data.

Full design docs: [architecture](docs/architecture.md) ·
[database ERD](docs/database-erd.md) · [sequences](docs/sequences.md) ·
[license format](docs/license-format.md) · [threat model](docs/threat-model.md) ·
[privacy](docs/privacy.md) · [deployment](docs/deployment.md)

## Repository layout

```text
hub/
├── apps/
│   ├── api/                  # FastAPI — desktop-facing (api)
│   │   ├── main.py
│   │   ├── dependencies.py
│   │   ├── middleware.py
│   │   └── routers/{health,activation,licenses,devices}.py
│   └── web/                  # Flask — admin portal (web)
│       ├── app.py
│       ├── extensions.py
│       ├── auth/ dashboard/ organizations/ users/ licenses/ devices/ audit/
│       ├── templates/ static/
├── src/licensing/            # shared domain package, imported by both apps
│   ├── config.py database.py exceptions.py
│   ├── models/ schemas/ repositories/ services/ security/ licensing/ audit/
├── migrations/                # Alembic
├── tests/{unit,integration,security}/
├── scripts/{create_admin,generate_signing_key,seed_development}.py
├── docker/  nginx/  docs/
├── alembic.ini  compose.yaml  pyproject.toml  .env.example
```

## API endpoint table (`/api/v1`, FastAPI — `api`)

| Method | Path | Auth | Purpose | Phase |
|---|---|---|---|---|
| GET | `/health/live` | none | liveness | A |
| GET | `/health/ready` | none | readiness (checks DB) | A |
| POST | `/activations` | none (rate-limited) | start activation, returns user code + verification URL | D |
| GET | `/activations/{id}` | none (rate-limited) | poll status; does not leak unrelated org/user existence | D |
| POST | `/activations/{id}/complete` | activation must be `approved` | submit device public key, receive signed license | D |
| POST | `/licenses/refresh/challenge` | device_id known | issue single-use renewal nonce | E |
| POST | `/licenses/refresh` | Ed25519 signature over nonce | verify + reissue signed license | E |
| GET | `/organizations/{org_id}/devices` | management session, org-scoped | list org devices | D/E |
| POST | `/devices/{device_id}/revoke` | management session, org-scoped | revoke device | E |
| POST | `/devices/{device_id}/replace` | management session, org-scoped | mark replaced, allow new activation | E |
| GET | `/licensing/public-keys` | none | active + still-needed retired public keys | A/D |

## Flask management-portal page map (`web`)

| Section | Routes (indicative) | Phase |
|---|---|---|
| Auth | `/login`, `/logout`, `/account/password` | B |
| Dashboard | `/` — orgs, licenses, seats, devices, activity, expiring, security events | C |
| Organizations | `/organizations`, `/organizations/new`, `/organizations/<id>` (edit/disable/memberships/licenses/devices/audit) | C |
| Users | `/users`, `/users/new`, `/users/<id>` (disable/reactivate/reset-password/memberships/seats/devices/security) | C |
| Licenses | `/organizations/<id>/licenses/new`, `/licenses/<id>` (suspend/revoke/renew/certificates) | C |
| Seats | `/licenses/<id>/seats` (assign/remove) | C |
| Devices | `/organizations/<id>/devices`, `/devices/<id>` (revoke/replace) | D/E |
| Signing keys | `/signing-keys` (read-only metadata; generation is CLI-only) | A/F |
| Audit | `/audit` (filter by date/org/user/event/target) | F |

## Sequence diagrams

See [`docs/sequences.md`](docs/sequences.md) for the full Mermaid activation
and renewal sequences (summary: browser-based device-code activation flow;
challenge-response renewal using the device's Ed25519 keypair — no
password re-entry).

## Cryptographic format decision

**Ed25519**, canonical JSON (sorted keys, no whitespace, UTF-8) as the signed
byte string, versioned envelope `{envelope_version, payload, signature,
key_id}`. Full rationale and test-vector strategy: [`docs/license-format.md`](docs/license-format.md).

## Threat model summary

Covers license-file copying, device-key copying/duplicate registration,
activation-code guessing/replay, payload tampering, refresh replay, stolen
admin sessions, cross-org access, DB compromise, signing-key compromise,
malicious clients, and the honest limits of offline enforcement. Full table:
[`docs/threat-model.md`](docs/threat-model.md).

## Implementation phases

This repo is built in the vertical phases specified for this project:
**A** foundation → **B** management auth → **C** orgs/licenses/seats
→ **D** activation → **E** renewal/revocation → **F** hardening.

### Phase A scope

* Repo/package structure as above.
* `src/licensing/config.py` — environment-based settings.
* `src/licensing/database.py` — SQLAlchemy 2.x engine/session (Psycopg 3),
  works against PostgreSQL.
* `src/licensing/models/*` — full normalized schema from the spec (users,
  organizations, memberships, products, editions, features, edition_features,
  organization_licenses, license_seat_assignments, device_activations,
  activation_requests, issued_license_certificates, signing_keys,
  audit_events, refresh_challenges) with the DB-level constraints described
  in `docs/database-erd.md`.
* Alembic wired to the models.
* `src/licensing/licensing/canonical.py` + `src/licensing/security/signing.py`
  — canonical serialization and Ed25519 sign/verify, with test vectors.
* FastAPI (`apps/api`) with `/health/live` and `/health/ready`
  (DB check); `devices.py` router remains a not-yet-implemented stub for
  Phase E.
* Flask (`apps/web`) app-factory skeleton with extensions wired
  (DB session, CSRF, security headers). Full RBAC/dashboard/org/user/license
  management screens remain Phase B/C.
* Docker Compose: postgres + api + web + nginx, with
  health checks and a persistent volume; migration and admin-creation
  commands documented.
* `scripts/generate_signing_key.py`, `create_admin.py`, and
  `seed_development.py` are all fully implemented.

### Activation slice (pulled forward from Phase D)

* `src/licensing/services/{activation,seats,devices,issuance,signing_keys}.py`
  — start/approve/complete activation, transactional seat assignment, device registration with duplicate-key and
  device-limit enforcement, certificate issuance, and public-key listing.
* `apps/api/routers/activation.py` — `POST /activations`,
  `GET /activations/{id}`, `POST /activations/{id}/complete`.
* `apps/api/routers/licenses.py` — `GET /licensing/public-keys`.
* `apps/api/error_handlers.py` — maps domain exceptions
  (`src/licensing/exceptions.py`) to HTTP status codes centrally.
* `apps/web/auth/` — minimal email/password login (Argon2id,
  session cookie, CSRF), just enough to gate the approval page below. Full
  RBAC/account-lifecycle screens are still Phase B.
* `apps/web/activate/` — the browser-side approval page: shows the
  device's user code, lists the signed-in user's organizations with an
  active license for the requested product, and approves on submit.
* `scripts/seed_development.py` now also seeds a demo organization, user,
  active professional license, and seat (see "Verifying activation end to
  end" below).

### Verifying activation end to end

```powershell
docker compose up -d
docker compose run --rm tools alembic upgrade head
docker compose run --rm tools python scripts/generate_signing_key.py --key-id dev-key-2026 --out-dir ./secrets
docker compose run --rm tools python scripts/seed_development.py --key-id dev-key-2026 --public-key-file secrets/dev-key-2026.public.b64
```

This seeds a demo org (`demo-org`) with an active `deepvac-insight`
professional license (5 seats) and a portal login: `demo@example.com` /
`DemoPass123!` at `http://localhost:8080/login`. Run the sibling `insight`
app (`python main.py` there) — its **Activate this installation** window
opens `http://localhost:8080/activate?user_code=...`; sign in with the demo
login and approve. The desktop app finishes activation automatically and
caches a verified license under `data/license/`. See `../insight/README.md`
("Cloud licensing (device activation)") for the desktop side.

* Test infra: pytest config, fixtures for a real Postgres test database,
  unit tests for models constraints and for canonical signing/verification
  (including tamper and wrong-key-rejection test vectors), and a first
  privacy-boundary static check.
* Ruff + mypy configuration.
* User-code format for activation: 8 uppercase-alphanumeric characters
   (Crockford-safe alphabet, excludes ambiguous characters) grouped as
   `XXXX-XXXX`, hashed with SHA-256 + server-side pepper (not Argon2id —
   Argon2id's deliberate slowness is unnecessary and counterproductive for a
   high-volume polling lookup; the code's entropy plus rate limiting is the
   actual defense, matching the "constant-time comparison" requirement via
   a hash-then-compare lookup).
* Session storage for Flask uses signed cookies (Flask's built-in,
   itsdangerous-based) rather than server-side sessions, since Redis is
   deliberately deferred; this is revisited if session revocation-on-demand
   becomes a hard requirement (noted as a Phase F candidate improvement).
