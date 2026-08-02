"""Deterministic, source-backed V1 hazard calculations.

The baseline engine calculates an empirical event-window frequency.  It does
not transform a percentile into a probability, estimate a made-up confidence
score, or train an in-request model.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date

from .schemas import (
    AnalysisDecision,
    BaselinePeriod,
    CalibrationStatus,
    Decision,
    FindingStatus,
    HazardFinding,
    HazardThresholds,
    HazardType,
    NormalizedDailyObservation,
    Severity,
)

MINIMUM_BASELINE_SAMPLES = 10


@dataclass(frozen=True, slots=True)
class HazardOutcome:
    findings: list[HazardFinding]
    data_gaps: list[str]
    limitations: list[str]


@dataclass(frozen=True, slots=True)
class _HazardDefinition:
    hazard: HazardType
    metric: str
    threshold: Callable[[HazardThresholds], float]
    operator: str
    unit: str
    value: Callable[[list[NormalizedDailyObservation]], float | None]
    minimum_days: int = 1


def _all_values(records: list[NormalizedDailyObservation], attribute: str) -> list[float] | None:
    values = [getattr(record, attribute) for record in records]
    if any(value is None for value in values):
        return None
    return [float(value) for value in values if value is not None]


def _max_value(attribute: str) -> Callable[[list[NormalizedDailyObservation]], float | None]:
    def get(records: list[NormalizedDailyObservation]) -> float | None:
        values = _all_values(records, attribute)
        return max(values) if values else None

    return get


def _min_value(attribute: str) -> Callable[[list[NormalizedDailyObservation]], float | None]:
    def get(records: list[NormalizedDailyObservation]) -> float | None:
        values = _all_values(records, attribute)
        return min(values) if values else None

    return get


def _sum_value(attribute: str) -> Callable[[list[NormalizedDailyObservation]], float | None]:
    def get(records: list[NormalizedDailyObservation]) -> float | None:
        values = _all_values(records, attribute)
        return sum(values) if values else None

    return get


HAZARDS = (
    _HazardDefinition(
        HazardType.EXTREME_HEAT,
        "maximum_daily_temperature",
        lambda thresholds: thresholds.extreme_heat_c,
        ">=",
        "degC",
        _max_value("temperature_max_c"),
    ),
    _HazardDefinition(
        HazardType.EXTREME_COLD,
        "minimum_daily_temperature",
        lambda thresholds: thresholds.extreme_cold_c,
        "<=",
        "degC",
        _min_value("temperature_min_c"),
    ),
    _HazardDefinition(
        HazardType.HEAVY_PRECIPITATION,
        "event_window_precipitation",
        lambda thresholds: thresholds.heavy_precipitation_mm,
        ">=",
        "mm",
        _sum_value("precipitation_mm"),
    ),
    _HazardDefinition(
        HazardType.WIND,
        "maximum_daily_mean_10m_wind_speed",
        lambda thresholds: thresholds.wind_speed_m_s,
        ">=",
        "m/s",
        _max_value("wind_speed_m_s"),
    ),
    _HazardDefinition(
        HazardType.DROUGHT,
        "event_window_precipitation",
        lambda thresholds: thresholds.drought_precipitation_mm,
        "<=",
        "mm",
        _sum_value("precipitation_mm"),
        minimum_days=14,
    ),
)


def _severity_from_frequency(frequency: float) -> Severity:
    if frequency >= 0.25:
        return Severity.HIGH
    if frequency >= 0.10:
        return Severity.MODERATE
    return Severity.LOW


def _recommendation(hazard: HazardType, severity: Severity) -> str:
    if severity == Severity.LOW:
        return "Record the historical event-window frequency; this result is not a forecast."
    actions = {
        HazardType.EXTREME_HEAT: "Review cooling capacity, heat safety, and continuity measures.",
        HazardType.EXTREME_COLD: "Review freeze protection, heating resilience, and access plans.",
        HazardType.HEAVY_PRECIPITATION: "Review drainage, weatherproofing, and site access measures.",
        HazardType.WIND: "Review wind operating limits, loose equipment, and continuity measures.",
        HazardType.DROUGHT: "Review water availability and drought-contingency measures.",
    }
    return actions[hazard]


def _is_event(value: float, threshold: float, operator: str) -> bool:
    return value >= threshold if operator == ">=" else value <= threshold


def _unavailable(
    definition: _HazardDefinition, threshold: float, reason: str, evidence_id
) -> HazardFinding:
    return HazardFinding(
        hazard=definition.hazard,
        status=FindingStatus.UNAVAILABLE,
        metric=definition.metric,
        operator=definition.operator,  # type: ignore[arg-type]
        threshold=threshold,
        unit=definition.unit,
        event_definition=f"{definition.metric} {definition.operator} {threshold:g} {definition.unit}",
        severity=Severity.UNKNOWN,
        calibration_status=CalibrationStatus.NOT_APPLICABLE,
        evidence_ids=[evidence_id],
        limitation=reason,
    )


def _records_by_local_date(
    observations: Iterable[NormalizedDailyObservation],
) -> dict[date, NormalizedDailyObservation]:
    # One source observation exists per date.  If an upstream source ever sends
    # duplicates, retaining the final one is deterministic and auditable in raw
    # evidence; no values are averaged invisibly.
    return {observation.local_date: observation for observation in observations}


def _year_window_dates(target_dates: list[date], year: int) -> list[date] | None:
    try:
        return [date(year, target.month, target.day) for target in target_dates]
    except ValueError:
        # Feb 29 is only compared with matching leap years.  It is not silently
        # shifted to Feb 28 or Mar 1.
        return None


def evaluate_baseline(
    observations: list[NormalizedDailyObservation],
    target_dates: list[date],
    baseline: BaselinePeriod,
    thresholds: HazardThresholds,
    evidence_id,
) -> HazardOutcome:
    """Calculate empirical event-window likelihoods over complete baseline years."""

    indexed = _records_by_local_date(observations)
    findings: list[HazardFinding] = []
    data_gaps: list[str] = []
    limitations = [
        "NASA POWER UTC daily aggregates are represented at 12:00 UTC before IANA calendar-label conversion; source aggregation boundaries remain UTC-defined.",
        "Wind uses NASA POWER WS10M daily-mean 10 m wind at the source grid. It is not a gust, peak-wind, or site-scale operating-wind measurement.",
        "Baseline likelihood is an empirical frequency across matching historical event windows, not a future-day forecast.",
    ]

    for definition in HAZARDS:
        threshold = definition.threshold(thresholds)
        if len(target_dates) < definition.minimum_days:
            reason = (
                f"{definition.hazard.value} requires an event window of at least "
                f"{definition.minimum_days} days."
            )
            data_gaps.append(reason)
            findings.append(_unavailable(definition, threshold, reason, evidence_id))
            continue

        values: list[float] = []
        for year in range(baseline.start_year, baseline.end_year + 1):
            dates_for_year = _year_window_dates(target_dates, year)
            if dates_for_year is None:
                continue
            records = [indexed.get(day) for day in dates_for_year]
            if any(record is None for record in records):
                continue
            metric = definition.value([record for record in records if record is not None])
            if metric is not None:
                values.append(metric)

        if len(values) < MINIMUM_BASELINE_SAMPLES:
            reason = (
                f"Only {len(values)} complete baseline event windows were available for "
                f"{definition.hazard.value}; at least {MINIMUM_BASELINE_SAMPLES} are required."
            )
            data_gaps.append(reason)
            findings.append(_unavailable(definition, threshold, reason, evidence_id))
            continue

        exceedances = sum(_is_event(value, threshold, definition.operator) for value in values)
        likelihood = exceedances / len(values)
        severity = _severity_from_frequency(likelihood)
        findings.append(
            HazardFinding(
                hazard=definition.hazard,
                status=FindingStatus.AVAILABLE,
                metric=definition.metric,
                operator=definition.operator,  # type: ignore[arg-type]
                threshold=threshold,
                unit=definition.unit,
                event_definition=(
                    f"P({definition.metric} {definition.operator} {threshold:g} {definition.unit} "
                    f"during the requested local calendar window)"
                ),
                likelihood=likelihood,
                likelihood_basis=(
                    f"{exceedances} threshold exceedances in {len(values)} complete "
                    f"{baseline.start_year}-{baseline.end_year} event windows"
                ),
                sample_size=len(values),
                severity=severity,
                calibration_status=CalibrationStatus.NOT_APPLICABLE,
                recommendation=_recommendation(definition.hazard, severity),
                evidence_ids=[evidence_id],
            )
        )
    return HazardOutcome(findings=findings, data_gaps=data_gaps, limitations=limitations)


def evaluate_observed(
    observations: list[NormalizedDailyObservation],
    target_dates: list[date],
    thresholds: HazardThresholds,
    evidence_id,
) -> HazardOutcome:
    """Report what the source observed/reanalysed, without attaching a probability."""

    indexed = _records_by_local_date(observations)
    records = [indexed.get(day) for day in target_dates]
    findings: list[HazardFinding] = []
    data_gaps: list[str] = []
    limitations = [
        "Observed/reanalysis findings describe source values for the completed window; they are not a forecast probability.",
        "NASA POWER UTC daily aggregates are represented at 12:00 UTC before IANA calendar-label conversion; source aggregation boundaries remain UTC-defined.",
        "Wind uses NASA POWER WS10M daily-mean 10 m wind at the source grid. It is not a gust, peak-wind, or site-scale operating-wind measurement.",
    ]
    for definition in HAZARDS:
        threshold = definition.threshold(thresholds)
        if len(target_dates) < definition.minimum_days:
            reason = (
                f"{definition.hazard.value} requires an event window of at least "
                f"{definition.minimum_days} days."
            )
            data_gaps.append(reason)
            findings.append(_unavailable(definition, threshold, reason, evidence_id))
            continue
        if any(record is None for record in records):
            reason = (
                f"NASA POWER did not cover every requested local day for {definition.hazard.value}."
            )
            data_gaps.append(reason)
            findings.append(_unavailable(definition, threshold, reason, evidence_id))
            continue
        observed_value = definition.value([record for record in records if record is not None])
        if observed_value is None:
            reason = (
                f"NASA POWER did not provide the required metric for {definition.hazard.value}."
            )
            data_gaps.append(reason)
            findings.append(_unavailable(definition, threshold, reason, evidence_id))
            continue
        event = _is_event(observed_value, threshold, definition.operator)
        severity = Severity.HIGH if event else Severity.LOW
        findings.append(
            HazardFinding(
                hazard=definition.hazard,
                status=FindingStatus.AVAILABLE,
                metric=definition.metric,
                operator="observed",
                threshold=threshold,
                unit=definition.unit,
                event_definition=(
                    f"Observed {definition.metric}; threshold condition is "
                    f"{definition.operator} {threshold:g} {definition.unit}"
                ),
                likelihood_basis="Observed/reanalysis value; probability is intentionally not calculated.",
                observed_value=observed_value,
                sample_size=len(target_dates),
                severity=severity,
                calibration_status=CalibrationStatus.NOT_APPLICABLE,
                recommendation=_recommendation(definition.hazard, severity),
                evidence_ids=[evidence_id],
            )
        )
    return HazardOutcome(findings=findings, data_gaps=data_gaps, limitations=limitations)


def make_decision(findings: list[HazardFinding]) -> AnalysisDecision:
    """Suppress asset-risk verdicts until a template-specific policy is published."""

    del findings
    return AnalysisDecision(
        status=Decision.INSUFFICIENT_EVIDENCE,
        rationale=(
            "V1 reports hazard evidence only. A published template-specific exposure, "
            "vulnerability, consequence, and decision policy is required before NimbusX "
            "can issue an asset-risk verdict."
        ),
    )
