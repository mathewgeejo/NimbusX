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
from .notifications import NotificationChannelConfig
from .schemas import (
    AlertEvent,
    AlertRule,
    AnalysisCreateRequest,
    Assessment,
    AuditEvent,
    EvidenceRecord,
    NotificationChannel,
    NotificationDispatchReceipt,
    PortfolioAsset,
    Project,
    StoredSite,
)


@dataclass(slots=True)
class StoredAnalysis:
    request: AnalysisCreateRequest
    assessment: Assessment
    evidence: list[EvidenceRecord] = field(default_factory=list)


@dataclass(slots=True)
class StoredNotificationChannel:
    """Internal channel state retaining only a secret-manager reference."""

    channel: NotificationChannel
    secret_reference: str | None = None


class InMemoryRepository:
    """Thread-safe local repository; state resets whenever the process restarts."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._projects: dict[UUID, Project] = {}
        self._sites: dict[UUID, StoredSite] = {}
        self._assets: dict[UUID, PortfolioAsset] = {}
        self._analyses: dict[UUID, StoredAnalysis] = {}
        self._alert_rules: dict[UUID, AlertRule] = {}
        self._alert_events: dict[UUID, AlertEvent] = {}
        self._alert_event_keys: dict[tuple[UUID, UUID, str], UUID] = {}
        self._notification_channels: dict[UUID, StoredNotificationChannel] = {}
        self._notification_receipts: dict[UUID, NotificationDispatchReceipt] = {}
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

    def create_asset(self, asset: PortfolioAsset, *, actor_id: str) -> PortfolioAsset:
        with self._lock:
            if asset.project_id not in self._projects:
                raise NotFound("Project", str(asset.project_id))
            site = self._sites.get(asset.site_id)
            if site is None:
                raise NotFound("Site", str(asset.site_id))
            if site.project_id != asset.project_id:
                raise ValueError("asset site must belong to the asset project")
            self._assets[asset.id] = asset.model_copy(deep=True)
            self._audit_events.append(
                AuditEvent(
                    actor_id=actor_id,
                    action="asset.created",
                    resource_type="asset",
                    resource_id=asset.id,
                    details={
                        "project_id": str(asset.project_id),
                        "site_id": str(asset.site_id),
                        "template_id": asset.template_id,
                    },
                )
            )
            return asset.model_copy(deep=True)

    def create_imported_site_asset(
        self, site: StoredSite, asset: PortfolioAsset, *, actor_id: str
    ) -> tuple[StoredSite, PortfolioAsset]:
        """Atomically create an imported point site and its attached asset."""

        with self._lock:
            if site.project_id not in self._projects:
                raise NotFound("Project", str(site.project_id))
            if asset.project_id != site.project_id or asset.site_id != site.id:
                raise ValueError("imported asset must reference the imported project site")
            self._sites[site.id] = site.model_copy(deep=True)
            self._assets[asset.id] = asset.model_copy(deep=True)
            self._audit_events.extend(
                [
                    AuditEvent(
                        actor_id=actor_id,
                        action="site.imported",
                        resource_type="site",
                        resource_id=site.id,
                        details={"project_id": str(site.project_id)},
                    ),
                    AuditEvent(
                        actor_id=actor_id,
                        action="asset.imported",
                        resource_type="asset",
                        resource_id=asset.id,
                        details={
                            "project_id": str(asset.project_id),
                            "site_id": str(asset.site_id),
                            "template_id": asset.template_id,
                        },
                    ),
                ]
            )
            return site.model_copy(deep=True), asset.model_copy(deep=True)

    def get_asset(self, asset_id: UUID) -> PortfolioAsset:
        with self._lock:
            asset = self._assets.get(asset_id)
            if asset is None:
                raise NotFound("Asset", str(asset_id))
            return asset.model_copy(deep=True)

    def list_project_assets(self, project_id: UUID) -> list[PortfolioAsset]:
        with self._lock:
            if project_id not in self._projects:
                raise NotFound("Project", str(project_id))
            assets = [
                asset.model_copy(deep=True)
                for asset in self._assets.values()
                if asset.project_id == project_id
            ]
            return sorted(assets, key=lambda asset: (asset.name.casefold(), str(asset.id)))

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

    def list_project_analysis_records(self, project_id: UUID) -> list[StoredAnalysis]:
        """Return assessment records for explicit alert-rule evaluation."""

        with self._lock:
            if project_id not in self._projects:
                raise NotFound("Project", str(project_id))
            records = [
                StoredAnalysis(
                    request=record.request.model_copy(deep=True),
                    assessment=record.assessment.model_copy(deep=True),
                    evidence=[item.model_copy(deep=True) for item in record.evidence],
                )
                for record in self._analyses.values()
                if record.assessment.project_id == project_id
            ]
            return sorted(records, key=lambda record: record.assessment.created_at, reverse=True)

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

    def create_alert_rule(self, rule: AlertRule, *, actor_id: str) -> AlertRule:
        with self._lock:
            if rule.project_id not in self._projects:
                raise NotFound("Project", str(rule.project_id))
            if rule.asset_id is not None:
                asset = self._assets.get(rule.asset_id)
                if asset is None:
                    raise NotFound("Asset", str(rule.asset_id))
                if asset.project_id != rule.project_id:
                    raise ValueError("alert rule asset must belong to the alert rule project")
            self._alert_rules[rule.id] = rule.model_copy(deep=True)
            self._audit_events.append(
                AuditEvent(
                    actor_id=actor_id,
                    action="alert_rule.created",
                    resource_type="alert_rule",
                    resource_id=rule.id,
                    details={"project_id": str(rule.project_id), "hazard": rule.hazard.value},
                )
            )
            return rule.model_copy(deep=True)

    def get_alert_rule(self, rule_id: UUID) -> AlertRule:
        with self._lock:
            rule = self._alert_rules.get(rule_id)
            if rule is None:
                raise NotFound("Alert rule", str(rule_id))
            return rule.model_copy(deep=True)

    def list_project_alert_rules(self, project_id: UUID) -> list[AlertRule]:
        with self._lock:
            if project_id not in self._projects:
                raise NotFound("Project", str(project_id))
            rules = [
                rule.model_copy(deep=True)
                for rule in self._alert_rules.values()
                if rule.project_id == project_id
            ]
            return sorted(rules, key=lambda rule: (rule.name.casefold(), str(rule.id)))

    def get_alert_event(self, event_id: UUID) -> AlertEvent:
        with self._lock:
            event = self._alert_events.get(event_id)
            if event is None:
                raise NotFound("Alert event", str(event_id))
            return event.model_copy(deep=True)

    def list_project_alert_events(self, project_id: UUID) -> list[AlertEvent]:
        with self._lock:
            if project_id not in self._projects:
                raise NotFound("Project", str(project_id))
            events = [
                event.model_copy(deep=True)
                for event in self._alert_events.values()
                if event.project_id == project_id
            ]
            return sorted(events, key=lambda event: event.created_at, reverse=True)

    def create_alert_event_if_absent(
        self, event: AlertEvent, *, actor_id: str
    ) -> tuple[AlertEvent, bool]:
        """Persist one immutable event per rule, assessment, and hazard."""

        event_key = (event.rule_id, event.analysis_id, event.hazard.value)
        with self._lock:
            existing_id = self._alert_event_keys.get(event_key)
            if existing_id is not None:
                existing = self._alert_events[existing_id]
                return existing.model_copy(deep=True), False
            self._alert_events[event.id] = event.model_copy(deep=True)
            self._alert_event_keys[event_key] = event.id
            self._audit_events.append(
                AuditEvent(
                    actor_id=actor_id,
                    action="alert_event.recorded",
                    resource_type="alert_event",
                    resource_id=event.id,
                    details={
                        "project_id": str(event.project_id),
                        "rule_id": str(event.rule_id),
                        "analysis_id": str(event.analysis_id),
                        "delivery_status": event.delivery_status.value,
                    },
                )
            )
            return event.model_copy(deep=True), True

    def create_notification_channel(
        self,
        channel: NotificationChannel,
        *,
        secret_reference: str | None,
        actor_id: str,
    ) -> NotificationChannel:
        """Persist a non-secret channel target for a project-local dry run."""

        with self._lock:
            if channel.project_id not in self._projects:
                raise NotFound("Project", str(channel.project_id))
            self._notification_channels[channel.id] = StoredNotificationChannel(
                channel=channel.model_copy(deep=True),
                secret_reference=secret_reference,
            )
            self._audit_events.append(
                AuditEvent(
                    actor_id=actor_id,
                    action="notification_channel.created",
                    resource_type="notification_channel",
                    resource_id=channel.id,
                    details={
                        "project_id": str(channel.project_id),
                        "kind": channel.kind.value,
                        "delivery_mode": channel.delivery_mode.value,
                        "enabled": channel.enabled,
                        "has_secret_reference": secret_reference is not None,
                    },
                )
            )
            return channel.model_copy(deep=True)

    def list_project_notification_channels(self, project_id: UUID) -> list[NotificationChannel]:
        with self._lock:
            if project_id not in self._projects:
                raise NotFound("Project", str(project_id))
            channels = [
                item.channel.model_copy(deep=True)
                for item in self._notification_channels.values()
                if item.channel.project_id == project_id
            ]
            return sorted(channels, key=lambda channel: (channel.name.casefold(), str(channel.id)))

    def get_notification_channel_config(self, channel_id: UUID) -> NotificationChannelConfig:
        """Return an internal config without ever placing secret references in responses."""

        with self._lock:
            stored = self._notification_channels.get(channel_id)
            if stored is None:
                raise NotFound("Notification channel", str(channel_id))
            channel = stored.channel
            return NotificationChannelConfig(
                id=channel.id,
                project_id=channel.project_id,
                name=channel.name,
                kind=channel.kind,
                target=channel.target,
                enabled=channel.enabled,
                delivery_mode=channel.delivery_mode,
                secret_reference=stored.secret_reference,
            )

    def create_notification_receipt(
        self, receipt: NotificationDispatchReceipt, *, actor_id: str
    ) -> NotificationDispatchReceipt:
        with self._lock:
            event = self._alert_events.get(receipt.alert_event_id)
            if event is None:
                raise NotFound("Alert event", str(receipt.alert_event_id))
            channel = self._notification_channels.get(receipt.channel_id)
            if channel is None:
                raise NotFound("Notification channel", str(receipt.channel_id))
            if (
                event.project_id != receipt.project_id
                or channel.channel.project_id != receipt.project_id
            ):
                raise ValueError("notification receipt project must match its event and channel")
            self._notification_receipts[receipt.id] = receipt.model_copy(deep=True)
            self._audit_events.append(
                AuditEvent(
                    actor_id=actor_id,
                    action="notification_dispatch.recorded",
                    resource_type="notification_receipt",
                    resource_id=receipt.id,
                    details={
                        "project_id": str(receipt.project_id),
                        "alert_event_id": str(receipt.alert_event_id),
                        "channel_id": str(receipt.channel_id),
                        "status": receipt.status.value,
                    },
                )
            )
            return receipt.model_copy(deep=True)

    def list_alert_event_notification_receipts(
        self, event_id: UUID
    ) -> list[NotificationDispatchReceipt]:
        with self._lock:
            if event_id not in self._alert_events:
                raise NotFound("Alert event", str(event_id))
            receipts = [
                receipt.model_copy(deep=True)
                for receipt in self._notification_receipts.values()
                if receipt.alert_event_id == event_id
            ]
            return sorted(receipts, key=lambda receipt: receipt.created_at, reverse=True)

    def audit_events(self) -> list[AuditEvent]:
        with self._lock:
            return [event.model_copy(deep=True) for event in self._audit_events]
