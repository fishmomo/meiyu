"""Literature-based spatial regions for Northeast China cold vortices.

The closed-circulation body is the outermost 500-hPa closed contour around
the objectively identified low center.  The peripheral circulation is the
connected positive-relative-vorticity component at 500 hPa.
"""

from dataclasses import dataclass

import matplotlib
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.path import Path as MatplotlibPath
from scipy import ndimage
from shapely.geometry import Point, Polygon


matplotlib.use("Agg")


@dataclass(frozen=True)
class ClosedContour:
    level_gpm: float
    polygon: Polygon


def _closed_subpaths(path: MatplotlibPath) -> list[np.ndarray]:
    """Extract closed components from a Matplotlib contour compound path."""
    if len(path.vertices) == 0:
        return []
    if path.codes is None:
        return [path.vertices] if np.allclose(path.vertices[0], path.vertices[-1]) else []
    starts = np.flatnonzero(path.codes == MatplotlibPath.MOVETO)
    ends = np.append(starts[1:], len(path.codes))
    closed: list[np.ndarray] = []
    for start, end in zip(starts, ends):
        vertices = path.vertices[start:end]
        codes = path.codes[start:end]
        is_closed = codes[-1] == MatplotlibPath.CLOSEPOLY or np.allclose(vertices[0], vertices[-1])
        if not is_closed:
            continue
        if codes[-1] == MatplotlibPath.CLOSEPOLY:
            vertices = vertices[:-1]
        if len(vertices) >= 3:
            closed.append(np.vstack((vertices, vertices[0])))
    return closed


def refine_center_to_z500_minimum(
    z500_gpm: np.ndarray,
    latitude_deg_n: np.ndarray,
    longitude_deg_e: np.ndarray,
    *,
    candidate_latitude: float,
    candidate_longitude: float,
    search_radius_deg: float = 2.5,
) -> tuple[float, float, float]:
    """Refine a coarse-grid center to the Z500 minimum in its local neighborhood."""
    latitude_ok = np.abs(latitude_deg_n - candidate_latitude) <= search_radius_deg
    longitude_ok = np.abs(longitude_deg_e - candidate_longitude) <= search_radius_deg
    if not latitude_ok.any() or not longitude_ok.any():
        raise ValueError("candidate center search neighborhood does not intersect the grid")
    local = z500_gpm[np.ix_(latitude_ok, longitude_ok)]
    row, column = np.unravel_index(np.nanargmin(local), local.shape)
    latitude_index = np.flatnonzero(latitude_ok)[row]
    longitude_index = np.flatnonzero(longitude_ok)[column]
    return (
        float(latitude_deg_n[latitude_index]),
        float(longitude_deg_e[longitude_index]),
        float(z500_gpm[latitude_index, longitude_index]),
    )


def outermost_closed_contour(
    z500_gpm: np.ndarray,
    latitude_deg_n: np.ndarray,
    longitude_deg_e: np.ndarray,
    *,
    center_latitude: float,
    center_longitude: float,
    interval_gpm: float = 40.0,
) -> ClosedContour | None:
    """Return the highest valid closed Z500 contour enclosing one low center."""
    start = np.ceil(float(np.nanmin(z500_gpm)) / interval_gpm) * interval_gpm
    stop = np.floor(float(np.nanmax(z500_gpm)) / interval_gpm) * interval_gpm
    center = Point(center_longitude, center_latitude)
    result: ClosedContour | None = None
    figure, axis = plt.subplots()
    try:
        for level in np.arange(start, stop + interval_gpm, interval_gpm):
            contour_set = axis.contour(
                longitude_deg_e, latitude_deg_n, z500_gpm, levels=[level]
            )
            for path in contour_set.get_paths():
                for vertices in _closed_subpaths(path):
                    polygon = Polygon(vertices)
                    if polygon.is_valid and polygon.area > 0 and polygon.covers(center):
                        result = ClosedContour(float(level), polygon)
    finally:
        plt.close(figure)
    return result


def relative_vorticity(
    u_ms: np.ndarray,
    v_ms: np.ndarray,
    latitude_deg_n: np.ndarray,
    longitude_deg_e: np.ndarray,
    *,
    earth_radius_m: float = 6_371_000.0,
) -> np.ndarray:
    """Calculate 500-hPa relative vorticity on a regular latitude/longitude grid."""
    latitude_rad = np.deg2rad(latitude_deg_n)
    longitude_rad = np.deg2rad(longitude_deg_e)
    dv_dlambda = np.gradient(v_ms, longitude_rad, axis=1)
    du_dphi = np.gradient(u_ms, latitude_rad, axis=0)
    return (dv_dlambda - du_dphi * np.cos(latitude_rad)[:, None]) / (
        earth_radius_m * np.cos(latitude_rad)[:, None]
    )


def connected_positive_vorticity_mask(
    relative_vorticity_s_1: np.ndarray,
    latitude_deg_n: np.ndarray,
    longitude_deg_e: np.ndarray,
    body_polygon: Polygon,
) -> np.ndarray:
    """Keep positive-vorticity cells that touch the closed-circulation body."""
    body_mask = polygon_mask(body_polygon, latitude_deg_n, longitude_deg_e)
    positive = np.isfinite(relative_vorticity_s_1) & (relative_vorticity_s_1 > 0.0)
    labels, _ = ndimage.label(positive, structure=np.ones((3, 3), dtype=int))
    touching = labels[ndimage.binary_dilation(body_mask, structure=np.ones((3, 3), dtype=bool))]
    touching = touching[touching > 0]
    return np.isin(labels, touching)


def polygon_mask(
    polygon: Polygon,
    latitude_deg_n: np.ndarray,
    longitude_deg_e: np.ndarray,
) -> np.ndarray:
    """Return a boolean grid mask for points covered by a polygon."""
    longitude_2d, latitude_2d = np.meshgrid(longitude_deg_e, latitude_deg_n)
    return np.fromiter(
        (
            polygon.covers(Point(lon, lat))
            for lon, lat in zip(longitude_2d.ravel(), latitude_2d.ravel())
        ),
        dtype=bool,
        count=longitude_2d.size,
    ).reshape(longitude_2d.shape)
