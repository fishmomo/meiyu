from __future__ import annotations

from pathlib import Path
from typing import Final

import numpy as np

from nc_compat import open_dataset_compat
from project_paths import era5_file


ERA5_PROFILE_SPECS: Final[dict[str, dict[str, str]]] = {
    "rh": {
        "filename": "ERA5_RH_201706.nc",
        "field": "r",
        "level": "pressure_level",
        "time_coord": "valid_time",
    },
    "temp": {
        "filename": "ERA5_tmp_201706.nc",
        "field": "t",
        "level": "pressure_level",
        "time_coord": "valid_time",
    },
    "w": {
        "filename": "ERA5_wdata_201706.nc",
        "field": "w",
        "level": "pressure_level",
        "time_coord": "valid_time",
    },
}


def _get_era5_profile_spec(variable: str) -> dict[str, str]:
    try:
        return ERA5_PROFILE_SPECS[variable]
    except KeyError as exc:
        raise ValueError(f"unsupported ERA5 profile variable: {variable}") from exc


def resolve_era5_profile_input(variable: str) -> Path:
    spec = _get_era5_profile_spec(variable)
    return Path(era5_file(spec["filename"]))


def read_era5_profile_cube(
    variable: str,
    input_path: Path,
    target_time: str,
    lats: np.ndarray,
    lons: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Read a 3D ERA5 profile cube for a specific target time.

    Parameters
    ----------
    variable : str
        Profile variable name (rh, temp, w).
    input_path : Path
        Path to the ERA5 monthly NetCDF file.
    target_time : str
        Target time in ISO format (YYYY-MM-DDTHH).
    lats : np.ndarray
        Target latitudes (1D).
    lons : np.ndarray
        Target longitudes (1D).

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        (cube, levels) where cube has shape (n_levels, n_lats, n_lons).
    """
    spec = _get_era5_profile_spec(variable)
    ds = open_dataset_compat(input_path)
    time_coord = spec["time_coord"]
    level_name = spec["level"]

    # Select the target time. ERA5 valid_time is often numpy datetime64.
    # Use nearest selection to avoid strict matching issues.
    time_sel = ds[spec["field"]].sel(
        {time_coord: np.datetime64(target_time)},
        method="nearest",
    )

    # Align to target lat/lon grid
    cube = time_sel.sel(
        latitude=lats,
        longitude=lons,
        method="nearest",
    ).values

    # Get levels from the full dataset (time-independent)
    levels = ds[level_name].values

    return cube, levels
