"""Source adapters.

Only the NASA POWER adapter returns data in this foundation.  The other horizon
adapters intentionally return a structured unavailable condition until their
licensed/client integrations and calibration artifacts are installed.  They
never substitute climatology, synthetic values, or arbitrary defaults for a
forecast, seasonal outlook, or scenario projection.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from .errors import ProviderUnavailable
from .schemas import EvidenceRecord, NormalizedDailyObservation, SiteInput

NASA_POWER_DAILY_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
NASA_PARAMETERS = ("T2M_MAX", "T2M_MIN", "PRECTOTCORR", "WS10M")
DAILY_LABEL_REPRESENTATIVE_TIME = time(hour=12)


@dataclass(frozen=True, slots=True)
class NormalizedDataset:
    evidence: EvidenceRecord
    observations: list[NormalizedDailyObservation]


class DailyClimateProvider(Protocol):
    def fetch_daily(
        self, site: SiteInput, start: date, end: date, *, purpose: str
    ) -> NormalizedDataset:
        """Return source-backed daily observations or raise ProviderUnavailable."""


def _number_or_none(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    # NASA POWER's documented fill value is -999.  Other obviously impossible
    # values are not coerced; they remain evidence and can be investigated.
    if number <= -999:
        return None
    return number


class PowerDailyProvider:
    """HTTPS-only NASA POWER Daily API adapter with content-hashed evidence metadata.

    POWER UTC daily keys represent daily aggregates, not instantaneous readings.
    NimbusX uses a 12:00 UTC representative timestamp only to choose an IANA
    calendar label; it does not recast a UTC aggregate as a local civil-day measurement.
    """

    def __init__(
        self,
        *,
        timeout_seconds: int = 30,
        opener: Callable[..., Any] = urlopen,
        endpoint: str = NASA_POWER_DAILY_URL,
    ) -> None:
        if not endpoint.startswith("https://"):
            raise ValueError("NASA POWER endpoint must use HTTPS")
        self.timeout_seconds = timeout_seconds
        self._opener = opener
        self.endpoint = endpoint

    def fetch_daily(
        self, site: SiteInput, start: date, end: date, *, purpose: str
    ) -> NormalizedDataset:
        if end < start:
            raise ValueError("end must be on or after start")

        params = {
            "parameters": ",".join(NASA_PARAMETERS),
            "community": "RE",
            "longitude": f"{site.longitude:.8f}",
            "latitude": f"{site.latitude:.8f}",
            "start": start.strftime("%Y%m%d"),
            "end": end.strftime("%Y%m%d"),
            "format": "JSON",
            "time-standard": "UTC",
        }
        url = f"{self.endpoint}?{urlencode(params)}"
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "NimbusX/1.0 evidence-first climate risk workspace",
            },
        )
        retrieved_at = datetime.now(UTC)
        try:
            with self._opener(request, timeout=self.timeout_seconds) as response:
                body = response.read()
                response_url = response.geturl() if hasattr(response, "geturl") else url
        except HTTPError as exc:
            raise ProviderUnavailable(
                "NASA POWER Daily API returned an HTTP error",
                {"provider": "NASA POWER", "http_status": exc.code},
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ProviderUnavailable(
                "NASA POWER Daily API could not be reached; no substitute data was used",
                {"provider": "NASA POWER", "reason": type(exc).__name__},
            ) from exc

        digest = hashlib.sha256(body).hexdigest()
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderUnavailable(
                "NASA POWER Daily API returned an unreadable response",
                {"provider": "NASA POWER", "content_hash": digest},
            ) from exc

        observations = self._normalize(payload, site)
        if not observations:
            raise ProviderUnavailable(
                "NASA POWER Daily API returned no usable daily observations",
                {"provider": "NASA POWER", "content_hash": digest},
            )

        evidence = EvidenceRecord(
            provider="NASA POWER",
            dataset="NASA POWER Daily API",
            model_version=self._model_version(payload),
            retrieved_at=retrieved_at,
            query={
                "url": response_url,
                "parameters": list(NASA_PARAMETERS),
                "latitude": site.latitude,
                "longitude": site.longitude,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "time_standard": "UTC",
                "wind_metric": "WS10M daily-mean wind speed at 10 m above the source grid",
                "daily_label_mapping": {
                    "representative_timestamp_utc": "12:00:00Z",
                    "purpose": "IANA calendar-label conversion only; source aggregation remains UTC-defined",
                },
                "purpose": purpose,
            },
            units={
                "temperature_max": "degC",
                "temperature_min": "degC",
                "precipitation": "mm/day",
                "wind_speed": "m/s",
            },
            resolution=(
                "Daily UTC point aggregates; 12:00 UTC representative timestamps are used only for IANA calendar-label conversion. Native source-grid resolution varies by parameter."
            ),
            license="NASA POWER data access and use terms",
            attribution="NASA POWER Project, NASA Langley Research Center",
            content_hash=digest,
            coverage_start=start,
            coverage_end=end,
            raw_available=True,
            raw_extract={"source_url": response_url, "payload": payload},
            normalized_observations=observations,
        )
        return NormalizedDataset(evidence=evidence, observations=observations)

    @staticmethod
    def _model_version(payload: dict[str, Any]) -> str | None:
        header = payload.get("header")
        if not isinstance(header, dict):
            return None
        for key in ("title", "api", "fill_value"):
            value = header.get(key)
            if value is not None:
                return str(value)
        return None

    @staticmethod
    def _normalize(payload: dict[str, Any], site: SiteInput) -> list[NormalizedDailyObservation]:
        properties = payload.get("properties")
        if not isinstance(properties, dict):
            return []
        parameter = properties.get("parameter")
        if not isinstance(parameter, dict):
            return []

        dates: set[str] = set()
        for name in NASA_PARAMETERS:
            series = parameter.get(name)
            if isinstance(series, dict):
                dates.update(str(key) for key in series)

        zone = ZoneInfo(site.timezone)
        observations: list[NormalizedDailyObservation] = []
        for key in sorted(dates):
            try:
                source_date = datetime.strptime(key, "%Y%m%d").date()
            except ValueError:
                # Do not guess an unsupported source date representation.
                continue
            timestamp_utc = datetime.combine(
                source_date, DAILY_LABEL_REPRESENTATIVE_TIME, tzinfo=UTC
            )
            local_timestamp = timestamp_utc.astimezone(zone)
            values = {
                name: _number_or_none(
                    parameter.get(name, {}).get(key)
                    if isinstance(parameter.get(name), dict)
                    else None
                )
                for name in NASA_PARAMETERS
            }
            observations.append(
                NormalizedDailyObservation(
                    timestamp_utc=timestamp_utc,
                    local_timestamp=local_timestamp,
                    local_date=local_timestamp.date(),
                    timezone=site.timezone,
                    temperature_max_c=values["T2M_MAX"],
                    temperature_min_c=values["T2M_MIN"],
                    precipitation_mm=values["PRECTOTCORR"],
                    wind_speed_m_s=values["WS10M"],
                )
            )
        return observations


class UnavailableHorizonProvider:
    """A truthful placeholder for adapters that need credentials/calibration data."""

    def __init__(self, provider_name: str, setup_message: str) -> None:
        self.provider_name = provider_name
        self.setup_message = setup_message

    def fetch(self) -> None:
        raise ProviderUnavailable(
            self.setup_message,
            {"provider": self.provider_name, "synthetic_fallback_used": False},
        )


class ECMWFOpenDataProvider(UnavailableHorizonProvider):
    def __init__(self) -> None:
        super().__init__(
            "ECMWF Open Data",
            "ECMWF Open Data forecast adapter is not implemented in this foundation; no forecast was generated",
        )


class CopernicusSeasonalProvider(UnavailableHorizonProvider):
    def __init__(self) -> None:
        super().__init__(
            "Copernicus Climate Data Store",
            "Copernicus seasonal retrieval and local hindcast calibration are not implemented in this foundation; no seasonal outlook was generated",
        )


class NexGddpCmip6Provider(UnavailableHorizonProvider):
    def __init__(self) -> None:
        super().__init__(
            "NASA NEX-GDDP-CMIP6",
            "NEX-GDDP-CMIP6 scenario extraction is not implemented in this foundation; no scenario projection was generated",
        )
