"""Typed, evidence-first boundaries for external source adapters.

This module deliberately contains contracts and registry logic only.  It does
not download data, generate values, or turn an unavailable provider into a
forecast.  Adapters implement these contracts before their output is allowed
into the hazard engine.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from math import isfinite
from typing import Any, Protocol
from uuid import UUID

from .schemas import EvidenceRecord, SiteInput


class SourceCapability(StrEnum):
    """A source capability, intentionally more specific than a UI mode."""

    OBSERVED_DAILY = "observed_daily"
    HISTORICAL_BASELINE = "historical_baseline"
    OPERATIONAL_FORECAST = "operational_forecast"
    SEASONAL_OUTLOOK = "seasonal_outlook"
    SCENARIO_PROJECTION = "scenario_projection"
    FLOOD_EXPOSURE = "flood_exposure"
    WILDFIRE_EXPOSURE = "wildfire_exposure"
    WATER_STRESS_EXPOSURE = "water_stress_exposure"


class SourceImplementationState(StrEnum):
    IMPLEMENTED = "implemented"
    UNAVAILABLE = "unavailable"


class SourceHealthState(StrEnum):
    """Health state without overstating whether a remote source is live."""

    NOT_CHECKED = "not_checked"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"


class RemoteProbePolicy(StrEnum):
    """When remote availability may be evaluated for a source."""

    ON_RETRIEVAL = "on_retrieval"
    EXPLICIT_ONLY = "explicit_only"
    NOT_APPLICABLE = "not_applicable"


class ForecastProductKind(StrEnum):
    ENSEMBLE = "ensemble"
    HIGH_RESOLUTION = "high_resolution"


class CalibrationState(StrEnum):
    CALIBRATED = "calibrated"
    INSUFFICIENT_SKILL = "insufficient_skill"
    UNAVAILABLE = "unavailable"


class SpatialExposureKind(StrEnum):
    FLOOD = "flood"
    WILDFIRE = "wildfire"
    WATER_STRESS = "water_stress"


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value.lower())


def _require_aware(value: datetime, *, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include a UTC offset")


def _require_finite(value: float, *, field_name: str) -> None:
    if isinstance(value, bool) or not isfinite(float(value)):
        raise ValueError(f"{field_name} must be a finite number")


@dataclass(frozen=True, slots=True)
class EvidenceContract:
    """Minimum immutable provenance required for a normalized provider output."""

    requires_model_version: bool = False
    requires_raw_extract: bool = False
    required_query_keys: tuple[str, ...] = ()
    required_unit_keys: tuple[str, ...] = ()

    def validate(self, evidence: EvidenceRecord) -> None:
        missing: list[str] = []
        if not evidence.provider:
            missing.append("provider")
        if not evidence.dataset:
            missing.append("dataset")
        if not evidence.license:
            missing.append("license")
        if not evidence.attribution:
            missing.append("attribution")
        if not evidence.resolution:
            missing.append("resolution")
        if not evidence.query:
            missing.append("query")
        if not evidence.units:
            missing.append("units")
        if self.requires_model_version and not evidence.model_version:
            missing.append("model_version")
        if self.requires_raw_extract and not evidence.raw_extract:
            missing.append("raw_extract")
        if missing:
            raise ValueError(f"evidence is missing required fields: {', '.join(missing)}")
        if not _is_sha256(evidence.content_hash):
            raise ValueError("evidence.content_hash must be a SHA-256 digest")
        _require_aware(evidence.retrieved_at, field_name="evidence.retrieved_at")
        absent_query = [key for key in self.required_query_keys if key not in evidence.query]
        if absent_query:
            raise ValueError(f"evidence.query is missing required keys: {', '.join(absent_query)}")
        absent_units = [key for key in self.required_unit_keys if key not in evidence.units]
        if absent_units:
            raise ValueError(f"evidence.units is missing required keys: {', '.join(absent_units)}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "requires_model_version": self.requires_model_version,
            "requires_raw_extract": self.requires_raw_extract,
            "required_query_keys": list(self.required_query_keys),
            "required_unit_keys": list(self.required_unit_keys),
        }


@dataclass(frozen=True, slots=True)
class SourceDescriptor:
    """Static disclosure of one adapter's scientific and operational boundary."""

    source_id: str
    provider: str
    dataset: str
    capabilities: tuple[SourceCapability, ...]
    implementation: SourceImplementationState
    remote_probe_policy: RemoteProbePolicy
    evidence_contract: EvidenceContract
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source_id or not self.provider or not self.dataset:
            raise ValueError("source descriptor identifiers must be non-empty")
        if not self.capabilities:
            raise ValueError("source descriptor must declare at least one capability")

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.source_id,
            "provider": self.provider,
            "dataset": self.dataset,
            "capabilities": [item.value for item in self.capabilities],
            "implementation": self.implementation.value,
            "remote_probe_policy": self.remote_probe_policy.value,
            "evidence_contract": self.evidence_contract.as_dict(),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class SourceHealth:
    """A non-fabricated source-health record suitable for a public endpoint."""

    descriptor: SourceDescriptor
    status: SourceHealthState
    checked_at: datetime
    message: str
    remote_checked: bool = False
    details: Mapping[str, str | int | float | bool | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_aware(self.checked_at, field_name="source health checked_at")
        if self.status == SourceHealthState.UNAVAILABLE and self.descriptor.implementation != (
            SourceImplementationState.UNAVAILABLE
        ):
            raise ValueError(
                "an implemented adapter cannot be reported unavailable without a probe result"
            )
        if self.remote_checked and self.status == SourceHealthState.NOT_CHECKED:
            raise ValueError("a remote-checked source cannot have not_checked status")

    def as_dict(self) -> dict[str, Any]:
        return {
            **self.descriptor.as_dict(),
            "status": self.status.value,
            "checked_at": self.checked_at.astimezone(UTC).isoformat(),
            "remote_checked": self.remote_checked,
            "message": self.message,
            "details": dict(self.details),
        }


class SourceHealthAdapter(Protocol):
    """Implemented by adapters that disclose their own non-network health state."""

    def source_health(self, *, now: datetime | None = None) -> SourceHealth:
        """Return configuration/implementation state without fetching source data."""


@dataclass(frozen=True, slots=True)
class SourceHealthRegistry:
    """Stable registry for a health endpoint; it never performs hidden remote I/O."""

    adapters: tuple[SourceHealthAdapter, ...]

    def __post_init__(self) -> None:
        identifiers = [adapter.source_health().descriptor.source_id for adapter in self.adapters]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("source health registry contains duplicate source ids")

    def snapshot(self, *, now: datetime | None = None) -> dict[str, Any]:
        generated_at = now or datetime.now(UTC)
        _require_aware(generated_at, field_name="source health generated_at")
        return {
            "generated_at": generated_at.astimezone(UTC).isoformat(),
            "sources": [
                adapter.source_health(now=generated_at).as_dict() for adapter in self.adapters
            ],
            "limitations": [
                "This endpoint reports adapter configuration and implementation state only. "
                "It does not issue hidden provider requests or claim remote availability."
            ],
        }


def validate_evidence(evidence: EvidenceRecord, contract: EvidenceContract) -> EvidenceRecord:
    """Validate and return evidence so adapter return sites stay concise."""

    contract.validate(evidence)
    return evidence


@dataclass(frozen=True, slots=True)
class ForecastMember:
    """One source ensemble/member value set at an explicit valid timestamp."""

    member_id: str
    initialization_time: datetime
    valid_time: datetime
    variables: Mapping[str, float | None]

    def __post_init__(self) -> None:
        if not self.member_id:
            raise ValueError("forecast member_id must be non-empty")
        _require_aware(self.initialization_time, field_name="forecast initialization_time")
        _require_aware(self.valid_time, field_name="forecast valid_time")
        if self.valid_time < self.initialization_time:
            raise ValueError("forecast valid_time must not precede initialization_time")
        if not self.variables:
            raise ValueError("forecast member must contain at least one source variable")
        for name, value in self.variables.items():
            if not name:
                raise ValueError("forecast variable names must be non-empty")
            if value is not None:
                _require_finite(value, field_name=f"forecast variable {name}")


@dataclass(frozen=True, slots=True)
class OperationalForecastDataset:
    """Adapter return contract for ECMWF-like operational forecast products.

    A high-resolution deterministic product may be included, but it is not
    sufficient to emit an ensemble exceedance probability.
    """

    evidence: EvidenceRecord
    product_kind: ForecastProductKind
    members: tuple[ForecastMember, ...]
    valid_start: datetime
    valid_end: datetime
    evidence_contract: EvidenceContract

    def __post_init__(self) -> None:
        validate_evidence(self.evidence, self.evidence_contract)
        _require_aware(self.valid_start, field_name="forecast valid_start")
        _require_aware(self.valid_end, field_name="forecast valid_end")
        if self.valid_end < self.valid_start:
            raise ValueError("forecast valid_end must be on or after valid_start")
        if not self.members:
            raise ValueError("forecast dataset must include at least one member")
        if self.product_kind == ForecastProductKind.ENSEMBLE and len(self.members) < 2:
            raise ValueError("an ensemble forecast needs at least two members")
        if len({item.member_id for item in self.members}) != len(self.members):
            raise ValueError("forecast member ids must be unique")
        if any(
            item.valid_time < self.valid_start or item.valid_time > self.valid_end
            for item in self.members
        ):
            raise ValueError("forecast member valid_time lies outside declared coverage")

    @property
    def can_emit_member_probability(self) -> bool:
        return self.product_kind == ForecastProductKind.ENSEMBLE and len(self.members) >= 2


@dataclass(frozen=True, slots=True)
class SeasonalCalibrationArtifact:
    """The evidence required before a seasonal local probability is decision-eligible."""

    state: CalibrationState
    method: str | None
    hindcast_start: date | None
    hindcast_end: date | None
    skill_metric: str | None
    skill_value: float | None
    evidence_ids: tuple[UUID, ...] = ()

    def __post_init__(self) -> None:
        if self.state == CalibrationState.CALIBRATED:
            if not all(
                (
                    self.method,
                    self.hindcast_start,
                    self.hindcast_end,
                    self.skill_metric,
                    self.skill_value is not None,
                    self.evidence_ids,
                )
            ):
                raise ValueError(
                    "a calibrated seasonal outlook requires hindcast and skill evidence"
                )
            assert self.hindcast_start is not None
            assert self.hindcast_end is not None
            assert self.skill_value is not None
            if self.hindcast_end < self.hindcast_start:
                raise ValueError("hindcast_end must be on or after hindcast_start")
            _require_finite(self.skill_value, field_name="seasonal skill_value")
            if self.skill_value <= 0:
                raise ValueError("a decision-eligible seasonal skill value must be positive")

    @property
    def decision_eligible(self) -> bool:
        return self.state == CalibrationState.CALIBRATED


@dataclass(frozen=True, slots=True)
class SeasonalOutlookDataset:
    """Adapter return contract for post-processed seasonal outlooks."""

    evidence: EvidenceRecord
    hindcast_evidence: EvidenceRecord | None
    target_start: date
    target_end: date
    member_count: int
    calibration: SeasonalCalibrationArtifact
    evidence_contract: EvidenceContract

    def __post_init__(self) -> None:
        validate_evidence(self.evidence, self.evidence_contract)
        if self.target_end < self.target_start:
            raise ValueError("seasonal target_end must be on or after target_start")
        if self.member_count < 1:
            raise ValueError("seasonal outlook needs at least one source ensemble member")
        if self.calibration.decision_eligible and self.hindcast_evidence is None:
            raise ValueError("calibrated seasonal output must include hindcast evidence")
        if self.hindcast_evidence is not None:
            validate_evidence(self.hindcast_evidence, self.evidence_contract)


@dataclass(frozen=True, slots=True)
class ScenarioRange:
    """A multi-model range, never a single model's falsely precise projection."""

    scenario: str
    target_period: str
    variable: str
    unit: str
    model_ids: tuple[str, ...]
    lower: float
    central: float
    upper: float

    def __post_init__(self) -> None:
        if self.scenario not in {"ssp126", "ssp245", "ssp585"}:
            raise ValueError("scenario must be one of ssp126, ssp245, or ssp585")
        if self.target_period not in {"2030s", "2050s", "2080s"}:
            raise ValueError("target_period must be 2030s, 2050s, or 2080s")
        if not self.variable or not self.unit:
            raise ValueError("scenario range variable and unit must be non-empty")
        if len(self.model_ids) < 2 or len(set(self.model_ids)) != len(self.model_ids):
            raise ValueError("scenario range requires at least two unique model ids")
        for name, value in (
            ("lower", self.lower),
            ("central", self.central),
            ("upper", self.upper),
        ):
            _require_finite(value, field_name=f"scenario range {name}")
        if not self.lower <= self.central <= self.upper:
            raise ValueError("scenario range must satisfy lower <= central <= upper")


@dataclass(frozen=True, slots=True)
class ScenarioProjectionDataset:
    """Adapter return contract for NEX-GDDP-CMIP6-style scenario comparisons."""

    evidence: EvidenceRecord
    baseline_start_year: int
    baseline_end_year: int
    ranges: tuple[ScenarioRange, ...]
    evidence_contract: EvidenceContract

    def __post_init__(self) -> None:
        validate_evidence(self.evidence, self.evidence_contract)
        if (self.baseline_start_year, self.baseline_end_year) != (1991, 2020):
            raise ValueError("scenario output must retain the 1991–2020 comparison baseline")
        if not self.ranges:
            raise ValueError("scenario output must include at least one multi-model range")


@dataclass(frozen=True, slots=True)
class SpatialExposureValue:
    """A source metric, not an asset-risk decision or probability by default."""

    metric: str
    value: float | None
    unit: str
    source_classification: str | None = None

    def __post_init__(self) -> None:
        if not self.metric or not self.unit:
            raise ValueError("spatial exposure metric and unit must be non-empty")
        if self.value is not None:
            _require_finite(self.value, field_name=f"spatial exposure value {self.metric}")


@dataclass(frozen=True, slots=True)
class SpatialExposureDataset:
    """Adapter return contract for dedicated flood, wildfire, or water-stress layers."""

    evidence: EvidenceRecord
    kind: SpatialExposureKind
    site: SiteInput
    geometry_hash: str
    values: tuple[SpatialExposureValue, ...]
    evidence_contract: EvidenceContract

    def __post_init__(self) -> None:
        validate_evidence(self.evidence, self.evidence_contract)
        if not _is_sha256(self.geometry_hash):
            raise ValueError("spatial exposure geometry_hash must be a SHA-256 digest")
        if not self.values:
            raise ValueError("spatial exposure output must include at least one source metric")


class OperationalForecastAdapter(Protocol):
    descriptor: SourceDescriptor

    def fetch_forecast(
        self, site: SiteInput, start: datetime, end: datetime
    ) -> OperationalForecastDataset:
        """Return source-backed member data or raise ProviderUnavailable."""


class SeasonalOutlookAdapter(Protocol):
    descriptor: SourceDescriptor

    def fetch_seasonal(
        self, site: SiteInput, target_start: date, target_end: date
    ) -> SeasonalOutlookDataset:
        """Return source-backed outlook + calibration artifacts or raise ProviderUnavailable."""


class ScenarioProjectionAdapter(Protocol):
    descriptor: SourceDescriptor

    def fetch_projection(self, site: SiteInput) -> ScenarioProjectionDataset:
        """Return evidence-backed multi-model scenario ranges or raise ProviderUnavailable."""


class SpatialExposureAdapter(Protocol):
    descriptor: SourceDescriptor

    def fetch_exposure(self, site: SiteInput) -> SpatialExposureDataset:
        """Return a dedicated spatial layer result or raise ProviderUnavailable."""


def require_unique_descriptors(descriptors: Sequence[SourceDescriptor]) -> None:
    """Validate source ids when an application constructs a static catalog."""

    identifiers = [descriptor.source_id for descriptor in descriptors]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("source descriptor ids must be unique")
