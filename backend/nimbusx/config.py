"""Runtime configuration for the NimbusX API.

Configuration deliberately has conservative defaults: provider traffic is HTTPS
only, browser origins are explicit, and production is explicitly disabled until
identity, tenant isolation, durable jobs, and object storage exist. The
in-memory development store is useful for local evaluation only; it is not
presented as a multi-tenant production store.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache


class ConfigurationError(RuntimeError):
    """Raised when an unsafe deployment configuration is requested."""


def _csv(name: str, default: str) -> tuple[str, ...]:
    value = os.getenv(name, default)
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int, *, minimum: int = 1) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if value < minimum:
        raise ConfigurationError(f"{name} must be at least {minimum}")
    return value


def _utc_datetime(name: str, default: str) -> datetime:
    raw = os.getenv(name, default).strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an ISO 8601 timestamp with an offset") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ConfigurationError(f"{name} must include a UTC offset")
    return parsed.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str
    cors_origins: tuple[str, ...]
    allowed_hosts: tuple[str, ...]
    require_api_key: bool
    api_keys: tuple[str, ...]
    nasa_timeout_seconds: int
    nasa_power_base_url: str
    rate_limit_per_minute: int
    analysis_execution: str
    max_window_days: int
    legacy_weather_adapter_sunset: datetime
    control_plane_heartbeat_url: str | None
    data_plane_id: str | None
    data_plane_client_cert: str | None
    data_plane_client_key: str | None

    @classmethod
    def from_environment(cls) -> Settings:
        settings = cls(
            environment=os.getenv("NIMBUSX_ENV", "development").strip().lower(),
            cors_origins=_csv(
                "NIMBUSX_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
            ),
            allowed_hosts=_csv("NIMBUSX_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver"),
            require_api_key=_bool("NIMBUSX_REQUIRE_API_KEY"),
            api_keys=_csv("NIMBUSX_API_KEYS", ""),
            nasa_timeout_seconds=_int("NIMBUSX_NASA_TIMEOUT_SECONDS", 30),
            nasa_power_base_url=os.getenv(
                "NIMBUSX_NASA_POWER_BASE_URL",
                "https://power.larc.nasa.gov/api/temporal/daily/point",
            ),
            rate_limit_per_minute=_int("NIMBUSX_RATE_LIMIT_PER_MINUTE", 120),
            analysis_execution=os.getenv("NIMBUSX_ANALYSIS_EXECUTION", "background")
            .strip()
            .lower(),
            max_window_days=_int("NIMBUSX_MAX_WINDOW_DAYS", 31),
            legacy_weather_adapter_sunset=_utc_datetime(
                "NIMBUSX_LEGACY_WEATHER_ADAPTER_SUNSET", "2026-09-01T00:00:00Z"
            ),
            control_plane_heartbeat_url=os.getenv("NIMBUSX_CONTROL_PLANE_HEARTBEAT_URL") or None,
            data_plane_id=os.getenv("NIMBUSX_DATA_PLANE_ID") or None,
            data_plane_client_cert=os.getenv("NIMBUSX_DATA_PLANE_CLIENT_CERT") or None,
            data_plane_client_key=os.getenv("NIMBUSX_DATA_PLANE_CLIENT_KEY") or None,
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.environment not in {
            "development",
            "test",
            "staging",
            "production",
            "private-data-plane",
        }:
            raise ConfigurationError(
                "NIMBUSX_ENV must be development, test, staging, production, or private-data-plane"
            )
        if self.analysis_execution not in {"background", "inline"}:
            raise ConfigurationError("NIMBUSX_ANALYSIS_EXECUTION must be background or inline")
        if not self.cors_origins or "*" in self.cors_origins:
            raise ConfigurationError("NIMBUSX_CORS_ORIGINS must be an explicit allow-list")
        if self.require_api_key and not self.api_keys:
            raise ConfigurationError("NIMBUSX_REQUIRE_API_KEY=true requires NIMBUSX_API_KEYS")
        if self.environment == "production":
            raise ConfigurationError(
                "production is disabled in this foundation until OIDC, role authorization, "
                "tenant-scoped Postgres/RLS, durable jobs, and object storage are configured"
            )
        if self.control_plane_heartbeat_url and not self.control_plane_heartbeat_url.startswith(
            "https://"
        ):
            raise ConfigurationError("NIMBUSX_CONTROL_PLANE_HEARTBEAT_URL must use HTTPS")
        if not self.nasa_power_base_url.startswith("https://"):
            raise ConfigurationError("NIMBUSX_NASA_POWER_BASE_URL must use HTTPS")
        data_plane_values = (
            self.control_plane_heartbeat_url,
            self.data_plane_id,
            self.data_plane_client_cert,
            self.data_plane_client_key,
        )
        if any(data_plane_values) and not all(data_plane_values):
            raise ConfigurationError(
                "data-plane heartbeat requires URL, ID, client certificate, and client key"
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_environment()
