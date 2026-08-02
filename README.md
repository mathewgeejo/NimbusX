# NimbusX

NimbusX is an evidence-first climate-risk workspace for built assets: facilities,
campuses, real estate, and infrastructure. It is designed to answer a
defensible question:

> What weather or climate hazards are supported by the available evidence for this site, time window, and risk threshold?

It does **not** manufacture forecasts from monthly climate normals, synthetic
data, untrained models, or hard-coded confidence scores.

## What is implemented

- A versioned FastAPI assessment API with typed requests, an async-style
  lifecycle, content-hashed provenance manifests, validation, and a deprecated
  legacy adapter.
- Explicit `observed`, `forecast`, `seasonal`, `baseline`, and `scenario`
  analysis modes. `seasonal` and `scenario` represent outlook/projection
  concepts; neither is presented as a daily forecast.
- A real NASA POWER Daily adapter for observed and baseline paths, with
  deterministic threshold-based hazard calculations.
- Clear `partial` and `unavailable` states for forecast, seasonal, and scenario
  modes, which are deliberately not implemented in this foundation.
- A React/TypeScript workspace for building assessments, reviewing evidence,
  comparing work, and exporting a report view.
- Docker, CI, and a Helm mTLS heartbeat scaffold. It is not yet a customer-VPC
  analysis worker.

## Scientific boundaries

| Mode | Appropriate claim |
| --- | --- |
| Observed / reanalysis | What was recorded, subject to source latency and coverage |
| Forecast (0–15 days) | Source-backed forecast threshold likelihood |
| Seasonal outlook | Broad, calibrated anomaly/risk outlook only |
| Baseline | Historical daily likelihood around a calendar window |
| Scenario projection | Conditional multi-model/SSP range, not a weather prediction |

NimbusX never substitutes synthetic weather when a provider fails. Missing
evidence is displayed as a data gap and can lead to an
`insufficient_evidence` decision.

## Quick start

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open the workspace at <http://localhost:8080>, the API documentation at
<http://localhost:8000/docs>, and health status at
<http://localhost:8000/healthz>.

For native development and troubleshooting, see [SETUP.md](SETUP.md).

## Architecture

```text
React/TypeScript workspace
  -> FastAPI control plane
      -> assessment orchestration
          -> hosted worker or customer-VPC data plane
              -> provider adapters -> normalized data -> hazard engine
                  -> content-hashed evidence manifest -> report
```

PostgreSQL/PostGIS, Redis-backed work/caching, and S3-compatible artifact
storage are the production target architecture. Local development intentionally
uses a process-local implementation, refuses production mode, and does not
claim multi-user durability or tenant isolation.

## Main API

```text
POST /v1/analyses
GET  /v1/analyses/{analysis_id}
GET  /v1/analyses/{analysis_id}/evidence
POST /v1/projects/{project_id}/sites
POST /v1/analyses/{analysis_id}/compare
GET  /v1/analyses/{analysis_id}/report
```

`POST /v1/analyses` returns `202` and an analysis ID. Poll its `GET` endpoint
until its status becomes `complete`, `partial`, or `failed`. See
[docs/API.md](docs/API.md), or use the interactive OpenAPI documentation
locally.

## Operational notes

- NASA POWER data is retrieved over HTTPS and recorded as source evidence. Cache requests and respect provider limits.
- NASA daily values are UTC aggregates. NimbusX uses a 12:00 UTC representative timestamp only to map a source label into an IANA calendar window, with guard days requested at range boundaries; it does not present that convention as a local civil-day measurement.
- Forecast, Copernicus seasonal, and climate-scenario retrieval are not
  implemented in this foundation. Those modes intentionally return an explicit
  unavailable result; credentials alone do not enable them.
- The frontend is not allowed to infer or embellish a missing metric. It
  renders the server status, limitations, sources, and evidence IDs.
- `POST /api/weather` has a fixed, configured migration deadline. After that
  timestamp it returns `410`; it never extends its own Sunset date.
- Optional AI narration is not part of the analysis engine. It must be
  tenant-approved, grounded in the structured result, and cite evidence IDs.

Further documentation:

- [Architecture](docs/architecture.md)
- [Science and data policy](docs/science-and-data-policy.md)
- [Hybrid data-plane guide](docs/hybrid-data-plane.md)

## Legacy materials

The retired hackathon implementation, its synthetic-model code, and its old
demo material live in [archive/hackathon-prototype](archive/hackathon-prototype).
They are historical artifacts only and must not be used as product or
scientific documentation.

## License

[MIT](LICENSE)