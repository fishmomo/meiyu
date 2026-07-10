from __future__ import annotations

from pathlib import Path
from typing import Final

import numpy as np

from nc_compat import open_dataset_compat
from project_paths import cra40_file


CRA40_PROFILE_SPECS: Final[dict[str, dict[str, str]]] = {
    "rh": {
        "filename": "CRA40_RHU_2017062218_GLB_0P25_HOUR_V1_0_0.grib2",
        "field": "r",
        "level": "isobaricInhPa",
    },
    "temp": {
        "filename": "CRA40_TEM_2017062218_GLB_0P25_HOUR_V1_0_0.grib2",
        "field": "t",
        "level": "isobaricInhPa",
    },
    "w": {
        "filename": "CRA40_VVP_2017062218_GLB_0P25_HOUR_V1_0_0.grib2",
        "field": "w",
        "level": "isobaricInhPa",
    },
}


def _get_cra40_profile_spec(variable: str) -> dict[str, str]:
    try:
        return CRA40_PROFILE_SPECS[variable]
    except KeyError as exc:
        raise ValueError(
            f"unsupported CRA40 profile variable: {variable}"
        ) from exc


def resolve_cra40_profile_input(variable: str) -> Path:
    spec = _get_cra40_profile_spec(variable)
    return Path(cra40_file(spec["filename"]))


def read_cra40_profile_cube(
    variable: str,
    input_path: Path,
    lats: np.ndarray,
    lons: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    spec = _get_cra40_profile_spec(variable)
    ds = open_dataset_compat(input_path)
    level_name = spec["level"]
    cube = ds[spec["field"]].isel({level_name: slice(0, 37)}).sel(
        latitude=lats,
        longitude=lons,
        method="nearest",
    ).values
    levels = ds[level_name].isel({level_name: slice(0, 37)}).values
    return cube, levels
