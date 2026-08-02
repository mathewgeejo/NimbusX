"""Route an analysis to the only scientifically valid time horizon."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from .schemas import AnalysisMode, TimeWindow


class HorizonError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class HorizonResolution:
    mode: AnalysisMode
    today: date
    forecast_last_day: date
    seasonal_last_day: date


def resolve_horizon(
    requested_mode: AnalysisMode,
    window: TimeWindow,
    timezone_name: str,
    *,
    now: datetime | None = None,
) -> HorizonResolution:
    """Resolve `auto` without turning a climatology into a daily forecast.

    A 15-day operational forecast window and a six-month seasonal window are
    intentionally hard boundaries.  Long-range automatic requests become a
    historical baseline, while scenario projection remains explicit.
    """

    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    zone = ZoneInfo(timezone_name)
    today = current.astimezone(zone).date()
    local_dates = window.local_dates(timezone_name)
    start, end = local_dates[0], local_dates[-1]
    forecast_last_day = today + timedelta(days=15)
    seasonal_last_day = today + timedelta(days=183)

    if requested_mode == AnalysisMode.AUTO:
        mode = _auto_mode_for_complete_window(
            start,
            end,
            today=today,
            forecast_last_day=forecast_last_day,
            seasonal_last_day=seasonal_last_day,
        )
        return HorizonResolution(mode, today, forecast_last_day, seasonal_last_day)

    if requested_mode == AnalysisMode.OBSERVED and end >= today:
        raise HorizonError("observed mode requires a window ending before the current local day")
    if requested_mode == AnalysisMode.FORECAST and (start < today or end > forecast_last_day):
        raise HorizonError("forecast mode supports windows from today through 15 days ahead")
    if requested_mode == AnalysisMode.SEASONAL and (
        start <= forecast_last_day or end > seasonal_last_day
    ):
        raise HorizonError(
            "seasonal mode supports windows more than 15 days and no more than 6 months ahead"
        )

    if requested_mode == AnalysisMode.SCENARIO and start <= today:
        raise HorizonError("scenario mode requires a future planning window")

    return HorizonResolution(requested_mode, today, forecast_last_day, seasonal_last_day)


def _auto_mode_for_complete_window(
    start: date,
    end: date,
    *,
    today: date,
    forecast_last_day: date,
    seasonal_last_day: date,
) -> AnalysisMode:
    """Resolve auto only when the complete local window fits one horizon.

    Each source horizon has a distinct event definition and calibration basis.
    Routing a range that crosses a source boundary to its earliest matching
    source would falsely imply coverage for the entire event window. Callers
    must split such requests or explicitly choose a calendar-window baseline.
    """

    if end < today:
        return AnalysisMode.OBSERVED
    if start >= today and end <= forecast_last_day:
        return AnalysisMode.FORECAST
    if start > forecast_last_day and end <= seasonal_last_day:
        return AnalysisMode.SEASONAL
    if start > seasonal_last_day:
        return AnalysisMode.BASELINE

    raise HorizonError(
        "auto mode cannot span observed, forecast, seasonal, or baseline horizons; "
        "split the local event window into separate analyses or choose an explicit baseline"
    )
