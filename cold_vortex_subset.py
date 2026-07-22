"""Create compact, reusable CRA40 subsets for cold-vortex research."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import xarray as xr


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw" / "cra40"
CACHE_ROOT = ROOT / "data" / "interim" / "cold_vortex_cra40_subset"
DOMAIN = {"latitude": slice(70.0, 20.0), "longitude": slice(90.0, 170.0)}
FIELD_NAMES = {"GPH": "gh", "WIU": "u", "WIV": "v", "VVP": "w", "RHU": "r", "SHU": "q", "TEM": "t"}


def subset_cache_path(root: Path, event: str, time_utc: str) -> Path:
    return root / event / f"{time_utc}_domain_90E_170E_20N_70N.npz"


def _raw_path(variable: str, time_utc: str) -> Path:
    name = f"CRA40_{variable}_{time_utc}_GLB_0P25_HOUR_V1_0_0.grib2"
    matches = list(RAW.glob(f"{time_utc[:4]}/{time_utc[:8]}/{name}"))
    if len(matches) != 1:
        raise RuntimeError(f"expected one {name}, found {matches}")
    return matches[0]


def build_subset(event: str, time_utc: str, *, overwrite: bool = False) -> Path:
    """Crop all already-downloaded pressure-level variables for one event time."""
    output = subset_cache_path(CACHE_ROOT, event, time_utc)
    if output.exists() and not overwrite:
        return output
    arrays: dict[str, np.ndarray] = {}
    latitude: np.ndarray | None = None
    longitude: np.ndarray | None = None
    for variable, field in FIELD_NAMES.items():
        dataset = xr.open_dataset(
            _raw_path(variable, time_utc), engine="cfgrib",
            backend_kwargs={"filter_by_keys": {"typeOfLevel": "isobaricInhPa"}, "indexpath": ""},
        )
        selected = dataset[field].sel(**DOMAIN).load()
        if latitude is None:
            latitude = np.asarray(selected.latitude.values, dtype=np.float32)
            longitude = np.asarray(selected.longitude.values, dtype=np.float32)
        arrays[field] = np.asarray(selected.values, dtype=np.float32)
        arrays[f"levels_{field}_hpa"] = np.asarray(selected.isobaricInhPa.values, dtype=np.float32)
        dataset.close()
    if latitude is None or longitude is None:
        raise RuntimeError(f"no fields were cropped for {event} {time_utc}")
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, latitude=latitude, longitude=longitude, **arrays)
    return output


def load_level(event: str, time_utc: str, field: str, level_hpa: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Read one pressure level from a cache file, with explicit level validation."""
    path = subset_cache_path(CACHE_ROOT, event, time_utc)
    arrays = np.load(path)
    levels = arrays[f"levels_{field}_hpa"]
    matches = np.flatnonzero(np.isclose(levels, float(level_hpa)))
    if matches.size != 1:
        raise ValueError(f"{path.name}: {field} does not contain {level_hpa} hPa")
    return arrays[field][int(matches[0])], arrays["latitude"], arrays["longitude"]
