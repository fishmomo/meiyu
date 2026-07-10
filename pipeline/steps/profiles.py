from dataclasses import dataclass

import numpy as np

from pipeline.core.section_ops import build_section_xy, sample_3d_field_along_sections, stack_profiles
from pipeline.steps.geometry import GeometryResult


@dataclass(slots=True)
class ProfileBundle:
    variable: str
    values: np.ndarray


def build_profile_bundle(variable: str, profiles: list[np.ndarray]) -> ProfileBundle:
    return ProfileBundle(variable=variable, values=stack_profiles(profiles))


def build_profile_bundle_from_field(
    variable: str,
    field: np.ndarray,
    levels: np.ndarray,
    lats: np.ndarray,
    lons: np.ndarray,
    geometry: GeometryResult,
) -> ProfileBundle:
    sample_x, sample_y = build_section_xy(geometry)
    sampled_profiles = sample_3d_field_along_sections(
        field,
        levels,
        lats,
        lons,
        sample_x,
        sample_y,
    )
    return ProfileBundle(variable=variable, values=sampled_profiles)
