from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from nimbusx.notifications import (
    NotificationChannelConfig,
    NotificationChannelKind,
    NotificationDeliveryMode,
    NotificationReceiptStatus,
    build_envelope,
    dispatch,
)


@dataclass
class Event:
    id: UUID
    project_id: UUID
    rule_id: UUID
    asset_id: UUID | None
    analysis_id: UUID
    hazard: str
    event_kind: str
    summary: str
    evidence_ids: list[UUID]


NOW = datetime(2026, 8, 2, 12, tzinfo=UTC)


def event() -> Event:
    return Event(
        id=uuid4(),
        project_id=uuid4(),
        rule_id=uuid4(),
        asset_id=uuid4(),
        analysis_id=uuid4(),
        hazard="extreme_heat",
        event_kind="baseline_likelihood",
        summary="Heat likelihood met the alert rule.",
        evidence_ids=[uuid4()],
    )


def channel(**changes) -> NotificationChannelConfig:
    values = {
        "id": uuid4(),
        "project_id": uuid4(),
        "name": "Operations webhook",
        "kind": NotificationChannelKind.WEBHOOK,
        "target": "https://alerts.example.test/nimbusx",
    }
    values.update(changes)
    return NotificationChannelConfig(**values)


def test_envelope_contains_only_structured_event_and_evidence_identifiers():
    payload = build_envelope(event(), now=NOW).as_payload()

    assert payload["hazard"] == "extreme_heat"
    assert payload["generated_at"] == "2026-08-02T12:00:00+00:00"
    assert len(payload["evidence_ids"]) == 1
    assert "token" not in payload


def test_dry_run_never_sends_an_external_notification():
    alert = event()

    receipt = dispatch(alert, channel(), now=NOW)

    assert receipt.status == NotificationReceiptStatus.DRY_RUN
    assert "no external notification" in receipt.message
    assert receipt.payload["alert_event_id"] == str(alert.id)


def test_live_delivery_is_explicitly_unavailable_without_a_dispatcher():
    receipt = dispatch(event(), channel(delivery_mode=NotificationDeliveryMode.LIVE), now=NOW)

    assert receipt.status == NotificationReceiptStatus.UNAVAILABLE
    assert "Live delivery is unavailable" in receipt.message


@pytest.mark.parametrize(
    ("kind", "target", "message"),
    [
        (NotificationChannelKind.WEBHOOK, "http://alerts.example.test", "must use HTTPS"),
        (NotificationChannelKind.SLACK, "mailto:ops@example.test", "must use HTTPS"),
        (NotificationChannelKind.EMAIL, "not-an-email", "recipient address"),
    ],
)
def test_channel_validation_rejects_unsafe_or_malformed_targets(kind, target, message):
    with pytest.raises(ValueError, match=message):
        dispatch(event(), channel(kind=kind, target=target), now=NOW)
