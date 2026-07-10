import unittest

import numpy as np


class GeometryStepTest(unittest.TestCase):
    def test_extract_largest_contour_rejects_empty_mask(self) -> None:
        from pipeline.core.front_ops import extract_largest_contour

        with self.assertRaisesRegex(ValueError, "No contour found"):
            extract_largest_contour(np.zeros((5, 5), dtype=bool))

    def test_build_sampling_offsets_shape(self) -> None:
        from pipeline.core.front_ops import build_normal_offsets

        nx = np.array([1.0, 0.0])
        ny = np.array([0.0, 1.0])
        offsets, sampled_dx, sampled_dy = build_normal_offsets(
            nx,
            ny,
            distance=1.0,
            n_points=5,
        )
        np.testing.assert_array_equal(
            offsets,
            np.array([-1.0, -0.5, 0.0, 0.5, 1.0]),
        )
        self.assertEqual(sampled_dx.shape, (2, 5))
        self.assertEqual(sampled_dy.shape, (2, 5))

    def test_build_sampling_offsets_rejects_mismatched_shapes(self) -> None:
        from pipeline.core.front_ops import build_normal_offsets

        nx = np.array([1.0, 0.0])
        ny = np.array([0.0])

        with self.assertRaisesRegex(
            ValueError,
            "nx and ny must have the same shape",
        ):
            build_normal_offsets(nx, ny, distance=1.0, n_points=5)

    def test_fit_centerline_and_normals_from_synthetic_points(self) -> None:
        from pipeline.core.front_ops import (
            estimate_unit_normals,
            fit_polynomial_centerline,
        )

        x = np.linspace(100.0, 110.0, 20)
        y = 0.1 * (x - 105.0) ** 2 + 25.0

        curve, x_sample, y_sample = fit_polynomial_centerline(
            x,
            y,
            degree=2,
            dense_points=200,
            n_sections=6,
        )
        nx, ny = estimate_unit_normals(curve, x_sample, delta_x=0.1)

        self.assertEqual(x_sample.shape, (6,))
        self.assertEqual(y_sample.shape, (6,))
        np.testing.assert_allclose(np.sqrt(nx**2 + ny**2), np.ones(6), atol=1e-6)

    def test_fit_centerline_accepts_repeated_x_values(self) -> None:
        from pipeline.core.front_ops import fit_polynomial_centerline

        x = np.array([100.0, 100.0, 101.0, 101.0, 102.0, 102.0])
        y = np.array([30.0, 30.5, 31.0, 31.5, 33.0, 33.5])

        _, x_sample, y_sample = fit_polynomial_centerline(
            x,
            y,
            degree=2,
            dense_points=100,
            n_sections=4,
        )

        self.assertEqual(x_sample.shape, (4,))
        self.assertEqual(y_sample.shape, (4,))

    def test_build_geometry_frame_includes_offsets_axis(self) -> None:
        from pipeline.steps.geometry import build_geometry_frame

        nx = np.array([1.0, 0.0])
        ny = np.array([0.0, 1.0])

        result = build_geometry_frame(nx, ny, distance=2.0, n_points=5)

        np.testing.assert_array_equal(
            result.offsets,
            np.array([-2.0, -1.0, 0.0, 1.0, 2.0]),
        )
        self.assertEqual(result.sampled_dx.shape, (2, 5))
        self.assertEqual(result.sampled_dy.shape, (2, 5))

    def test_build_geometry_from_mask_returns_sampling_frame(self) -> None:
        from pipeline.steps.geometry import build_geometry_from_mask

        mask = np.zeros((20, 20), dtype=bool)
        for idx in range(4, 16):
            mask[idx, max(idx - 1, 0):min(idx + 2, 20)] = True

        lons = np.linspace(100.0, 110.0, 20)
        lats = np.linspace(30.0, 20.0, 20)

        result = build_geometry_from_mask(
            mask,
            lons,
            lats,
            degree=2,
            dense_points=200,
            n_sections=6,
            distance=1.5,
            n_points=7,
            delta_x=0.1,
        )

        self.assertEqual(result.centerline_x.shape, (6,))
        self.assertEqual(result.centerline_y.shape, (6,))
        self.assertEqual(result.sampled_dx.shape, (6, 7))
        self.assertEqual(result.sampled_dy.shape, (6, 7))
        self.assertGreater(result.contour_x.size, 0)


if __name__ == "__main__":
    unittest.main()
