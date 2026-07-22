from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import xarray as xr

from pipeline.core.era5_dynamics import Era5DynamicsInput
from pipeline.core.era5_dynamics import calculate_era5_dynamics
from pipeline.core.era5_dynamics import read_era5_dynamics


def make_dynamics_input(
    u: float,
    v: float,
    q: float,
    t: float,
    rh: float,
) -> Era5DynamicsInput:
    lons = np.linspace(108.0, 112.0, 9)
    lats = np.linspace(28.0, 32.0, 9)
    shape = (len(lats), len(lons))
    return Era5DynamicsInput(
        lons=lons,
        lats=lats,
        temperature=np.full(shape, t),
        relative_humidity=np.full(shape, rh),
        specific_humidity=np.full(shape, q),
        u=np.full(shape, u),
        v=np.full(shape, v),
    )


def make_linear_flow_input(sign: float) -> Era5DynamicsInput:
    data = make_dynamics_input(u=0.0, v=0.0, q=0.01, t=290.0, rh=80.0)
    lon2d, lat2d = np.meshgrid(data.lons, data.lats)
    x_m = (lon2d - 110.0) * 111_000.0 * np.cos(np.radians(lat2d))
    y_m = (lat2d - 30.0) * 111_000.0
    return replace(
        data,
        u=sign * 1e-5 * x_m,
        v=sign * 1e-5 * y_m,
    )


def test_uniform_wind_has_zero_divergence():
    data = make_dynamics_input(u=10.0, v=0.0, q=0.01, t=290.0, rh=80.0)

    result = calculate_era5_dynamics(data, 850.0)

    assert np.nanmax(np.abs(result.divergence)) < 1e-12


def test_linear_outflow_has_positive_divergence():
    data = make_linear_flow_input(sign=1.0)

    result = calculate_era5_dynamics(data, 850.0)

    assert float(np.nanmean(result.divergence)) > 0.0


def test_converging_moisture_flux_is_positive():
    data = make_linear_flow_input(sign=-1.0)

    result = calculate_era5_dynamics(data, 850.0)

    assert float(np.nanmean(result.moisture_flux_convergence)) > 0.0


def test_read_era5_dynamics_selects_time_level_and_domain():
    times = np.array(["2017-06-28T12", "2017-06-28T18"], dtype="datetime64[h]")
    levels = np.array([850.0, 700.0])
    latitudes = np.array([32.0, 31.0, 30.0])
    longitudes = np.array([110.0, 111.0, 112.0, 113.0])
    shape = (len(times), len(levels), len(latitudes), len(longitudes))
    data_vars = {
        name: (
            ("valid_time", "pressure_level", "latitude", "longitude"),
            np.full(shape, value, dtype=float),
        )
        for name, value in {
            "u": 10.0,
            "v": 2.0,
            "q": 0.01,
            "t": 290.0,
            "r": 80.0,
        }.items()
    }
    dataset = xr.Dataset(
        data_vars,
        coords={
            "valid_time": times,
            "pressure_level": levels,
            "latitude": latitudes,
            "longitude": longitudes,
        },
    )

    with patch(
        "pipeline.core.era5_dynamics.open_dataset_compat",
        return_value=dataset,
    ):
        result = read_era5_dynamics(
            Path("era5.nc"),
            "2017-06-28T18",
            850.0,
            np.array([30.0, 31.0]),
            np.array([111.0, 112.0]),
        )

    assert result.temperature.shape == (2, 2)
    assert np.array_equal(result.lats, np.array([30.0, 31.0]))
    assert np.array_equal(result.lons, np.array([111.0, 112.0]))
    assert np.all(result.u == 10.0)


def _mock_era5_dataset() -> xr.Dataset:
    times = np.array(["2017-06-28T18"], dtype="datetime64[h]")
    levels = np.array([850.0])
    latitudes = np.array([31.0, 30.0])
    longitudes = np.array([111.0, 112.0])
    shape = (1, 1, 2, 2)
    return xr.Dataset(
        {
            name: (
                ("valid_time", "pressure_level", "latitude", "longitude"),
                np.full(shape, value, dtype=float),
            )
            for name, value in {
                "u": 10.0,
                "v": 2.0,
                "q": 0.01,
                "t": 290.0,
                "r": 80.0,
            }.items()
        },
        coords={
            "valid_time": times,
            "pressure_level": levels,
            "latitude": latitudes,
            "longitude": longitudes,
        },
    )


@pytest.mark.parametrize(
    ("target_time", "level_hpa", "lats", "lons"),
    [
        ("2017-06-28T12", 850.0, [30.0], [111.0]),
        ("2017-06-28T18", 700.0, [30.0], [111.0]),
        ("2017-06-28T18", 850.0, [30.1], [111.0]),
    ],
)
def test_read_era5_dynamics_rejects_missing_exact_selection(
    target_time,
    level_hpa,
    lats,
    lons,
):
    with patch(
        "pipeline.core.era5_dynamics.open_dataset_compat",
        return_value=_mock_era5_dataset(),
    ), pytest.raises(ValueError, match="requires exact target time"):
        read_era5_dynamics(
            Path("era5.nc"),
            target_time,
            level_hpa,
            np.asarray(lats),
            np.asarray(lons),
        )
