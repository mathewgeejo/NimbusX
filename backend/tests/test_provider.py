import json
from datetime import date
from urllib.error import URLError

import pytest

from nimbusx.errors import ProviderUnavailable
from nimbusx.providers import PowerDailyProvider
from nimbusx.schemas import SiteInput


class Response:
    def __init__(self, payload):
        self.body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body

    def geturl(self):
        return "https://power.example.test/daily"


def test_power_provider_normalizes_source_values_and_preserves_evidence():
    payload = {
        "header": {"title": "NASA POWER Daily"},
        "properties": {
            "parameter": {
                "T2M_MAX": {"20200102": 31.5},
                "T2M_MIN": {"20200102": 22.0},
                "PRECTOTCORR": {"20200102": 4.2},
                "WS10M": {"20200102": 6.0},
            }
        },
    }
    provider = PowerDailyProvider(
        opener=lambda *_args, **_kwargs: Response(payload),
        endpoint="https://power.example.test/daily",
    )
    dataset = provider.fetch_daily(
        SiteInput(name="New York", latitude=40.7, longitude=-74.0, timezone="America/New_York"),
        date(2020, 1, 2),
        date(2020, 1, 2),
        purpose="test",
    )

    assert len(dataset.observations) == 1
    observation = dataset.observations[0]
    assert observation.temperature_max_c == 31.5
    # A UTC daily aggregate uses an explicit midpoint convention for local labels.
    assert observation.timestamp_utc.isoformat() == "2020-01-02T12:00:00+00:00"
    assert observation.local_date.isoformat() == "2020-01-02"
    assert (
        dataset.evidence.query["daily_label_mapping"]["representative_timestamp_utc"] == "12:00:00Z"
    )
    assert (
        dataset.evidence.query["wind_metric"]
        == "WS10M daily-mean wind speed at 10 m above the source grid"
    )
    assert dataset.evidence.content_hash
    assert dataset.evidence.raw_extract["payload"] == payload


def test_power_provider_never_emits_fallback_on_network_failure():
    provider = PowerDailyProvider(
        opener=lambda *_args, **_kwargs: (_ for _ in ()).throw(URLError("offline")),
        endpoint="https://power.example.test/daily",
    )
    with pytest.raises(ProviderUnavailable, match="no substitute data"):
        provider.fetch_daily(
            SiteInput(name="Equator", latitude=0, longitude=0, timezone="UTC"),
            date(2020, 1, 1),
            date(2020, 1, 2),
            purpose="test",
        )
