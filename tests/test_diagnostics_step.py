import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

from pipeline.steps.diagnostics import write_front_diagnostics
from pipeline.steps.diagnostics import write_geometry_diagnostics
from pipeline.steps.diagnostics import write_statistics_diagnostics
from pipeline.steps.geometry import GeometryResult
from pipeline.steps.profiles import ProfileBundle


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
