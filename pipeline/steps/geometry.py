from dataclasses import dataclass

import numpy as np

from pipeline.core.front_ops import (
    build_normal_offsets,
    contour_to_lonlat,
    estimate_unit_normals,
    extract_largest_contour,
    fit_polynomial_centerline,
)


@dataclass(slots=True)
class GeometryResult:
    offsets: np.ndarray
    sampled_dx: np.ndarray
    sampled_dy: np.ndarray
    contour_x: np.ndarray
    contour_y: np.ndarray
    centerline_x: np.ndarray
    centerline_y: np.ndarray
    normal_x: np.ndarray
    normal_y: np.ndarray


def build_geometry_frame(
    nx: np.ndarray,
    ny: np.ndarray,
    distance: float,
    n_points: int,
) -> GeometryResult:
    offsets, sampled_dx, sampled_dy = build_normal_offsets(
        nx,
        ny,
        distance,
        n_points,
    )
    return GeometryResult(
        offsets=offsets,
        sampled_dx=sampled_dx,
        sampled_dy=sampled_dy,
        contour_x=np.array([], dtype=float),
        contour_y=np.array([], dtype=float),
        centerline_x=np.array([], dtype=float),
        centerline_y=np.array([], dtype=float),
        normal_x=np.asarray(nx, dtype=float),
        normal_y=np.asarray(ny, dtype=float),
    )


def build_geometry_from_mask(
    mask: np.ndarray,
    lons: np.ndarray,
    lats: np.ndarray,
    degree: int = 4,
    dense_points: int = 1000,
    n_sections: int = 10,
    distance: float = 1.0,
    n_points: int = 20,
    delta_x: float = 0.1,
) -> GeometryResult:
    contour = extract_largest_contour(mask)
    contour_x, contour_y = contour_to_lonlat(contour, lons, lats)
    curve, centerline_x, centerline_y = fit_polynomial_centerline(
        contour_x,
        contour_y,
        degree=degree,
        dense_points=dense_points,
        n_sections=n_sections,
    )
    normal_x, normal_y = estimate_unit_normals(
        curve,
        centerline_x,
        delta_x=delta_x,
    )
    offsets, sampled_dx, sampled_dy = build_normal_offsets(
        normal_x,
        normal_y,
        distance=distance,
        n_points=n_points,
    )
    return GeometryResult(
        offsets=offsets,
        sampled_dx=sampled_dx,
        sampled_dy=sampled_dy,
        contour_x=contour_x,
        contour_y=contour_y,
        centerline_x=centerline_x,
        centerline_y=centerline_y,
        normal_x=normal_x,
        normal_y=normal_y,
    )
