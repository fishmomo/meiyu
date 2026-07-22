"""Objective 850-hPa diagnostics for low-trough cold-front cases.

The frontogenesis definition deliberately matches the existing Meiyu-front
workflow: MetPy's kinematic frontogenesis of potential temperature using the
horizontal wind.  This module adds the companion fields needed to turn a
thermal-gradient band into a cold-front candidate.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import gaussian_filter
from metpy.calc import dewpoint_from_relative_humidity
from metpy.calc import divergence
from metpy.calc import equivalent_potential_temperature
from metpy.calc import frontogenesis
from metpy.calc import gradient
from metpy.calc import lat_lon_grid_deltas
from metpy.calc import potential_temperature
from metpy.units import units


@dataclass(frozen=True, slots=True)
class LowTroughColdFrontInput:
    lons: np.ndarray
    lats: np.ndarray
    temperature: np.ndarray
    relative_humidity: np.ndarray
    u: np.ndarray
    v: np.ndarray
    geopotential_height_500: np.ndarray


@dataclass(frozen=True, slots=True)
class LowTroughColdFrontResult:
    lons: np.ndarray
    lats: np.ndarray
    thetae: np.ndarray
    thetae_gradient: np.ndarray
    theta: np.ndarray
    theta_gradient: np.ndarray
    tfp: np.ndarray
    cold_advection: np.ndarray
    divergence: np.ndarray
    frontogenesis: np.ndarray
    candidate_mask: np.ndarray
    geopotential_height_500: np.ndarray
    u: np.ndarray
    v: np.ndarray


def tfp_in_strong_gradient(
    tfp: np.ndarray,
    thetae_gradient: np.ndarray,
    *,
    percentile: float = 85.0,
) -> np.ndarray:
    """Mask TFP outside the high theta-e-gradient band for map display."""
    if not 0.0 <= percentile <= 100.0:
        raise ValueError("percentile must be between 0 and 100")
    tfp_values = np.asarray(tfp, dtype=float)
    gradient_values = np.asarray(thetae_gradient, dtype=float)
    if tfp_values.shape != gradient_values.shape:
        raise ValueError("tfp and thetae_gradient must share the same shape")
    threshold = np.nanpercentile(gradient_values, percentile)
    return np.where(gradient_values >= threshold, tfp_values, np.nan)


def _relative_humidity_quantity(values: np.ndarray):
    rh = np.asarray(values, dtype=float)
    finite = rh[np.isfinite(rh)]
    if finite.size and np.nanmax(finite) > 1.5:
        rh = rh / 100.0
    return rh * units.dimensionless


def _validate(data: LowTroughColdFrontInput) -> tuple[int, int]:
    expected = (len(data.lats), len(data.lons))
    fields = {
        "temperature": data.temperature,
        "relative_humidity": data.relative_humidity,
        "u": data.u,
        "v": data.v,
        "geopotential_height_500": data.geopotential_height_500,
    }
    mismatched = {name: np.asarray(value).shape for name, value in fields.items() if np.asarray(value).shape != expected}
    if mismatched:
        raise ValueError(f"low-trough cold-front fields do not match grid {expected}: {mismatched}")
    return expected


def calculate_low_trough_cold_front(
    data: LowTroughColdFrontInput,
    *,
    level_hpa: float = 850.0,
    gradient_percentile: float = 97.0,
    smoothing_sigma: float = 1.5,
) -> LowTroughColdFrontResult:
    """Calculate a thermal-front candidate at one 850-hPa analysis time.

    ``cold_advection`` follows the meteorological convention ``-V·∇T``;
    consequently negative values denote cold advection.  The candidate mask
    requires a strong theta-e gradient and at least one support signal:
    cold advection, horizontal convergence, or positive frontogenesis.
    """
    _validate(data)
    if smoothing_sigma < 0.0:
        raise ValueError("smoothing_sigma must be non-negative")
    smooth = lambda values: gaussian_filter(np.asarray(values, dtype=float), smoothing_sigma) if smoothing_sigma else np.asarray(values, dtype=float)
    temperature = smooth(data.temperature) * units.kelvin
    pressure = float(level_hpa) * units.hPa
    rh = _relative_humidity_quantity(smooth(data.relative_humidity))
    u = smooth(data.u) * units("m/s")
    v = smooth(data.v) * units("m/s")
    dewpoint = dewpoint_from_relative_humidity(temperature, rh)
    thetae = equivalent_potential_temperature(pressure, temperature, dewpoint)
    theta = potential_temperature(pressure, temperature)
    dx, dy = lat_lon_grid_deltas(data.lons, data.lats)

    thetae_grad_y, thetae_grad_x = gradient(thetae, deltas=(dy, dx))
    thetae_gradient = np.sqrt(thetae_grad_x**2 + thetae_grad_y**2)
    theta_grad_y, theta_grad_x = gradient(theta, deltas=(dy, dx))
    theta_gradient = np.sqrt(theta_grad_x**2 + theta_grad_y**2)
    magnitude_grad_y, magnitude_grad_x = gradient(theta_gradient, deltas=(dy, dx))
    gradient_norm = np.sqrt(theta_grad_x**2 + theta_grad_y**2)
    safe_norm = np.where(gradient_norm.magnitude > 1e-15, gradient_norm.magnitude, np.nan) * gradient_norm.units
    tfp = -(magnitude_grad_x * thetae_grad_x + magnitude_grad_y * thetae_grad_y) / safe_norm

    temperature_grad_y, temperature_grad_x = gradient(temperature, deltas=(dy, dx))
    cold_advection = -(u * temperature_grad_x + v * temperature_grad_y)
    div = divergence(u, v, dx=dx, dy=dy)
    fg = frontogenesis(theta, u, v, dx=dx, dy=dy)

    gradient_values = np.asarray(theta_gradient.to("kelvin / meter").magnitude, dtype=float)
    threshold = np.nanpercentile(gradient_values, gradient_percentile)
    candidate = (gradient_values >= threshold) & (
        (np.asarray(cold_advection.to("kelvin / second").magnitude) < 0.0)
        | (np.asarray(div.to("1 / second").magnitude) < 0.0)
        | (np.asarray(fg.to("kelvin / meter / second").magnitude) > 0.0)
    )

    return LowTroughColdFrontResult(
        lons=np.asarray(data.lons, dtype=float),
        lats=np.asarray(data.lats, dtype=float),
        thetae=np.asarray(thetae.to("kelvin").magnitude, dtype=float),
        thetae_gradient=np.asarray(thetae_gradient.to("kelvin / meter").magnitude, dtype=float),
        theta=np.asarray(theta.to("kelvin").magnitude, dtype=float),
        theta_gradient=gradient_values,
        tfp=np.asarray(tfp.to("kelvin / meter**2").magnitude, dtype=float),
        cold_advection=np.asarray(cold_advection.to("kelvin / second").magnitude, dtype=float),
        divergence=np.asarray(div.to("1 / second").magnitude, dtype=float),
        frontogenesis=np.asarray(fg.to("kelvin / meter / second").magnitude, dtype=float),
        candidate_mask=np.asarray(candidate, dtype=bool),
        geopotential_height_500=np.asarray(data.geopotential_height_500, dtype=float),
        u=np.asarray(u.magnitude, dtype=float),
        v=np.asarray(v.magnitude, dtype=float),
    )
