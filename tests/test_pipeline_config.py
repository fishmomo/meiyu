import unittest
from pathlib import Path


class PipelineConfigLoadTest(unittest.TestCase):
    def test_load_case_config(self) -> None:
        from pipeline.config import load_case_config

        cfg = load_case_config(Path("pipeline/schemas/pipeline_config.yaml"))
        self.assertEqual(cfg.case_name, "cra40_front2_2017-06-22T18")
        self.assertEqual(cfg.dataset, "cra40")
        self.assertEqual(cfg.front_id, "front2")


if __name__ == "__main__":
    unittest.main()
