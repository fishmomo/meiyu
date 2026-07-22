import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

from pipeline.core.era5_dynamics import Era5DynamicsResult
from pipeline.steps import diagnostics as diagnostics_module
from pipeline.steps.diagnostics import write_front_diagnostics
from pipeline.steps.diagnostics import write_geometry_diagnostics
from pipeline.steps.diagnostics import write_cra40_research_diagnostics
from pipeline.steps.diagnostics import write_statistics_diagnostics
from pipeline.steps.geometry import GeometryResult
from pipeline.steps.profiles import ProfileBundle
from pipeline.steps.signed_section_diagnostics import (
    build_thetae_sections,
    write_signed_section_diagnostics,
)
from pipeline.steps.dynamics_diagnostics import (
    write_era5_dynamics_diagnostics,
)


class DiagnosticsStepTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_path = Path(tempfile.mkdtemp())
        self.geometry = GeometryResult(
            offsets=np.linspace(-1, 1, 9),
            sampled_dx=np.zeros((8, 9)),
            sampled_dy=np.zeros((8, 9)),
            contour_x=np.array([1.0, 2.0, 3.0]),
            contour_y=np.array([3.0, 4.0, 5.0]),
            centerline_x=np.linspace(0, 1, 8),
            centerline_y=np.linspace(0, 1, 8),
            normal_x=np.ones(8),
            normal_y=np.zeros(8),
        )
        self.bundle = ProfileBundle(
            variable="rh",
            values=np.random.rand(8, 9, 37) * 100,
        )
        self.mask_bool = np.ones((10, 10), dtype=bool)
        self.lons = np.linspace(100, 120, 10)
        self.lats = np.linspace(20, 40, 10)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_path, ignore_errors=True)

    def test_write_front_diagnostics_creates_png_files(self) -> None:
        outputs = write_front_diagnostics(
            case_name="demo_case",
            output_dir=self.tmp_path,
            geometry=self.geometry,
            profile_bundles={"rh": self.bundle},
            statistics={
                "variables": {"rh": {"front_mean": 80.0, "subarea_mean": 82.0}}
            },
        )
        self.assertGreaterEqual(len(outputs), 1)
        for output in outputs:
            self.assertTrue(Path(output).exists())
            self.assertTrue(str(output).endswith(".png"))

    def test_write_front_diagnostics_supports_multiple_variables(self) -> None:
        bundles = {
            "rh": ProfileBundle(variable="rh", values=np.random.rand(8, 9, 37) * 100),
            "temp": ProfileBundle(
                variable="temp", values=np.random.rand(8, 9, 37) * 30
            ),
        }
        outputs = write_front_diagnostics(
            case_name="multi_case",
            output_dir=self.tmp_path,
            geometry=self.geometry,
            profile_bundles=bundles,
            statistics={
                "variables": {
                    "rh": {"front_mean": 80.0, "subarea_mean": 82.0},
                    "temp": {"front_mean": 25.0, "subarea_mean": 26.0},
                }
            },
        )
        self.assertGreaterEqual(len(outputs), 1)
        for output in outputs:
            self.assertTrue(Path(output).exists())
            self.assertTrue(str(output).endswith(".png"))

    def test_write_geometry_diagnostics_creates_png_files(self) -> None:
        outputs = write_geometry_diagnostics(
            case_name="geo_case",
            output_dir=self.tmp_path,
            geometry=self.geometry,
            mask_bool=self.mask_bool,
            lons=self.lons,
            lats=self.lats,
        )
        self.assertGreaterEqual(len(outputs), 1)
        for output in outputs:
            self.assertTrue(Path(output).exists())
            self.assertTrue(str(output).endswith(".png"))

    def test_write_statistics_diagnostics_creates_png_files(self) -> None:
        outputs = write_statistics_diagnostics(
            case_name="stats_case",
            output_dir=self.tmp_path,
            statistics={
                "variables": {
                    "rh": {"front_mean": 85.0, "subarea_mean": 87.0},
                    "temp": {"front_mean": 295.0, "subarea_mean": 296.0},
                }
            },
        )
        self.assertGreaterEqual(len(outputs), 1)
        for output in outputs:
            self.assertTrue(Path(output).exists())
            self.assertTrue(str(output).endswith(".png"))

    def test_write_statistics_diagnostics_handles_partial_stats(self) -> None:
        outputs = write_statistics_diagnostics(
            case_name="partial_case",
            output_dir=self.tmp_path,
            statistics={
                "variables": {
                    "rh": {
                        "front_mean": 85.0,
                        "subarea_mean": None,
                        "subarea_status": "skipped",
                    }
                }
            },
        )
        self.assertGreaterEqual(len(outputs), 1)
        for output in outputs:
            self.assertTrue(Path(output).exists())

    def test_write_cra40_research_diagnostics_creates_research_pngs(self) -> None:
        levels = np.array([1000.0, 925.0, 850.0, 700.0])
        bundles = {
            "rh": ProfileBundle(
                variable="rh",
                values=np.full((8, 9, 4), 80.0),
                levels=levels,
            ),
            "temp": ProfileBundle(
                variable="temp",
                values=np.full((8, 9, 4), 295.0),
                levels=levels,
            ),
            "w": ProfileBundle(
                variable="w",
                values=np.full((8, 9, 4), 0.02),
                levels=levels,
            ),
        }
        lons = np.linspace(100.0, 120.0, 10)
        lats = np.linspace(20.0, 40.0, 10)
        field_cache = {
            "rh": (np.full((4, 10, 10), 80.0), levels),
            "temp": (np.full((4, 10, 10), 295.0), levels),
            "w": (np.full((4, 10, 10), 0.02), levels),
            "precip": (np.full((10, 10), 12.0), np.array([], dtype=float)),
        }
        submask = np.zeros((10, 10), dtype=bool)
        submask[2:5, 2:5] = True

        outputs = write_cra40_research_diagnostics(
            case_name="cra40_demo",
            output_dir=self.tmp_path,
            geometry=self.geometry,
            mask_bool=self.mask_bool,
            lons=lons,
            lats=lats,
            submask=submask,
            profile_bundles=bundles,
            field_cache=field_cache,
        )

        expected_names = {
            "cra40_demo_thetae_gradient_mask_overlay.png",
            "cra40_demo_precip_mask_overlay.png",
            "cra40_demo_subarea_overlay.png",
            "cra40_demo_sections_rh.png",
            "cra40_demo_sections_temp.png",
            "cra40_demo_sections_w.png",
            "cra40_demo_sections_rh_thetae.png",
            "cra40_demo_sections_w_thetae.png",
        }
        self.assertEqual({Path(output).name for output in outputs}, expected_names)
        for output in outputs:
            self.assertTrue(Path(output).exists())

    def test_horizontal_gradient_uses_physical_grid_spacing(self) -> None:
        coarse_lons = np.linspace(100.0, 104.0, 5)
        fine_lons = np.linspace(100.0, 104.0, 9)
        lats = np.linspace(28.0, 32.0, 5)
        coarse_field = np.broadcast_to(coarse_lons, (len(lats), len(coarse_lons)))
        fine_field = np.broadcast_to(fine_lons, (len(lats), len(fine_lons)))

        coarse_gradient = diagnostics_module._horizontal_gradient_magnitude(
            coarse_field,
            coarse_lons,
            lats,
        )
        fine_gradient = diagnostics_module._horizontal_gradient_magnitude(
            fine_field,
            fine_lons,
            lats,
        )

        self.assertAlmostEqual(
            float(np.nanmean(coarse_gradient)),
            float(np.nanmean(fine_gradient)),
            delta=5e-8,
        )

    def test_write_signed_section_diagnostics_creates_expected_products(self) -> None:
        levels = np.array([1000.0, 850.0, 700.0])
        point_gradient = np.linspace(0.0, 1.0, 9)[None, :, None]
        bundles = {
            "rh": ProfileBundle(
                variable="rh",
                values=np.broadcast_to(
                    70.0 + 20.0 * point_gradient,
                    (8, 9, 3),
                ).copy(),
                levels=levels,
            ),
            "temp": ProfileBundle(
                variable="temp",
                values=np.broadcast_to(
                    288.0 + 6.0 * point_gradient,
                    (8, 9, 3),
                ).copy(),
                levels=levels,
            ),
            "w": ProfileBundle(
                variable="w",
                values=np.broadcast_to(
                    -0.02 + 0.04 * point_gradient,
                    (8, 9, 3),
                ).copy(),
                levels=levels,
            ),
        }

        paths, metadata = write_signed_section_diagnostics(
            "demo",
            self.tmp_path,
            self.geometry,
            bundles,
        )

        self.assertEqual(
            {Path(path).name for path in paths},
            {
                "demo_sections_rh_signed_km.png",
                "demo_sections_temp_signed_km.png",
                "demo_sections_w_signed_km.png",
                "demo_sections_rh_thetae_signed_km.png",
                "demo_sections_w_thetae_signed_km.png",
            },
        )
        self.assertEqual(metadata["status"], "completed")
        self.assertEqual(metadata["distance_unit"], "km")
        for path in paths:
            self.assertTrue(Path(path).exists())

    def test_thetae_sections_reject_reordered_pressure_levels(self) -> None:
        rh = ProfileBundle(
            variable="rh",
            values=np.full((2, 4, 3), 80.0),
            levels=np.array([1000.0, 850.0, 700.0]),
        )
        temp = ProfileBundle(
            variable="temp",
            values=np.full((2, 4, 3), 290.0),
            levels=np.array([700.0, 850.0, 1000.0]),
        )

        with self.assertRaisesRegex(ValueError, "same order"):
            build_thetae_sections(rh, temp)

    def test_thetae_sections_reject_missing_pressure_level(self) -> None:
        rh = ProfileBundle(
            variable="rh",
            values=np.full((2, 4, 2), 80.0),
            levels=np.array([1000.0, 850.0]),
        )
        temp = ProfileBundle(
            variable="temp",
            values=np.full((2, 4, 3), 290.0),
            levels=np.array([1000.0, 850.0, 700.0]),
        )

        with self.assertRaisesRegex(ValueError, "pressure levels must match"):
            build_thetae_sections(rh, temp)

    def test_write_era5_dynamics_diagnostics_creates_expected_products(self) -> None:
        lon2d, lat2d = np.meshgrid(self.lons, self.lats)
        result = Era5DynamicsResult(
            lons=self.lons,
            lats=self.lats,
            thetae=335.0 + 0.1 * lon2d,
            thetae_gradient=np.full(lon2d.shape, 1.5e-4),
            divergence=(lon2d - lon2d.mean()) * 1e-6,
            moisture_flux_convergence=(lat2d - lat2d.mean()) * 1e-6,
            frontogenesis=(lon2d - lon2d.mean()) * 1e-10,
            u=np.full(lon2d.shape, 10.0),
            v=np.full(lon2d.shape, 2.0),
        )

        paths = write_era5_dynamics_diagnostics(
            case_name="era5_demo",
            target_time="2017-06-28T18",
            level_hpa=850.0,
            output_dir=self.tmp_path,
            mask_bool=self.mask_bool,
            result=result,
        )

        self.assertEqual(
            {Path(path).name for path in paths},
            {
                "era5_demo_850_thetae_gradient_wind.png",
                "era5_demo_850_divergence.png",
                "era5_demo_850_moisture_flux_convergence.png",
                "era5_demo_850_frontogenesis.png",
            },
        )
        for path in paths:
            self.assertTrue(Path(path).exists())
