"""Contract tests for safe, evidence-linked notification dry runs."""

from test_api import baseline_request, client


def _historical_alert_event(api):
    project = api.post("/v1/projects", json={"name": "Notification portfolio"}).json()
    site = api.post(
        f"/v1/projects/{project['id']}/sites",
        json={
            "name": "Notification site",
            "latitude": 12.5,
            "longitude": 77.6,
            "timezone": "Asia/Kolkata",
        },
    ).json()
    request = baseline_request()
    request.pop("site")
    request["project_id"] = project["id"]
    request["site_id"] = site["id"]
    analysis_id = api.post("/v1/analyses", json=request).json()["id"]
    rule = api.post(
        f"/v1/projects/{project['id']}/alert-rules",
        json={
            "name": "Heat-history review",
            "hazard": "extreme_heat",
            "trigger_type": "baseline_likelihood",
            "minimum_likelihood": 0.4,
        },
    ).json()
    evaluation = api.post(
        f"/v1/projects/{project['id']}/alert-rules/{rule['id']}/evaluate",
        json={"analysis_ids": [analysis_id]},
    )
    assert evaluation.status_code == 200, evaluation.text
    return project, evaluation.json()["events"][0]


def test_webhook_dry_run_records_evidence_linked_receipt_without_exposing_reference():
    api = client()
    project, alert_event = _historical_alert_event(api)

    channel_response = api.post(
        f"/v1/projects/{project['id']}/notification-channels",
        json={
            "name": "Operations webhook",
            "kind": "webhook",
            "target": "https://alerts.example.test/nimbusx",
            "secret_reference": "secret://nimbusx/operations-webhook",
        },
    )
    assert channel_response.status_code == 201, channel_response.text
    channel = channel_response.json()
    assert channel["delivery_mode"] == "dry_run"
    assert channel["has_secret_reference"] is True
    assert "secret_reference" not in channel

    dispatch = api.post(
        f"/v1/projects/{project['id']}/alert-events/{alert_event['id']}"
        f"/notification-channels/{channel['id']}/dispatch"
    )
    assert dispatch.status_code == 201, dispatch.text
    receipt = dispatch.json()
    assert receipt["status"] == "dry_run"
    assert "no external notification was sent" in receipt["message"]
    assert receipt["payload"]["alert_event_id"] == alert_event["id"]
    assert receipt["payload"]["evidence_ids"] == alert_event["evidence_ids"]

    receipts = api.get(
        f"/v1/projects/{project['id']}/alert-events/{alert_event['id']}/notification-receipts"
    )
    assert receipts.status_code == 200
    assert [item["id"] for item in receipts.json()] == [receipt["id"]]


def test_live_notification_mode_is_explicitly_unavailable_and_http_targets_are_rejected():
    api = client()
    project, alert_event = _historical_alert_event(api)

    unsafe = api.post(
        f"/v1/projects/{project['id']}/notification-channels",
        json={
            "name": "Unsafe webhook",
            "kind": "webhook",
            "target": "http://alerts.example.test/nimbusx",
        },
    )
    assert unsafe.status_code == 422
    assert unsafe.json()["error"]["code"] == "validation_error"

    live = api.post(
        f"/v1/projects/{project['id']}/notification-channels",
        json={
            "name": "Future dispatcher",
            "kind": "slack",
            "target": "https://hooks.slack.example.test/services/placeholder",
            "delivery_mode": "live",
        },
    )
    assert live.status_code == 201
    receipt = api.post(
        f"/v1/projects/{project['id']}/alert-events/{alert_event['id']}"
        f"/notification-channels/{live.json()['id']}/dispatch"
    )
    assert receipt.status_code == 201
    assert receipt.json()["status"] == "unavailable"
    assert "Live delivery is unavailable" in receipt.json()["message"]


def test_openapi_advertises_the_safe_notification_contract():
    api = client()

    paths = api.get("/openapi.json").json()["paths"]

    assert "/v1/projects/{project_id}/notification-channels" in paths
    assert "/v1/projects/{project_id}/alert-events/{event_id}/notification-receipts" in paths
    assert (
        "/v1/projects/{project_id}/alert-events/{event_id}/notification-channels/{channel_id}/dispatch"
        in paths
    )
