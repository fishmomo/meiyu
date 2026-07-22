"""Read the common 0.25-degree CRA40 archive without copying it per case."""

from __future__ import annotations

from pathlib import Path
import shutil
import uuid
import tempfile

import numpy as np
import xarray as xr



ROOT = Path(__file__).resolve().parent
COMMON_ROOT = ROOT / "data" / "raw" / "cra40" / "cold_vortex_china_circulation_70p125E_165p125E_14p875N_80p125N"
FIELD_NAMES = {"GPH": "gh", "WIU": "u", "WIV": "v", "VVP": "w", "RHU": "r", "SHU": "q", "TEM": "t"}
RAW_ROOTS = (Path("E:/CRA_global"), Path("E:/data"))


def cropped_field_path(root: Path, variable: str, time_utc: str) -> Path:
    """Return one uniquely named cropped file from the shared archive."""
    matches = list((root / time_utc[:4] / time_utc[:8]).glob(f"CRA40_{variable}_{time_utc}_CHN_0P25_*.nc"))
    if len(matches) != 1:
        raise RuntimeError(f"expected one cropped {variable} file at {time_utc}, found {matches}")
    return matches[0]


def read_level(variable: str, time_utc: str, level_hpa: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Read one pressure level from the common archive."""
    source = cropped_field_path(COMMON_ROOT, variable, time_utc)
    # netCDF4 is reliable on the local ASCII system temporary path; only one
    # small input copy exists at a time and it is deleted immediately.
    staged_root = Path(tempfile.gettempdir()) / "meiyu_cold_vortex_read"
    staged_root.mkdir(parents=True, exist_ok=True)
    staged = staged_root / f"read_{uuid.uuid4().hex}.nc"
    shutil.copy2(source, staged)
    try:
        dataset = xr.open_dataset(staged)
    except OSError:
        # A few early batch outputs were interrupted while being written.
        # Diagnose from the original GRIB instead of blocking the case run.
        try:
            for raw_root in RAW_ROOTS:
                raw = raw_root / time_utc[:4] / time_utc[:8] / f"CRA40_{variable}_{time_utc}_GLB_0P25_HOUR_V1_0_0.grib2"
                if raw.exists():
                    raw_dataset = xr.open_dataset(raw, engine="cfgrib", backend_kwargs={"filter_by_keys": {"typeOfLevel": "isobaricInhPa"}, "indexpath": ""})
                    try:
                        field = raw_dataset[FIELD_NAMES[variable]].sel(isobaricInhPa=level_hpa, latitude=slice(80.125, 14.875), longitude=slice(70.125, 165.125)).load()
                        return np.asarray(field.values, dtype=float), np.asarray(field.latitude.values, dtype=float), np.asarray(field.longitude.values, dtype=float)
                    finally:
                        raw_dataset.close()
            raise RuntimeError(f"cannot read shared cropped file {source} and no raw GRIB fallback exists")
        finally:
            # netCDF4 can retain a Windows file handle after a failed open.
            # A later startup sweep removes that harmless stale copy; it must
            # not hide a successful raw-GRIB fallback.
            try:
                staged.unlink(missing_ok=True)
            except PermissionError:
                pass
    try:
        field = dataset[FIELD_NAMES[variable]].sel(isobaricInhPa=level_hpa)
        return (
            np.asarray(field.values, dtype=float),
            np.asarray(field.latitude.values, dtype=float),
            np.asarray(field.longitude.values, dtype=float),
        )
    finally:
        dataset.close()
        try:
            staged.unlink(missing_ok=True)
        except PermissionError:
            pass


def read_precipitation(time_utc: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Read the cropped six-hour land-precipitation field."""
    matches = list((COMMON_ROOT / time_utc[:4] / time_utc[:8]).glob(f"CRA40LAND_PRECIP_{time_utc}_CHN_0P25_*.nc"))
    if len(matches) != 1:
        raise RuntimeError(f"expected one precipitation file at {time_utc}, found {matches}")
    staged_root = Path(tempfile.gettempdir()) / "meiyu_cold_vortex_read"
    staged_root.mkdir(parents=True, exist_ok=True)
    staged = staged_root / f"precip_{uuid.uuid4().hex}.nc"
    shutil.copy2(matches[0], staged)
    dataset = xr.open_dataset(staged)
    try:
        field = dataset["precipitation"].load()
        return np.asarray(field.values, dtype=float), np.asarray(field.latitude.values, dtype=float), np.asarray(field.longitude.values, dtype=float)
    finally:
        dataset.close()
        try:
            staged.unlink(missing_ok=True)
        except PermissionError:
            pass
