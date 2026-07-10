import unittest
from pathlib import Path
from unittest.mock import patch


class MaskStepTest(unittest.TestCase):
    def test_resolve_existing_cra40_front1_assets(self) -> None:
        from pipeline.steps.masks import resolve_case_masks

        assets = resolve_case_masks("front1", "2017-06-22T18")
        self.assertIn("front_mask", assets)
        self.assertIn("extend_mask", assets)
        self.assertTrue(assets["front_mask"].endswith("front1\\2017-06-22T18.nc"))
        self.assertTrue(assets["extend_mask"].endswith("front1\\extend\\2017-06-22T18.nc"))
        self.assertTrue(Path(assets["front_mask"]).exists())
        self.assertTrue(Path(assets["extend_mask"]).exists())

    def test_resolve_existing_cra40_front2_assets(self) -> None:
        from pipeline.steps.masks import resolve_case_masks

        assets = resolve_case_masks("front2", "2017-06-22T18")
        self.assertIn("front_mask", assets)
        self.assertIn("extend_mask", assets)
        self.assertIn("subarea_mask", assets)
        self.assertTrue(assets["front_mask"].endswith("front2\\2017-06-22T18.nc"))
        self.assertTrue(assets["extend_mask"].endswith("front2_extend\\2017-06-22T18.nc"))
        self.assertTrue(
            assets["subarea_mask"].endswith("front2_subareas\\area2_lonlat_0622T18.nc")
        )
        self.assertTrue(Path(assets["front_mask"]).exists())
        self.assertTrue(Path(assets["extend_mask"]).exists())
        self.assertTrue(Path(assets["subarea_mask"]).exists())

    def test_front1_mask_assets_raise_when_mask_is_missing(self) -> None:
        from pipeline.steps.masks import resolve_case_masks

        missing_path = "H:\\fake\\front1_missing.nc"

        def fake_exists(self: Path) -> bool:
            return str(self) != missing_path

        with patch("pipeline.core.mask_ops.cra40_front_mask", return_value=missing_path):
            with patch("pathlib.Path.exists", autospec=True, side_effect=fake_exists):
                with self.assertRaises(FileNotFoundError) as ctx:
                    resolve_case_masks("front1", "2017-06-22T18")

        self.assertEqual(str(ctx.exception), missing_path)


if __name__ == "__main__":
    unittest.main()
