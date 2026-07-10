import numpy as np

from pipeline.core.subarea_ops import select_points_between_sections
from pipeline.steps.geometry import GeometryResult


def build_subarea_filename(front_id: str, area_id: str, target_time: str) -> str:
    return f"{front_id}_subarea_{area_id}_{target_time}.nc"


def build_subarea_mask(
    mask_lon2d: np.ndarray,
    mask_lat2d: np.ndarray,
    mask_bool: np.ndarray,
    geometry: GeometryResult,
    start_section: int,
    end_section: int,
) -> np.ndarray:
    points_lonlat = np.column_stack(
        [
            mask_lon2d[mask_bool],
            mask_lat2d[mask_bool],
        ]
    )
    selected_points = select_points_between_sections(
        points_lonlat,
        geometry.centerline_x[start_section] + geometry.sampled_dx[start_section],
        geometry.centerline_y[start_section] + geometry.sampled_dy[start_section],
        geometry.centerline_x[end_section] + geometry.sampled_dx[end_section],
        geometry.centerline_y[end_section] + geometry.sampled_dy[end_section],
    )

    subarea_mask = np.zeros(mask_bool.shape, dtype=bool)
    for lon_value, lat_value in selected_points:
        point_mask = (mask_lon2d == lon_value) & (mask_lat2d == lat_value)
        subarea_mask[point_mask] = True
    return subarea_mask
