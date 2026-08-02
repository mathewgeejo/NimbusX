# Science and data policy

## Non-negotiable rules

1. Never emit synthetic weather or random fallback values.
2. Never call a climatological result an exact-date forecast.
3. Never turn model disagreement, missing data, or a hard-coded constant into a confidence percentage.
4. Define every probability as a specific threshold event and preserve the source/model population used to calculate it.
5. Keep raw source data, transformed data, outputs, and data-quality warnings traceable through an evidence manifest.
6. Use generative AI only for optional, grounded prose; it cannot calculate, alter, or invent findings.

## Implemented V1 hazard definitions

- **Extreme heat:** daily/event-window maximum temperature at or above the configured threshold.
- **Extreme cold:** daily/event-window minimum temperature at or below the configured threshold.
- **Heavy precipitation:** daily/event-window accumulated precipitation at or above the configured threshold.
- **Wind:** the maximum, across the event window, of NASA POWER's daily-mean 10 m WS10M value. It is not a gust, peak-wind, sustained-wind, or site-scale operating-wind measurement.
- **Drought:** an event-window precipitation threshold for windows of at least 14 days. It is a limited screening metric, not a full hydrological drought assessment.

## Implemented calculations

- **Observed:** source daily values for a completed window. No probability is reported.
- **Baseline:** empirical exceedance rate across complete daily historical windows around the requested calendar date. It reports sample count and baseline period. The displayed V1 screening severity is deterministic and transparent: `low` below 10%, `moderate` from 10% to below 25%, and `high` at or above 25%. These labels describe threshold-event frequency only; they are not a calibrated asset-risk score or a decision verdict.

V1 records optional asset context but suppresses all asset-risk verdicts as `insufficient_evidence` until a published template-specific exposure, vulnerability, consequence, and decision policy exists.

Daily NASA POWER values are explicitly requested in UTC. NimbusX assigns each
aggregate a 12:00 UTC representative timestamp only to select an IANA calendar
label, and queries one guard day on each range boundary. The source’s daily
aggregation boundary remains UTC-defined; this foundation does not claim a
conversion to local civil-day measurements or sub-daily local-calendar precision.

## Planned, unavailable modes

- **Forecast:** requires ECMWF ensemble retrieval and a provider-supported threshold probability calculation.
- **Seasonal outlook:** requires Copernicus retrieval plus local hindcast calibration and skill suppression.
- **Scenario projection:** requires NASA NEX-GDDP-CMIP6 model extracts, future time slices, and multi-model/SSP ranges.

Until the relevant source adapter and validation artifacts exist, each mode
returns `partial`/`unavailable`. NimbusX does not substitute a baseline,
climatology, or guessed probability.

## Production quality and calibration requirements

Before a forecast or seasonal decision can be enabled, forecast skill must be
evaluated with rolling held-out backtests and published by hazard, region, and
lead-time bucket. Brier score, Brier skill relative to climatology, reliability
diagrams, coverage, and sample sizes must be retained as evidence artifacts. A
decision verdict must be suppressed when calibration is unavailable or fails the
configured policy. These controls are target requirements, not active foundation
features.