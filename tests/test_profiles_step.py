import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_read_cra40_profile_cube_uses_mapped_field_and_level(self) -> None:
        from pipeline.core.cra40_fields import read_cra40_profile_cube

        lats = np.array([30.0, 31.0])
        lons = np.array([100.0, 101.0])
        levels = np.arange(40, dtype=float)
        field = np.arange(40 * 2 * 2, dtype=float).reshape(40, 2, 2)

        class FakeArray:
            def __init__(self, values, recorder=None):
                self.values = values
                self.recorder = recorder if recorder is not None else self

            def isel(self, indexers):
                (_, selector), = indexers.items()
                return FakeArray(self.values[selector], recorder=self.recorder)

            def sel(self, **kwargs):
                self.recorder.last_sel = kwargs
                return self

        class FakeDataset:
            def __init__(self):
                self.arrays = {
                    "t": FakeArray(field),
                    "isobaricInhPa": FakeArray(levels),
                }

            def __getitem__(self, key):
                return self.arrays[key]

        fake_ds = FakeDataset()

        with patch(
            "pipeline.core.cra40_fields.open_dataset_compat",
            return_value=fake_ds,
        ):
            cube, resolved_levels = read_cra40_profile_cube(
                "temp",
                Path("dummy.grib2"),
                lats,
                lons,
            )

        np.testing.assert_array_equal(cube, field[:37])
        np.testing.assert_array_equal(resolved_levels, levels[:37])
        self.assertEqual(
            fake_ds.arrays["t"].last_sel,
            {"latitude": lats, "longitude": lons, "method": "nearest"},
        )


    def test_read_era5_profile_cube_uses_mapped_field_and_selects_time(self) -> None:
        from pipeline.core.era5_fields import read_era5_profile_cube

        lats = np.array([30.0, 31.0])
        lons = np.array([100.0, 101.0])
        levels = np.array([1000.0, 900.0, 800.0])
        field = np.arange(3 * 2 * 2, dtype=float).reshape(3, 2, 2)

        class FakeArray:
            def __init__(self, values, recorder=None):
                self.values = values
                self.recorder = recorder if recorder is not None else self

            def sel(self, *args, **kwargs):
                if args:
                    kwargs.update(args[0] if isinstance(args[0], dict) else {})
                if "valid_time" in kwargs:
                    self.recorder.time_sel = kwargs
                else:
                    self.recorder.space_sel = kwargs
                return self

        class FakeDataset:
            def __init__(self):
                recorder = self
                self.arrays = {
                    "t": FakeArray(field, recorder=recorder),
                    "pressure_level": FakeArray(levels, recorder=recorder),
                }
                self.time_sel = None
                self.space_sel = None

            def __getitem__(self, key):
                return self.arrays[key]

        fake_ds = FakeDataset()

        with patch(
            "pipeline.core.era5_fields.open_dataset_compat",
            return_value=fake_ds,
        ):
            cube, resolved_levels = read_era5_profile_cube(
                "temp",
                Path("dummy.nc"),
                "2017-06-22T18",
                lats,
                lons,
            )

        self.assertEqual(cube.shape, field.shape)
        np.testing.assert_array_equal(resolved_levels, levels)
        self.assertIn("valid_time", fake_ds.time_sel)
        self.assertEqual(
            fake_ds.space_sel,
            {"latitude": lats, "longitude": lons, "method": "nearest"},
        )


if __name__ == "__main__":
    unittest.main()
