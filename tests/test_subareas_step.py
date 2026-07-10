import unittest

import numpy as np


class SubareaStepTest(unittest.TestCase):
    def test_subarea_filename_builder(self) -> None:
        from pipeline.steps.subareas import build_subarea_filename

        self.assertEqual(
            build_subarea_filename("front2", "area2", "2017-06-22T18"),
            "front2_subarea_area2_2017-06-22T18.nc",
        )

    def test_select_points_between_vertical_sections(self) -> None:
        from pipeline.core.subarea_ops import select_points_between_sections

        points = np.array(
            [
                [1.0, 0.0],
                [2.0, 0.0],
                [3.0, 0.0],
                [4.0, 0.0],
            ]
        )
        start_x = np.array([1.5, 1.5])
        start_y = np.array([-1.0, 1.0])
        end_x = np.array([3.5, 3.5])
        end_y = np.array([-1.0, 1.0])

        selected = select_points_between_sections(
            points,
            start_x,
            start_y,
            end_x,
            end_y,
        )

        np.testing.assert_array_equal(
            selected,
            np.array(
                [
                    [2.0, 0.0],
                    [3.0, 0.0],
                ]
            ),
        )

    def test_build_subarea_mask_from_geometry(self) -> None:
        from pipeline.steps.geometry import GeometryResult
        from pipeline.steps.subareas import build_subarea_mask

        lon2d, lat2d = np.meshgrid(
            np.array([1.0, 2.0, 3.0, 4.0]),
            np.array([0.0]),
        )
        mask_bool = np.array([[True, True, True, True]])
        geometry = GeometryResult(
            offsets=np.array([-1.0, 1.0]),
            sampled_dx=np.array(
                [
                    [0.0, 0.0],
                    [0.0, 0.0],
                    [0.0, 0.0],
                ]
            ),
            sampled_dy=np.array(
                [
                    [-1.0, 1.0],
                    [-1.0, 1.0],
                    [-1.0, 1.0],
                ]
            ),
            contour_x=np.array([], dtype=float),
            contour_y=np.array([], dtype=float),
            centerline_x=np.array([1.5, 2.5, 3.5]),
            centerline_y=np.array([0.0, 0.0, 0.0]),
            normal_x=np.array([0.0, 0.0, 0.0]),
            normal_y=np.array([1.0, 1.0, 1.0]),
        )

        subarea_mask = build_subarea_mask(
            lon2d,
            lat2d,
            mask_bool,
            geometry,
            start_section=0,
            end_section=2,
        )

        np.testing.assert_array_equal(
            subarea_mask,
            np.array([[False, True, True, False]]),
        )


if __name__ == "__main__":
    unittest.main()
