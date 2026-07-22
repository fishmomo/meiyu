"""Build formal cropped CRA40 NetCDF research datasets for low-trough fronts."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import xarray as xr

from nc_compat import open_dataset_compat
from nc_compat import to_netcdf_compat


ROOT = Path(__file__).resolve().parent
RAW = Path(r"E:\data")
DATA_ROOT = ROOT / "data" / "derived" / "cra40_low_trough_cold_front_70E140E_15N60N"
DOMAIN = {"latitude": slice(60.0, 15.0), "longitude": slice(70.0, 140.0)}
FIELD_NAMES = {"GPH": "gh", "WIU": "u", "WIV": "v", "VVP": "w", "RHU": "r", "SHU": "q", "TEM": "t"}
DIAGNOSTIC_LEVELS = {"gh": [500], "u": [500, 850], "v": [500, 850], "w": [700], "r": [500, 850], "q": [850], "t": [500, 850]}


def research_dataset_path(root: Path, case_name: str, time_utc: str) -> Path:
    return root / case_name / f"CRA40_{time_utc}_0P25_70E140E_15N60N.nc"


def diagnostic_dataset_path(root: Path, case_name: str, time_utc: str) -> Path:
    return root / "diagnostic_levels" / case_name / f"CRA40_{time_utc}_0P25_70E140E_15N60N_diagnostic_levels.nc"


def _raw_path(variable: str, time_utc: str) -> Path:
    filename = f"CRA40_{variable}_{time_utc}_GLB_0P25_HOUR_V1_0_0.grib2"
    direct = RAW / filename
    if direct.exists():
        return direct
    matches = list(RAW.rglob(filename))
    if len(matches) != 1:
        raise RuntimeError(f"expected one {filename}, found {matches}")
    return matches[0]


def _cropped_fields(time_utc: str, levels: dict[str, list[int]] | None = None) -> dict[str, xr.DataArray]:
    fields: dict[str, xr.DataArray] = {}
    for variable, field in FIELD_NAMES.items():
        dataset = xr.open_dataset(
            _raw_path(variable, time_utc),
            engine="cfgrib",
            backend_kwargs={"filter_by_keys": {"typeOfLevel": "isobaricInhPa"}, "indexpath": ""},
        )
        try:
            selected = dataset[field]
            if levels is not None:
                selected = selected.sel(isobaricInhPa=levels[field])
            fields[field] = selected.sel(**DOMAIN).load().astype(np.float32)
        finally:
            dataset.close()
    return fields


def _write(fields: dict[str, xr.DataArray], output: Path, *, case_name: str, time_utc: str, title: str) -> Path:
    merged = xr.Dataset(fields)
    merged.attrs.update({
        "title": title,
        "spatial_domain": "70-140E, 15-60N",
        "source_resolution": "0.25 degree",
        "source_format": "CRA40 GRIB2; cropped without changing field values",
        "case": case_name,
        "time_utc": time_utc,
    })
    encoding = {name: {"zlib": True, "complevel": 4, "dtype": "float32"} for name in merged.data_vars}
    to_netcdf_compat(merged, output, engine="netcdf4", encoding=encoding)
    merged.close()
    return output


def build_research_dataset(case_name: str, time_utc: str, *, overwrite: bool = False) -> Path:
    """Write every pressure level of all seven CRA40 fields to one cropped NetCDF."""
    output = research_dataset_path(DATA_ROOT, case_name, time_utc)
    if output.exists() and not overwrite:
        return output
    return _write(
        _cropped_fields(time_utc), output, case_name=case_name, time_utc=time_utc,
        title="CRA40 cropped low-trough cold-front research dataset",
    )


def build_diagnostic_dataset(case_name: str, time_utc: str, *, overwrite: bool = False) -> Path:
    """Write the levels required for 2-D low-trough/cold-front diagnostics."""
    output = diagnostic_dataset_path(DATA_ROOT, case_name, time_utc)
    if output.exists() and not overwrite:
        return output
    return _write(
        _cropped_fields(time_utc, DIAGNOSTIC_LEVELS), output, case_name=case_name, time_utc=time_utc,
        title="CRA40 cropped low-trough cold-front diagnostic-level dataset",
    )


def read_level(case_name: str, time_utc: str, field: str, level_hpa: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Read one pressure level, accepting research or diagnostic NetCDFs."""
    path = research_dataset_path(DATA_ROOT, case_name, time_utc)
    if not path.exists():
        path = diagnostic_dataset_path(DATA_ROOT, case_name, time_utc)
    dataset = open_dataset_compat(path)
    try:
        selected = dataset[field].sel(isobaricInhPa=level_hpa)
        return (np.asarray(selected.values, dtype=float), np.asarray(selected.latitude.values, dtype=float), np.asarray(selected.longitude.values, dtype=float))
    finally:
        dataset.close()
