import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from nimbusx.errors import ProviderUnavailable
from nimbusx.providers import (
    COPERNICUS_SEASONAL_DESCRIPTOR,
    ECMWF_OPEN_DATA_DESCRIPTOR,
    NEX_GDDP_CMIP6_DESCRIPTOR,
    PowerDailyProvider,
    UnavailableSpatialExposureProvider,
)
from nimbusx.schemas import EvidenceRecord, SiteInput
from nimbusx.source_catalog import source_health_payload
from nimbusx.source_contracts import (
    CalibrationState,
    ForecastMember,
    ForecastProductKind,
    OperationalForecastDataset,
    ScenarioProjectionDataset,
    ScenarioRange,
    SeasonalCalibrationArtifact,
    SeasonalOutlookDataset,
    SpatialExposureKind,
)

FIXED_NOW = datetime(2026, 8, 2, 12, tzinfo=UTC)
FIXTURE = Path(__file__).parent / "fixtures" / "source_health_contract.json"


def evidence(*, query, model_version="fixture-v1"):
    return EvidenceRecord(
        provider="fixture source",
        dataset="fixture dataset",
        model_version=model_version,
        retrieved_at=FIXED_NOW,
        query=query,
        units={"temperature": "degC"},
        resolution="fixture resolution",
        license="fixture license",
        attribution="fixture attribution",
        content_hash="a" * 64,
        raw_available=False,
    )


def test_source_health_catalog_matches_fixture_and_performs_no_remote_probe():
    contract = json.loads(FIXTURE.read_text(encoding="utf-8"))
    provider = PowerDailyProvider(endpoint="https://power.example.test/daily")

    payload = source_health_payload(provider, now=FIXED_NOW)

    assert payload["generated_at"] == "2026-08-02T12:00:00+00:00"
    sources = {source["id"]: source for source in payload["sources"]}
    assert list(sources) == contract["expected_source_ids"]
    assert sources["nasa-power-daily"]["status"] == "not_checked"
    assert sources["nasa-power-daily"]["remote_checked"] is False
    assert sources["nasa-power-daily"]["details"]["endpoint"].startswith("https://")
    for source_id in contract["expected_unavailable_source_ids"]:
        assert sources[source_id]["status"] == "unavailable"
        assert sources[source_id]["implementation"] == "unavailable"
        assert sources[source_id]["details"]["synthetic_fallback_used"] is False


def test_operational_forecast_contract_requires_real_ensemble_members_and_evidence():
    valid = datetime(2026, 8, 4, tzinfo=UTC)
    member = ForecastMember(
        member_id="control",
        initialization_time=FIXED_NOW,
        valid_time=valid,
        variables={"temperature_max_c": 35.0},
    )
    forecast_evidence = evidence(
        query={
            "run_time": FIXED_NOW.isoformat(),
            "valid_start": valid.isoformat(),
            "valid_end": valid.isoformat(),
            "parameters": ["temperature_max_c"],
        }
    )

    with pytest.raises(ValueError, match="at least two members"):
        OperationalForecastDataset(
            evidence=forecast_evidence,
            product_kind=ForecastProductKind.ENSEMBLE,
            members=(member,),
            valid_start=valid,
            valid_end=valid,
            evidence_contract=ECMWF_OPEN_DATA_DESCRIPTOR.evidence_contract,
        )

    dataset = OperationalForecastDataset(
        evidence=forecast_evidence,
        product_kind=ForecastProductKind.ENSEMBLE,
        members=(
            member,
            ForecastMember(
                member_id="perturbed-1",
                initialization_time=FIXED_NOW,
                valid_time=valid,
                variables={"temperature_max_c": 36.0},
            ),
        ),
        valid_start=valid,
        valid_end=valid,
        evidence_contract=ECMWF_OPEN_DATA_DESCRIPTOR.evidence_contract,
    )
    assert dataset.can_emit_member_probability is True


def test_seasonal_contract_suppresses_decision_eligibility_without_calibration():
    seasonal_evidence = evidence(
        query={
            "initialization": "2026-08-01",
            "target_start": "2026-09-01",
            "target_end": "2026-11-30",
            "parameters": ["temperature"],
        }
    )
    artifact = SeasonalCalibrationArtifact(
        state=CalibrationState.INSUFFICIENT_SKILL,
        method=None,
        hindcast_start=None,
        hindcast_end=None,
        skill_metric=None,
        skill_value=None,
    )
    dataset = SeasonalOutlookDataset(
        evidence=seasonal_evidence,
        hindcast_evidence=None,
        target_start=date(2026, 9, 1),
        target_end=date(2026, 11, 30),
        member_count=51,
        calibration=artifact,
        evidence_contract=COPERNICUS_SEASONAL_DESCRIPTOR.evidence_contract,
    )
    assert dataset.calibration.decision_eligible is False


def test_scenario_contract_requires_1991_2020_and_multi_model_ranges():
    scenario_evidence = evidence(
        query={
            "baseline_period": "1991-2020",
            "target_period": "2050s",
            "scenarios": ["ssp245"],
            "models": ["model-a", "model-b"],
        }
    )
    scenario_range = ScenarioRange(
        scenario="ssp245",
        target_period="2050s",
        variable="annual_hot_days",
        unit="days/year",
        model_ids=("model-a", "model-b"),
        lower=5.0,
        central=8.0,
        upper=12.0,
    )
    with pytest.raises(ValueError, match="1991"):
        ScenarioProjectionDataset(
            evidence=scenario_evidence,
            baseline_start_year=1990,
            baseline_end_year=2020,
            ranges=(scenario_range,),
            evidence_contract=NEX_GDDP_CMIP6_DESCRIPTOR.evidence_contract,
        )


def test_spatial_exposure_adapter_stays_unavailable_without_a_dedicated_source():
    adapter = UnavailableSpatialExposureProvider(SpatialExposureKind.FLOOD)
    with pytest.raises(ProviderUnavailable, match="no exposure result was generated"):
        adapter.fetch_exposure(SiteInput(name="Facility", latitude=0, longitude=0, timezone="UTC"))
