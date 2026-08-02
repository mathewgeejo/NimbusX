"""Repository boundary.

The default implementation is explicitly an in-memory development repository.
The narrow methods are intentionally suitable for a Postgres/PostGIS-backed
implementation without changing public API semantics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from uuid import UUID

from .errors import NotFound
from .schemas import (
    AnalysisCreateRequest,
    Assessment,
    AuditEvent,
    EvidenceRecord,
    Project,
    StoredSite,
)


@dataclass(slots=True)
class StoredAnalysis:
    request: AnalysisCreateRequest
    assessment: Assessment
    evidence: list[EvidenceRecord] = field(default_factory=list)


class InMemoryRepository:
    """Thread-safe local repository; state resets whenever the process restarts."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._projects: dict[UUID, Project] = {}
        self._sites: dict[UUID, StoredSite] = {}
        self._analyses: dict[UUID, StoredAnalysis] = {}
        self._audit_events: list[AuditEvent] = []

    def create_project(self, project: Project, *, actor_id: str) -> Project:
        with self._lock:
            self._projects[project.id] = project.model_copy(deep=True)
            self._audit_events.append(
                AuditEvent(
                    actor_id=actor_id,
                    action="project.created",
                    resource_type="project",
                    resource_id=project.id,
                )
            )
            return project.model_copy(deep=True)

    def list_projects(self) -> list[Project]:
        with self._lock:
            return [project.model_copy(deep=True) for project in self._projects.values()]

    def get_project(self, project_id: UUID) -> Project:
        with self._lock:
            project = self._projects.get(project_id)
            if project is None:
                raise NotFound("Project", str(project_id))
            return project.model_copy(deep=True)

    def create_site(self, site: StoredSite, *, actor_id: str) -> StoredSite:
        with self._lock:
            if site.project_id not in self._projects:
                raise NotFound("Project", str(site.project_id))
            self._sites[site.id] = site.model_copy(deep=True)
            self._audit_events.append(
                AuditEvent(
                    actor_id=actor_id,
                    action="site.created",
                    resource_type="site",
                    resource_id=site.id,
                    details={"project_id": str(site.project_id)},
                )
            )
            return site.model_copy(deep=True)

    def get_site(self, site_id: UUID) -> StoredSite:
        with self._lock:
            site = self._sites.get(site_id)
            if site is None:
                raise NotFound("Site", str(site_id))
            return site.model_copy(deep=True)

    def put_analysis(self, analysis: StoredAnalysis, *, actor_id: str) -> None:
        with self._lock:
            self._analyses[analysis.assessment.id] = StoredAnalysis(
                request=analysis.request.model_copy(deep=True),
                assessment=analysis.assessment.model_copy(deep=True),
                evidence=[item.model_copy(deep=True) for item in analysis.evidence],
            )
            self._audit_events.append(
                AuditEvent(
                    actor_id=actor_id,
                    action="analysis.created",
                    resource_type="analysis",
                    resource_id=analysis.assessment.id,
                )
            )

    def get_analysis(self, analysis_id: UUID) -> StoredAnalysis:
        with self._lock:
            record = self._analyses.get(analysis_id)
            if record is None:
                raise NotFound("Analysis", str(analysis_id))
            return StoredAnalysis(
                request=record.request.model_copy(deep=True),
                assessment=record.assessment.model_copy(deep=True),
                evidence=[item.model_copy(deep=True) for item in record.evidence],
            )

    def list_project_assessments(self, project_id: UUID) -> list[Assessment]:
        with self._lock:
            if project_id not in self._projects:
                raise NotFound("Project", str(project_id))
            records = [
                record.assessment.model_copy(deep=True)
                for record in self._analyses.values()
                if record.assessment.project_id == project_id
            ]
            return sorted(records, key=lambda assessment: assessment.created_at, reverse=True)

    def update_analysis(
        self,
        analysis_id: UUID,
        assessment: Assessment,
        evidence: list[EvidenceRecord],
        *,
        actor_id: str = "system",
    ) -> None:
        with self._lock:
            current = self._analyses.get(analysis_id)
            if current is None:
                raise NotFound("Analysis", str(analysis_id))
            self._analyses[analysis_id] = StoredAnalysis(
                request=current.request.model_copy(deep=True),
                assessment=assessment.model_copy(deep=True),
                evidence=[item.model_copy(deep=True) for item in evidence],
            )
            self._audit_events.append(
                AuditEvent(
                    actor_id=actor_id,
                    action=f"analysis.{assessment.status.value}",
                    resource_type="analysis",
                    resource_id=analysis_id,
                )
            )

    def audit_events(self) -> list[AuditEvent]:
        with self._lock:
            return [event.model_copy(deep=True) for event in self._audit_events]
