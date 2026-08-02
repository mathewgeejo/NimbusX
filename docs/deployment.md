# Deployment guide

## Local development stack

1. Copy `.env.example` to `.env`.
2. Run `docker compose up --build`.
3. Open the workspace at `http://localhost:8080`, API docs at
   `http://localhost:8000/docs`, and health at `http://localhost:8000/healthz`.

Compose starts PostgreSQL and Redis to make the intended service boundaries
visible, but the current API uses an in-process repository and background task
runner. Restarting the API loses projects, sites, analyses, and evidence. Do
not mistake the local stack for a database migration or durable queue.

## Production status

Production deployment is intentionally disabled in this foundation. The API
rejects `NIMBUSX_ENV=production` until OIDC/roles, tenant-scoped
PostgreSQL/PostGIS with row-level security, durable jobs/caches, encrypted
artifact storage, and audit controls are implemented and tested.

The included Dockerfiles use the minimal hash-locked runtime dependency set. Their base-image tags are still development scaffolding rather than immutable production artifacts. Pin images by digest, scan images, and deploy only after the production controls above exist.

## Private data plane

The Helm chart deploys only the outbound mTLS heartbeat scaffold described in
[the hybrid guide](hybrid-data-plane.md). It cannot process private assessment
jobs or persist customer artifacts. Configure a Secret containing `tls.crt` and
`tls.key`, an explicit heartbeat URL, a data-plane ID, and approved egress
rules before installing it. Do not send customer raw data to the scaffold.