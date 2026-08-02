# NimbusX architecture

NimbusX is an evidence-first climate-risk workspace. It keeps observations,
operational forecasts, seasonal outlooks, historical baselines, and climate
scenarios separate rather than presenting them as the same kind of prediction.

## Current foundation

```text
React + TypeScript workspace
  -> FastAPI v1 control-plane API
      -> in-process development job store
          -> NASA POWER Daily adapter
              -> normalized daily observations
                  -> deterministic hazard engine
                      -> content-hashed evidence manifest
```

The runnable foundation supports two source-backed paths:

- `observed`: daily NASA POWER source values for a completed local window;
- `baseline`: empirical event-window frequencies over a requested daily
  historical baseline period.

`forecast`, `seasonal`, and `scenario` remain explicit `partial` results because
their source adapters and required calibration/projection artifacts are not
implemented in this foundation. Credentials alone do not enable them. NimbusX
does not replace any of those modes with a climatology, a synthetic value, or an
uncalibrated probability.

The development repository is process-local and resets on restart. It is not a
multi-user, tenant-isolated, or production persistence implementation.

## Target production design

```text
Browser workspace
  -> authenticated control plane
      -> durable job queue
          -> hosted worker OR customer-VPC data plane
              -> provider adapters -> normalized data -> hazard engine
                  -> encrypted raw artifacts + content-hashed manifest
                      -> immutable report version + audit record
```

Before production is enabled, the control plane needs OIDC claims, role
authorization, organization-scoped PostgreSQL/PostGIS with row-level security,
a durable queue/cache, tenant-segregated object storage, and immutable report
versioning. The current process refuses `NIMBUSX_ENV=production` so these
requirements cannot be mistaken for completed work.

## Evidence boundary

An evidence manifest records provider, dataset/model version, query parameters,
units, resolution, retrieval time, attribution/license, source content hash,
and data-quality warnings. Browser-facing evidence responses expose that
manifest metadata only. In the current development repository, raw provider
payloads and normalized time series exist only in process memory and are lost on
restart. A production artifact service must create and authorize any durable,
controlled download.

## Private data plane maturity

The supplied Helm chart is intentionally a **heartbeat scaffold**, not a job
worker. It mounts an existing mTLS Secret and sends metadata-only, outbound
heartbeats. It does not claim signed jobs, fetch provider data, transmit raw
series, or return derived findings yet.

A deployable private plane requires a reviewed signed-job protocol, idempotent
claim handling, customer-owned encrypted artifact storage, tenant-bound
credentials, provider-specific egress policy, and encrypted derived-result
returns. Until then, no customer raw data should be routed through the chart.