import unittest
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch


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
        self.assertEqual(
            summary["profiles"]["variables"]["rh"]["bundle_shape"],
            [8, 9, 37],
        )
        self.assertEqual(summary["profiles"]["status"], "completed")
        self.assertEqual(summary["subareas"]["selected_points"], 48)
        self.assertEqual(summary["subareas"]["status"], "completed")
        self.assertEqual(
            summary["statistics"]["variables"]["rh"]["front_mean"],
            85.81288001650856,
        )
        self.assertIn("subarea_mean", summary["statistics"]["variables"]["rh"])
        self.assertEqual(summary["statistics"]["status"], "completed")
        self.assertEqual(summary["diagnostics"]["status"], "completed")
        self.assertGreaterEqual(len(summary["diagnostics"]["files"]), 1)
        for fpath in summary["diagnostics"]["files"]:
            self.assertTrue(str(fpath).endswith(".png"))

    def test_run_case_from_front1_manifest_returns_multivariable_summary(self) -> None:
        from pipeline.runner import run_case_from_manifest

        summary = run_case_from_manifest(
            Path("manifests/cases/cra40_front1_20170622T18.yml")
        )

        self.assertEqual(summary["case_name"], "cra40_front1_20170622T18")
        self.assertEqual(summary["geometry"]["section_shape"], [8, 9])
        self.assertEqual(
            set(summary["profiles"]["variables"].keys()),
            {"rh", "temp", "w"},
        )
        for variable in ("rh", "temp", "w"):
            self.assertIn("subarea_mean", summary["statistics"]["variables"][variable])
        self.assertEqual(summary["statistics"]["status"], "completed")
        self.assertEqual(summary["diagnostics"]["status"], "completed")
        self.assertGreaterEqual(len(summary["diagnostics"]["files"]), 1)

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
        self.assertEqual(set(summary["profiles"]["variables"].keys()), {"rh"})
        self.assertEqual(
            summary["profiles"]["variables"]["rh"]["bundle_shape"],
            [8, 9, 37],
        )
        self.assertEqual(summary["subareas"]["mask_shape"], [81, 141])
        self.assertEqual(
            summary["statistics"]["variables"]["rh"]["front_mean"],
            85.81288001650856,
        )
        self.assertIn("subarea_mean", summary["statistics"]["variables"]["rh"])

    def test_run_case_from_manifest_applies_geometry_override(self) -> None:
        summary = self._run_manifest(
            overrides={"params.geometry.n_sections": 6},
        )

        self.assertEqual(summary["geometry"]["section_shape"], [6, 9])
        self.assertEqual(
            summary["profiles"]["variables"]["rh"]["bundle_shape"],
            [6, 9, 37],
        )

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
        self.assertIsNone(summary["statistics"]["variables"]["rh"]["subarea_mean"])
        self.assertEqual(
            summary["statistics"]["variables"]["rh"]["subarea_status"],
            "skipped",
        )

    def test_run_case_from_manifest_skips_statistics_when_disabled(self) -> None:
        summary = self._run_manifest(overrides={"steps.statistics": False})

        self.assertEqual(
            summary["statistics"],
            {"enabled": False, "status": "skipped"},
        )

    def test_run_case_from_manifest_rejects_non_rh_even_when_steps_disabled(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "front2 requires at least 'rh' profile variable",
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

        cfg = load_case_config(Path("pipeline/schemas/pipeline_config.yaml"))

        with self.subTest("unsupported_dataset"):
            bad_cfg = load_case_config(Path("pipeline/schemas/pipeline_config.yaml"))
            bad_cfg.dataset = "not-cra40"
            with self.assertRaisesRegex(
                ValueError,
                "runner only supports CRA40 dataset",
            ):
                run_case(bad_cfg)

        with self.subTest("unsupported_front_id"):
            bad_cfg = load_case_config(Path("pipeline/schemas/pipeline_config.yaml"))
            bad_cfg.front_id = "front3"
            with self.assertRaisesRegex(
                ValueError,
                "runner only supports front1/front2",
            ):
                run_case(bad_cfg)

        with self.subTest("missing_mask_assets"):
            bad_cfg = load_case_config(Path("pipeline/schemas/pipeline_config.yaml"))
            bad_cfg.target_time = "2017-06-29T00"
            with self.assertRaisesRegex(
                ValueError,
                "no mask assets found",
            ):
                run_case(bad_cfg)

    def test_runner_main_returns_zero_and_prints_json_for_manifest(self) -> None:
        from contextlib import redirect_stderr, redirect_stdout
        from io import StringIO

        import pipeline.runner as runner

        fake_summary = {
            "case_name": "验证用例",
            "statistics": {"status": "completed"},
        }
        stdout = StringIO()
        stderr = StringIO()
        with patch.object(runner, "run_case_from_manifest", return_value=fake_summary):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = runner.main(
                    [
                        "--manifest",
                        "manifests/cases/cra40_front2_20170622T18.yml",
                    ]
                )

        self.assertEqual(code, 0)
        self.assertEqual(stderr.getvalue(), "")
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["case_name"], "验证用例")
        self.assertEqual(payload["statistics"]["status"], "completed")
        self.assertNotIn("\\u9a8c\\u8bc1", stdout.getvalue())

    def test_runner_main_applies_cli_overrides(self) -> None:
        from contextlib import redirect_stderr, redirect_stdout
        from io import StringIO

        import pipeline.runner as runner

        stdout = StringIO()
        stderr = StringIO()
        with patch.object(runner, "run_case_from_manifest", return_value={"case_name": "验证用例"} ) as mocked:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = runner.main(
                    [
                        "--manifest",
                        "manifests/cases/cra40_front2_20170622T18.yml",
                        "--override",
                        "steps.subareas=false",
                        "--override",
                        "steps.statistics=true",
                        "--override",
                        "params.geometry.n_sections=6",
                        "--override",
                        "params.geometry.scale=1.5",
                        "--override",
                        "params.profiles.variables=rh",
                    ]
                )

        self.assertEqual(code, 0)
        self.assertEqual(stderr.getvalue(), "")
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["case_name"], "验证用例")
        mocked.assert_called_once()
        _, kwargs = mocked.call_args
        self.assertEqual(
            kwargs["overrides"],
            {
                "steps.subareas": False,
                "steps.statistics": True,
                "params.geometry.n_sections": 6,
                "params.geometry.scale": 1.5,
                "params.profiles.variables": "rh",
            },
        )

    def test_runner_main_returns_one_for_bad_override_pair(self) -> None:
        from contextlib import redirect_stderr, redirect_stdout
        from io import StringIO

        import pipeline.runner as runner

        stdout = StringIO()
        stderr = StringIO()
        with patch.object(runner, "run_case_from_manifest") as mocked:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = runner.main(
                    [
                        "--manifest",
                        "manifests/cases/cra40_front2_20170622T18.yml",
                        "--override",
                        "badpair",
                    ]
                )

        self.assertEqual(code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("ERROR:", stderr.getvalue())

    def test_runner_main_returns_one_for_missing_manifest(self) -> None:
        from contextlib import redirect_stderr, redirect_stdout
        from io import StringIO

        import pipeline.runner as runner

        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = runner.main([])

        self.assertEqual(code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("ERROR:", stderr.getvalue())

    def test_runner_main_returns_one_for_unsupported_cli_case(self) -> None:
        from contextlib import redirect_stderr, redirect_stdout
        from io import StringIO

        import pipeline.runner as runner

        stdout = StringIO()
        stderr = StringIO()
        with patch.object(
            runner,
            "run_case_from_manifest",
            side_effect=ValueError(
                "runner only supports the verified CRA40 front2 rh pipeline and CRA40 front1 rh/temp/w profile variables in this version"
            ),
        ):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = runner.main(
                    [
                        "--manifest",
                        "manifests/cases/cra40_front2_20170622T18.yml",
                        "--override",
                        "params.profiles.variables=temp",
                    ]
                )

        self.assertEqual(code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("ERROR:", stderr.getvalue())
        self.assertIn("verified CRA40 front2 rh pipeline", stderr.getvalue())

    def test_runner_module_entrypoint_executes_manifest(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pipeline.runner",
                "--manifest",
                "manifests/cases/cra40_front2_20170622T18.yml",
            ],
            capture_output=True,
            text=True,
            cwd=Path("."),
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stderr, "")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["case_name"], "cra40_front2_20170622T18")
        self.assertEqual(payload["statistics"]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
