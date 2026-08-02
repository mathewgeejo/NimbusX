"""Safe notification preparation for operational alert events.

NimbusX must not make an external call merely because an assessment produced a
finding.  This module builds a compact, evidence-linked notification envelope
and supports deterministic dry-run receipts.  A production dispatcher may
consume the envelope only after a tenant-approved channel, secret reference,
retry policy, and audit store are available.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from .schemas import (
    NotificationChannelKind,
    NotificationDeliveryMode,
    NotificationReceiptStatus,
)


class AlertEventLike(Protocol):
    """The minimal, non-sensitive event shape needed by the dispatcher."""

    id: UUID
    project_id: UUID
    rule_id: UUID
    asset_id: UUID | None
    analysis_id: UUID
    hazard: object
    event_kind: object
    summary: str
    evidence_ids: list[UUID]


@dataclass(frozen=True, slots=True)
class NotificationChannelConfig:
    """A non-secret channel configuration.

    ``target`` is an HTTPS URL for webhooks/Slack or a recipient address for
    email.  It intentionally does not hold a token, password, or webhook
    secret; those belong in a future secret manager and dispatcher.
    """

    id: UUID
    project_id: UUID
    name: str
    kind: NotificationChannelKind
    target: str
    enabled: bool = True
    delivery_mode: NotificationDeliveryMode = NotificationDeliveryMode.DRY_RUN
    secret_reference: str | None = None

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("notification channel name is required")
        if self.kind in {NotificationChannelKind.WEBHOOK, NotificationChannelKind.SLACK}:
            if not self.target.startswith("https://"):
                raise ValueError("webhook and Slack notification targets must use HTTPS")
        elif "@" not in self.target or self.target.startswith("@") or self.target.endswith("@"):
            raise ValueError("email notification target must be a recipient address")
        if self.secret_reference and not self.secret_reference.startswith("secret://"):
            raise ValueError("notification secret_reference must use the secret:// scheme")


@dataclass(frozen=True, slots=True)
class NotificationEnvelope:
    """A minimal structured payload suitable for human or webhook delivery."""

    alert_event_id: UUID
    project_id: UUID
    rule_id: UUID
    asset_id: UUID | None
    analysis_id: UUID
    hazard: str
    event_kind: str
    summary: str
    evidence_ids: list[UUID]
    generated_at: datetime

    def as_payload(self) -> dict[str, object]:
        payload = asdict(self)
        for key in ("alert_event_id", "project_id", "rule_id", "asset_id", "analysis_id"):
            if payload[key] is not None:
                payload[key] = str(payload[key])
        payload["evidence_ids"] = [str(identifier) for identifier in self.evidence_ids]
        payload["generated_at"] = self.generated_at.isoformat()
        return payload


@dataclass(frozen=True, slots=True)
class NotificationReceipt:
    id: UUID
    alert_event_id: UUID
    channel_id: UUID
    status: NotificationReceiptStatus
    created_at: datetime
    message: str
    payload: dict[str, object]


def build_envelope(event: AlertEventLike, *, now: datetime | None = None) -> NotificationEnvelope:
    """Create an evidence-linked delivery envelope without contacting a provider."""

    timestamp = now or datetime.now(UTC)
    return NotificationEnvelope(
        alert_event_id=event.id,
        project_id=event.project_id,
        rule_id=event.rule_id,
        asset_id=event.asset_id,
        analysis_id=event.analysis_id,
        hazard=str(event.hazard),
        event_kind=str(event.event_kind),
        summary=event.summary,
        evidence_ids=list(event.evidence_ids),
        generated_at=timestamp,
    )


def dispatch(
    event: AlertEventLike,
    channel: NotificationChannelConfig,
    *,
    now: datetime | None = None,
) -> NotificationReceipt:
    """Record a safe dry run or explain why live delivery is unavailable.

    This deliberately has no networking code.  Returning ``unavailable`` for a
    live configuration prevents a caller from believing that a message was sent
    when the foundation has neither a trusted secret store nor a durable retry
    queue.
    """

    channel.validate()
    timestamp = now or datetime.now(UTC)
    envelope = build_envelope(event, now=timestamp)
    payload = envelope.as_payload()
    if not channel.enabled:
        return NotificationReceipt(
            id=uuid4(),
            alert_event_id=event.id,
            channel_id=channel.id,
            status=NotificationReceiptStatus.DISABLED,
            created_at=timestamp,
            message="Notification channel is disabled; no delivery was attempted.",
            payload=payload,
        )
    if channel.delivery_mode == NotificationDeliveryMode.DRY_RUN:
        return NotificationReceipt(
            id=uuid4(),
            alert_event_id=event.id,
            channel_id=channel.id,
            status=NotificationReceiptStatus.DRY_RUN,
            created_at=timestamp,
            message="Dry run recorded; no external notification was sent.",
            payload=payload,
        )
    return NotificationReceipt(
        id=uuid4(),
        alert_event_id=event.id,
        channel_id=channel.id,
        status=NotificationReceiptStatus.UNAVAILABLE,
        created_at=timestamp,
        message=(
            "Live delivery is unavailable in the foundation. Configure a reviewed dispatcher, "
            "secret manager, retry queue, and audit store before enabling it."
        ),
        payload=payload,
    )
