"""Contract tests for asset, operational-rule, import, alert, and report flows."""

from test_api import baseline_request, client


def _project_and_site(api):
    project = api.post("/v1/projects", json={"name": "Operational portfolio"}).json()
    site = api.post(
        f"/v1/projects/{project['id']}/sites",
        json={
            "name": "Operations site",
            "latitude": 12.5,
            "longitude": 77.6,
            "timezone": "Asia/Kolkata",
        },
    ).json()
    return project, site


def _data_center_asset(api, project_id, site_id, *, complete=True):
    payload = {
        "name": "Primary data center",
        "site_id": site_id,
        "template_id": "data_center",
        "criticality": "critical",
        "tags": ["production", "digital"],
        "exposure": {"service_criticality": "critical"},
        "vulnerability": {
            "cooling_redundancy": "n_plus_1",
            "backup_power_hours": 24,
        }
        if complete
        else {},
    }
    response = api.post(f"/v1/projects/{project_id}/assets", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _asset_baseline_request(project_id, asset_id):
    payload = baseline_request()
    payload.pop("site")
    payload["project_id"] = project_id
    payload["asset_id"] = asset_id
    return payload


def test_asset_templates_assets_and_operational_findings_are_source_linked():
    api = client()
    templates = api.get("/v1/asset-templates")
    assert templates.status_code == 200
    data_center = next(item for item in templates.json() if item["id"] == "data_center")
    assert data_center["operational_rules"][0]["hazard"] == "extreme_heat"
    assert data_center["operational_rules"][0]["minimum_severity"] == "moderate"

    project, site = _project_and_site(api)
    asset = _data_center_asset(api, project["id"], site["id"])
    listed = api.get(f"/v1/projects/{project['id']}/assets")
    assert [item["id"] for item in listed.json()] == [asset["id"]]

    created = api.post("/v1/analyses", json=_asset_baseline_request(project["id"], asset["id"]))
    assert created.status_code == 202
    assessment = api.get(f"/v1/analyses/{created.json()['id']}")
    assert assessment.status_code == 200
    body = assessment.json()
    assert body["asset_id"] == asset["id"]
    heat_rule = next(
        finding
        for finding in body["operational_findings"]
        if finding["rule_id"] == "data-center-heat-cooling-v1"
    )
    assert heat_rule["status"] == "action_required"
    assert heat_rule["evidence_ids"] == body["evidence_ids"]
    assert "not forecasts" in body["limitations"][-1]


def test_incomplete_asset_context_never_becomes_an_action_required_operational_result():
    api = client()
    project, site = _project_and_site(api)
    asset = _data_center_asset(api, project["id"], site["id"], complete=False)
    created = api.post("/v1/analyses", json=_asset_baseline_request(project["id"], asset["id"]))
    assessment = api.get(f"/v1/analyses/{created.json()['id']}").json()
    heat_rule = next(
        finding
        for finding in assessment["operational_findings"]
        if finding["rule_id"] == "data-center-heat-cooling-v1"
    )
    assert heat_rule["status"] == "insufficient_context"
    assert sorted(heat_rule["missing_vulnerability_fields"]) == [
        "backup_power_hours",
        "cooling_redundancy",
    ]


def test_csv_import_returns_row_level_validation_and_does_not_guess_missing_timezone():
    api = client()
    project = api.post("/v1/projects", json={"name": "Imported portfolio"}).json()
    csv_text = """name,latitude,longitude,timezone,template_id,criticality,exposure_json,vulnerability_json,tags
North warehouse,77.6,12.5,Asia/Kolkata,warehouse,high,"{""goods_sensitivity"":""high""}","{""roof_condition"":""verified"",""drainage_condition"":""adequate""}",logistics|priority
Missing timezone,77.7,12.6,,warehouse,medium,,,\n"""

    response = api.post(
        f"/v1/projects/{project['id']}/assets/import",
        json={"csv_text": csv_text},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "partial"
    assert body["created_count"] == 1
    assert body["rejected_count"] == 1
    assert body["rows"][0]["status"] == "created"
    assert body["rows"][1]["code"] == "invalid_asset_row"
    assert "timezone is required" in body["rows"][1]["message"]
    assert len(api.get(f"/v1/projects/{project['id']}/assets").json()) == 1


def test_geojson_dry_run_rejects_polygon_without_persisting_or_claiming_spatial_analysis():
    api = client()
    project = api.post("/v1/projects", json={"name": "GeoJSON portfolio"}).json()
    response = api.post(
        f"/v1/projects/{project['id']}/assets/import",
        json={
            "dry_run": True,
            "default_template_id": "campus",
            "geojson": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"name": "Area campus", "timezone": "UTC"},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]],
                        },
                    }
                ],
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["rows"][0]["status"] == "rejected"
    assert "Point features only" in body["rows"][0]["message"]
    assert api.get(f"/v1/projects/{project['id']}/assets").json() == []


def test_geojson_point_import_creates_a_site_backed_asset_with_explicit_timezone():
    api = client()
    project = api.post("/v1/projects", json={"name": "Point GeoJSON portfolio"}).json()
    response = api.post(
        f"/v1/projects/{project['id']}/assets/import",
        json={
            "default_template_id": "campus",
            "geojson": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "name": "Point campus",
                            "timezone": "Asia/Kolkata",
                            "exposure": {"occupancy_band": "high"},
                            "vulnerability": {
                                "cooling_resilience": "standard",
                                "drainage_condition": "verified",
                            },
                        },
                        "geometry": {"type": "Point", "coordinates": [77.6, 12.5]},
                    }
                ],
            },
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "complete"
    assert body["rows"][0]["site_id"] is not None
    asset = api.get(f"/v1/projects/{project['id']}/assets").json()[0]
    assert asset["template_id"] == "campus"


def test_alert_rules_create_deduplicated_evidence_events_and_never_claim_delivery():
    api = client()
    project, site = _project_and_site(api)
    asset = _data_center_asset(api, project["id"], site["id"])
    analysis_id = api.post(
        "/v1/analyses", json=_asset_baseline_request(project["id"], asset["id"])
    ).json()["id"]
    rule = api.post(
        f"/v1/projects/{project['id']}/alert-rules",
        json={
            "name": "Heat-history review",
            "asset_id": asset["id"],
            "hazard": "extreme_heat",
            "trigger_type": "baseline_likelihood",
            "minimum_likelihood": 0.4,
        },
    )
    assert rule.status_code == 201, rule.text
    evaluate = api.post(
        f"/v1/projects/{project['id']}/alert-rules/{rule.json()['id']}/evaluate",
        json={"analysis_ids": [analysis_id]},
    )
    assert evaluate.status_code == 200, evaluate.text
    body = evaluate.json()
    assert body["created_count"] == 1
    assert body["events"][0]["event_kind"] == "historical_pattern"
    assert body["events"][0]["delivery_status"] == "recorded_only"
    assert "do not forecast" in body["limitations"][0]

    duplicate = api.post(
        f"/v1/projects/{project['id']}/alert-rules/{rule.json()['id']}/evaluate",
        json={"analysis_ids": [analysis_id]},
    ).json()
    assert duplicate["created_count"] == 0
    assert duplicate["existing_count"] == 1
    assert len(api.get(f"/v1/projects/{project['id']}/alert-events").json()) == 1


def test_alert_rule_contract_rejects_a_baseline_rule_without_a_likelihood_threshold():
    api = client()
    project = api.post("/v1/projects", json={"name": "Alert contract"}).json()
    response = api.post(
        f"/v1/projects/{project['id']}/alert-rules",
        json={
            "name": "Incomplete baseline rule",
            "hazard": "extreme_heat",
            "trigger_type": "baseline_likelihood",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_enhanced_report_manifest_and_source_health_are_explicit_about_boundaries():
    api = client()
    created = api.post("/v1/analyses", json=baseline_request())
    analysis_id = created.json()["id"]
    manifest = api.get(f"/v1/analyses/{analysis_id}/report?format=manifest")
    assert manifest.status_code == 200
    body = manifest.json()
    assert len(body["content_hash"]) == 64
    assert body["evidence"][0]["content_hash"] == "f" * 64
    assert "not durably immutable" in body["limitations"][0]
    csv_report = api.get(f"/v1/analyses/{analysis_id}/report?format=csv")
    assert csv_report.status_code == 200
    assert "report_content_hash" in csv_report.text

    source_health = api.get("/v1/sources/health")
    assert source_health.status_code == 200
    assert len(source_health.json()["sources"]) == 7
    assert source_health.json()["sources"][0]["remote_checked"] is False
