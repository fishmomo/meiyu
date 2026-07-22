"""Build and read the independently stored cropped CRA40 cold-vortex dataset."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import xarray as xr

from nc_compat import open_dataset_compat, to_netcdf_compat


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw" / "cra40"
DATA_ROOT = ROOT / "data" / "derived" / "cra40_cold_vortex_90E170E_20N70N"
DOMAIN = {"latitude": slice(70.0, 20.0), "longitude": slice(90.0, 170.0)}
FIELD_NAMES = {"GPH": "gh", "WIU": "u", "WIV": "v", "VVP": "w", "RHU": "r", "SHU": "q", "TEM": "t"}


def research_dataset_path(root: Path, event: str, time_utc: str) -> Path:
    return root / event / f"CRA40_{time_utc}_0P25_90E170E_20N70N.nc"


def diagnostic_dataset_path(root: Path, event: str, time_utc: str) -> Path:
    return root / "diagnostic_levels" / event / f"CRA40_{time_utc}_0P25_90E170E_20N70N_diagnostic_levels.nc"


def _raw_path(variable: str, time_utc: str) -> Path:
    name = f"CRA40_{variable}_{time_utc}_GLB_0P25_HOUR_V1_0_0.grib2"
    matches = list(RAW.glob(f"{time_utc[:4]}/{time_utc[:8]}/{name}"))
    if len(matches) != 1:
        raise RuntimeError(f"expected one {name}, found {matches}")
    return matches[0]


def build_research_dataset(event: str, time_utc: str, *, overwrite: bool = False) -> Path:
    """Write all downloaded pressure-level fields for one time to a cropped NetCDF."""
    output = research_dataset_path(DATA_ROOT, event, time_utc)
    if output.exists() and not overwrite:
        return output
    fields: dict[str, xr.DataArray] = {}
    for variable, field in FIELD_NAMES.items():
        dataset = xr.open_dataset(
            _raw_path(variable, time_utc), engine="cfgrib",
            backend_kwargs={"filter_by_keys": {"typeOfLevel": "isobaricInhPa"}, "indexpath": ""},
        )
        fields[field] = dataset[field].sel(**DOMAIN).load().astype(np.float32)
        dataset.close()
    merged = xr.Dataset(fields)
    merged.attrs.update({
        "title": "CRA40 cropped cold-vortex research dataset",
        "spatial_domain": "90-170E, 20-70N",
        "source_resolution": "0.25 degree",
        "source_format": "CRA40 GRIB2; cropped without changing field values",
        "event": event,
        "time_utc": time_utc,
    })
    encoding = {name: {"zlib": True, "complevel": 4, "dtype": "float32"} for name in merged.data_vars}
    to_netcdf_compat(merged, output, engine="netcdf4", encoding=encoding)
    merged.close()
    return output


def build_diagnostic_dataset(event: str, time_utc: str, *, overwrite: bool = False) -> Path:
    """Write only the levels required for lifecycle and horizontal diagnostics."""
    output = diagnostic_dataset_path(DATA_ROOT, event, time_utc)
    if output.exists() and not overwrite:
        return output
    required_levels = {"gh": [500], "u": [500, 850], "v": [500, 850], "w": [700], "r": [500, 850], "q": [850], "t": [500, 850]}
    fields: dict[str, xr.DataArray] = {}
    for variable, field in FIELD_NAMES.items():
        dataset = xr.open_dataset(
            _raw_path(variable, time_utc), engine="cfgrib",
            backend_kwargs={"filter_by_keys": {"typeOfLevel": "isobaricInhPa"}, "indexpath": ""},
        )
        fields[field] = dataset[field].sel(isobaricInhPa=required_levels[field], **DOMAIN).load().astype(np.float32)
        dataset.close()
    merged = xr.Dataset(fields)
    merged.attrs.update({"title": "CRA40 cropped cold-vortex diagnostic-level dataset", "spatial_domain": "90-170E, 20-70N", "source_resolution": "0.25 degree", "event": event, "time_utc": time_utc})
    encoding = {name: {"zlib": True, "complevel": 4, "dtype": "float32"} for name in merged.data_vars}
    to_netcdf_compat(merged, output, engine="netcdf4", encoding=encoding)
    merged.close()
    return output


def read_level(event: str, time_utc: str, field: str, level_hpa: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Read one level from the cropped research dataset."""
    path = research_dataset_path(DATA_ROOT, event, time_utc)
    if not path.exists():
        path = diagnostic_dataset_path(DATA_ROOT, event, time_utc)
    dataset = open_dataset_compat(path)
    try:
        selected = dataset[field].sel(isobaricInhPa=level_hpa)
        return (
            np.asarray(selected.values, dtype=float),
            np.asarray(selected.latitude.values, dtype=float),
            np.asarray(selected.longitude.values, dtype=float),
        )
    finally:
        dataset.close()
