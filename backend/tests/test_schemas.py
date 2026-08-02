from datetime import date

import pytest
from pydantic import ValidationError

from nimbusx.schemas import SiteGeometry, SiteInput, TimeWindow


def test_zero_coordinates_are_valid_for_site_and_point_geometry():
    site = SiteInput(
        name="Prime Meridian site",
        latitude=0,
        longitude=0,
        timezone="UTC",
        geometry=SiteGeometry(type="Point", coordinates=[0, 0]),
    )

    assert site.latitude == 0
    assert site.longitude == 0
    assert site.geometry is not None
    assert site.geometry.coordinates == [0, 0]


def test_polygon_accepts_closed_wgs84_ring_with_zero_coordinates():
    geometry = SiteGeometry(
        type="Polygon",
        coordinates=[[[0, 0], [1, 0], [1, 1], [0, 0]]],
    )

    assert geometry.type == "Polygon"


@pytest.mark.parametrize(
    ("coordinates", "message"),
    [
        ([[[0, 0], [1, 0], [1, 1]]], "at least four positions"),
        ([[[0, 0], [1, 0], [1, 1], [0, 1]]], "must be closed"),
        ([[[0, 0], [0, 0], [0, 0], [0, 0]]], "three distinct vertices"),
        ([[[0, 0], [181, 0], [1, 1], [0, 0]]], "outside WGS84"),
    ],
)
def test_polygon_rejects_invalid_or_degenerate_rings(coordinates, message):
    with pytest.raises(ValidationError, match=message):
        SiteGeometry(type="Polygon", coordinates=coordinates)


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (float("nan"), 0),
        (0, float("inf")),
        (True, 0),
        (0, False),
    ],
)
def test_site_rejects_non_finite_or_boolean_coordinates(latitude, longitude):
    with pytest.raises(ValidationError, match="finite numbers"):
        SiteInput(name="Invalid coordinate", latitude=latitude, longitude=longitude, timezone="UTC")


def test_time_window_uses_a_single_local_date_through_dst_transition():
    window = TimeWindow(
        start="2024-03-10T00:30:00-05:00",
        end="2024-03-10T23:30:00-04:00",
    )

    assert window.local_dates("America/New_York") == [date(2024, 3, 10)]


def test_time_window_supports_leap_day_local_calendar_window():
    window = TimeWindow(
        start="2024-02-29T00:00:00+00:00",
        end="2024-02-29T23:59:59+00:00",
    )

    assert window.local_dates("UTC") == [date(2024, 2, 29)]


def test_time_window_rejects_invalid_calendar_date_and_naive_timestamp():
    with pytest.raises(ValidationError):
        TimeWindow(start="2023-02-29T00:00:00+00:00", end="2023-03-01T00:00:00+00:00")
    with pytest.raises(ValidationError, match="explicit UTC offset"):
        TimeWindow(start="2024-02-29T00:00:00", end="2024-02-29T23:59:59")
