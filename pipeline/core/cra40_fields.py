from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Final

import numpy as np

from nc_compat import open_dataset_compat
from project_paths import cra40_file


CRA40_PROFILE_SPECS: Final[dict[str, dict[str, str]]] = {
    "rh": {
        "prefix": "CRA40_RHU",
        "field": "r",
        "level": "isobaricInhPa",
    },
    "temp": {
        "prefix": "CRA40_TEM",
        "field": "t",
        "level": "isobaricInhPa",
    },
    "w": {
        "prefix": "CRA40_VVP",
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


def _cra40_time_token(target_time: str) -> str:
    return datetime.strptime(target_time, "%Y-%m-%dT%H").strftime("%Y%m%d%H")


def build_cra40_filename(variable: str, target_time: str) -> str:
    spec = _get_cra40_profile_spec(variable)
    token = _cra40_time_token(target_time)
    return f"{spec['prefix']}_{token}_GLB_0P25_HOUR_V1_0_0.grib2"


def resolve_cra40_profile_input(variable: str, target_time: str = "2017-06-22T18") -> Path:
    spec = _get_cra40_profile_spec(variable)
    filename = build_cra40_filename(variable, target_time)
    return Path(cra40_file(filename))


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
