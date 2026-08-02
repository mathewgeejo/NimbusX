# NimbusX API

The API is versioned under `/v1`. It uses JSON, explicit UTC-offset timestamps, SI units, and stable error envelopes. OpenAPI is available from a running API at `/docs` and `/openapi.json`.

## Create an analysis

`POST /v1/analyses` returns `202 Accepted`.

```json
{
  "site": {
    "name": "Example facility",
    "latitude": 40.7128,
    "longitude": -74.006,
    "timezone": "America/New_York"
  },
  "window": {
    "start": "2032-07-15T09:00:00-04:00",
    "end": "2032-07-15T17:00:00-04:00"
  },
  "mode": "baseline",
  "asset": {
    "template": "facility",
    "exposure": { "criticality": 3 },
    "vulnerability": { "backup_power": true }
  },
  "thresholds": {
    "extreme_heat_c": 35,
    "heavy_precipitation_mm": 25,
    "wind_speed_m_s": 15
  },
  "baseline": { "start_year": 1991, "end_year": 2020 },
  "scenarios": ["ssp126", "ssp245", "ssp585"]
}
```

Pass either an inline `site` or a previously stored `site_id`, never both. A timezone must be an IANA identifier; start and end values must include an explicit UTC offset. `auto` selects only a scientifically appropriate mode.

Example response:

```json
{
  "id": "2d450b53-2aae-4475-b65b-ff1f8f3dd63f",
  "status": "queued",
  "mode": "baseline",
  "created_at": "2026-08-02T10:00:00Z"
}
```

## Read results and evidence

- `GET /v1/analyses/{id}` returns the assessment lifecycle status and, after processing, findings, decision, limitations, evidence IDs, and data gaps.
- `GET /v1/analyses/{id}/evidence` returns browser-safe, content-hashed source-manifest metadata. Raw extracts and normalized time series are not sent to browser clients and are only process-local in this foundation.
- `POST /v1/analyses/{id}/compare` lists up to ten selected terminal assessment summaries. It does not calculate an aligned change, delta, or ranking by window, site, baseline, or scenario yet.
- `GET /v1/analyses/{id}/report?format=json|csv` exports the structured assessment. PDF signing/rendering belongs in the production artifact service.

A finding includes a hazard name, threshold event definition, operator, unit, sample size or source basis, likelihood where scientifically valid, calibration status, recommendation, evidence IDs, and limitations. V1 always suppresses asset-risk verdicts as `insufficient_evidence` until a published template-specific exposure, vulnerability, consequence, and decision policy exists.

## Projects and sites

- `GET /v1/projects`
- `POST /v1/projects`
- `POST /v1/projects/{project_id}/sites`
- `GET /v1/projects/{project_id}/analyses`

An analysis created with a stored site inherits that site's project; an inline site must provide `project_id` to be associated. Polygon geometries may be stored for a future spatial workflow but are rejected for V1 analysis until a source-backed spatial aggregation adapter exists. The foundation uses development-scoped in-memory storage. Production deployments must back these endpoints with organization-scoped Postgres/PostGIS and authorization.

## Error envelope

```json
{
  "error": {
    "code": "provider_unavailable",
    "message": "NASA POWER Daily API could not be reached; no substitute data was used",
    "details": { "provider": "NASA POWER" },
    "request_id": "..."
  }
}
```

Validation errors, provider outages, and unavailable horizon sources must be explicit. Clients must not infer missing values or retry a non-retryable request indefinitely.

## Legacy endpoint

`POST /api/weather` exists only as a deprecated development adapter during migration. Its configured fixed Sunset timestamp is exposed in the HTTP `Sunset` header; after that timestamp the endpoint returns `410`. New clients must use `/v1` and must not rely on its old probability schema.
