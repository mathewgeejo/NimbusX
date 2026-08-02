"""FastAPI application for the NimbusX evidence-first public v1 API."""

from __future__ import annotations

import secrets
import time
from collections import defaultdict, deque
from datetime import UTC, datetime
from email.utils import format_datetime
from threading import Lock
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from . import __version__
from .config import Settings, get_settings
from .errors import ApiProblem, error_payload
from .providers import DailyClimateProvider, PowerDailyProvider
from .repository import InMemoryRepository
from .schemas import (
    AnalysisCreated,
    AnalysisCreateRequest,
    Assessment,
    CompareRequest,
    ComparisonResponse,
    EvidenceResponse,
    HealthResponse,
    Project,
    ProjectCreate,
    ReadinessResponse,
    SiteInput,
    StoredSite,
)
from .service import AnalysisService


class RateLimiter:
    """Small process-local limiter for development; replace at the edge in production."""

    def __init__(self, requests_per_minute: int) -> None:
        self.limit = requests_per_minute
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allowed(self, client_key: str) -> bool:
        now = time.monotonic()
        cutoff = now - 60
        with self._lock:
            events = self._events[client_key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(now)
            return True


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _actor(
    request: Request,
    x_api_key: Annotated[str | None, Header()] = None,
    x_organization_id: Annotated[str | None, Header()] = None,
) -> tuple[str, str]:
    settings: Settings = request.app.state.settings
    if settings.require_api_key:
        if not x_api_key or not any(
            secrets.compare_digest(x_api_key, configured) for configured in settings.api_keys
        ):
            raise ApiProblem("authentication_required", "A valid X-API-Key is required", 401)
        actor_id = "api-key"
    else:
        actor_id = "development"
    organization_id = x_organization_id or "development"
    return actor_id, organization_id


Actor = Annotated[tuple[str, str], Depends(_actor)]


def create_app(
    *,
    settings: Settings | None = None,
    repository: InMemoryRepository | None = None,
    daily_provider: DailyClimateProvider | None = None,
    now_fn=None,
) -> FastAPI:
    """Build an app with injectable dependencies for contract and provider tests."""

    active_settings = settings or get_settings()
    active_clock = now_fn or (lambda: datetime.now(UTC))
    active_repository = repository or InMemoryRepository()
    provider = daily_provider or PowerDailyProvider(
        timeout_seconds=active_settings.nasa_timeout_seconds,
        endpoint=active_settings.nasa_power_base_url,
    )
    service = AnalysisService(
        active_repository,
        provider,
        max_window_days=active_settings.max_window_days,
        now_fn=active_clock,
    )
    app = FastAPI(
        title="NimbusX Evidence-First Climate Risk API",
        version=__version__,
        description=(
            "Source-backed climate risk assessments. The API never substitutes synthetic "
            "weather, invented confidence, or climatology for an operational forecast."
        ),
    )
    app.state.settings = active_settings
    app.state.repository = active_repository
    app.state.service = service
    app.state.rate_limiter = RateLimiter(active_settings.rate_limit_per_minute)

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(active_settings.allowed_hosts))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(active_settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Accept", "Content-Type", "X-API-Key", "X-Organization-ID", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Deprecation", "Sunset"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-ID") or str(uuid4())
        client_key = request.client.host if request.client else "unknown"
        if not request.app.state.rate_limiter.allowed(client_key):
            response = JSONResponse(
                status_code=429,
                content=error_payload(
                    code="rate_limited",
                    message="Request rate limit exceeded",
                    request_id=request.state.request_id,
                ),
            )
        else:
            response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(ApiProblem)
    async def api_problem_handler(request: Request, exc: ApiProblem) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                request_id=_request_id(request),
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=error_payload(
                code="validation_error",
                message="The request did not match the v1 contract",
                details=details,
                request_id=_request_id(request),
            ),
        )

    @app.get("/healthz", response_model=HealthResponse, tags=["operations"])
    def health() -> HealthResponse:
        return HealthResponse(status="ok", service="nimbusx-api", version=__version__)

    @app.get("/readyz", response_model=ReadinessResponse, tags=["operations"])
    def readiness() -> ReadinessResponse:
        return ReadinessResponse(
            status="degraded",
            persistence="in_memory_development",
            provider="not_checked",
            limitations=[
                "Readiness verifies only the local process configuration; it does not probe NASA POWER reachability or freshness.",
                "The foundation uses process-local persistence and background work; production requires Postgres, object storage, and a durable queue.",
            ],
        )

    @app.post("/v1/projects", response_model=Project, status_code=201, tags=["workspace"])
    def create_project(request: ProjectCreate, actor: Actor, api_request: Request) -> Project:
        actor_id, organization_id = actor
        return api_request.app.state.service.create_project(
            request, actor_id=actor_id, organization_id=organization_id
        )

    @app.get("/v1/projects", response_model=list[Project], tags=["workspace"])
    def list_projects(api_request: Request, actor: Actor) -> list[Project]:
        del actor
        return api_request.app.state.service.list_projects()

    @app.get(
        "/v1/projects/{project_id}/analyses",
        response_model=list[Assessment],
        tags=["workspace"],
    )
    def list_project_assessments(
        project_id: UUID, actor: Actor, api_request: Request
    ) -> list[Assessment]:
        del actor
        return api_request.app.state.service.list_project_assessments(project_id)

    @app.post(
        "/v1/projects/{project_id}/sites",
        response_model=StoredSite,
        status_code=201,
        tags=["workspace"],
    )
    def create_site(
        project_id: UUID, site: SiteInput, actor: Actor, api_request: Request
    ) -> StoredSite:
        actor_id, _ = actor
        return api_request.app.state.service.create_site(project_id, site, actor_id=actor_id)

    @app.post(
        "/v1/analyses",
        response_model=AnalysisCreated,
        status_code=202,
        tags=["analyses"],
    )
    def create_analysis(
        request: AnalysisCreateRequest,
        background_tasks: BackgroundTasks,
        actor: Actor,
        api_request: Request,
    ) -> AnalysisCreated:
        actor_id, _ = actor
        active_service: AnalysisService = api_request.app.state.service
        created = active_service.create_analysis(request, actor_id=actor_id)
        if api_request.app.state.settings.analysis_execution == "inline":
            active_service.run_analysis(created.id)
        else:
            background_tasks.add_task(active_service.run_analysis, created.id)
        return created

    @app.get("/v1/analyses/{analysis_id}", response_model=Assessment, tags=["analyses"])
    def get_analysis(analysis_id: UUID, actor: Actor, api_request: Request) -> Assessment:
        del actor
        return api_request.app.state.service.get_assessment(analysis_id)

    @app.get(
        "/v1/analyses/{analysis_id}/evidence",
        response_model=EvidenceResponse,
        tags=["analyses"],
    )
    def get_evidence(analysis_id: UUID, actor: Actor, api_request: Request) -> EvidenceResponse:
        del actor
        return api_request.app.state.service.get_evidence(analysis_id)

    @app.post(
        "/v1/analyses/{analysis_id}/compare",
        response_model=ComparisonResponse,
        tags=["analyses"],
    )
    def compare_analysis(
        analysis_id: UUID,
        request: CompareRequest,
        actor: Actor,
        api_request: Request,
    ) -> ComparisonResponse:
        del actor
        return api_request.app.state.service.compare(analysis_id, request)

    @app.get("/v1/analyses/{analysis_id}/report", tags=["analyses"])
    def get_report(
        analysis_id: UUID,
        actor: Actor,
        api_request: Request,
        format: str = Query(default="json", pattern="^(json|csv|pdf)$"),
    ) -> Response:
        del actor
        service: AnalysisService = api_request.app.state.service
        if format == "json":
            return JSONResponse(content=service.get_assessment(analysis_id).model_dump(mode="json"))
        if format == "csv":
            return PlainTextResponse(
                service.report_csv(analysis_id),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f'attachment; filename="nimbusx-{analysis_id}.csv"'
                },
            )
        raise ApiProblem(
            "report_format_unavailable",
            "PDF export is not configured in the foundation; use JSON or CSV evidence exports.",
            501,
        )

    @app.post("/api/weather", status_code=202, tags=["legacy"], deprecated=True)
    def legacy_weather_adapter(
        payload: dict,
        background_tasks: BackgroundTasks,
        actor: Actor,
        api_request: Request,
    ) -> JSONResponse:
        """Fixed-sunset compatibility adapter that returns a v1 job, never old fake values."""

        if active_clock() >= active_settings.legacy_weather_adapter_sunset:
            raise ApiProblem(
                "legacy_endpoint_expired",
                "The deprecated /api/weather adapter has reached its configured Sunset date. Use POST /v1/analyses.",
                410,
            )

        try:
            latitude = float(payload["lat"])
            longitude = float(payload["lon"])
            month, day = (int(part) for part in str(payload["date"]).split("-", 1))
            year = int(payload.get("year", datetime.now(UTC).year))
            start = datetime(year, month, day, tzinfo=UTC)
            end = datetime(year, month, day, 23, 59, 59, tzinfo=UTC)
        except (KeyError, TypeError, ValueError) as exc:
            raise ApiProblem(
                "legacy_validation_error",
                "Legacy requests require numeric lat/lon, date as MM-DD, and an optional year.",
                422,
            ) from exc
        request = AnalysisCreateRequest.model_validate(
            {
                "site": {
                    "name": str(payload.get("location") or "Legacy selected location"),
                    "latitude": latitude,
                    "longitude": longitude,
                    "timezone": "UTC",
                },
                "window": {"start": start.isoformat(), "end": end.isoformat()},
                "mode": "auto",
            }
        )
        actor_id, _ = actor
        service: AnalysisService = api_request.app.state.service
        created = service.create_analysis(request, actor_id=actor_id)
        background_tasks.add_task(service.run_analysis, created.id)
        sunset = format_datetime(active_settings.legacy_weather_adapter_sunset, usegmt=True)
        return JSONResponse(
            status_code=202,
            content={
                "deprecated": True,
                "message": "This adapter returns a v1 analysis job and will be removed after the Sunset date.",
                "migration": "POST /v1/analyses",
                "analysis": created.model_dump(mode="json"),
            },
            headers={"Deprecation": "true", "Sunset": sunset},
        )

    @app.get("/api/health", deprecated=True, tags=["legacy"])
    def legacy_health() -> JSONResponse:
        return JSONResponse(
            content={"deprecated": True, "migration": "/healthz"},
            headers={"Deprecation": "true"},
        )

    return app


app = create_app()
