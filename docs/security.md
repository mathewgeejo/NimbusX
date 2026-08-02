# Security guide

## Implemented foundation controls

- Provider URLs must use HTTPS.
- CORS accepts only an explicit allow-list; wildcard origins are rejected.
- The API emits structured error envelopes with correlation IDs.
- A process-local rate limiter protects development requests.
- `NIMBUSX_REQUIRE_API_KEY` can protect a local or test API with constant-time
  comparison. It is not a substitute for user identity or authorization.
- Browser-facing evidence omits raw provider payloads and normalized time
  series; it exposes content-hashed provenance metadata instead.
- Notification targets are constrained to email recipients or HTTPS
  webhook/Slack-compatible URLs. A secret-manager reference must use
  `secret://`; it is retained internally and never returned by the API.
- Notification dispatch is a local dry run or an explicit unavailable result;
  this repository contains no outbound delivery client.
- The private-plane chart runs as non-root, drops Linux capabilities, mounts
  mTLS material read-only, disables service-account token mounting, defaults
  to deny-all Kubernetes ingress/egress, and requires a successful
  metadata-only mTLS heartbeat before reporting Ready.

## Explicit non-production boundary

This foundation does **not** implement OIDC, memberships, organization roles,
row-level tenant isolation, Postgres persistence, durable queueing, or
production artifact storage. `NIMBUSX_ENV=production` therefore fails startup.
Do not infer tenant isolation from `X-Organization-ID`; that development header
is not a trusted identity claim.

## Requirements before production enablement

- OIDC/JWT validation tied to `admin`, `analyst`, `reviewer`, and `viewer`
  memberships.
- Organization-scoped PostgreSQL/PostGIS repositories with enforced row-level
  security on every tenant-owned table.
- Durable worker queue, encrypted tenant-segregated object storage, and
  immutable evidence/report version records.
- Secret-manager references for provider credentials, mTLS materials, and
  database passwords; never commit production values to `.env`.
- Per-principal and per-IP limits, security telemetry, audit completeness,
  dependency/image scanning, and incident procedures.
- A reviewed outbound notification dispatcher with secret retrieval, SSRF
  defenses, tenant-bound allow-lists, idempotency keys, retry/dead-letter
  handling, delivery receipts, and immutable audit records.

## Optional narration

Narration is disabled by default. If enabled later, send only an approved
structured assessment and evidence IDs to the selected model. Validate the
returned schema, display its cited evidence IDs, and reject prose that adds an
unsupported number, confidence value, source, or recommendation.
