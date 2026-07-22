"""Shared scalar summaries for time-resolved cold-vortex core diagnostics."""

from __future__ import annotations

import numpy as np


def moisture_flux_convergence(
    *,
    specific_humidity: np.ndarray,
    u: np.ndarray,
    v: np.ndarray,
    latitude: np.ndarray,
    longitude: np.ndarray,
    earth_radius_m: float = 6_371_000.0,
) -> np.ndarray:
    """Calculate -div(q*u, q*v) on a regular latitude-longitude grid."""
    q = np.asarray(specific_humidity, dtype=float)
    zonal_wind = np.asarray(u, dtype=float)
    meridional_wind = np.asarray(v, dtype=float)
    lat = np.asarray(latitude, dtype=float)
    lon = np.asarray(longitude, dtype=float)
    expected = (lat.size, lon.size)
    if q.shape != expected or zonal_wind.shape != expected or meridional_wind.shape != expected:
        raise ValueError("specific humidity and winds must match the latitude-longitude grid")
    lat_rad = np.deg2rad(lat)
    lon_rad = np.deg2rad(lon)
    flux_u = q * zonal_wind
    flux_v = q * meridional_wind
    d_flux_u_dlon = np.gradient(flux_u, lon_rad, axis=1)
    d_flux_v_dlat = np.gradient(flux_v, lat_rad, axis=0)
    divergence = d_flux_u_dlon / (earth_radius_m * np.cos(lat_rad)[:, None]) + d_flux_v_dlat / earth_radius_m
    return -divergence


def area_weighted_mean(
    field: np.ndarray,
    core_mask: np.ndarray,
    cell_area_km2: np.ndarray,
) -> float:
    """Return the area-weighted mean over finite cells in the vortex core."""
    values = np.asarray(field, dtype=float)
    core = np.asarray(core_mask, dtype=bool)
    weights = np.asarray(cell_area_km2, dtype=float)
    valid = core & np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    if not np.any(valid):
        return float("nan")
    return float(np.average(values[valid], weights=weights[valid]))


def core_summary(
    *,
    core_mask: np.ndarray,
    cell_area_km2: np.ndarray,
    fields: dict[str, np.ndarray],
) -> dict[str, float]:
    """Summarize named two-dimensional diagnostics over one core mask."""
    core = np.asarray(core_mask, dtype=bool)
    area = np.asarray(cell_area_km2, dtype=float)
    if core.shape != area.shape:
        raise ValueError("core_mask and cell_area_km2 must have the same shape")
    summary = {"core_area_km2": float(area[core].sum())}
    for name, field in fields.items():
        if np.asarray(field).shape != core.shape:
            raise ValueError(f"field {name} does not match core-mask shape")
        summary[name] = area_weighted_mean(field, core, area)
    return summary
