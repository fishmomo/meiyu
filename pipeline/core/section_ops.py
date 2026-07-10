import numpy as np
from scipy.interpolate import RegularGridInterpolator

from pipeline.steps.geometry import GeometryResult


def build_section_xy(geometry: GeometryResult) -> tuple[np.ndarray, np.ndarray]:
    centerline_x = np.asarray(geometry.centerline_x, dtype=float)[:, None]
    centerline_y = np.asarray(geometry.centerline_y, dtype=float)[:, None]
    return centerline_x + geometry.sampled_dx, centerline_y + geometry.sampled_dy


def sample_3d_field_along_sections(
    field: np.ndarray,
    levels: np.ndarray,
    lats: np.ndarray,
    lons: np.ndarray,
    sample_x: np.ndarray,
    sample_y: np.ndarray,
) -> np.ndarray:
    interpolator = RegularGridInterpolator(
        (levels, lats, lons),
        field,
        bounds_error=False,
        fill_value=np.nan,
    )

    profiles: list[np.ndarray] = []
    n_levels = len(levels)
    for section_x, section_y in zip(sample_x, sample_y):
        section_points = np.column_stack(
            [
                np.repeat(section_x, n_levels),
                np.repeat(section_y, n_levels),
                np.tile(levels, len(section_x)),
            ]
        )
        sampled = interpolator(section_points[:, ::-1])
        profiles.append(sampled.reshape(len(section_x), n_levels))

    return np.stack(profiles, axis=0)


def stack_profiles(profiles: list[np.ndarray]) -> np.ndarray:
    return np.stack(profiles, axis=0)
