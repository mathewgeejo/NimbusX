"""Application-facing source catalog.

The catalog is intentionally local and non-networked.  It lets an API endpoint
show which adapters exist, which ones are deliberately unavailable, and which
ones have not been remotely checked.  A source retrieval remains the only
place that can establish source availability for an actual assessment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .providers import (
    CopernicusSeasonalProvider,
    ECMWFOpenDataProvider,
    NexGddpCmip6Provider,
    PowerDailyProvider,
    UnavailableSpatialExposureProvider,
)
from .source_contracts import (
    EvidenceContract,
    RemoteProbePolicy,
    SourceCapability,
    SourceDescriptor,
    SourceHealth,
    SourceHealthAdapter,
    SourceHealthRegistry,
    SourceHealthState,
    SourceImplementationState,
    SpatialExposureKind,
)


@dataclass(frozen=True, slots=True)
class _UninstrumentedDailyProviderHealth:
    """Honest source-health representation for a test/injected daily provider."""

    provider_name: str

    @property
    def descriptor(self) -> SourceDescriptor:
        return SourceDescriptor(
            source_id="injected-development-daily-provider",
            provider=self.provider_name,
            dataset="Injected development daily provider",
            capabilities=(SourceCapability.OBSERVED_DAILY, SourceCapability.HISTORICAL_BASELINE),
            implementation=SourceImplementationState.IMPLEMENTED,
            remote_probe_policy=RemoteProbePolicy.NOT_APPLICABLE,
            evidence_contract=EvidenceContract(),
            limitations=(
                "This injected provider does not expose a source-health contract.",
                "Its availability and provenance must be evaluated by the retrieval test or adapter itself.",
            ),
        )

    def source_health(self, *, now: datetime | None = None) -> SourceHealth:
        return SourceHealth(
            descriptor=self.descriptor,
            status=SourceHealthState.NOT_CHECKED,
            checked_at=now or datetime.now(UTC),
            message="An injected development provider has no independent remote health probe.",
        )


def _health_adapter_for_daily_provider(daily_provider: object) -> SourceHealthAdapter:
    candidate = getattr(daily_provider, "source_health", None)
    if callable(candidate):
        return daily_provider  # type: ignore[return-value]
    return _UninstrumentedDailyProviderHealth(type(daily_provider).__name__)


def build_source_health_registry(
    daily_provider: object | None = None,
) -> SourceHealthRegistry:
    """Build the complete V1 catalog without testing any remote provider.

    Passing the application's injected daily provider keeps test health output
    truthful.  The default POWER instance only validates local HTTPS config and
    does not perform a request.
    """

    daily = daily_provider or PowerDailyProvider()
    adapters: tuple[SourceHealthAdapter, ...] = (
        _health_adapter_for_daily_provider(daily),
        ECMWFOpenDataProvider(),
        CopernicusSeasonalProvider(),
        NexGddpCmip6Provider(),
        UnavailableSpatialExposureProvider(SpatialExposureKind.FLOOD),
        UnavailableSpatialExposureProvider(SpatialExposureKind.WILDFIRE),
        UnavailableSpatialExposureProvider(SpatialExposureKind.WATER_STRESS),
    )
    return SourceHealthRegistry(adapters)


def source_health_payload(
    daily_provider: object | None = None, *, now: datetime | None = None
) -> dict[str, Any]:
    """Convenience helper for `GET /v1/sources/health` route wiring."""

    return build_source_health_registry(daily_provider).snapshot(now=now)
