import unittest
from glob import glob
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


class PipelinePathsTest(unittest.TestCase):
    def test_case_output_dirs_are_created(self) -> None:
        from pipeline.core import paths as pipeline_paths

        with TemporaryDirectory() as tmpdir:
            with patch.object(pipeline_paths, "OUTPUT_DIR", Path(tmpdir)):
                paths = pipeline_paths.ensure_case_dirs("unit_case")
                self.assertTrue(paths["root"].exists())
                self.assertTrue(paths["profiles"].exists())
                self.assertTrue(paths["statistics"].exists())

    def test_cra40_file_finds_unique_dated_file_when_root_file_is_absent(self) -> None:
        import project_paths

        with TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir)
            target = (
                raw_dir
                / "2017"
                / "20170622"
                / "CRA40_RHU_2017062218_GLB_0P25_HOUR_V1_0_0.grib2"
            )
            target.parent.mkdir(parents=True)
            target.touch()

            with patch.object(project_paths, "RAW_CRA40_DIR", raw_dir):
                resolved = project_paths.cra40_file(target.name)

        self.assertEqual(resolved, str(target))

    def test_cra40_file_rejects_multiple_dated_matches(self) -> None:
        import project_paths

        with TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir)
            filename = "CRA40_RHU_2017062218_GLB_0P25_HOUR_V1_0_0.grib2"
            for folder in (
                raw_dir / "2017" / "20170622",
                raw_dir / "backup" / "20170622",
            ):
                folder.mkdir(parents=True)
                (folder / filename).touch()

            with patch.object(project_paths, "RAW_CRA40_DIR", raw_dir):
                with self.assertRaisesRegex(RuntimeError, "multiple CRA40 files"):
                    project_paths.cra40_file(filename)

    def test_cra40_glob_includes_dated_subdirectories(self) -> None:
        import project_paths

        with TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir)
            dated_dir = raw_dir / "2017" / "20170622"
            dated_dir.mkdir(parents=True)
            target = dated_dir / "CRA40_2017062218.nc"
            target.touch()

            with patch.object(project_paths, "RAW_CRA40_DIR", raw_dir):
                pattern = project_paths.cra40_glob("CRA40*.nc")
                matches = glob(pattern, recursive=True)

            self.assertIn("**", pattern)
            self.assertEqual(matches, [str(target)])


if __name__ == "__main__":
    unittest.main()
