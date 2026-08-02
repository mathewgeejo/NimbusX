from datetime import UTC, datetime

import pytest

from nimbusx.config import ConfigurationError, Settings
from nimbusx.data_plane import send_heartbeat, status


def build_settings(**overrides) -> Settings:
    values = {
        "environment": "test",
        "cors_origins": ("http://localhost:5173",),
        "allowed_hosts": ("testserver",),
        "require_api_key": False,
        "api_keys": (),
        "nasa_timeout_seconds": 1,
        "nasa_power_base_url": "https://power.example.test/daily",
        "rate_limit_per_minute": 60,
        "analysis_execution": "inline",
        "max_window_days": 31,
        "legacy_weather_adapter_sunset": datetime(2026, 9, 1, tzinfo=UTC),
        "control_plane_heartbeat_url": None,
        "data_plane_id": None,
        "data_plane_client_cert": None,
        "data_plane_client_key": None,
    }
    values.update(overrides)
    return Settings(**values)


def test_private_data_plane_requires_complete_mtls_configuration():
    settings = build_settings(
        environment="private-data-plane",
        control_plane_heartbeat_url="https://control.example.test/heartbeat",
        data_plane_id="plane-123",
    )
    with pytest.raises(ConfigurationError, match="data-plane heartbeat requires"):
        settings.validate()


def test_private_data_plane_status_is_metadata_only_when_configured():
    settings = build_settings(
        environment="private-data-plane",
        control_plane_heartbeat_url="https://control.example.test/heartbeat",
        data_plane_id="plane-123",
        data_plane_client_cert="/run/mtls/tls.crt",
        data_plane_client_key="/run/mtls/tls.key",
    )
    settings.validate()
    assert status(settings) == {
        "status": "configured",
        "data_plane_id": "plane-123",
        "transport": "outbound_mtls_https",
        "raw_data_transfer": False,
        "message": "Heartbeat configuration is present; invoke with --heartbeat to send metadata only.",
    }


def test_production_startup_is_refused_until_tenant_controls_exist():
    settings = build_settings(
        environment="production",
        require_api_key=True,
        api_keys=("local-test-key",),
    )
    with pytest.raises(ConfigurationError, match="production is disabled"):
        settings.validate()


def test_private_data_plane_reports_missing_mtls_files_without_crashing():
    settings = build_settings(
        environment="private-data-plane",
        control_plane_heartbeat_url="https://control.example.test/heartbeat",
        data_plane_id="plane-123",
        data_plane_client_cert="C:/missing/tls.crt",
        data_plane_client_key="C:/missing/tls.key",
    )

    result = send_heartbeat(settings)

    assert result["status"] == "unreachable"
    assert result["reason"] in {"FileNotFoundError", "OSError"}
    assert result["raw_data_transfer"] is False
