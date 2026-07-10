import unittest

import numpy as np


class ProfilesStepTest(unittest.TestCase):
    def test_build_section_xy_adds_centerline_and_offsets(self) -> None:
        from pipeline.core.section_ops import build_section_xy
        from pipeline.steps.geometry import GeometryResult

        geometry = GeometryResult(
            offsets=np.array([-1.0, 1.0]),
            sampled_dx=np.array([[0.0, 1.0], [0.0, 1.0]]),
            sampled_dy=np.array([[0.0, 0.0], [0.0, 0.0]]),
            contour_x=np.array([], dtype=float),
            contour_y=np.array([], dtype=float),
            centerline_x=np.array([100.0, 101.0]),
            centerline_y=np.array([30.0, 31.0]),
            normal_x=np.array([1.0, 1.0]),
            normal_y=np.array([0.0, 0.0]),
        )

        sample_x, sample_y = build_section_xy(geometry)

        np.testing.assert_array_equal(
            sample_x,
            np.array([[100.0, 101.0], [101.0, 102.0]]),
        )
        np.testing.assert_array_equal(
            sample_y,
            np.array([[30.0, 30.0], [31.0, 31.0]]),
        )

    def test_sample_3d_field_along_sections_returns_expected_shape(self) -> None:
        from pipeline.core.section_ops import sample_3d_field_along_sections

        levels = np.array([900.0, 1000.0])
        lats = np.array([30.0, 31.0])
        lons = np.array([100.0, 101.0, 102.0])
        field = np.arange(2 * 2 * 3, dtype=float).reshape(2, 2, 3)
        sample_x = np.array([[100.0, 101.0], [101.0, 102.0]])
        sample_y = np.array([[30.0, 30.0], [31.0, 31.0]])

        profiles = sample_3d_field_along_sections(
            field,
            levels,
            lats,
            lons,
            sample_x,
            sample_y,
        )

        self.assertEqual(profiles.shape, (2, 2, 2))
        self.assertEqual(profiles[0, 0, 0], field[0, 0, 0])

    def test_build_profile_bundle_keeps_variable_and_stacks_values(self) -> None:
        from pipeline.steps.profiles import build_profile_bundle

        arr1 = np.ones((5, 4))
        arr2 = np.zeros((5, 4))

        bundle = build_profile_bundle("thetae", [arr1, arr2])

        self.assertEqual(bundle.variable, "thetae")
        self.assertEqual(bundle.values.shape, (2, 5, 4))

    def test_build_profile_bundle_from_field_keeps_variable_and_shape(self) -> None:
        from pipeline.steps.geometry import GeometryResult
        from pipeline.steps.profiles import build_profile_bundle_from_field

        geometry = GeometryResult(
            offsets=np.array([-1.0, 1.0]),
            sampled_dx=np.array([[0.0, 1.0], [0.0, 1.0]]),
            sampled_dy=np.array([[0.0, 0.0], [0.0, 0.0]]),
            contour_x=np.array([], dtype=float),
            contour_y=np.array([], dtype=float),
            centerline_x=np.array([100.0, 101.0]),
            centerline_y=np.array([30.0, 31.0]),
            normal_x=np.array([1.0, 1.0]),
            normal_y=np.array([0.0, 0.0]),
        )
        levels = np.array([1000.0, 900.0])
        lats = np.array([31.0, 30.0])
        lons = np.array([100.0, 101.0, 102.0])
        field = np.arange(2 * 2 * 3, dtype=float).reshape(2, 2, 3)

        bundle = build_profile_bundle_from_field(
            "rh",
            field,
            levels,
            lats,
            lons,
            geometry,
        )

        self.assertEqual(bundle.variable, "rh")
        self.assertEqual(bundle.values.shape, (2, 2, 2))

    def test_stack_section_profiles_shape(self) -> None:
        from pipeline.core.section_ops import stack_profiles

        arr1 = np.ones((5, 4))
        arr2 = np.zeros((5, 4))

        stacked = stack_profiles([arr1, arr2])

        self.assertEqual(stacked.shape, (2, 5, 4))


if __name__ == "__main__":
    unittest.main()
