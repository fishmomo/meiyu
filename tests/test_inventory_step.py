import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


class InventoryStepTest(unittest.TestCase):
    def test_directory_snapshot_returns_missing_shape_for_absent_directory(self) -> None:
        from pipeline.steps.inventory import _directory_snapshot

        with TemporaryDirectory() as tmpdir:
            missing = Path(tmpdir) / "missing"

            snapshot = _directory_snapshot(missing)

        self.assertEqual(snapshot, {"exists": False, "children": []})

    def test_directory_snapshot_returns_sorted_children_for_existing_directory(self) -> None:
        from pipeline.steps.inventory import _directory_snapshot

        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "zeta.txt").write_text("z", encoding="utf-8")
            (root / "alpha.txt").write_text("a", encoding="utf-8")

            snapshot = _directory_snapshot(root)

        self.assertEqual(
            snapshot,
            {"exists": True, "children": ["alpha.txt", "zeta.txt"]},
        )

    def test_inventory_report_contains_expected_shapes_and_environment_keys(self) -> None:
        from pipeline.steps import inventory

        with TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            raw_dir = base / "raw"
            interim_dir = base / "interim"
            processed_dir = base / "processed"
            raw_dir.mkdir()
            interim_dir.mkdir()
            processed_dir.mkdir()
            (raw_dir / "cra40").mkdir()
            (interim_dir / "manual_masks").mkdir()
            (processed_dir / "mask_statistics").mkdir()

            with patch.object(inventory, "RAW_DIR", raw_dir), patch.object(
                inventory, "INTERIM_DIR", interim_dir
            ), patch.object(inventory, "PROCESSED_DIR", processed_dir):
                report = inventory.build_inventory_report()

        self.assertEqual(set(report.keys()), {"raw", "interim", "processed", "environment"})
        self.assertEqual(
            report["raw"],
            {"exists": True, "children": ["cra40"]},
        )
        self.assertEqual(
            report["interim"],
            {"exists": True, "children": ["manual_masks"]},
        )
        self.assertEqual(
            report["processed"],
            {"exists": True, "children": ["mask_statistics"]},
        )
        self.assertEqual(
            set(report["environment"].keys()),
            {"xarray", "cfgrib", "cartopy", "matplotlib"},
        )
        for value in report["environment"].values():
            self.assertIsInstance(value, bool)

    def test_write_json_manifest_creates_parent_and_round_trips_utf8_json(self) -> None:
        from pipeline.io.manifest import write_json_manifest

        payload = {
            "label": "梅雨锋面",
            "paths": ["raw", "processed"],
            "count": 2,
        }

        with TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "nested" / "inventory.json"

            write_json_manifest(manifest_path, payload)

            self.assertTrue(manifest_path.parent.exists())
            raw_text = manifest_path.read_text(encoding="utf-8")
            self.assertIn("梅雨锋面", raw_text)
            self.assertEqual(json.loads(raw_text), payload)


if __name__ == "__main__":
    unittest.main()
