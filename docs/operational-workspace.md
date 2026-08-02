# Operational workspace

NimbusX now has a project-level operational workspace for built assets. It is
designed to turn a completed, source-backed hazard assessment into an
inspectable screening workflow without inventing an asset-risk score or
pretending that an alert is a forecast.

## What runs today

1. Create a project and point site with an explicit IANA time zone.
2. Choose a versioned built-asset template and record its declared exposure
   and vulnerability fields.
3. Run an observed or historical-baseline assessment against that saved asset.
4. Inspect the linked hazard findings and deterministic template screening
   results.
5. Create an alert rule, then explicitly evaluate it against completed
   assessments.
6. Optionally create a reviewed notification target and record a dry-run
   delivery receipt containing only the alert event and its evidence IDs.

The foundation contains templates for campuses, data centres, warehouses,
healthcare facilities, industrial facilities, and solar sites. Template rules
are versioned and visible to clients. Their result is one of:

| Operational result | Meaning |
| --- | --- |
| `action_required` | A completed source-backed finding met the declared template rule and all required context fields were supplied. It asks for the named human review action. |
| `monitored` | A usable source-backed finding did not meet the rule threshold. |
| `insufficient_context` | Required exposure or vulnerability fields are missing. No action is inferred. |
| `source_unavailable` | The requested hazard has no usable source-backed finding. |

These are screening/control outcomes, not loss estimates, emergency orders,
regulatory findings, or a general asset-risk verdict. The assessment-level
decision remains `insufficient_evidence` until NimbusX has a published
template-specific exposure, vulnerability, consequence, and decision policy.

## Project API

| Endpoint | Purpose |
| --- | --- |
| `GET /v1/asset-templates` | View versioned templates, required context, supported hazards, and published screening rules. |
| `GET/POST /v1/projects/{project_id}/assets` | Register/list asset records linked to a saved point site. |
| `POST /v1/projects/{project_id}/assets/import` | Validate or create CSV / Point GeoJSON assets with individual row outcomes. |
| `GET/POST /v1/projects/{project_id}/alert-rules` | List/create explicit evidence-triggered review rules. |
| `POST /v1/projects/{project_id}/alert-rules/{rule_id}/evaluate` | Evaluate named completed assessments; events are deduplicated by rule, assessment, and hazard. |
| `GET /v1/projects/{project_id}/alert-events` | Read immutable, evidence-linked alert events. |
| `GET/POST /v1/projects/{project_id}/notification-channels` | List/create reviewed delivery targets. Secret references are accepted but never returned. |
| `POST /v1/projects/{project_id}/alert-events/{event_id}/notification-channels/{channel_id}/dispatch` | Record a dry run or explicit unavailable-live-delivery receipt. It never makes an external request in this foundation. |
| `GET /v1/projects/{project_id}/alert-events/{event_id}/notification-receipts` | Inspect dispatch receipts and their small structured envelopes. |
| `GET /v1/sources/health` | See adapter implementation state without causing a hidden remote provider request. |

### Import contract

Asset CSV imports use a header row. A row needs either an existing `site_id`,
or `latitude`, `longitude`, and `timezone`; it also needs a `name` and either a
row `template_id` or `default_template_id`. Optional fields include
`site_name`, `address`, `external_id`, `criticality`, `tags`,
`exposure_json`, `vulnerability_json`, plus `exposure.field_name` and
`vulnerability.field_name` convenience columns.

GeoJSON imports must be a `FeatureCollection` of `Point` features. Polygon
geometry and address geocoding are deliberately not converted into an analysis
location because no source-backed spatial aggregation or geocoder is installed.
A `dry_run: true` request validates every row without writing a site or asset.

## Alert and notification controls

An alert rule can target:

- an observed threshold breach in a completed observed assessment;
- an empirical historical baseline likelihood at or above an explicit value;
- a completed finding severity at or above an explicit level.

The rule can be project-wide or bound to a single asset. It never evaluates a
queued job, unavailable finding, or an assessment from another project.

Notification targets are limited to email recipients and HTTPS webhook/Slack
URLs. The supplied `secret_reference` must use `secret://` and is retained only
internally in the process-local development store. The public API returns only
`has_secret_reference`. `dry_run` is the default and records no network call.
Selecting `live` returns an `unavailable` receipt until a reviewed dispatcher,
secret manager, durable retry queue, and delivery audit store are installed.

## Evidence and source boundaries

`GET /v1/sources/health` shows NASA POWER Daily as implemented but
`not_checked`, because the endpoint never performs an undisclosed network
probe. ECMWF Open Data, Copernicus seasonal, NEX-GDDP-CMIP6, and dedicated
flood/wildfire/water-stress exposure adapters disclose their required evidence
contracts but remain `unavailable` until a real retrieval integration exists.

Every completed assessment and alert event retains the source evidence IDs.
Report manifests retain the content hash and source metadata. In this
development foundation those records are process-local and disappear on API
restart; they are not a durable audit/archive system.
