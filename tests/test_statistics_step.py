import unittest

import numpy as np


class StatisticsStepTest(unittest.TestCase):
    def test_grid_mean_ignores_nan(self) -> None:
        from pipeline.steps.statistics import grid_mean

        values = np.array([1.0, np.nan, 3.0])

        self.assertEqual(grid_mean(values), 2.0)

    def test_masked_grid_mean_uses_only_true_mask_points(self) -> None:
        from pipeline.core.stat_ops import masked_grid_mean

        field = np.array([[1.0, 2.0], [3.0, 4.0]])
        mask = np.array([[True, False], [True, False]])

        self.assertEqual(masked_grid_mean(field, mask), 2.0)

    def test_masked_grid_series_mean_returns_one_value_per_time(self) -> None:
        from pipeline.core.stat_ops import masked_grid_series_mean

        field_series = np.array(
            [
                [[1.0, 2.0], [3.0, 4.0]],
                [[2.0, 4.0], [6.0, 8.0]],
            ]
        )
        mask = np.array([[True, False], [True, False]])

        series = masked_grid_series_mean(field_series, mask)

        np.testing.assert_array_equal(series, np.array([2.0, 4.0]))

    def test_build_masked_mean_wraps_core_mean(self) -> None:
        from pipeline.steps.statistics import build_masked_mean

        field = np.array([[1.0, 2.0], [3.0, 4.0]])
        mask = np.array([[True, False], [True, False]])

        self.assertEqual(build_masked_mean("rh", field, mask), 2.0)

    def test_build_masked_series_wraps_core_series(self) -> None:
        from pipeline.steps.statistics import build_masked_series

        field_series = np.array(
            [
                [[1.0, 2.0], [3.0, 4.0]],
                [[2.0, 4.0], [6.0, 8.0]],
            ]
        )
        mask = np.array([[True, False], [True, False]])

        np.testing.assert_array_equal(
            build_masked_series("rh", field_series, mask),
            np.array([2.0, 4.0]),
        )


if __name__ == "__main__":
    unittest.main()
