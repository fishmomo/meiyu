from dataclasses import replace

import numpy as np

from pipeline.core.low_trough_cold_front import LowTroughColdFrontInput
from pipeline.core.low_trough_cold_front import calculate_low_trough_cold_front
from pipeline.core.low_trough_cold_front import tfp_in_strong_gradient


def _input() -> LowTroughColdFrontInput:
    lons = np.linspace(108.0, 112.0, 9)
    lats = np.linspace(28.0, 32.0, 9)
    lon2d, lat2d = np.meshgrid(lons, lats)
    temperature = 285.0 + 0.4 * (lon2d - 110.0)
    return LowTroughColdFrontInput(
        lons=lons,
        lats=lats,
        temperature=temperature,
        relative_humidity=np.full(temperature.shape, 0.75),
        u=np.full(temperature.shape, 8.0),
        v=np.zeros(temperature.shape),
        geopotential_height_500=np.full(temperature.shape, 5600.0),
    )


def test_calculate_low_trough_cold_front_returns_gridded_diagnostics():
    result = calculate_low_trough_cold_front(_input())

    assert result.thetae.shape == (9, 9)
    assert np.nanmax(result.thetae_gradient) > 0.0
    assert result.theta.shape == (9, 9)
    assert np.nanmax(result.theta_gradient) > 0.0
    assert result.tfp.shape == (9, 9)
    assert result.frontogenesis.shape == (9, 9)
    assert result.cold_advection.shape == (9, 9)
    assert result.candidate_mask.shape == (9, 9)


def test_uniform_wind_has_near_zero_divergence_and_expected_cold_advection_sign():
    result = calculate_low_trough_cold_front(_input())

    assert np.nanmax(np.abs(result.divergence)) < 1e-12
    assert float(np.nanmedian(result.cold_advection)) < 0.0


def test_convergent_flow_is_retained_as_candidate_support():
    base = _input()
    lon2d, lat2d = np.meshgrid(base.lons, base.lats)
    x_m = (lon2d - 110.0) * 111_000.0 * np.cos(np.deg2rad(lat2d))
    y_m = (lat2d - 30.0) * 111_000.0
    convergent = replace(base, u=-1e-5 * x_m, v=-1e-5 * y_m)

    result = calculate_low_trough_cold_front(convergent)

    assert float(np.nanmean(result.divergence)) < 0.0
    assert result.candidate_mask.dtype == bool


def test_tfp_plot_is_restricted_to_the_strong_gradient_band():
    tfp = np.arange(6.0).reshape(2, 3)
    gradient = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])

    masked = tfp_in_strong_gradient(tfp, gradient, percentile=50.0)

    assert np.isnan(masked[0, 0])
    assert np.isnan(masked[0, 2])
    assert np.array_equal(masked[1], np.array([3.0, 4.0, 5.0]))
