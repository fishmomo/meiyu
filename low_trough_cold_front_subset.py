"""Create reusable CRA40 subsets for North China low-trough cold-front cases.

The source GRIB2 files remain in ``E:\\data``.  For every verified 6-hourly
case time, this script reads each required isobaric field, crops it to the
East-Asia diagnostic domain, and writes one compressed cache file.  Subsequent
front detection and cross-front diagnostics should read these caches instead
of repeatedly opening the global files.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import xarray as xr


ROOT = Path(__file__).resolve().parent
RAW = Path(r"E:\data")
CACHE_ROOT = ROOT / "data" / "interim" / "low_trough_cold_front_cra40_subset"
DOMAIN = {"latitude": slice(60.0, 15.0), "longitude": slice(70.0, 140.0)}
FIELD_NAMES = {
    "GPH": "gh",
    "WIU": "u",
    "WIV": "v",
    "VVP": "w",
    "RHU": "r",
    "SHU": "q",
    "TEM": "t",
}
CASE_WINDOWS = {
    "2017_may21_23": ("2017052000", "2017052418"),
    "2018_apr20_22": ("2018041900", "2018042318"),
    "2018_apr30_may02": ("2018042900", "2018050318"),
    "2019_mar09_11": ("2019030800", "2019031218"),
    "2019_mar19_21": ("2019031800", "2019032218"),
    "2019_mar27_29": ("2019032600", "2019033018"),
    "2019_apr23_25": ("2019042200", "2019042618"),
}


def case_times(case_name: str) -> list[str]:
    """Return inclusive 6-hourly UTC timestamps for one configured case."""
    try:
        start_text, end_text = CASE_WINDOWS[case_name]
    except KeyError as error:
        raise ValueError(f"unsupported low-trough cold-front case: {case_name}") from error
    start = np.datetime64(
        f"{start_text[:4]}-{start_text[4:6]}-{start_text[6:8]}T{start_text[8:]}"
    )
    end = np.datetime64(f"{end_text[:4]}-{end_text[4:6]}-{end_text[6:8]}T{end_text[8:]}")
    return [
        str(value).replace("-", "").replace("T", "").replace(":", "")[:10]
        for value in np.arange(start, end + np.timedelta64(6, "h"), np.timedelta64(6, "h"))
    ]


def _raw_path(variable: str, time_utc: str) -> Path:
    filename = f"CRA40_{variable}_{time_utc}_GLB_0P25_HOUR_V1_0_0.grib2"
    matches = list(RAW.rglob(filename))
    if len(matches) != 1:
        raise RuntimeError(f"expected one {filename}, found {matches}")
    return matches[0]


def subset_cache_path(case_name: str, time_utc: str) -> Path:
    return CACHE_ROOT / case_name / f"{time_utc}_domain_70E_140E_15N_60N.npz"


def build_subset(case_name: str, time_utc: str, *, overwrite: bool = False) -> Path:
    """Crop all required pressure-level CRA40 fields for one case time."""
    output = subset_cache_path(case_name, time_utc)
    if output.exists() and not overwrite:
        return output

    arrays: dict[str, np.ndarray] = {}
    latitude: np.ndarray | None = None
    longitude: np.ndarray | None = None
    for variable, field in FIELD_NAMES.items():
        dataset = xr.open_dataset(
            _raw_path(variable, time_utc),
            engine="cfgrib",
            backend_kwargs={"filter_by_keys": {"typeOfLevel": "isobaricInhPa"}, "indexpath": ""},
        )
        try:
            selected = dataset[field].sel(**DOMAIN).load()
            if latitude is None:
                latitude = np.asarray(selected.latitude.values, dtype=np.float32)
                longitude = np.asarray(selected.longitude.values, dtype=np.float32)
            arrays[field] = np.asarray(selected.values, dtype=np.float32)
            arrays[f"levels_{field}_hpa"] = np.asarray(
                selected.isobaricInhPa.values, dtype=np.float32
            )
        finally:
            dataset.close()

    if latitude is None or longitude is None:
        raise RuntimeError(f"no fields were cropped for {case_name} {time_utc}")
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, latitude=latitude, longitude=longitude, **arrays)
    return output


def main(case_names: list[str], *, overwrite: bool) -> None:
    for case_name in case_names:
        times = case_times(case_name)
        for index, time_utc in enumerate(times, start=1):
            output = build_subset(case_name, time_utc, overwrite=overwrite)
            print(f"{case_name} {index}/{len(times)} {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", choices=tuple(CASE_WINDOWS))
    parser.add_argument("--overwrite", action="store_true")
    arguments = parser.parse_args()
    main(arguments.case or list(CASE_WINDOWS), overwrite=arguments.overwrite)
