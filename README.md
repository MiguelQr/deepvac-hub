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
| GET | `/licensing/public-keys` | none | active + still-needed retired public keys | A/D |

Phase D is the FastAPI surface's final state: licenses are lifetime grants
issued once at `/activations/{id}/complete`, so there is deliberately no
renewal endpoint (`/licenses/refresh*`) and no device management endpoint
(`GET /organizations/{org_id}/devices`, `/devices/{id}/revoke`,
`/devices/{id}/replace`) — see "Phase D scope" below and
`docs/threat-model.md`.

## Flask management-portal page map (`web`)

| Section | Routes (indicative) | Phase |
|---|---|---|
| Auth | `/login`, `/logout`, `/account/password` | B |
| Dashboard | `/` — orgs, licenses, seats, devices, expiring soon | C |
| Organizations | `/organizations`, `/organizations/new`, `/organizations/<id>` (edit/disable/memberships/licenses/devices) | C |
| Users | `/users`, `/users/new`, `/users/<id>` (disable/reactivate/reset-password/memberships/seats/devices/security) | C |
| Licenses | `/organizations/<id>/licenses/new`, `/licenses/<id>` (read-only overview, seats, certificates) | C |
| Seats | `/licenses/<id>/seats` (assign/remove) | C |
| Devices | read-only, inline on organization/user detail pages | C |
| Signing keys | `/signing-keys` (read-only metadata; generation is CLI-only) | A/F |
| Audit | `/audit` (filter by date/org/user/event/target) | F |

No standalone `/devices` page and no suspend/revoke/renew actions on
licenses: see "Phase D scope" below for why.

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
→ **D** activation → **F** hardening.

**Phase E (renewal/revocation) is deliberately dropped, not deferred.**
Licenses in this product are lifetime grants for an organization and
everyone in it — not subscriptions — so there is no periodic renewal
check-in and no device revoke/replace flow. See "Phase D scope" below and
`docs/threat-model.md` for what that trades away.

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

### Phase B/C scope

* `src/licensing/services/auth.py` — the authorization core: `require_vendor`
  (any vendor role for read, `vendor_super_admin` for write),
  `require_org_view`/`require_org_admin` (vendor staff may view any
  organization; `organization_admin`/`organization_member` only their own,
  via an active `OrganizationMembership`). Every org/user/license service
  function authorizes through this module before touching data — see
  `docs/threat-model.md` threat #9.
* `src/licensing/services/{organizations,users,licenses,dashboard}.py` —
  organization lifecycle and membership management, the vendor-managed user
  directory, license creation plus org-scoped seat assignment (delegates
  locking to the existing `services/seats.py`), and dashboard summary
  counts. (Originally this also had suspend/reactivate/revoke/renew license
  actions; removed in Phase D once licenses became lifetime grants — see
  "Phase D scope" below.)
* `apps/web/{dashboard,organizations,users,licenses}/` — the rest of the
  admin portal: dashboard (vendor-only summary + licenses expiring soon),
  organizations (list/create/detail with memberships/licenses/devices
  sections), users (vendor-only directory, disable/reactivate/password
  reset/vendor-role grant), licenses (create under an org, seat
  assign/remove, read-only certificate list). `vendor_support` gets
  read-only access everywhere; write actions require `vendor_super_admin`
  or (for org-scoped actions) that org's `organization_admin`.
* `apps/web/auth/` — `/account/password` self-service change added; login
  converted to a `FlaskForm`; session gains a sliding idle timeout
  (`SESSION_IDLE_TIMEOUT_MINUTES`, default 60) on top of the existing 8h
  absolute lifetime.
* `apps/web/errors.py` — centralized 403/404 handling for
  `PermissionDeniedError`/`NotFoundError`, sharing a status map
  (`licensing.exceptions.EXCEPTION_STATUS_MAP`) with `apps/api/error_handlers.py`
  so the two surfaces can't drift. Business-logic errors (validation,
  conflicts, seat limits) stay inline per route via flash messages, matching
  the pattern already established by `apps/web/activate/routes.py`.
* Admin-initiated password reset sets the new password directly (no forced
  change flow, no email dependency — this app has no mail sender).
* Audit events are recorded for every write action (org/user/license/
  membership/seat lifecycle changes) via the existing `licensing.audit.record_event`
  and its metadata allow-list, which already covered everything needed with
  no changes.
* Deliberately deferred to Phase F: the filterable `/audit` page — org/user
  detail pages surface no audit data in the meantime.
* Tests: `tests/factories.py` (shared builders), a `flask_client` fixture
  (joins the Flask app's session to the same per-test transactional
  connection as `db_session` via SQLAlchemy's `join_transaction_mode="create_savepoint"`,
  so `db.commit()` calls in routes don't end the test's outer transaction),
  unit tests per new service, integration tests per new blueprint, and
  `tests/security/test_cross_org_access.py` — the explicit cross-org/role
  enforcement test threat #9 calls for.

### Phase D scope

Device-code activation itself (`POST /activations`, `GET /activations/{id}`,
`POST /activations/{id}/complete`, `GET /licensing/public-keys`) already
shipped as part of the Phase A/D pull-forward (see above) — Phase D's
remaining work was a product decision and its consequences, prompted by
re-auditing the sibling `../insight` desktop client for protocol
compatibility:

* **Compatibility audit result: no drift.** Insight's
  `app/services/licensing_client.py` was read end-to-end against this repo's
  actual FastAPI schemas/routes — request/response field names, the
  base64url device-key encoding, the canonical-JSON signing bytes
  (`sort_keys=True, separators=(",", ":")`), the `REQUIRED_PAYLOAD_KEYS`
  set, the activation status vocabulary (`pending/approved/denied/expired/consumed`),
  and the `{"detail": "..."}` error shape all match exactly. Insight also
  already has **zero** client code calling any renewal or device-revoke
  endpoint — confirming the "no Phase E" decision below doesn't remove
  anything the desktop app was relying on.
* **Licenses are lifetime grants, not subscriptions.** A device's issued
  certificate is valid for `OrganizationLicense.offline_validity_days` from
  issuance (default **36500 days, ~100 years** — was 14, sized for a
  renewal flow that's being dropped instead of built).
  `Settings.default_license_validity_days` (the fallback used if that field
  is ever falsy) was bumped the same way, so no code path can produce a
  short-lived certificate. This is a one-line-default change, not a
  formula change: certificate expiry is still `issued_at + offline_validity_days`,
  independent of the organization license's own `expires_at` — a lifetime
  grant shouldn't retroactively shrink if an admin later edits the license
  record.
* **Phase E (renewal/revocation) dropped, and so is the suspend/revoke/renew
  UI Phase C had added for organization licenses.** With lifetime
  certificates and no live check-in from the desktop app, a suspend/revoke
  action can only ever block *new* activations — it cannot pull back access
  already granted to an activated device, since insight never calls
  anything that would let it learn about that. Given that, the actions were
  removed rather than kept as a UI that implies more control than actually
  exists; a license's status is now set once at creation and read-only
  after. `apps/api/routers/devices.py` (a stub since Phase A, never
  implemented) was deleted outright — nothing calls it or ever would.
* `docs/threat-model.md`, `docs/sequences.md`, `docs/architecture.md`,
  `docs/database-erd.md`, and `docs/license-format.md` were updated to
  match — several threat mitigations previously described a renewal
  challenge-response flow as the enforcement backstop; those are rewritten
  to describe the actual (narrower) protection this system provides now,
  including the accepted residual risk: copying both `license.json` and
  the device's local private-key file clones a working install with no
  remote way to cut it off. `refresh_challenges` (table) and
  `RefreshChallenge` (model) are kept as inert, never-written schema rather
  than migrated out — same treatment as the now-unused
  `OrganizationLicenseStatus.SUSPENDED`/`REVOKED` enum values.
