import importlib.util

from project_paths import INTERIM_DIR, PROCESSED_DIR, RAW_DIR


def _directory_snapshot(path) -> dict[str, object]:
    if not path.exists():
        return {"exists": False, "children": []}
    return {
        "exists": True,
        "children": sorted(child.name for child in path.iterdir()),
    }


def build_inventory_report() -> dict[str, dict[str, object]]:
    return {
        "raw": _directory_snapshot(RAW_DIR),
        "interim": _directory_snapshot(INTERIM_DIR),
        "processed": _directory_snapshot(PROCESSED_DIR),
        "environment": {
            "xarray": importlib.util.find_spec("xarray") is not None,
            "cfgrib": importlib.util.find_spec("cfgrib") is not None,
            "cartopy": importlib.util.find_spec("cartopy") is not None,
            "matplotlib": importlib.util.find_spec("matplotlib") is not None,
        },
    }
