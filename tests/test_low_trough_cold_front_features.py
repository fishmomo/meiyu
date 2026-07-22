import numpy as np

from pipeline.core.low_trough_cold_front_features import FrontLine
from pipeline.core.low_trough_cold_front_features import extract_primary_front_line
from pipeline.core.low_trough_cold_front_features import extract_trough_axis
from pipeline.core.low_trough_cold_front_features import signed_front_trough_separation_deg


def test_extract_primary_front_line_follows_tfp_zero_inside_candidate_band():
    lons = np.linspace(100.0, 108.0, 9)
    lats = np.linspace(30.0, 36.0, 7)
    lon2d, _ = np.meshgrid(lons, lats)
    tfp = lon2d - 104.0
    gradient = np.ones_like(tfp)
    candidate = np.ones_like(tfp, dtype=bool)

    line = extract_primary_front_line(lons, lats, tfp, gradient, candidate)

    assert line is not None
    assert line.longitude.size >= 6
    assert np.allclose(line.longitude, 104.0, atol=0.25)


def test_extract_trough_axis_follows_zonal_height_minimum():
    lons = np.linspace(96.0, 124.0, 57)
    lats = np.linspace(25.0, 45.0, 41)
    lon2d, lat2d = np.meshgrid(lons, lats)
    height = 5600.0 + (lon2d - 110.0) ** 2 + 0.02 * (lat2d - 35.0) ** 2

    trough = extract_trough_axis(lons, lats, height, latitude_bounds=(28.0, 42.0))

    assert trough is not None
    assert trough.longitude.size > 10
    assert np.allclose(trough.longitude, 110.0, atol=0.6)


def test_signed_separation_is_positive_when_front_is_east_of_trough():
    front = FrontLine(
        longitude=np.array([113.0, 113.0, 113.0]),
        latitude=np.array([31.0, 33.0, 35.0]),
    )
    trough = FrontLine(
        longitude=np.array([110.0, 110.0, 110.0]),
        latitude=np.array([30.0, 33.0, 36.0]),
    )

    separation = signed_front_trough_separation_deg(front, trough)

    assert separation == 3.0
