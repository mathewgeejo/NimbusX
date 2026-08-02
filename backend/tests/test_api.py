from datetime import UTC, datetime, time, timedelta

from fastapi.testclient import TestClient

from nimbusx.config import Settings
from nimbusx.main import create_app
from nimbusx.providers import NormalizedDataset
from nimbusx.schemas import EvidenceRecord, NormalizedDailyObservation
from nimbusx.service import _baseline_source_date_bounds

FIXED_NOW = datetime(2026, 8, 2, 8, tzinfo=UTC)


class FakeDailyProvider:
    """Source-backed fixture provider; it does not use the production fallback path."""

    def fetch_daily(self, site, start, end, *, purpose):
        observations = []
        current = start
        while current <= end:
            observations.append(
                NormalizedDailyObservation(
                    timestamp_utc=datetime.combine(current, time.min, tzinfo=UTC),
                    local_timestamp=datetime.combine(current, time.min, tzinfo=UTC),
                    local_date=current,
                    timezone=site.timezone,
                    temperature_max_c=36.0 if current.year % 2 == 0 else 31.0,
                    temperature_min_c=-2.0 if current.year % 3 == 0 else 5.0,
                    precipitation_mm=2.0,
                    wind_speed_m_s=17.0 if current.year % 4 == 0 else 8.0,
                )
            )
            current += timedelta(days=1)
        evidence = EvidenceRecord(
            provider="fixture daily source",
            dataset="fixture daily source",
            retrieved_at=FIXED_NOW,
            query={"purpose": purpose, "start": start.isoformat(), "end": end.isoformat()},
            units={"temperature": "degC", "precipitation": "mm/day", "wind": "m/s"},
            resolution="fixture",
            license="test-only",
            attribution="test fixture",
            content_hash="f" * 64,
            coverage_start=start,
            coverage_end=end,
            raw_extract={"fixture": True},
            normalized_observations=observations,
        )
        return NormalizedDataset(evidence=evidence, observations=observations)


def make_settings(**overrides):
    values = {
        "environment": "test",
        "cors_origins": ("http://localhost:5173",),
        "allowed_hosts": ("testserver", "localhost"),
        "require_api_key": False,
        "api_keys": (),
        "nasa_timeout_seconds": 1,
        "nasa_power_base_url": "https://power.example.test/daily",
        "rate_limit_per_minute": 1000,
        "analysis_execution": "inline",
        "max_window_days": 31,
        "legacy_weather_adapter_sunset": FIXED_NOW + timedelta(days=30),
        "control_plane_heartbeat_url": None,
        "data_plane_id": None,
        "data_plane_client_cert": None,
        "data_plane_client_key": None,
    }
    values.update(overrides)
    return Settings(**values)


def client(settings=None):
    return TestClient(
        create_app(
            settings=settings or make_settings(),
            daily_provider=FakeDailyProvider(),
            now_fn=lambda: FIXED_NOW,
        )
    )


def baseline_request(latitude=0.0, longitude=0.0):
    return {
        "site": {
            "name": "Equatorial campus",
            "latitude": latitude,
            "longitude": longitude,
            "timezone": "UTC",
        },
        "window": {
            "start": "2027-06-21T09:00:00+00:00",
            "end": "2027-07-04T17:00:00+00:00",
        },
        "mode": "baseline",
        "asset": {
            "template": "campus",
            "exposure": {"occupancy": "high"},
            "vulnerability": {"cooling": "limited"},
        },
    }


def test_baseline_job_is_traceable_and_accepts_zero_coordinates():
    api = client()
    created = api.post("/v1/analyses", json=baseline_request())
    assert created.status_code == 202
    analysis_id = created.json()["id"]

    result = api.get(f"/v1/analyses/{analysis_id}")
    assert result.status_code == 200
    body = result.json()
    assert body["status"] == "complete"
    assert body["resolved_mode"] == "baseline"
    assert body["site"]["latitude"] == 0.0
    assert len(body["findings"]) == 5
    heat = next(item for item in body["findings"] if item["hazard"] == "extreme_heat")
    assert heat["event_definition"].startswith("P(")
    assert heat["likelihood"] == 0.5
    assert "confidence" not in heat
    assert body["project_id"] is None
    assert body["decision"]["status"] == "insufficient_evidence"
    assert "published template-specific" in body["decision"]["rationale"]

    evidence = api.get(f"/v1/analyses/{analysis_id}/evidence")
    assert evidence.status_code == 200
    assert evidence.json()["evidence"][0]["provider"] == "fixture daily source"
    public_evidence = evidence.json()["evidence"][0]
    assert public_evidence["content_hash"] == "f" * 64
    assert "raw_extract" not in public_evidence
    assert "normalized_observations" not in public_evidence


def test_forecast_is_partial_when_ecmwf_adapter_is_not_configured():
    api = client()
    payload = baseline_request(10, 10)
    payload["window"] = {
        "start": "2026-08-05T09:00:00+00:00",
        "end": "2026-08-05T17:00:00+00:00",
    }
    payload["mode"] = "forecast"
    created = api.post("/v1/analyses", json=payload)
    result = api.get(f"/v1/analyses/{created.json()['id']}")
    body = result.json()
    assert body["status"] == "partial"
    assert body["findings"] == []
    assert body["evidence_ids"] == []
    assert "ECMWF Open Data" in body["data_gaps"][0]


def test_legacy_weather_adapter_is_deprecated_and_returns_a_v1_job():
    api = client()
    response = api.post(
        "/api/weather",
        json={"lat": 0, "lon": 0, "location": "Equator", "date": "06-21", "year": 2027},
    )
    assert response.status_code == 202
    assert response.headers["deprecation"] == "true"
    assert "Sunset" in response.headers
    assert response.json()["analysis"]["status"] == "queued"


def test_legacy_weather_adapter_expires_at_the_configured_sunset():
    api = client(make_settings(legacy_weather_adapter_sunset=FIXED_NOW))

    response = api.post(
        "/api/weather",
        json={"lat": 0, "lon": 0, "location": "Equator", "date": "06-21", "year": 2027},
    )

    assert response.status_code == 410
    assert response.json()["error"]["code"] == "legacy_endpoint_expired"


def test_api_key_gate_returns_a_stable_error_and_allows_valid_key():
    api = client(make_settings(require_api_key=True, api_keys=("test-key",)))
    denied = api.get("/v1/projects")
    assert denied.status_code == 401
    assert denied.json()["error"]["code"] == "authentication_required"

    allowed = api.get("/v1/projects", headers={"X-API-Key": "test-key"})
    assert allowed.status_code == 200


def test_rate_limit_returns_a_stable_error_envelope():
    api = client(make_settings(rate_limit_per_minute=1))
    assert api.get("/healthz").status_code == 200
    limited = api.get("/healthz")
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "rate_limited"


def test_auto_mode_rejects_a_request_that_crosses_forecast_and_seasonal_horizons():
    api = client()
    payload = baseline_request(10, 10)
    payload["mode"] = "auto"
    payload["window"] = {
        "start": "2026-08-17T09:00:00+00:00",
        "end": "2026-08-18T17:00:00+00:00",
    }

    response = api.post("/v1/analyses", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_horizon"
    assert "cannot span" in response.json()["error"]["message"]


def test_baseline_source_query_includes_timezone_mapping_guards():
    assert _baseline_source_date_bounds(1991, 2020) == (
        datetime(1990, 12, 31).date(),
        datetime(2021, 1, 2).date(),
    )
    assert _baseline_source_date_bounds(1981, 1981) == (
        datetime(1981, 1, 1).date(),
        datetime(1982, 1, 2).date(),
    )


def test_polygon_assessment_is_rejected_until_spatial_aggregation_exists():
    api = client()
    payload = baseline_request()
    payload["site"]["geometry"] = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]],
    }

    response = api.post("/v1/analyses", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "polygon_assessment_unavailable"


def test_project_association_is_persisted_and_listed():
    api = client()
    project = api.post("/v1/projects", json={"name": "Campus program"}).json()
    site = api.post(
        f"/v1/projects/{project['id']}/sites",
        json={
            "name": "Equatorial campus",
            "latitude": 0,
            "longitude": 0,
            "timezone": "UTC",
        },
    ).json()
    payload = baseline_request()
    payload.pop("site")
    payload["site_id"] = site["id"]
    payload["project_id"] = project["id"]

    created = api.post("/v1/analyses", json=payload)
    analysis_id = created.json()["id"]
    assessment = api.get(f"/v1/analyses/{analysis_id}").json()
    listed = api.get(f"/v1/projects/{project['id']}/analyses")

    assert assessment["project_id"] == project["id"]
    assert [item["id"] for item in listed.json()] == [analysis_id]


def test_compare_returns_selected_assessment_summaries_without_a_delta_claim():
    api = client()
    first = api.post("/v1/analyses", json=baseline_request()).json()["id"]
    second = api.post("/v1/analyses", json=baseline_request(10, 10)).json()["id"]

    response = api.post(f"/v1/analyses/{first}/compare", json={"analysis_ids": [second]})

    assert response.status_code == 200
    body = response.json()
    assert body["comparison"] == "selected_assessments"
    assert [item["analysis_id"] for item in body["analyses"]] == [first, second]
    assert "does not calculate aligned changes" in body["limitations"][0]


def test_readiness_does_not_claim_to_probe_provider_health():
    api = client()

    response = api.get("/readyz")

    assert response.status_code == 200
    assert response.json()["provider"] == "not_checked"
    assert "does not probe NASA POWER" in response.json()["limitations"][0]


def test_openapi_exposes_the_canonical_v1_contract():
    api = client()

    response = api.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    for path in (
        "/v1/analyses",
        "/v1/analyses/{analysis_id}",
        "/v1/analyses/{analysis_id}/evidence",
        "/v1/projects/{project_id}/sites",
        "/v1/projects/{project_id}/analyses",
        "/v1/analyses/{analysis_id}/compare",
        "/v1/analyses/{analysis_id}/report",
    ):
        assert path in paths


def test_schema_mismatch_returns_the_stable_validation_envelope():
    api = client()
    payload = baseline_request()
    payload["mode"] = "unsupported_mode"

    response = api.post("/v1/analyses", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_cors_allows_only_the_configured_browser_origin():
    api = client()
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
    }

    allowed = api.options("/v1/analyses", headers=headers)
    blocked = api.options(
        "/v1/analyses",
        headers={**headers, "Origin": "https://untrusted.example"},
    )

    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in blocked.headers
