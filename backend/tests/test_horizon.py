from datetime import UTC, datetime

import pytest

from nimbusx.horizon import HorizonError, resolve_horizon
from nimbusx.schemas import AnalysisMode, TimeWindow

NOW = datetime(2026, 8, 2, 8, tzinfo=UTC)


def window(day: str) -> TimeWindow:
    return window_range(day, day)


def window_range(start_day: str, end_day: str) -> TimeWindow:
    return TimeWindow(
        start=f"{start_day}T09:00:00+00:00",
        end=f"{end_day}T17:00:00+00:00",
    )


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        ("2026-08-01", AnalysisMode.OBSERVED),
        ("2026-08-17", AnalysisMode.FORECAST),
        ("2026-08-18", AnalysisMode.SEASONAL),
        ("2027-02-02", AnalysisMode.BASELINE),
    ],
)
def test_auto_horizon_boundaries(day, expected):
    resolution = resolve_horizon(AnalysisMode.AUTO, window(day), "UTC", now=NOW)
    assert resolution.mode == expected


def test_explicit_baseline_accepts_a_past_calendar_window():
    resolution = resolve_horizon(AnalysisMode.BASELINE, window("2026-07-02"), "UTC", now=NOW)
    assert resolution.mode == AnalysisMode.BASELINE


def test_explicit_forecast_cannot_exceed_provider_horizon():
    with pytest.raises(HorizonError, match="15 days"):
        resolve_horizon(AnalysisMode.FORECAST, window("2026-08-18"), "UTC", now=NOW)


@pytest.mark.parametrize(
    ("start_day", "end_day"),
    [
        ("2026-08-01", "2026-08-02"),
        ("2026-08-17", "2026-08-18"),
        ("2027-02-01", "2027-02-02"),
    ],
)
def test_auto_mode_rejects_windows_that_cross_evidence_horizons(start_day, end_day):
    with pytest.raises(HorizonError, match="cannot span"):
        resolve_horizon(
            AnalysisMode.AUTO,
            window_range(start_day, end_day),
            "UTC",
            now=NOW,
        )


def test_auto_mode_uses_local_calendar_dates_at_timezone_boundary():
    # 01:00 UTC on 2 August is still 1 August in New York.
    resolution = resolve_horizon(
        AnalysisMode.AUTO,
        window("2026-08-02"),
        "America/New_York",
        now=datetime(2026, 8, 2, 1, tzinfo=UTC),
    )
    assert resolution.today.isoformat() == "2026-08-01"
    assert resolution.mode == AnalysisMode.FORECAST


def test_scenario_mode_rejects_a_past_or_current_local_calendar_window():
    with pytest.raises(HorizonError, match="future planning window"):
        resolve_horizon(AnalysisMode.SCENARIO, window("2026-08-02"), "UTC", now=NOW)
    with pytest.raises(HorizonError, match="future planning window"):
        resolve_horizon(AnalysisMode.SCENARIO, window("2026-08-01"), "UTC", now=NOW)


def test_scenario_mode_accepts_a_future_local_calendar_window():
    resolution = resolve_horizon(AnalysisMode.SCENARIO, window("2030-08-02"), "UTC", now=NOW)
    assert resolution.mode == AnalysisMode.SCENARIO
