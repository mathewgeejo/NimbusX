# Source adapter contracts

NimbusX separates an adapter's local implementation state from remote source
availability. A health view must not make an undisclosed network request or
claim that a provider is currently available merely because its adapter can be
imported.

`nimbusx.source_catalog.source_health_payload()` is the route-ready helper for
`GET /v1/sources/health`. It reports one record per registered source:

- `implementation`: whether NimbusX has an adapter capable of returning that
  source's normalized output;
- `status`: `not_checked`, `unavailable`, or `degraded`;
- `remote_probe_policy`: whether remote availability is evaluated during a
  real retrieval, only by an explicit probe, or is not applicable;
- the evidence fields that a future adapter must retain; and
- declared limitations.

The registry is deliberately non-networked. NASA POWER is therefore
`implemented` but `not_checked`: a real assessment retrieval establishes
whether it is reachable. Forecast, seasonal, scenario, flood, wildfire, and
water-stress adapters are explicitly `unavailable` until they are installed.

## Immutable evidence contract

Every normalized dataset must carry an `EvidenceRecord` with a SHA-256 content
hash, provider, dataset, retrieval timestamp with UTC offset, source query,
units, resolution, licence, and attribution. Individual source descriptors may
also require model/layer version and query fields. An adapter cannot return a
dataset that fails its evidence contract.

The raw extract may remain inside a customer data plane or object store, but
the browser-facing manifest must preserve its content hash and provenance. A
missing source is a data gap; it is never replaced with climatology, a random
value, an unlabeled proxy, or a confidence score.

## Operational forecast contract

An operational forecast adapter returns explicit source members, each with:

- a member ID;
- initialization and valid timestamps with offsets;
- source variable values; and
- an evidence manifest identifying run, valid coverage, parameters, and model
  version.

Only an ensemble with at least two unique members can support an
ensemble-member exceedance probability. A deterministic high-resolution product
may still be useful operational evidence, but it cannot be relabelled as a
probability.

## Seasonal outlook contract

A seasonal output carries target coverage, member count, its primary evidence,
and a calibration artifact. `calibrated` requires a retained hindcast period,
method, skill metric/value, and evidence IDs; a non-positive skill value cannot
be marked decision-eligible. `insufficient_skill` and `unavailable` remain
valid outputs, but must suppress a decision verdict.

## Scenario projection contract

A scenario range has a named SSP, one of the 2030s/2050s/2080s target periods,
a variable/unit, at least two unique climate-model IDs, and ordered lower,
central, and upper values. The current contract retains the requested 1991–2020
comparison baseline. It represents a multi-model scenario range—not a daily
weather forecast.

## Spatial exposure contract

Flood, wildfire, and water-stress are separate source-layer capabilities. A
spatial adapter must retain a source evidence manifest, the queried site's
geometry hash, a declared exposure layer kind, and source metrics/units. These
metrics are exposure evidence, not an asset-risk probability or decision. A
published exposure, vulnerability, consequence, and decision policy is still
required before it can affect an asset verdict.

## Integration checklist

Before enabling an unavailable adapter:

1. Add authenticated/licensed retrieval and provider rate-limit handling.
2. Normalize source timestamps and SI units into the typed contract.
3. Persist raw extracts or customer-side references before publishing derived
   findings.
4. Add fixed raw-response fixtures plus contract, outage, cache-expiry, and
   calibration/backtest tests.
5. Register the adapter in the source catalog and expose its limitations in the
   source-health endpoint.
6. Enable any decision logic only after the documented calibration and
   exposure/vulnerability policy gates pass.
