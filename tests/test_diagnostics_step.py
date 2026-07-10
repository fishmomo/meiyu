import tempfile
import unittest
from pathlib import Path

import numpy as np

from pipeline.steps.diagnostics import write_front_diagnostics
from pipeline.steps.geometry import GeometryResult
from pipeline.steps.profiles import ProfileBundle


class DiagnosticsStepTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_path = Path(tempfile.mkdtemp())
        self.geometry = GeometryResult(
            offsets=np.linspace(-1, 1, 9),
            sampled_dx=np.zeros((8, 9)),
            sampled_dy=np.zeros((8, 9)),
            contour_x=np.array([1.0, 2.0]),
            contour_y=np.array([3.0, 4.0]),
            centerline_x=np.linspace(0, 1, 8),
            centerline_y=np.linspace(0, 1, 8),
            normal_x=np.ones(8),
            normal_y=np.zeros(8),
        )
        self.bundle = ProfileBundle(
            variable="rh",
            values=np.random.rand(8, 9, 37) * 100,
        )

    def tearDown(self) -> None:
        import shutil

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
