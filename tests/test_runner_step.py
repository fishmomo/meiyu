import unittest
from pathlib import Path


class RunnerStepTest(unittest.TestCase):
    def _run_manifest(self, overrides: dict[str, object] | None = None) -> dict[str, object]:
        from pipeline.runner import run_case_from_manifest

        return run_case_from_manifest(
            Path("manifests/cases/cra40_front2_20170622T18.yml"),
            overrides=overrides,
        )

    def test_run_case_from_manifest_returns_verified_summary(self) -> None:
        summary = self._run_manifest()

        self.assertEqual(summary["geometry"]["centerline_points"], 8)
        self.assertEqual(summary["geometry"]["section_shape"], [8, 9])
        self.assertEqual(summary["profiles"]["bundle_shape"], [8, 9, 37])
        self.assertEqual(summary["profiles"]["status"], "completed")
        self.assertEqual(summary["subareas"]["selected_points"], 48)
        self.assertEqual(summary["subareas"]["status"], "completed")
        self.assertEqual(summary["statistics"]["front_mean"], 85.81288001650856)
        self.assertEqual(summary["statistics"]["subarea_mean"], 87.94710636138916)
        self.assertEqual(summary["statistics"]["status"], "completed")

    def test_run_case_returns_summary_from_pipeline_config(self) -> None:
        from pipeline.config import load_case_config
        from pipeline.runner import run_case

        cfg = load_case_config(Path("pipeline/schemas/pipeline_config.yaml"))
        summary = run_case(cfg)

        self.assertEqual(summary["case_name"], "cra40_front2_2017-06-22T18")
        self.assertIn("geometry", summary)
        self.assertIn("profiles", summary)
        self.assertIn("subareas", summary)
        self.assertIn("statistics", summary)

        self.assertEqual(summary["geometry"]["centerline_points"], 8)
        self.assertEqual(summary["geometry"]["section_shape"], [8, 9])
        self.assertEqual(summary["profiles"]["variable"], "rh")
        self.assertEqual(summary["profiles"]["bundle_shape"], [8, 9, 37])
        self.assertEqual(summary["subareas"]["mask_shape"], [81, 141])
        self.assertEqual(summary["statistics"]["front_mean"], 85.81288001650856)
        self.assertEqual(summary["statistics"]["subarea_mean"], 87.94710636138916)

    def test_run_case_from_manifest_applies_geometry_override(self) -> None:
        summary = self._run_manifest(
            overrides={"params.geometry.n_sections": 6},
        )

        self.assertEqual(summary["geometry"]["section_shape"], [6, 9])
        self.assertEqual(summary["profiles"]["bundle_shape"], [6, 9, 37])

    def test_run_case_from_manifest_applies_subarea_section_override(self) -> None:
        summary = self._run_manifest(
            overrides={
                "params.subareas.start_section": 2,
                "params.subareas.end_section": 5,
            },
        )

        self.assertEqual(summary["subareas"]["status"], "completed")
        self.assertEqual(summary["subareas"]["start_section"], 2)
        self.assertEqual(summary["subareas"]["end_section"], 5)
        self.assertGreater(summary["subareas"]["selected_points"], 0)

    def test_run_case_from_manifest_skips_profiles_when_disabled(self) -> None:
        summary = self._run_manifest(overrides={"steps.profiles": False})

        self.assertEqual(summary["geometry"]["section_shape"], [8, 9])
        self.assertEqual(
            summary["profiles"],
            {"enabled": False, "status": "skipped"},
        )

    def test_run_case_from_manifest_returns_partial_statistics_without_subareas(
        self,
    ) -> None:
        summary = self._run_manifest(
            overrides={
                "steps.subareas": False,
                "steps.statistics": True,
            },
        )

        self.assertEqual(
            summary["subareas"],
            {"enabled": False, "status": "skipped"},
        )
        self.assertIs(summary["statistics"]["enabled"], True)
        self.assertEqual(summary["statistics"]["status"], "partial")
        self.assertIsNone(summary["statistics"]["subarea_mean"])
        self.assertEqual(summary["statistics"]["subarea_status"], "skipped")

    def test_run_case_from_manifest_skips_statistics_when_disabled(self) -> None:
        summary = self._run_manifest(overrides={"steps.statistics": False})

        self.assertEqual(
            summary["statistics"],
            {"enabled": False, "status": "skipped"},
        )

    def test_run_case_from_manifest_rejects_non_rh_even_when_steps_disabled(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "runner only supports the verified CRA40 front2 2017-06-22T18 rh pipeline in this version",
        ):
            self._run_manifest(
                overrides={
                    "params.profiles.variables": ["temp"],
                    "steps.profiles": False,
                    "steps.statistics": False,
                }
            )

    def test_run_case_rejects_unsupported_configuration(self) -> None:
        from pipeline.config import load_case_config
        from pipeline.runner import run_case

        for attr, value in (
            ("dataset", "not-cra40"),
            ("front_id", "front1"),
            ("target_time", "2017-06-23T00"),
        ):
            cfg = load_case_config(Path("pipeline/schemas/pipeline_config.yaml"))
            setattr(cfg, attr, value)

            with self.subTest(attr=attr, value=value):
                with self.assertRaisesRegex(
                    ValueError,
                    "runner only supports the verified CRA40 front2 2017-06-22T18 pipeline in this version",
                ):
                    run_case(cfg)


if __name__ == "__main__":
    unittest.main()
