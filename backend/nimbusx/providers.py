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
from typing import Any, NoReturn, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from .errors import ProviderUnavailable
from .schemas import EvidenceRecord, NormalizedDailyObservation, SiteInput
from .source_contracts import (
    EvidenceContract,
    OperationalForecastDataset,
    RemoteProbePolicy,
    ScenarioProjectionDataset,
    SeasonalOutlookDataset,
    SourceCapability,
    SourceDescriptor,
    SourceHealth,
    SourceHealthState,
    SourceImplementationState,
    SpatialExposureDataset,
    SpatialExposureKind,
    validate_evidence,
)

NASA_POWER_DAILY_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
NASA_PARAMETERS = ("T2M_MAX", "T2M_MIN", "PRECTOTCORR", "WS10M")
DAILY_LABEL_REPRESENTATIVE_TIME = time(hour=12)


POWER_DAILY_DESCRIPTOR = SourceDescriptor(
    source_id="nasa-power-daily",
    provider="NASA POWER",
    dataset="NASA POWER Daily API",
    capabilities=(SourceCapability.OBSERVED_DAILY, SourceCapability.HISTORICAL_BASELINE),
    implementation=SourceImplementationState.IMPLEMENTED,
    remote_probe_policy=RemoteProbePolicy.ON_RETRIEVAL,
    evidence_contract=EvidenceContract(
        required_query_keys=(
            "parameters",
            "latitude",
            "longitude",
            "start",
            "end",
            "time_standard",
        ),
        required_unit_keys=("temperature_max", "temperature_min", "precipitation", "wind_speed"),
    ),
    limitations=(
        "Daily source aggregation is UTC-defined; IANA dates use a documented representative-label convention.",
        "WS10M is a daily-mean 10 m source-grid wind speed, not a gust or site-scale operating-wind measurement.",
    ),
)

ECMWF_OPEN_DATA_DESCRIPTOR = SourceDescriptor(
    source_id="ecmwf-open-data-forecast",
    provider="ECMWF Open Data",
    dataset="ECMWF Open Data operational forecast products",
    capabilities=(SourceCapability.OPERATIONAL_FORECAST,),
    implementation=SourceImplementationState.UNAVAILABLE,
    remote_probe_policy=RemoteProbePolicy.NOT_APPLICABLE,
    evidence_contract=EvidenceContract(
        requires_model_version=True,
        required_query_keys=("run_time", "valid_start", "valid_end", "parameters"),
    ),
    limitations=(
        "No ECMWF retrieval, member normalization, or event-window exceedance calculation is installed.",
        "A high-resolution deterministic product cannot be presented as an ensemble probability.",
    ),
)

COPERNICUS_SEASONAL_DESCRIPTOR = SourceDescriptor(
    source_id="copernicus-seasonal-outlook",
    provider="Copernicus Climate Data Store",
    dataset="Copernicus multi-system seasonal forecast",
    capabilities=(SourceCapability.SEASONAL_OUTLOOK,),
    implementation=SourceImplementationState.UNAVAILABLE,
    remote_probe_policy=RemoteProbePolicy.NOT_APPLICABLE,
    evidence_contract=EvidenceContract(
        requires_model_version=True,
        required_query_keys=("initialization", "target_start", "target_end", "parameters"),
    ),
    limitations=(
        "No Copernicus retrieval, local hindcast bias correction, or skill artifact is installed.",
        "A seasonal probability is suppressed unless calibration evidence is positive and retained.",
    ),
)

NEX_GDDP_CMIP6_DESCRIPTOR = SourceDescriptor(
    source_id="nex-gddp-cmip6-scenarios",
    provider="NASA NEX-GDDP-CMIP6",
    dataset="NASA NEX-GDDP-CMIP6 downscaled climate projections",
    capabilities=(SourceCapability.SCENARIO_PROJECTION,),
    implementation=SourceImplementationState.UNAVAILABLE,
    remote_probe_policy=RemoteProbePolicy.NOT_APPLICABLE,
    evidence_contract=EvidenceContract(
        requires_model_version=True,
        required_query_keys=("baseline_period", "target_period", "scenarios", "models"),
    ),
    limitations=(
        "No NEX-GDDP-CMIP6 extraction or multi-model aggregation is installed.",
        "Scenario output must remain a 1991–2020 comparison and a multi-model/SSP range, never a daily forecast.",
    ),
)


def _spatial_exposure_descriptor(kind: SpatialExposureKind) -> SourceDescriptor:
    label = kind.value.replace("_", " ")
    return SourceDescriptor(
        source_id=f"{kind.value}-exposure",
        provider="No source selected",
        dataset=f"Dedicated {label} exposure layer",
        capabilities=(SourceCapability(f"{kind.value}_exposure"),),
        implementation=SourceImplementationState.UNAVAILABLE,
        remote_probe_policy=RemoteProbePolicy.NOT_APPLICABLE,
        evidence_contract=EvidenceContract(
            requires_model_version=True,
            required_query_keys=("geometry_hash", "layer_version"),
        ),
        limitations=(
            f"No dedicated, source-backed {label} exposure adapter has been selected or installed.",
            "This capability cannot emit an asset-risk decision without a published exposure/vulnerability policy.",
        ),
    )


FLOOD_EXPOSURE_DESCRIPTOR = _spatial_exposure_descriptor(SpatialExposureKind.FLOOD)
WILDFIRE_EXPOSURE_DESCRIPTOR = _spatial_exposure_descriptor(SpatialExposureKind.WILDFIRE)
WATER_STRESS_EXPOSURE_DESCRIPTOR = _spatial_exposure_descriptor(SpatialExposureKind.WATER_STRESS)


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

    descriptor = POWER_DAILY_DESCRIPTOR

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

        evidence = validate_evidence(
            EvidenceRecord(
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
            ),
            self.descriptor.evidence_contract,
        )
        return NormalizedDataset(evidence=evidence, observations=observations)

    def source_health(self, *, now: datetime | None = None) -> SourceHealth:
        """Disclose local adapter state without adding a hidden POWER request."""

        return SourceHealth(
            descriptor=self.descriptor,
            status=SourceHealthState.NOT_CHECKED,
            checked_at=now or datetime.now(UTC),
            message=(
                "The NASA POWER adapter is configured. Remote availability is evaluated when an "
                "assessment retrieves source data, not by this health snapshot."
            ),
            details={"endpoint": self.endpoint},
        )

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
    """A truthful adapter boundary for a source that is not installed yet."""

    descriptor: SourceDescriptor

    def __init__(self, descriptor: SourceDescriptor, setup_message: str) -> None:
        if descriptor.implementation != SourceImplementationState.UNAVAILABLE:
            raise ValueError("unavailable provider needs an unavailable source descriptor")
        self.descriptor = descriptor
        self.provider_name = descriptor.provider
        self.setup_message = setup_message

    def fetch(self) -> NoReturn:
        raise ProviderUnavailable(
            self.setup_message,
            {"provider": self.provider_name, "synthetic_fallback_used": False},
        )

    def source_health(self, *, now: datetime | None = None) -> SourceHealth:
        return SourceHealth(
            descriptor=self.descriptor,
            status=SourceHealthState.UNAVAILABLE,
            checked_at=now or datetime.now(UTC),
            message=self.setup_message,
            details={"synthetic_fallback_used": False},
        )


class ECMWFOpenDataProvider(UnavailableHorizonProvider):
    def __init__(self) -> None:
        super().__init__(
            ECMWF_OPEN_DATA_DESCRIPTOR,
            "ECMWF Open Data forecast adapter is not implemented in this foundation; no forecast was generated",
        )

    def fetch_forecast(
        self, _site: SiteInput, _start: datetime, _end: datetime
    ) -> OperationalForecastDataset:
        self.fetch()


class CopernicusSeasonalProvider(UnavailableHorizonProvider):
    def __init__(self) -> None:
        super().__init__(
            COPERNICUS_SEASONAL_DESCRIPTOR,
            "Copernicus seasonal retrieval and local hindcast calibration are not implemented in this foundation; no seasonal outlook was generated",
        )

    def fetch_seasonal(
        self, _site: SiteInput, _target_start: date, _target_end: date
    ) -> SeasonalOutlookDataset:
        self.fetch()


class NexGddpCmip6Provider(UnavailableHorizonProvider):
    def __init__(self) -> None:
        super().__init__(
            NEX_GDDP_CMIP6_DESCRIPTOR,
            "NEX-GDDP-CMIP6 scenario extraction is not implemented in this foundation; no scenario projection was generated",
        )

    def fetch_projection(self, _site: SiteInput) -> ScenarioProjectionDataset:
        self.fetch()


class UnavailableSpatialExposureProvider(UnavailableHorizonProvider):
    """No spatial hazard is substituted with weather or an unlabeled proxy."""

    def __init__(self, kind: SpatialExposureKind) -> None:
        descriptor_by_kind = {
            SpatialExposureKind.FLOOD: FLOOD_EXPOSURE_DESCRIPTOR,
            SpatialExposureKind.WILDFIRE: WILDFIRE_EXPOSURE_DESCRIPTOR,
            SpatialExposureKind.WATER_STRESS: WATER_STRESS_EXPOSURE_DESCRIPTOR,
        }
        descriptor = descriptor_by_kind[kind]
        super().__init__(
            descriptor,
            f"No dedicated {kind.value.replace('_', ' ')} exposure adapter is installed; no exposure result was generated",
        )

    def fetch_exposure(self, _site: SiteInput) -> SpatialExposureDataset:
        self.fetch()
