"""Canonical request and response schemas for the public `/v1` API.

All quantities exposed by this module are SI.  A presentation client may convert
units, but the API never changes scientific units based on an implicit locale.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from math import isfinite
from typing import Any, Literal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=False)


class AnalysisMode(StrEnum):
    AUTO = "auto"
    OBSERVED = "observed"
    FORECAST = "forecast"
    SEASONAL = "seasonal"
    BASELINE = "baseline"
    SCENARIO = "scenario"


class AnalysisStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"
    EXPIRED = "expired"


class HazardType(StrEnum):
    EXTREME_HEAT = "extreme_heat"
    EXTREME_COLD = "extreme_cold"
    HEAVY_PRECIPITATION = "heavy_precipitation"
    WIND = "wind"
    DROUGHT = "drought"


class FindingStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class Severity(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    UNKNOWN = "unknown"


class CalibrationStatus(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    UNAVAILABLE = "unavailable"
    CALIBRATED = "calibrated"
    INSUFFICIENT_SKILL = "insufficient_skill"


class Decision(StrEnum):
    ACCEPTABLE = "acceptable"
    MITIGATION_REQUIRED = "mitigation_required"
    HIGH_RISK = "high_risk"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class Scenario(StrEnum):
    SSP126 = "ssp126"
    SSP245 = "ssp245"
    SSP585 = "ssp585"


class SiteGeometry(ApiModel):
    """GeoJSON Point or Polygon geometry with coordinate-range validation.

    NimbusX does not attempt topology repair. A submitted polygon must already
    be a closed GeoJSON linear-ring boundary with valid WGS84 coordinates.
    """

    type: Literal["Point", "Polygon"]
    coordinates: list[Any]

    @staticmethod
    def _position(value: Any, *, context: str) -> tuple[float, float]:
        if not isinstance(value, list) or len(value) < 2:
            raise ValueError(f"{context} must be a position [longitude, latitude]")
        longitude, latitude = value[0], value[1]
        if any(
            isinstance(item, bool) or not isinstance(item, (int, float))
            for item in (longitude, latitude)
        ):
            raise ValueError(f"{context} longitude and latitude must be finite numbers")
        longitude_float, latitude_float = float(longitude), float(latitude)
        if not isfinite(longitude_float) or not isfinite(latitude_float):
            raise ValueError(f"{context} longitude and latitude must be finite numbers")
        if not -180 <= longitude_float <= 180 or not -90 <= latitude_float <= 90:
            raise ValueError(f"{context} coordinates are outside WGS84 longitude/latitude bounds")
        return longitude_float, latitude_float

    @model_validator(mode="after")
    def validate_coordinates(self) -> SiteGeometry:
        if self.type == "Point":
            if len(self.coordinates) != 2:
                raise ValueError("Point geometry coordinates must be [longitude, latitude]")
            self._position(self.coordinates, context="Point geometry")
            return self

        if not self.coordinates:
            raise ValueError("Polygon geometry must contain at least one ring")
        for ring_index, ring in enumerate(self.coordinates):
            if not isinstance(ring, list) or len(ring) < 4:
                raise ValueError(
                    f"Polygon ring {ring_index} must contain at least four positions including closure"
                )
            positions = [
                self._position(
                    position, context=f"Polygon ring {ring_index} position {position_index}"
                )
                for position_index, position in enumerate(ring)
            ]
            if positions[0] != positions[-1]:
                raise ValueError(f"Polygon ring {ring_index} must be closed")
            if len(set(positions[:-1])) < 3:
                raise ValueError(
                    f"Polygon ring {ring_index} must contain at least three distinct vertices"
                )
        return self


class SiteInput(ApiModel):
    name: str = Field(min_length=1, max_length=200)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str = Field(default="UTC", min_length=1, max_length=64)
    geometry: SiteGeometry | None = None
    address: str | None = Field(default=None, max_length=500)

    @field_validator("latitude", "longitude", mode="before")
    @classmethod
    def finite_site_coordinate(cls, value: Any) -> Any:
        if isinstance(value, bool):
            raise ValueError("site coordinates must be finite numbers, not booleans")
        try:
            numeric_value = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("site coordinates must be finite numbers") from exc
        if not isfinite(numeric_value):
            raise ValueError("site coordinates must be finite numbers")
        return value

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(
                "timezone must be an IANA timezone, for example 'Asia/Kolkata'"
            ) from exc
        return value

    @model_validator(mode="after")
    def point_geometry_matches_site(self) -> SiteInput:
        if self.geometry and self.geometry.type == "Point":
            longitude, latitude = self.geometry.coordinates
            if (
                abs(float(latitude) - self.latitude) > 1e-8
                or abs(float(longitude) - self.longitude) > 1e-8
            ):
                raise ValueError("Point geometry must match latitude and longitude")
        return self


class StoredSite(SiteInput):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProjectCreate(ApiModel):
    name: str = Field(min_length=1, max_length=200)
    organization_id: str | None = Field(default=None, min_length=1, max_length=128)


class Project(ApiModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    organization_id: str = "development"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TimeWindow(ApiModel):
    """Timezone-aware event window; both boundaries are inclusive calendar days."""

    start: datetime
    end: datetime

    @field_validator("start", "end")
    @classmethod
    def timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("time window values must include an explicit UTC offset")
        return value

    @model_validator(mode="after")
    def valid_order(self) -> TimeWindow:
        if self.end < self.start:
            raise ValueError("window.end must be on or after window.start")
        return self

    def local_dates(self, timezone_name: str) -> list[date]:
        zone = ZoneInfo(timezone_name)
        start_date = self.start.astimezone(zone).date()
        end_date = self.end.astimezone(zone).date()
        days = (end_date - start_date).days
        return [start_date + timedelta(days=index) for index in range(days + 1)]


class BaselinePeriod(ApiModel):
    start_year: int = Field(default=1991, ge=1981, le=2100)
    end_year: int = Field(default=2020, ge=1981, le=2100)

    @model_validator(mode="after")
    def valid_order(self) -> BaselinePeriod:
        if self.end_year < self.start_year:
            raise ValueError("baseline.end_year must be on or after baseline.start_year")
        return self


class HazardThresholds(ApiModel):
    """Thresholds are explicitly defined, not percentiles rescaled as probabilities."""

    extreme_heat_c: float = Field(default=35.0, ge=-90, le=80)
    extreme_cold_c: float = Field(default=0.0, ge=-90, le=50)
    heavy_precipitation_mm: float = Field(default=25.0, ge=0, le=5000)
    wind_speed_m_s: float = Field(default=15.0, ge=0, le=200)
    drought_precipitation_mm: float = Field(default=1.0, ge=0, le=5000)


class AssetContext(ApiModel):
    """Optional context retained for a future, published asset-risk policy.

    V1 records supplied fields but does not treat arbitrary free-text exposure
    and vulnerability dictionaries as sufficient for an asset-risk verdict.
    """

    template: str | None = Field(default=None, max_length=100)
    exposure: dict[str, Any] | None = None
    vulnerability: dict[str, Any] | None = None


class AnalysisCreateRequest(ApiModel):
    project_id: UUID | None = None
    site_id: UUID | None = None
    site: SiteInput | None = None
    window: TimeWindow
    mode: AnalysisMode = AnalysisMode.AUTO
    asset: AssetContext | None = None
    thresholds: HazardThresholds = Field(default_factory=HazardThresholds)
    baseline: BaselinePeriod = Field(default_factory=BaselinePeriod)
    scenarios: list[Scenario] = Field(
        default_factory=lambda: [Scenario.SSP126, Scenario.SSP245, Scenario.SSP585]
    )

    @model_validator(mode="after")
    def one_site_source(self) -> AnalysisCreateRequest:
        if (self.site is None) == (self.site_id is None):
            raise ValueError("provide exactly one of site or site_id")
        return self


class AnalysisCreated(ApiModel):
    id: UUID
    status: AnalysisStatus
    mode: AnalysisMode
    created_at: datetime


class SourceFreshness(ApiModel):
    provider: str
    status: Literal["current", "stale", "unavailable"]
    retrieved_at: datetime | None = None
    valid_until: datetime | None = None
    message: str | None = None


class NormalizedDailyObservation(ApiModel):
    """Normalized daily aggregate; timestamp_utc may be a documented representative label."""

    timestamp_utc: datetime
    local_timestamp: datetime
    local_date: date
    timezone: str
    temperature_max_c: float | None = None
    temperature_min_c: float | None = None
    precipitation_mm: float | None = None
    wind_speed_m_s: float | None = None


class EvidenceRecord(ApiModel):
    """Internal evidence record including raw material retained by the data boundary."""

    id: UUID = Field(default_factory=uuid4)
    provider: str
    dataset: str
    model_version: str | None = None
    retrieved_at: datetime
    query: dict[str, Any]
    units: dict[str, str]
    resolution: str
    license: str
    attribution: str
    content_hash: str
    coverage_start: date | None = None
    coverage_end: date | None = None
    raw_available: bool = True
    raw_extract: dict[str, Any] | None = None
    normalized_observations: list[NormalizedDailyObservation] = Field(default_factory=list)


class EvidenceManifestRecord(ApiModel):
    """Browser-safe provenance metadata; raw payloads stay behind the data boundary."""

    id: UUID
    provider: str
    dataset: str
    model_version: str | None = None
    retrieved_at: datetime
    query: dict[str, Any]
    units: dict[str, str]
    resolution: str
    license: str
    attribution: str
    content_hash: str
    coverage_start: date | None = None
    coverage_end: date | None = None
    raw_available: bool

    @classmethod
    def from_internal(cls, record: EvidenceRecord) -> EvidenceManifestRecord:
        return cls(
            id=record.id,
            provider=record.provider,
            dataset=record.dataset,
            model_version=record.model_version,
            retrieved_at=record.retrieved_at,
            query=record.query,
            units=record.units,
            resolution=record.resolution,
            license=record.license,
            attribution=record.attribution,
            content_hash=record.content_hash,
            coverage_start=record.coverage_start,
            coverage_end=record.coverage_end,
            raw_available=record.raw_available,
        )


class HazardFinding(ApiModel):
    hazard: HazardType
    status: FindingStatus
    metric: str
    operator: Literal[">=", "<=", "observed"]
    threshold: float
    unit: str
    event_definition: str
    likelihood: float | None = Field(default=None, ge=0, le=1)
    likelihood_basis: str | None = None
    observed_value: float | None = None
    sample_size: int | None = Field(default=None, ge=0)
    severity: Severity = Severity.UNKNOWN
    calibration_status: CalibrationStatus
    recommendation: str | None = None
    evidence_ids: list[UUID] = Field(default_factory=list)
    limitation: str | None = None


class AnalysisDecision(ApiModel):
    status: Decision
    rationale: str


class Assessment(ApiModel):
    id: UUID
    status: AnalysisStatus
    mode: AnalysisMode
    project_id: UUID | None = None
    resolved_mode: AnalysisMode | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    generated_at: datetime | None = None
    expires_at: datetime | None = None
    source_freshness: list[SourceFreshness] = Field(default_factory=list)
    site: SiteInput
    window: TimeWindow
    findings: list[HazardFinding] = Field(default_factory=list)
    decision: AnalysisDecision | None = None
    evidence_ids: list[UUID] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    report_version: str = "1.0"


class EvidenceResponse(ApiModel):
    analysis_id: UUID
    evidence: list[EvidenceManifestRecord]


class ComparisonType(StrEnum):
    SELECTED_ASSESSMENTS = "selected_assessments"


class CompareRequest(ApiModel):
    """Select terminal assessments for review; V1 does not calculate deltas yet."""

    analysis_ids: list[UUID] = Field(default_factory=list, max_length=10)


class ComparisonItem(ApiModel):
    analysis_id: UUID
    site_name: str
    status: AnalysisStatus
    mode: AnalysisMode | None = None
    decision: Decision | None = None
    findings: list[HazardFinding] = Field(default_factory=list)


class ComparisonResponse(ApiModel):
    comparison: ComparisonType
    analyses: list[ComparisonItem]
    limitations: list[str] = Field(default_factory=list)


class AuditEvent(ApiModel):
    id: UUID = Field(default_factory=uuid4)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    actor_id: str
    action: str
    resource_type: str
    resource_id: UUID
    details: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(ApiModel):
    status: Literal["ok"]
    service: Literal["nimbusx-api"]
    version: str


class ReadinessResponse(ApiModel):
    status: Literal["ready", "degraded"]
    persistence: Literal["in_memory_development"]
    provider: Literal["not_checked"]
    limitations: list[str] = Field(default_factory=list)
