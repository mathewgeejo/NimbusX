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
- `GET /v1/analyses/{id}/report?format=json|csv|manifest` exports the structured assessment or its evidence/report manifest. PDF signing/rendering belongs in the production artifact service.

A finding includes a hazard name, threshold event definition, operator, unit, sample size or source basis, likelihood where scientifically valid, calibration status, recommendation, evidence IDs, and limitations. V1 always suppresses asset-risk verdicts as `insufficient_evidence` until a published template-specific exposure, vulnerability, consequence, and decision policy exists.

## Projects and sites

- `GET /v1/projects`
- `POST /v1/projects`
- `POST /v1/projects/{project_id}/sites`
- `GET /v1/projects/{project_id}/analyses`

An analysis created with a stored site inherits that site's project; an inline site must provide `project_id` to be associated. Polygon geometries may be stored for a future spatial workflow but are rejected for V1 analysis until a source-backed spatial aggregation adapter exists. The foundation uses development-scoped in-memory storage. Production deployments must back these endpoints with organization-scoped Postgres/PostGIS and authorization.

## Assets and operational screening

- `GET /v1/asset-templates` returns versioned built-asset templates, their
  required exposure/vulnerability fields, supported hazards, and published
  screening rules.
- `GET/POST /v1/projects/{project_id}/assets` lists or registers an asset
  linked to a saved project point site.
- `POST /v1/projects/{project_id}/assets/import` accepts either `csv_text` or a
  Point-only GeoJSON `FeatureCollection`; set `dry_run: true` to validate rows
  without writing records.

An assessment submitted with `asset_id` inherits that asset's site and retains
the template's source-linked operational findings. These outcomes are
screening controls (`action_required`, `monitored`, `insufficient_context`, or
`source_unavailable`), not asset-risk verdicts. Missing context never becomes
an action.

## Alerts and safe notification rehearsal

- `GET/POST /v1/projects/{project_id}/alert-rules` manages explicit rules for
  observed threshold breaches, historical baseline likelihood, or finding
  severity.
- `POST /v1/projects/{project_id}/alert-rules/{rule_id}/evaluate` evaluates
  selected terminal project assessments and creates deduplicated,
  evidence-linked events.
- `GET /v1/projects/{project_id}/alert-events` lists recorded events.
- `GET/POST /v1/projects/{project_id}/notification-channels` lists or creates
  email/HTTPS webhook/Slack-compatible targets. A `secret_reference` must use
  `secret://` and is never returned in the public response.
- `POST /v1/projects/{project_id}/alert-events/{event_id}/notification-channels/{channel_id}/dispatch`
  records a dry run by default. The foundation makes no external request. A
  channel configured as `live` returns an explicit `unavailable` receipt until
  a reviewed dispatcher, secret manager, retry queue, and durable audit store
  exist.
- `GET /v1/projects/{project_id}/alert-events/{event_id}/notification-receipts`
  returns the immutable local dispatch-receipt history.

Alert events are not forecasts, emergency actions, or proof that a message was
delivered.

## Source catalog

`GET /v1/sources/health` exposes adapter implementation and local health
disclosure without making hidden provider calls. It must not be treated as a
remote availability probe. NASA POWER Daily is configured but `not_checked`
until an assessment retrieval; forecast, seasonal, scenario, and spatial
exposure sources explicitly report `unavailable` until their real adapters are
installed.

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
