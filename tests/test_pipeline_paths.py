import unittest
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


if __name__ == "__main__":
    unittest.main()
