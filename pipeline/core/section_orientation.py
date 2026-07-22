from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pipeline.core.section_ops import build_section_xy
from pipeline.steps.geometry import GeometryResult


EARTH_RADIUS_KM = 6371.0088


@dataclass(frozen=True, slots=True)
class SectionOrientation:
    distances_km: np.ndarray
    flip: np.ndarray
    status: tuple[str, ...]


def _segment_distance_km(
    lon1: np.ndarray,
    lat1: np.ndarray,
    lon2: np.ndarray,
    lat2: np.ndarray,
) -> np.ndarray:
    lon1r, lat1r, lon2r, lat2r = map(
        np.radians,
        (lon1, lat1, lon2, lat2),
    )
    dlon = lon2r - lon1r
    dlat = lat2r - lat1r
    a = (
        np.sin(dlat / 2.0) ** 2
        + np.cos(lat1r) * np.cos(lat2r) * np.sin(dlon / 2.0) ** 2
    )
    return EARTH_RADIUS_KM * 2.0 * np.arctan2(
        np.sqrt(a),
        np.sqrt(np.maximum(0.0, 1.0 - a)),
    )


def _signed_section_distances_km(
    section_x: np.ndarray,
    section_y: np.ndarray,
) -> np.ndarray:
    segments = _segment_distance_km(
        section_x[:-1],
        section_y[:-1],
        section_x[1:],
        section_y[1:],
    )
    cumulative = np.concatenate(([0.0], np.cumsum(segments)))
    middle = len(cumulative) // 2
    if len(cumulative) % 2:
        origin = cumulative[middle]
    else:
        origin = (cumulative[middle - 1] + cumulative[middle]) / 2.0
    return cumulative - origin


def _finite_median(values: np.ndarray) -> float:
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return float("nan")
    return float(np.median(finite))


def build_section_orientation(
    geometry: GeometryResult,
    thetae_sections: np.ndarray,
    threshold_k: float = 0.5,
) -> SectionOrientation:
    thetae = np.asarray(thetae_sections, dtype=float)
    sample_x, sample_y = build_section_xy(geometry)
    if thetae.shape != sample_x.shape:
        raise ValueError(
            "thetae_sections shape must match geometry sampling shape: "
            f"{thetae.shape} != {sample_x.shape}"
        )
    if thetae.shape[1] < 4:
        raise ValueError("at least four cross-front samples are required")

    distances: list[np.ndarray] = []
    flip: list[bool] = []
    status: list[str] = []
    for section_x, section_y, section_thetae in zip(sample_x, sample_y, thetae):
        section_distance = _signed_section_distances_km(section_x, section_y)
        left = _finite_median(section_thetae[:2])
        right = _finite_median(section_thetae[-2:])
        contrast = right - left
        should_flip = bool(np.isfinite(contrast) and contrast <= -threshold_k)
        resolved = bool(np.isfinite(contrast) and abs(contrast) >= threshold_k)
        if should_flip:
            section_distance = -section_distance[::-1]
        distances.append(section_distance)
        flip.append(should_flip)
        status.append(
            "warm_side_positive" if resolved else "orientation_unresolved"
        )

    return SectionOrientation(
        distances_km=np.stack(distances),
        flip=np.asarray(flip, dtype=bool),
        status=tuple(status),
    )


def apply_section_orientation(
    values: np.ndarray,
    orientation: SectionOrientation,
) -> np.ndarray:
    oriented = np.asarray(values).copy()
    if oriented.ndim < 2:
        raise ValueError("section values must have section and point dimensions")
    if oriented.shape[:2] != orientation.distances_km.shape:
        raise ValueError(
            "section values shape must match orientation: "
            f"{oriented.shape[:2]} != {orientation.distances_km.shape}"
        )
    for index, should_flip in enumerate(orientation.flip):
        if should_flip:
            oriented[index] = oriented[index, ::-1, ...]
    return oriented
