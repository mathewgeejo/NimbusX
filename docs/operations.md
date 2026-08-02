# Operations guide

## Foundation health and readiness

- `GET /healthz` verifies that the API process is alive.
- `GET /readyz` reports the explicit development-state limitation: in-memory persistence and background work. It is configuration-only and does not probe NASA POWER reachability or freshness.
- Source provider availability belongs in an analysis result and evidence manifest; a temporary NASA outage is not hidden behind a fake value.

## Current operational boundary

This repository does not yet emit production telemetry, retain durable artifacts,
or operate a production worker queue. The following list is a production
runbook target, not evidence that those controls are active:

- request rate, error rate, latency, and rate-limit rejections;
- analysis lifecycle counts by status and horizon mode;
- provider request latency, failure rate, response freshness, and cache hit rate;
- source/data gaps by provider, hazard, region, and tenant;
- report generation success, artifact retention, and audit-log write failures;
- forecast calibration metrics: sample count, Brier score, Brier skill,
  reliability, and decision-suppression rate.

## Required production incident behavior

A production deployment must preserve an immutable evidence/report version for a
completed assessment, mark new work `partial` or `failed` when an approved
provider is unavailable, disable malformed/stale adapters, and roll back API
and web images together with their OpenAPI compatibility version. The local
foundation cannot provide these durability guarantees because its repository
resets on restart.

## Required production retention controls

Organizations must configure retention for raw extracts, artifacts, analysis
metadata, and audit events. In a private data plane, raw provider extracts and
private asset attributes must remain in customer-owned storage unless an
organization explicitly permits synchronization. These policies depend on the
future durable storage and authorization implementation.