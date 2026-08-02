"""Application service for analysis jobs and workspace records."""

from __future__ import annotations

import csv
import logging
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from io import StringIO
from uuid import UUID, uuid4

from .errors import AnalysisNotReady, ApiProblem, ProviderUnavailable
from .hazards import evaluate_baseline, evaluate_observed, make_decision
from .horizon import HorizonError, resolve_horizon
from .providers import (
    CopernicusSeasonalProvider,
    DailyClimateProvider,
    ECMWFOpenDataProvider,
    NexGddpCmip6Provider,
)
from .repository import InMemoryRepository, StoredAnalysis
from .schemas import (
    AnalysisCreated,
    AnalysisCreateRequest,
    AnalysisDecision,
    AnalysisMode,
    AnalysisStatus,
    Assessment,
    CompareRequest,
    ComparisonItem,
    ComparisonResponse,
    ComparisonType,
    Decision,
    EvidenceManifestRecord,
    EvidenceResponse,
    Project,
    ProjectCreate,
    SiteInput,
    SourceFreshness,
    StoredSite,
)

logger = logging.getLogger(__name__)


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
        site, project_id = self._resolve_site(request)
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
            site, _ = self._resolve_site(record.request)
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
                    "decision": decision,
                    "evidence_ids": [dataset.evidence.id],
                    "data_gaps": outcome.data_gaps,
                    "limitations": outcome.limitations,
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

    def report_csv(self, analysis_id: UUID) -> str:
        assessment = self.get_assessment(analysis_id)
        stream = StringIO()
        writer = csv.writer(stream)
        writer.writerow(
            [
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
            ]
        )
        for finding in assessment.findings:
            writer.writerow(
                [
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

    def _resolve_site(self, request: AnalysisCreateRequest) -> tuple[SiteInput, UUID | None]:
        if request.site is not None:
            if request.project_id is not None:
                self.repository.get_project(request.project_id)
            return _require_assessable_point_site(request.site), request.project_id
        assert request.site_id is not None
        stored = self.repository.get_site(request.site_id)
        if request.project_id is not None and stored.project_id != request.project_id:
            raise ApiProblem(
                "site_project_mismatch",
                "The supplied site does not belong to the supplied project",
                422,
            )
        return _require_assessable_point_site(_as_site_input(stored)), stored.project_id
