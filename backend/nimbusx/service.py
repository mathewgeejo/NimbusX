"""Application service for analysis jobs and workspace records."""

from __future__ import annotations

import csv
import json
import logging
from collections.abc import Callable, Mapping
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from io import StringIO
from typing import Any
from uuid import UUID, uuid4

from .catalog import get_template, list_templates
from .errors import AnalysisNotReady, ApiProblem, ProviderUnavailable
from .hazards import evaluate_baseline, evaluate_observed, make_decision
from .horizon import HorizonError, resolve_horizon
from .notifications import dispatch as dispatch_notification
from .operational import evaluate_operational_rules, severity_at_least
from .providers import (
    CopernicusSeasonalProvider,
    DailyClimateProvider,
    ECMWFOpenDataProvider,
    NexGddpCmip6Provider,
)
from .repository import InMemoryRepository, StoredAnalysis
from .schemas import (
    AlertEvaluateRequest,
    AlertEvaluationResponse,
    AlertEvaluationSkip,
    AlertEvent,
    AlertEventKind,
    AlertRule,
    AlertRuleCreate,
    AlertTriggerType,
    AnalysisCreated,
    AnalysisCreateRequest,
    AnalysisDecision,
    AnalysisMode,
    AnalysisStatus,
    Assessment,
    AssetImportRequest,
    AssetImportResult,
    AssetImportRowResult,
    AssetTemplate,
    CompareRequest,
    ComparisonItem,
    ComparisonResponse,
    ComparisonType,
    Decision,
    EvidenceManifestRecord,
    EvidenceResponse,
    FindingStatus,
    HazardFinding,
    NotificationChannel,
    NotificationChannelCreate,
    NotificationDispatchReceipt,
    PortfolioAsset,
    PortfolioAssetCreate,
    Project,
    ProjectCreate,
    SiteInput,
    SourceFreshness,
    StoredSite,
)

logger = logging.getLogger(__name__)

MAX_ASSET_IMPORT_ROWS = 1_000


def _as_site_input(stored: StoredSite) -> SiteInput:
    return SiteInput(
        name=stored.name,
        latitude=stored.latitude,
        longitude=stored.longitude,
        timezone=stored.timezone,
        geometry=stored.geometry,
        address=stored.address,
    )


def _source_date_bounds(target_dates: list[date]) -> tuple[date, date]:
    # NASA labels daily aggregates in UTC. Querying a one-day guard either side
    # is necessary when 12:00 UTC representative labels map into an IANA zone.
    return target_dates[0] - timedelta(days=1), target_dates[-1] + timedelta(days=1)


def _baseline_source_date_bounds(start_year: int, end_year: int) -> tuple[date, date]:
    """Return the source-date range plus UTC/IANA mapping guard days."""

    first_day = date(start_year, 1, 1)
    if start_year > 1981:
        first_day -= timedelta(days=1)
    return first_day, date(end_year + 1, 1, 2)


def _require_assessable_point_site(site: SiteInput) -> SiteInput:
    if site.geometry is not None and site.geometry.type == "Polygon":
        raise ApiProblem(
            "polygon_assessment_unavailable",
            "Polygon assessment requires a source-backed spatial aggregation adapter. Store the geometry if needed, but submit an explicit point site for V1 analysis.",
            422,
        )
    return site


def _text(value: Any) -> str | None:
    if value is None:
        return None
    rendered = str(value).strip()
    return rendered or None


def _import_context(values: Mapping[str, Any], field: str) -> dict[str, Any]:
    """Read an object or CSV JSON cell plus ``field.key`` convenience columns."""

    raw = values.get(field, values.get(f"{field}_json"))
    if raw is None or raw == "":
        result: dict[str, Any] = {}
    elif isinstance(raw, Mapping):
        result = dict(raw)
    elif isinstance(raw, str):
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{field}_json must contain a JSON object") from exc
        if not isinstance(decoded, dict):
            raise ValueError(f"{field}_json must contain a JSON object")
        result = decoded
    else:
        raise ValueError(f"{field} must be an object")
    prefix = f"{field}."
    for key, value in values.items():
        if key.startswith(prefix) and value not in (None, ""):
            result[key[len(prefix) :]] = value
    return result


def _import_tags(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split("|") if item.strip()]
    raise ValueError("tags must be an array or a pipe-separated string")


def _csv_import_rows(csv_text: str) -> list[tuple[int, dict[str, Any]]]:
    try:
        reader = csv.DictReader(StringIO(csv_text))
        if not reader.fieldnames:
            raise ApiProblem(
                "invalid_asset_import",
                "CSV import requires a header row.",
                422,
            )
        headers = [header.strip().casefold() if header else "" for header in reader.fieldnames]
        if not all(headers) or len(set(headers)) != len(headers):
            raise ApiProblem(
                "invalid_asset_import",
                "CSV import headers must be non-empty and unique, ignoring case.",
                422,
            )
        rows: list[tuple[int, dict[str, Any]]] = []
        for row_number, raw in enumerate(reader, start=2):
            if len(rows) >= MAX_ASSET_IMPORT_ROWS:
                raise ApiProblem(
                    "asset_import_too_large",
                    f"An import may contain at most {MAX_ASSET_IMPORT_ROWS} asset rows.",
                    422,
                )
            if None in raw:
                rows.append(
                    (
                        row_number,
                        {"__row_error": "CSV row has more cells than the header row."},
                    )
                )
                continue
            rows.append(
                (
                    row_number,
                    {
                        header.strip().casefold(): value
                        for header, value in raw.items()
                        if header is not None
                    },
                )
            )
    except csv.Error as exc:
        raise ApiProblem("invalid_asset_import", "CSV could not be parsed safely.", 422) from exc
    if not rows:
        raise ApiProblem("invalid_asset_import", "CSV import contains no asset rows.", 422)
    return rows


def _geojson_import_rows(document: Mapping[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    if document.get("type") != "FeatureCollection":
        raise ApiProblem(
            "invalid_asset_import",
            "geojson must be a GeoJSON FeatureCollection.",
            422,
        )
    features = document.get("features")
    if not isinstance(features, list) or not features:
        raise ApiProblem(
            "invalid_asset_import",
            "GeoJSON FeatureCollection must contain at least one feature.",
            422,
        )
    if len(features) > MAX_ASSET_IMPORT_ROWS:
        raise ApiProblem(
            "asset_import_too_large",
            f"An import may contain at most {MAX_ASSET_IMPORT_ROWS} asset rows.",
            422,
        )
    rows: list[tuple[int, dict[str, Any]]] = []
    for row_number, feature in enumerate(features, start=1):
        if not isinstance(feature, Mapping) or feature.get("type") != "Feature":
            rows.append((row_number, {"__row_error": "GeoJSON entry must be a Feature."}))
            continue
        properties = feature.get("properties") or {}
        geometry = feature.get("geometry")
        if not isinstance(properties, Mapping):
            rows.append((row_number, {"__row_error": "Feature properties must be an object."}))
            continue
        if not isinstance(geometry, Mapping) or geometry.get("type") != "Point":
            rows.append(
                (
                    row_number,
                    {
                        "__row_error": (
                            "GeoJSON asset import supports Point features only; polygon analysis "
                            "requires a source-backed spatial aggregation adapter."
                        )
                    },
                )
            )
            continue
        coordinates = geometry.get("coordinates")
        if not isinstance(coordinates, list) or len(coordinates) != 2:
            rows.append(
                (row_number, {"__row_error": "GeoJSON Point must contain [longitude, latitude]."})
            )
            continue
        values = {str(key).casefold(): value for key, value in properties.items()}
        values["longitude"] = coordinates[0]
        values["latitude"] = coordinates[1]
        rows.append((row_number, values))
    return rows


class AnalysisService:
    def __init__(
        self,
        repository: InMemoryRepository,
        daily_provider: DailyClimateProvider,
        *,
        max_window_days: int = 31,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self.daily_provider = daily_provider
        self.max_window_days = max_window_days
        self.now_fn = now_fn or (lambda: datetime.now(UTC))
        self.forecast_provider = ECMWFOpenDataProvider()
        self.seasonal_provider = CopernicusSeasonalProvider()
        self.scenario_provider = NexGddpCmip6Provider()

    def create_analysis(
        self, request: AnalysisCreateRequest, *, actor_id: str = "development"
    ) -> AnalysisCreated:
        site, project_id, asset = self._resolve_target(request)
        local_dates = request.window.local_dates(site.timezone)
        if len(local_dates) > self.max_window_days:
            raise ApiProblem(
                "window_too_large",
                f"The local event window may not exceed {self.max_window_days} days",
                422,
            )
        try:
            resolve_horizon(request.mode, request.window, site.timezone, now=self.now_fn())
        except HorizonError as exc:
            raise ApiProblem("invalid_horizon", str(exc), 422) from exc

        assessment = Assessment(
            id=uuid4(),
            status=AnalysisStatus.QUEUED,
            mode=request.mode,
            project_id=project_id,
            asset_id=asset.id if asset is not None else None,
            site=site,
            window=request.window,
            limitations=[
                "This analysis is queued. It will never substitute synthetic values when a source is unavailable."
            ],
        )
        self.repository.put_analysis(
            StoredAnalysis(request=request, assessment=assessment), actor_id=actor_id
        )
        return AnalysisCreated(
            id=assessment.id,
            status=assessment.status,
            mode=assessment.mode,
            created_at=assessment.created_at,
        )

    def run_analysis(self, analysis_id: UUID) -> None:
        """Run a single job.  Provider failures become evidence gaps, not data."""

        record = self.repository.get_analysis(analysis_id)
        running = record.assessment.model_copy(
            update={
                "status": AnalysisStatus.RUNNING,
                "limitations": [],
                "generated_at": None,
            }
        )
        self.repository.update_analysis(analysis_id, running, [], actor_id="system")

        try:
            site, _, asset = self._resolve_target(record.request)
            resolution = resolve_horizon(
                record.request.mode,
                record.request.window,
                site.timezone,
                now=self.now_fn(),
            )
            target_dates = record.request.window.local_dates(site.timezone)
            if resolution.mode == AnalysisMode.BASELINE:
                start, end = _baseline_source_date_bounds(
                    record.request.baseline.start_year, record.request.baseline.end_year
                )
                dataset = self.daily_provider.fetch_daily(
                    site, start, end, purpose="historical_baseline"
                )
                outcome = evaluate_baseline(
                    dataset.observations,
                    target_dates,
                    record.request.baseline,
                    record.request.thresholds,
                    dataset.evidence.id,
                )
                expires_at = None
            elif resolution.mode == AnalysisMode.OBSERVED:
                start, end = _source_date_bounds(target_dates)
                dataset = self.daily_provider.fetch_daily(
                    site, start, end, purpose="observed_reanalysis"
                )
                outcome = evaluate_observed(
                    dataset.observations,
                    target_dates,
                    record.request.thresholds,
                    dataset.evidence.id,
                )
                expires_at = None
            else:
                self._run_unavailable_horizon(resolution.mode)
                raise AssertionError("unavailable provider must raise")

            status = AnalysisStatus.PARTIAL if outcome.data_gaps else AnalysisStatus.COMPLETE
            decision = make_decision(outcome.findings)
            operational_findings = []
            operational_limitations: list[str] = []
            if asset is not None:
                operational_findings, operational_limitations = evaluate_operational_rules(
                    asset, outcome.findings
                )
            completed = record.assessment.model_copy(
                update={
                    "status": status,
                    "resolved_mode": resolution.mode,
                    "generated_at": self.now_fn(),
                    "expires_at": expires_at,
                    "source_freshness": [
                        SourceFreshness(
                            provider=dataset.evidence.provider,
                            status="current",
                            retrieved_at=dataset.evidence.retrieved_at,
                            valid_until=expires_at,
                        )
                    ],
                    "site": site,
                    "findings": outcome.findings,
                    "operational_findings": operational_findings,
                    "decision": decision,
                    "evidence_ids": [dataset.evidence.id],
                    "data_gaps": outcome.data_gaps,
                    "limitations": [*outcome.limitations, *operational_limitations],
                }
            )
            self.repository.update_analysis(
                analysis_id, completed, [dataset.evidence], actor_id="system"
            )
        except ProviderUnavailable as exc:
            self._store_unavailable(record, exc)
        except Exception:
            logger.exception("Analysis job failed", extra={"analysis_id": str(analysis_id)})
            failed = record.assessment.model_copy(
                update={
                    "status": AnalysisStatus.FAILED,
                    "generated_at": self.now_fn(),
                    "decision": AnalysisDecision(
                        status=Decision.INSUFFICIENT_EVIDENCE,
                        rationale="The analysis could not complete; no decision was made.",
                    ),
                    "data_gaps": [
                        "The analysis job failed before source-backed evidence was available."
                    ],
                    "limitations": [
                        "No synthetic data or fallback probability was returned after the failure."
                    ],
                }
            )
            self.repository.update_analysis(analysis_id, failed, [], actor_id="system")

    def _store_unavailable(self, record: StoredAnalysis, exc: ProviderUnavailable) -> None:
        unavailable = record.assessment.model_copy(
            update={
                "status": AnalysisStatus.PARTIAL,
                "generated_at": self.now_fn(),
                "decision": AnalysisDecision(
                    status=Decision.INSUFFICIENT_EVIDENCE,
                    rationale="A required source was unavailable, so NimbusX did not make an asset-risk decision.",
                ),
                "source_freshness": [
                    SourceFreshness(
                        provider=(exc.details or {}).get("provider", "required source"),
                        status="unavailable",
                        message=exc.message,
                    )
                ],
                "data_gaps": [exc.message],
                "limitations": [
                    "No synthetic weather, climatology substitute, or fabricated confidence was used."
                ],
            }
        )
        self.repository.update_analysis(record.assessment.id, unavailable, [], actor_id="system")

    def _run_unavailable_horizon(self, mode: AnalysisMode) -> None:
        if mode == AnalysisMode.FORECAST:
            self.forecast_provider.fetch()
        elif mode == AnalysisMode.SEASONAL:
            self.seasonal_provider.fetch()
        elif mode == AnalysisMode.SCENARIO:
            self.scenario_provider.fetch()
        raise ProviderUnavailable("No source adapter exists for this requested mode")

    def get_assessment(self, analysis_id: UUID) -> Assessment:
        return self.repository.get_analysis(analysis_id).assessment

    def get_evidence(self, analysis_id: UUID) -> EvidenceResponse:
        record = self.repository.get_analysis(analysis_id)
        return EvidenceResponse(
            analysis_id=analysis_id,
            evidence=[EvidenceManifestRecord.from_internal(item) for item in record.evidence],
        )

    def compare(self, analysis_id: UUID, request: CompareRequest) -> ComparisonResponse:
        identifiers = [analysis_id, *request.analysis_ids]
        seen: set[UUID] = set()
        records: list[StoredAnalysis] = []
        for identifier in identifiers:
            if identifier in seen:
                continue
            seen.add(identifier)
            record = self.repository.get_analysis(identifier)
            if record.assessment.status in {AnalysisStatus.QUEUED, AnalysisStatus.RUNNING}:
                raise AnalysisNotReady(str(identifier))
            records.append(record)
        return ComparisonResponse(
            comparison=ComparisonType.SELECTED_ASSESSMENTS,
            analyses=[
                ComparisonItem(
                    analysis_id=record.assessment.id,
                    site_name=record.assessment.site.name,
                    status=record.assessment.status,
                    mode=record.assessment.resolved_mode,
                    decision=(
                        record.assessment.decision.status
                        if record.assessment.decision is not None
                        else None
                    ),
                    findings=record.assessment.findings,
                )
                for record in records
            ],
            limitations=[
                "This endpoint lists selected terminal assessment summaries only. It does not calculate aligned changes, deltas, or rankings by window, site, baseline, or scenario."
            ],
        )

    def report_manifest(self, analysis_id: UUID) -> dict[str, Any]:
        """Build a traceable report manifest without exposing raw source extracts."""

        record = self.repository.get_analysis(analysis_id)
        assessment_payload = record.assessment.model_dump(mode="json")
        evidence_payload = [
            EvidenceManifestRecord.from_internal(item).model_dump(mode="json")
            for item in record.evidence
        ]
        hash_payload = {
            "assessment": assessment_payload,
            "evidence": evidence_payload,
            "report_version": record.assessment.report_version,
        }
        content_hash = sha256(
            json.dumps(hash_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return {
            "analysis": assessment_payload,
            "evidence": evidence_payload,
            "report_version": record.assessment.report_version,
            "content_hash": content_hash,
            "generated_at": self.now_fn().isoformat(),
            "limitations": [
                "This on-demand report is traceable to the listed evidence manifests but is not durably immutable in the process-local development repository.",
                "No raw provider extract or normalized daily time series is included in this browser-facing report.",
            ],
        }

    def report_csv(self, analysis_id: UUID) -> str:
        manifest = self.report_manifest(analysis_id)
        assessment = self.get_assessment(analysis_id)
        stream = StringIO()
        writer = csv.writer(stream)
        writer.writerow(
            [
                "report_version",
                "report_content_hash",
                "record_type",
                "analysis_id",
                "status",
                "mode",
                "hazard",
                "finding_status",
                "metric",
                "operator",
                "threshold",
                "unit",
                "likelihood",
                "observed_value",
                "sample_size",
                "severity",
                "evidence_ids",
                "operational_rule_id",
                "operational_status",
                "action",
                "rationale",
                "missing_exposure_fields",
                "missing_vulnerability_fields",
            ]
        )
        for finding in assessment.findings:
            writer.writerow(
                [
                    assessment.report_version,
                    manifest["content_hash"],
                    "hazard_finding",
                    assessment.id,
                    assessment.status.value,
                    assessment.resolved_mode.value if assessment.resolved_mode else "",
                    finding.hazard.value,
                    finding.status.value,
                    finding.metric,
                    finding.operator,
                    finding.threshold,
                    finding.unit,
                    finding.likelihood,
                    finding.observed_value,
                    finding.sample_size,
                    finding.severity.value,
                    ";".join(str(identifier) for identifier in finding.evidence_ids),
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )
        for finding in assessment.operational_findings:
            writer.writerow(
                [
                    assessment.report_version,
                    manifest["content_hash"],
                    "operational_finding",
                    assessment.id,
                    assessment.status.value,
                    assessment.resolved_mode.value if assessment.resolved_mode else "",
                    finding.hazard.value,
                    finding.source_finding_status.value,
                    "",
                    "",
                    "",
                    "",
                    "",
                    finding.source_severity.value,
                    ";".join(str(identifier) for identifier in finding.evidence_ids),
                    finding.rule_id,
                    finding.status.value,
                    finding.action or "",
                    finding.rationale,
                    ";".join(finding.missing_exposure_fields),
                    ";".join(finding.missing_vulnerability_fields),
                ]
            )
        return stream.getvalue()

    def create_project(
        self, request: ProjectCreate, *, actor_id: str, organization_id: str
    ) -> Project:
        project = Project(
            name=request.name, organization_id=request.organization_id or organization_id
        )
        return self.repository.create_project(project, actor_id=actor_id)

    def list_projects(self) -> list[Project]:
        return self.repository.list_projects()

    def create_site(self, project_id: UUID, site: SiteInput, *, actor_id: str) -> StoredSite:
        self.repository.get_project(project_id)
        stored = StoredSite(project_id=project_id, **site.model_dump())
        return self.repository.create_site(stored, actor_id=actor_id)

    def list_project_assessments(self, project_id: UUID) -> list[Assessment]:
        self.repository.get_project(project_id)
        return self.repository.list_project_assessments(project_id)

    def list_asset_templates(self) -> list[AssetTemplate]:
        return list_templates()

    def create_asset(
        self, project_id: UUID, request: PortfolioAssetCreate, *, actor_id: str
    ) -> PortfolioAsset:
        self.repository.get_project(project_id)
        if get_template(request.template_id) is None:
            raise ApiProblem(
                "asset_template_not_found",
                f"Asset template '{request.template_id}' is not in the published catalog.",
                422,
            )
        site = self.repository.get_site(request.site_id)
        if site.project_id != project_id:
            raise ApiProblem(
                "asset_site_project_mismatch",
                "An asset may only reference a site in the same project.",
                422,
            )
        asset = PortfolioAsset(project_id=project_id, **request.model_dump())
        return self.repository.create_asset(asset, actor_id=actor_id)

    def list_project_assets(self, project_id: UUID) -> list[PortfolioAsset]:
        self.repository.get_project(project_id)
        return self.repository.list_project_assets(project_id)

    def import_assets(
        self, project_id: UUID, request: AssetImportRequest, *, actor_id: str
    ) -> AssetImportResult:
        """Validate and optionally create Point-backed assets from CSV or GeoJSON.

        A bad row never causes NimbusX to guess a coordinate, timezone, template,
        or source-backed site.  Valid rows are independent so import callers can
        correct only the rejected rows.
        """

        self.repository.get_project(project_id)
        if request.default_template_id and get_template(request.default_template_id) is None:
            raise ApiProblem(
                "asset_template_not_found",
                f"Asset template '{request.default_template_id}' is not in the published catalog.",
                422,
            )
        rows = (
            _csv_import_rows(request.csv_text or "")
            if request.csv_text is not None
            else _geojson_import_rows(request.geojson or {})
        )
        results: list[AssetImportRowResult] = []
        created_count = 0
        rejected_count = 0
        for row_number, values in rows:
            raw_name = _text(values.get("name"))
            try:
                if "__row_error" in values:
                    raise ValueError(str(values["__row_error"]))
                if raw_name is None:
                    raise ValueError("name is required")
                template_id = _text(values.get("template_id")) or request.default_template_id
                if template_id is None:
                    raise ValueError(
                        "template_id is required unless default_template_id is supplied"
                    )
                if get_template(template_id) is None:
                    raise ValueError(f"template_id '{template_id}' is not in the published catalog")
                existing_site_id = _text(values.get("site_id"))
                has_latitude = _text(values.get("latitude")) is not None
                has_longitude = _text(values.get("longitude")) is not None
                if existing_site_id and (has_latitude or has_longitude):
                    raise ValueError("provide either site_id or latitude/longitude, not both")
                imported_site: StoredSite | None = None
                if existing_site_id:
                    site_id = UUID(existing_site_id)
                    existing_site = self.repository.get_site(site_id)
                    if existing_site.project_id != project_id:
                        raise ValueError("site_id belongs to another project")
                else:
                    if not has_latitude or not has_longitude:
                        raise ValueError(
                            "latitude and longitude are required when site_id is not supplied"
                        )
                    timezone = _text(values.get("timezone"))
                    if timezone is None:
                        raise ValueError("timezone is required when site_id is not supplied")
                    imported_site = StoredSite(
                        project_id=project_id,
                        name=_text(values.get("site_name")) or raw_name,
                        latitude=values["latitude"],
                        longitude=values["longitude"],
                        timezone=timezone,
                        address=_text(values.get("address")),
                    )
                    site_id = imported_site.id

                exposure = _import_context(values, "exposure")
                vulnerability = _import_context(values, "vulnerability")
                asset_request = PortfolioAssetCreate.model_validate(
                    {
                        "name": raw_name,
                        "site_id": site_id,
                        "template_id": template_id,
                        "external_id": _text(values.get("external_id")),
                        "criticality": _text(values.get("criticality")) or "medium",
                        "tags": _import_tags(values.get("tags")),
                        "exposure": exposure,
                        "vulnerability": vulnerability,
                    }
                )
                asset = PortfolioAsset(project_id=project_id, **asset_request.model_dump())
                if not request.dry_run:
                    if imported_site is not None:
                        self.repository.create_imported_site_asset(
                            imported_site, asset, actor_id=actor_id
                        )
                    else:
                        self.repository.create_asset(asset, actor_id=actor_id)
                created_count += 1
                results.append(
                    AssetImportRowResult(
                        row_number=row_number,
                        name=raw_name,
                        status="validated" if request.dry_run else "created",
                        asset_id=None if request.dry_run else asset.id,
                        site_id=None if request.dry_run else asset.site_id,
                        message=(
                            "Row passed validation; dry_run did not persist an asset."
                            if request.dry_run
                            else "Asset and its required point site were created."
                        ),
                    )
                )
            except ApiProblem as exc:
                rejected_count += 1
                results.append(
                    AssetImportRowResult(
                        row_number=row_number,
                        name=raw_name,
                        status="rejected",
                        code=exc.code,
                        message=exc.message,
                    )
                )
            except (TypeError, ValueError) as exc:
                rejected_count += 1
                results.append(
                    AssetImportRowResult(
                        row_number=row_number,
                        name=raw_name,
                        status="rejected",
                        code="invalid_asset_row",
                        message=str(exc),
                    )
                )
        status = "complete" if rejected_count == 0 else "partial" if created_count else "failed"
        return AssetImportResult(
            project_id=project_id,
            dry_run=request.dry_run,
            status=status,
            created_count=created_count,
            rejected_count=rejected_count,
            rows=results,
            limitations=[
                "Import state is process-local in this foundation and is lost when the API restarts.",
                "Only Point CSV/GeoJSON assets are imported. Addresses are not geocoded and polygons are not spatially aggregated.",
                "Imported exposure and vulnerability fields enable published screening rules only; they do not create an asset-risk verdict.",
            ],
        )

    def create_alert_rule(
        self, project_id: UUID, request: AlertRuleCreate, *, actor_id: str
    ) -> AlertRule:
        self.repository.get_project(project_id)
        if request.asset_id is not None:
            asset = self.repository.get_asset(request.asset_id)
            if asset.project_id != project_id:
                raise ApiProblem(
                    "alert_rule_asset_project_mismatch",
                    "An alert rule may only reference an asset in the same project.",
                    422,
                )
        rule = AlertRule(project_id=project_id, **request.model_dump())
        return self.repository.create_alert_rule(rule, actor_id=actor_id)

    def list_project_alert_rules(self, project_id: UUID) -> list[AlertRule]:
        self.repository.get_project(project_id)
        return self.repository.list_project_alert_rules(project_id)

    def list_project_alert_events(self, project_id: UUID) -> list[AlertEvent]:
        self.repository.get_project(project_id)
        return self.repository.list_project_alert_events(project_id)

    def create_notification_channel(
        self,
        project_id: UUID,
        request: NotificationChannelCreate,
        *,
        actor_id: str,
    ) -> NotificationChannel:
        """Register a reviewed target without accepting or returning a secret value."""

        self.repository.get_project(project_id)
        channel = NotificationChannel(
            project_id=project_id,
            name=request.name,
            kind=request.kind,
            target=request.target,
            enabled=request.enabled,
            delivery_mode=request.delivery_mode,
            has_secret_reference=request.secret_reference is not None,
            created_at=self.now_fn(),
        )
        return self.repository.create_notification_channel(
            channel,
            secret_reference=request.secret_reference,
            actor_id=actor_id,
        )

    def list_project_notification_channels(self, project_id: UUID) -> list[NotificationChannel]:
        self.repository.get_project(project_id)
        return self.repository.list_project_notification_channels(project_id)

    def list_notification_receipts(
        self, project_id: UUID, event_id: UUID
    ) -> list[NotificationDispatchReceipt]:
        self.repository.get_project(project_id)
        event = self.repository.get_alert_event(event_id)
        if event.project_id != project_id:
            raise ApiProblem(
                "alert_event_project_mismatch", "Alert event is not in this project.", 404
            )
        return self.repository.list_alert_event_notification_receipts(event_id)

    def dispatch_alert_event(
        self,
        project_id: UUID,
        event_id: UUID,
        channel_id: UUID,
        *,
        actor_id: str,
    ) -> NotificationDispatchReceipt:
        """Persist a dry-run/unavailable receipt; this function has no network side effect."""

        self.repository.get_project(project_id)
        event = self.repository.get_alert_event(event_id)
        if event.project_id != project_id:
            raise ApiProblem(
                "alert_event_project_mismatch", "Alert event is not in this project.", 404
            )
        channel = self.repository.get_notification_channel_config(channel_id)
        if channel.project_id != project_id:
            raise ApiProblem(
                "notification_channel_project_mismatch",
                "Notification channel is not in this project.",
                404,
            )
        internal_receipt = dispatch_notification(event, channel, now=self.now_fn())
        receipt = NotificationDispatchReceipt(
            id=internal_receipt.id,
            project_id=project_id,
            alert_event_id=internal_receipt.alert_event_id,
            channel_id=internal_receipt.channel_id,
            status=internal_receipt.status,
            created_at=internal_receipt.created_at,
            message=internal_receipt.message,
            payload=internal_receipt.payload,
        )
        return self.repository.create_notification_receipt(receipt, actor_id=actor_id)

    def evaluate_alert_rule(
        self,
        project_id: UUID,
        rule_id: UUID,
        request: AlertEvaluateRequest,
        *,
        actor_id: str,
    ) -> AlertEvaluationResponse:
        self.repository.get_project(project_id)
        rule = self.repository.get_alert_rule(rule_id)
        if rule.project_id != project_id:
            raise ApiProblem(
                "alert_rule_project_mismatch", "Alert rule is not in this project.", 404
            )
        if not rule.enabled:
            return AlertEvaluationResponse(
                rule=rule,
                created_count=0,
                existing_count=0,
                limitations=["This alert rule is disabled; no assessment findings were evaluated."],
            )

        events: list[AlertEvent] = []
        skipped: list[AlertEvaluationSkip] = []
        created_count = 0
        existing_count = 0
        for analysis_id in request.analysis_ids:
            record = self.repository.get_analysis(analysis_id)
            assessment = record.assessment
            if assessment.project_id != project_id:
                raise ApiProblem(
                    "analysis_project_mismatch",
                    "Every assessment supplied for alert evaluation must belong to this project.",
                    422,
                )
            if assessment.status in {AnalysisStatus.QUEUED, AnalysisStatus.RUNNING}:
                skipped.append(
                    AlertEvaluationSkip(
                        analysis_id=analysis_id,
                        reason="Assessment is not terminal and has no completed source-backed findings.",
                    )
                )
                continue
            if rule.asset_id is not None and assessment.asset_id != rule.asset_id:
                skipped.append(
                    AlertEvaluationSkip(
                        analysis_id=analysis_id,
                        reason="Assessment is not linked to the asset scoped by this alert rule.",
                    )
                )
                continue
            finding = next(
                (item for item in assessment.findings if item.hazard == rule.hazard), None
            )
            if finding is None or finding.status != FindingStatus.AVAILABLE:
                skipped.append(
                    AlertEvaluationSkip(
                        analysis_id=analysis_id,
                        reason="No available source-backed finding exists for this rule's hazard.",
                    )
                )
                continue
            event_kind = self._alert_event_kind(rule, assessment.resolved_mode, finding)
            if event_kind is None:
                continue
            event = AlertEvent(
                project_id=project_id,
                rule_id=rule.id,
                asset_id=assessment.asset_id,
                analysis_id=assessment.id,
                hazard=rule.hazard,
                event_kind=event_kind,
                summary=self._alert_summary(rule, assessment, finding, event_kind),
                evidence_ids=finding.evidence_ids,
                created_at=self.now_fn(),
            )
            stored, created = self.repository.create_alert_event_if_absent(event, actor_id=actor_id)
            events.append(stored)
            if created:
                created_count += 1
            else:
                existing_count += 1
        return AlertEvaluationResponse(
            rule=rule,
            events=events,
            created_count=created_count,
            existing_count=existing_count,
            skipped=skipped,
            limitations=[
                "Alert events are derived from completed source-backed findings only. They do not forecast a future threshold breach.",
                "Events are recorded in the process-local development store. Notification delivery is not configured by this endpoint.",
            ],
        )

    @staticmethod
    def _alert_event_kind(
        rule: AlertRule, resolved_mode: AnalysisMode | None, finding: HazardFinding
    ) -> AlertEventKind | None:
        if rule.trigger_type == AlertTriggerType.OBSERVED_THRESHOLD_BREACH:
            if resolved_mode != AnalysisMode.OBSERVED or finding.severity.value != "high":
                return None
            return AlertEventKind.OBSERVED_THRESHOLD_BREACH
        if rule.trigger_type == AlertTriggerType.BASELINE_LIKELIHOOD:
            if (
                resolved_mode != AnalysisMode.BASELINE
                or finding.likelihood is None
                or rule.minimum_likelihood is None
                or finding.likelihood < rule.minimum_likelihood
            ):
                return None
            return AlertEventKind.HISTORICAL_PATTERN
        if rule.minimum_severity is None or not severity_at_least(
            finding.severity, rule.minimum_severity
        ):
            return None
        return AlertEventKind.SEVERITY_TRIGGER

    @staticmethod
    def _alert_summary(
        rule: AlertRule,
        assessment: Assessment,
        finding: HazardFinding,
        event_kind: AlertEventKind,
    ) -> str:
        if event_kind == AlertEventKind.OBSERVED_THRESHOLD_BREACH:
            return (
                f"{rule.name}: observed {finding.hazard.value} threshold condition was met in "
                f"assessment {assessment.id}."
            )
        if event_kind == AlertEventKind.HISTORICAL_PATTERN:
            return (
                f"{rule.name}: historical {finding.hazard.value} event-window likelihood "
                f"({finding.likelihood:.0%}) met the configured screening threshold."
            )
        return (
            f"{rule.name}: source-backed {finding.hazard.value} screening severity "
            f"({finding.severity.value}) met the configured rule."
        )

    def _resolve_target(
        self, request: AnalysisCreateRequest
    ) -> tuple[SiteInput, UUID | None, PortfolioAsset | None]:
        if request.asset_id is not None:
            asset = self.repository.get_asset(request.asset_id)
            if request.project_id is not None and request.project_id != asset.project_id:
                raise ApiProblem(
                    "asset_project_mismatch",
                    "The supplied asset does not belong to the supplied project",
                    422,
                )
            stored_site = self.repository.get_site(asset.site_id)
            return (
                _require_assessable_point_site(_as_site_input(stored_site)),
                asset.project_id,
                asset,
            )
        if request.site is not None:
            if request.project_id is not None:
                self.repository.get_project(request.project_id)
            return _require_assessable_point_site(request.site), request.project_id, None
        assert request.site_id is not None
        stored = self.repository.get_site(request.site_id)
        if request.project_id is not None and stored.project_id != request.project_id:
            raise ApiProblem(
                "site_project_mismatch",
                "The supplied site does not belong to the supplied project",
                422,
            )
        return _require_assessable_point_site(_as_site_input(stored)), stored.project_id, None
