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


class AssetCriticality(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AssetFieldSpec(ApiModel):
    """A published field required by an asset template's screening rules."""

    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    label: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=500)
    value_type: Literal["string", "number", "boolean", "enum"] = "string"
    allowed_values: list[str] = Field(default_factory=list, max_length=30)
    required: bool = True

    @model_validator(mode="after")
    def enum_values_match_type(self) -> AssetFieldSpec:
        if self.value_type == "enum" and not self.allowed_values:
            raise ValueError("enum asset fields must declare at least one allowed value")
        if self.value_type != "enum" and self.allowed_values:
            raise ValueError("allowed_values may only be set for enum asset fields")
        return self


class OperationalRuleDefinition(ApiModel):
    """A versioned, published screening rule; it is never an asset-risk verdict."""

    id: str = Field(pattern=r"^[a-z][a-z0-9-]{2,99}$")
    name: str = Field(min_length=1, max_length=160)
    hazard: HazardType
    minimum_severity: Severity
    required_exposure_fields: list[str] = Field(default_factory=list, max_length=30)
    required_vulnerability_fields: list[str] = Field(default_factory=list, max_length=30)
    action: str = Field(min_length=1, max_length=1000)
    rationale: str = Field(min_length=1, max_length=1000)

    @field_validator("minimum_severity")
    @classmethod
    def actionable_minimum_severity(cls, value: Severity) -> Severity:
        if value == Severity.UNKNOWN:
            raise ValueError("operational rules cannot use unknown as a minimum severity")
        return value


class AssetTemplate(ApiModel):
    """A public, versioned catalog entry for a built-asset type."""

    id: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    display_name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=1000)
    required_exposure_fields: list[AssetFieldSpec] = Field(default_factory=list, max_length=30)
    required_vulnerability_fields: list[AssetFieldSpec] = Field(default_factory=list, max_length=30)
    supported_hazards: list[HazardType] = Field(default_factory=list, max_length=10)
    operational_rules: list[OperationalRuleDefinition] = Field(default_factory=list, max_length=30)
    version: str = "1.0"


class PortfolioAssetCreate(ApiModel):
    """An asset references a project site; no coordinates are silently duplicated."""

    name: str = Field(min_length=1, max_length=200)
    site_id: UUID
    template_id: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    external_id: str | None = Field(default=None, max_length=200)
    criticality: AssetCriticality = AssetCriticality.MEDIUM
    tags: list[str] = Field(default_factory=list, max_length=30)
    exposure: dict[str, Any] = Field(default_factory=dict)
    vulnerability: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value.strip()]
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("asset tags must not contain duplicates")
        if any(len(value) > 80 for value in cleaned):
            raise ValueError("asset tags must not exceed 80 characters")
        return cleaned


class PortfolioAsset(PortfolioAssetCreate):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AssetImportRequest(ApiModel):
    """One source document per request; uploads stay in the caller's control plane."""

    csv_text: str | None = Field(default=None, max_length=1_000_000)
    geojson: dict[str, Any] | None = None
    default_template_id: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{1,63}$")
    dry_run: bool = False

    @model_validator(mode="after")
    def one_import_source(self) -> AssetImportRequest:
        if (self.csv_text is None) == (self.geojson is None):
            raise ValueError("provide exactly one of csv_text or geojson")
        if self.csv_text is not None and not self.csv_text.strip():
            raise ValueError("csv_text must not be empty")
        return self


class AssetImportRowResult(ApiModel):
    row_number: int = Field(ge=1)
    name: str | None = None
    status: Literal["created", "validated", "rejected"]
    asset_id: UUID | None = None
    site_id: UUID | None = None
    code: str | None = None
    message: str = Field(min_length=1, max_length=1000)


class AssetImportResult(ApiModel):
    project_id: UUID
    dry_run: bool
    status: Literal["complete", "partial", "failed"]
    created_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    rows: list[AssetImportRowResult] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class OperationalFindingStatus(StrEnum):
    ACTION_REQUIRED = "action_required"
    MONITORED = "monitored"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    SOURCE_UNAVAILABLE = "source_unavailable"


class OperationalRiskFinding(ApiModel):
    """A rule outcome tied to source-backed hazard evidence and asset context."""

    asset_id: UUID
    template_id: str
    rule_id: str
    rule_name: str
    hazard: HazardType
    status: OperationalFindingStatus
    source_finding_status: FindingStatus
    source_severity: Severity
    evidence_ids: list[UUID] = Field(default_factory=list)
    action: str | None = None
    rationale: str
    missing_exposure_fields: list[str] = Field(default_factory=list)
    missing_vulnerability_fields: list[str] = Field(default_factory=list)


class AlertTriggerType(StrEnum):
    OBSERVED_THRESHOLD_BREACH = "observed_threshold_breach"
    BASELINE_LIKELIHOOD = "baseline_likelihood"
    SEVERITY_AT_LEAST = "severity_at_least"


class AlertEventKind(StrEnum):
    OBSERVED_THRESHOLD_BREACH = "observed_threshold_breach"
    HISTORICAL_PATTERN = "historical_pattern"
    SEVERITY_TRIGGER = "severity_trigger"


class AlertDeliveryStatus(StrEnum):
    RECORDED_ONLY = "recorded_only"


class AlertRuleCreate(ApiModel):
    """A rule that evaluates completed source-backed assessment findings only."""

    name: str = Field(min_length=1, max_length=200)
    hazard: HazardType
    trigger_type: AlertTriggerType
    asset_id: UUID | None = None
    minimum_likelihood: float | None = Field(default=None, ge=0, le=1)
    minimum_severity: Severity | None = None
    enabled: bool = True

    @model_validator(mode="after")
    def valid_trigger_parameters(self) -> AlertRuleCreate:
        if self.minimum_severity == Severity.UNKNOWN:
            raise ValueError("minimum_severity may not be unknown")
        if self.trigger_type == AlertTriggerType.BASELINE_LIKELIHOOD:
            if self.minimum_likelihood is None:
                raise ValueError("baseline_likelihood rules require minimum_likelihood")
            if self.minimum_severity is not None:
                raise ValueError("baseline_likelihood rules must not include minimum_severity")
        elif self.trigger_type == AlertTriggerType.SEVERITY_AT_LEAST:
            if self.minimum_severity is None:
                raise ValueError("severity_at_least rules require minimum_severity")
            if self.minimum_likelihood is not None:
                raise ValueError("severity_at_least rules must not include minimum_likelihood")
        elif self.minimum_likelihood is not None or self.minimum_severity is not None:
            raise ValueError("observed_threshold_breach rules must not include trigger thresholds")
        return self


class AlertRule(AlertRuleCreate):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AlertEvent(ApiModel):
    """An immutable local record of a matched evidence-backed rule."""

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    rule_id: UUID
    asset_id: UUID | None = None
    analysis_id: UUID
    hazard: HazardType
    event_kind: AlertEventKind
    summary: str = Field(min_length=1, max_length=1000)
    evidence_ids: list[UUID] = Field(default_factory=list)
    delivery_status: AlertDeliveryStatus = AlertDeliveryStatus.RECORDED_ONLY
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AlertEvaluateRequest(ApiModel):
    analysis_ids: list[UUID] = Field(min_length=1, max_length=100)

    @field_validator("analysis_ids")
    @classmethod
    def distinct_analysis_ids(cls, values: list[UUID]) -> list[UUID]:
        if len(set(values)) != len(values):
            raise ValueError("analysis_ids must not contain duplicates")
        return values


class AlertEvaluationSkip(ApiModel):
    analysis_id: UUID
    reason: str


class AlertEvaluationResponse(ApiModel):
    rule: AlertRule
    events: list[AlertEvent] = Field(default_factory=list)
    created_count: int = Field(ge=0)
    existing_count: int = Field(ge=0)
    skipped: list[AlertEvaluationSkip] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class NotificationChannelKind(StrEnum):
    """The intentionally small set of reviewed notification channel shapes."""

    WEBHOOK = "webhook"
    EMAIL = "email"
    SLACK = "slack"


class NotificationDeliveryMode(StrEnum):
    """Live delivery remains unavailable until a durable dispatcher is installed."""

    DRY_RUN = "dry_run"
    LIVE = "live"


class NotificationReceiptStatus(StrEnum):
    DRY_RUN = "dry_run"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"


class NotificationChannelCreate(ApiModel):
    """A tenant-approved delivery target, never a secret or provider credential."""

    name: str = Field(min_length=1, max_length=200)
    kind: NotificationChannelKind
    target: str = Field(min_length=3, max_length=2_048)
    enabled: bool = True
    delivery_mode: NotificationDeliveryMode = NotificationDeliveryMode.DRY_RUN
    secret_reference: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def safe_notification_target(self) -> NotificationChannelCreate:
        if self.kind in {NotificationChannelKind.WEBHOOK, NotificationChannelKind.SLACK}:
            if not self.target.startswith("https://"):
                raise ValueError("webhook and Slack notification targets must use HTTPS")
        elif "@" not in self.target or self.target.startswith("@") or self.target.endswith("@"):
            raise ValueError("email notification target must be a recipient address")
        if self.secret_reference and not self.secret_reference.startswith("secret://"):
            raise ValueError("notification secret_reference must use the secret:// scheme")
        return self


class NotificationChannel(ApiModel):
    """Browser-safe notification channel view; secret references are never returned."""

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    name: str
    kind: NotificationChannelKind
    target: str
    enabled: bool
    delivery_mode: NotificationDeliveryMode
    has_secret_reference: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class NotificationDispatchReceipt(ApiModel):
    """An immutable record of a dispatch attempt or safe dry run."""

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    alert_event_id: UUID
    channel_id: UUID
    status: NotificationReceiptStatus
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    message: str = Field(min_length=1, max_length=1_000)
    payload: dict[str, Any] = Field(default_factory=dict)


class AnalysisCreateRequest(ApiModel):
    project_id: UUID | None = None
    site_id: UUID | None = None
    site: SiteInput | None = None
    asset_id: UUID | None = None
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
        if self.asset_id is not None:
            if self.site is not None or self.site_id is not None:
                raise ValueError("asset_id may not be combined with site or site_id")
            return self
        if (self.site is None) == (self.site_id is None):
            raise ValueError("provide exactly one of site or site_id, or provide asset_id")
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
    asset_id: UUID | None = None
    resolved_mode: AnalysisMode | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    generated_at: datetime | None = None
    expires_at: datetime | None = None
    source_freshness: list[SourceFreshness] = Field(default_factory=list)
    site: SiteInput
    window: TimeWindow
    findings: list[HazardFinding] = Field(default_factory=list)
    operational_findings: list[OperationalRiskFinding] = Field(default_factory=list)
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
