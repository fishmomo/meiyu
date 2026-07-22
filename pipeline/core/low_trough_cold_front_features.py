"""Geometric first-pass features for low-trough cold-front diagnostics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.signal import find_peaks
from skimage.measure import find_contours


@dataclass(frozen=True, slots=True)
class FrontLine:
    """A latitude-longitude polyline used for either a front or trough axis."""

    longitude: np.ndarray
    latitude: np.ndarray


def _contour_length_km(longitude: np.ndarray, latitude: np.ndarray) -> float:
    if longitude.size < 2:
        return 0.0
    dlon = np.diff(longitude) * np.cos(np.deg2rad((latitude[1:] + latitude[:-1]) / 2.0))
    dlat = np.diff(latitude)
    return float(np.sum(np.hypot(dlon, dlat)) * 111.0)


def extract_primary_front_line(
    lons: np.ndarray,
    lats: np.ndarray,
    tfp: np.ndarray,
    thetae_gradient: np.ndarray,
    candidate_mask: np.ndarray,
    *,
    gradient_percentile: float = 85.0,
) -> FrontLine | None:
    """Return the longest TFP=0 segment within a strong candidate thermal band.

    This is an objective first pass only.  The selected segment is deliberately
    retained as a separate line so a forecaster can replace or edit it later.
    """
    longitude = np.asarray(lons, dtype=float)
    latitude = np.asarray(lats, dtype=float)
    tfp_values = np.asarray(tfp, dtype=float)
    gradient_values = np.asarray(thetae_gradient, dtype=float)
    candidate = np.asarray(candidate_mask, dtype=bool)
    expected = (latitude.size, longitude.size)
    if tfp_values.shape != expected or gradient_values.shape != expected or candidate.shape != expected:
        raise ValueError("front-line fields must match the latitude-longitude grid")
    threshold = np.nanpercentile(gradient_values, gradient_percentile)
    allowed = candidate & (gradient_values >= threshold)
    field = np.where(allowed, tfp_values, np.nan)
    contours = find_contours(field, level=0.0)
    if not contours:
        return None

    best: FrontLine | None = None
    best_length = 0.0
    row_index = np.arange(latitude.size, dtype=float)
    col_index = np.arange(longitude.size, dtype=float)
    for contour in contours:
        contour_lons = np.interp(contour[:, 1], col_index, longitude)
        contour_lats = np.interp(contour[:, 0], row_index, latitude)
        length = _contour_length_km(contour_lons, contour_lats)
        if length > best_length:
            best = FrontLine(contour_lons, contour_lats)
            best_length = length
    return best


def extract_trough_axis(
    lons: np.ndarray,
    lats: np.ndarray,
    geopotential_height: np.ndarray,
    *,
    latitude_bounds: tuple[float, float] = (25.0, 50.0),
    smoothing_sigma: float = 1.5,
) -> FrontLine | None:
    """Extract a first-pass 500-hPa trough axis from zonal local minima."""
    longitude = np.asarray(lons, dtype=float)
    latitude = np.asarray(lats, dtype=float)
    height = np.asarray(geopotential_height, dtype=float)
    if height.shape != (latitude.size, longitude.size):
        raise ValueError("geopotential_height must match the latitude-longitude grid")
    smoothed = gaussian_filter(height, smoothing_sigma) if smoothing_sigma else height
    lower, upper = sorted(latitude_bounds)
    selected_lons: list[float] = []
    selected_lats: list[float] = []
    for row, lat in enumerate(latitude):
        if not lower <= lat <= upper:
            continue
        minima, _ = find_peaks(-smoothed[row])
        if minima.size == 0:
            continue
        index = int(minima[np.argmin(smoothed[row, minima])])
        selected_lons.append(float(longitude[index]))
        selected_lats.append(float(lat))
    if len(selected_lons) < 3:
        return None
    return FrontLine(np.asarray(selected_lons), np.asarray(selected_lats))


def signed_front_trough_separation_deg(front: FrontLine, trough: FrontLine) -> float:
    """Return mean front-minus-trough longitude at matched latitudes.

    Positive means the front is east/downstream of the trough, the usual
    Northern-Hemisphere interpretation of a trough-front configuration.
    """
    order = np.argsort(trough.latitude)
    trough_lon = np.interp(
        front.latitude,
        trough.latitude[order],
        trough.longitude[order],
        left=np.nan,
        right=np.nan,
    )
    separation = front.longitude - trough_lon
    if not np.any(np.isfinite(separation)):
        return float("nan")
    return float(np.nanmean(separation))
