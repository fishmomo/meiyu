import numpy as np

from pipeline.core.section_orientation import (
    apply_section_orientation,
    build_section_orientation,
)
from pipeline.steps.geometry import GeometryResult


def make_geometry_with_east_west_sections() -> GeometryResult:
    offsets = np.linspace(-1.0, 1.0, 9)
    return GeometryResult(
        offsets=offsets,
        sampled_dx=np.tile(offsets, (2, 1)),
        sampled_dy=np.zeros((2, 9)),
        contour_x=np.array([], dtype=float),
        contour_y=np.array([], dtype=float),
        centerline_x=np.array([110.0, 112.0]),
        centerline_y=np.array([30.0, 31.0]),
        normal_x=np.ones(2),
        normal_y=np.zeros(2),
    )


def test_build_section_orientation_centres_distance_and_keeps_warm_side_positive():
    geometry = make_geometry_with_east_west_sections()
    thetae = np.tile(np.linspace(330.0, 338.0, 9), (2, 1))

    result = build_section_orientation(geometry, thetae)

    assert np.allclose(result.distances_km[:, 4], 0.0)
    assert np.all(np.diff(result.distances_km, axis=1) > 0)
    assert result.flip.tolist() == [False, False]
    assert result.status == ("warm_side_positive", "warm_side_positive")


def test_build_section_orientation_flips_warm_side_on_left():
    geometry = make_geometry_with_east_west_sections()
    thetae = np.tile(np.linspace(338.0, 330.0, 9), (2, 1))

    result = build_section_orientation(geometry, thetae)
    values = np.tile(np.arange(9.0), (2, 1))
    oriented = apply_section_orientation(values, result)

    assert result.flip.tolist() == [True, True]
    assert np.array_equal(oriented[0], values[0, ::-1])
    assert np.all(np.diff(result.distances_km, axis=1) > 0)


def test_build_section_orientation_marks_weak_contrast_unresolved():
    geometry = make_geometry_with_east_west_sections()
    thetae = np.full((2, 9), 334.0)

    result = build_section_orientation(geometry, thetae)

    assert result.status == ("orientation_unresolved", "orientation_unresolved")
    assert not result.flip.any()


def test_apply_section_orientation_flips_point_axis_for_3d_profiles():
    geometry = make_geometry_with_east_west_sections()
    thetae = np.tile(np.linspace(338.0, 330.0, 9), (2, 1))
    result = build_section_orientation(geometry, thetae)
    values = np.arange(2 * 9 * 3, dtype=float).reshape(2, 9, 3)

    oriented = apply_section_orientation(values, result)

    assert np.array_equal(oriented[0], values[0, ::-1, :])


def test_even_sample_count_places_zero_between_central_samples():
    offsets = np.linspace(-1.0, 1.0, 8)
    geometry = GeometryResult(
        offsets=offsets,
        sampled_dx=np.tile(offsets, (1, 1)),
        sampled_dy=np.zeros((1, 8)),
        contour_x=np.array([], dtype=float),
        contour_y=np.array([], dtype=float),
        centerline_x=np.array([110.0]),
        centerline_y=np.array([30.0]),
        normal_x=np.ones(1),
        normal_y=np.zeros(1),
    )
    thetae = np.linspace(330.0, 338.0, 8)[None, :]

    result = build_section_orientation(geometry, thetae)

    assert result.distances_km[0, 3] < 0.0
    assert result.distances_km[0, 4] > 0.0
    assert np.isclose(
        result.distances_km[0, 3] + result.distances_km[0, 4],
        0.0,
    )
