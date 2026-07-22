"""Safely crop global CRA40 GRIB files to the cold-vortex circulation domain.

Source GRIB files remain untouched.  The command is deliberately single-threaded
so it can run alongside an ongoing transfer from the download disk.
"""

from __future__ import annotations

import argparse
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path


def runtime_temp_root(project_path: Path) -> Path:
    """Return an ASCII temporary directory on the project's drive."""
    return Path(project_path.resolve().anchor) / "meiyu_new_xarray_cache"


# Native NetCDF/ecCodes components can use TEMP/TMP independently of Python's
# tempfile module.  Set both before importing xarray so parallel crop workers
# never spill multi-gigabyte intermediates onto C:.
RUNTIME_TEMP_ROOT = runtime_temp_root(Path(__file__))
RUNTIME_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
os.environ["TEMP"] = str(RUNTIME_TEMP_ROOT)
os.environ["TMP"] = str(RUNTIME_TEMP_ROOT)

import xarray as xr
import numpy as np

from nc_compat import open_dataset_compat, to_netcdf_compat


# Bounds are cell edges.  CRA40 0.25-degree cell centres retained by this
# selection are 70.25--165.00E and 15.00--80.00N.
CHINA_DOMAIN = {"latitude": slice(80.125, 14.875), "longitude": slice(70.125, 165.125)}
GRIB_SUFFIXES = {".grib", ".grib2", ".grb", ".grb2"}


def china_output_path(source: Path, source_root: Path, target_root: Path) -> Path:
    """Map one global GRIB to a China-cropped NetCDF, preserving its tree."""
    relative = source.relative_to(source_root)
    name = relative.name.replace("_GLB_", "_CHN_")
    return target_root / relative.parent / Path(name).with_suffix(".nc")


def select_china_domain(dataset: xr.Dataset) -> xr.Dataset:
    """Select the cold-vortex circulation study domain from a CRA40 dataset."""
    latitude = dataset.latitude.values
    latitude_slice = CHINA_DOMAIN["latitude"]
    if latitude[0] < latitude[-1]:
        latitude_slice = slice(latitude_slice.stop, latitude_slice.start)
    return dataset.sel(latitude=latitude_slice, longitude=CHINA_DOMAIN["longitude"])


def crop_land_precipitation_values(values: np.ndarray) -> xr.DataArray:
    """Crop CRA40LAND precipitation with reconstructed 0.25-degree coordinates.

    These GRIB files have an incorrect ``jScansPositively`` flag, so ecCodes
    cannot construct their geographic iterator.  Their declared endpoints and
    shape define an unambiguous 89.875-- -89.875N, 0.125--359.875E grid.
    """
    if values.shape != (720, 1440):
        raise ValueError(f"unexpected CRA40LAND precipitation grid: {values.shape}")
    latitude = 89.875 - 0.25 * np.arange(720)
    longitude = 0.125 + 0.25 * np.arange(1440)
    latitude_mask = (latitude <= 80.125) & (latitude >= 14.875)
    longitude_mask = (longitude >= 70.125) & (longitude <= 165.125)
    return xr.DataArray(
        values[np.ix_(latitude_mask, longitude_mask)],
        coords={"latitude": latitude[latitude_mask], "longitude": longitude[longitude_mask]},
        dims=("latitude", "longitude"),
        name="precipitation",
    )


def _open_land_precipitation(source: Path) -> xr.Dataset:
    import pygrib

    grib = pygrib.open(str(source))
    try:
        message = grib.message(1)
        precipitation = crop_land_precipitation_values(np.asarray(message.values, dtype=np.float32))
        precipitation.attrs.update({
            "source_variable": "CRA40LAND_PRECIP",
            "source_short_name": str(message["shortName"]),
            "source_units": str(message["units"]),
            "step_range": str(message["stepRange"]),
            "note": "Coordinates reconstructed from CRA40LAND GRIB endpoints because jScansPositively is inconsistent.",
        })
        return xr.Dataset({"precipitation": precipitation})
    finally:
        grib.close()


def _open_grib(source: Path) -> xr.Dataset:
    if source.name.startswith("CRA40LAND_PRECIP_"):
        return _open_land_precipitation(source)
    return open_dataset_compat(source, engine="cfgrib", backend_kwargs={"indexpath": ""})


def crop_one(source: Path, source_root: Path, target_root: Path, *, overwrite: bool = False) -> tuple[str, Path]:
    """Crop one stable source file; return ``(status, output_path)``.

    A source whose size or timestamp changes during reading is skipped.  Its
    partial output is removed and the original download is never modified.
    """
    output = china_output_path(source, source_root, target_root)
    if output.exists() and not overwrite:
        return "exists", output
    before = source.stat()
    dataset = _open_grib(source)
    try:
        cropped = select_china_domain(dataset).load()
    finally:
        dataset.close()
    after_read = source.stat()
    if (before.st_size, before.st_mtime_ns) != (after_read.st_size, after_read.st_mtime_ns):
        cropped.close()
        return "source_changed", output
    cropped.attrs.update({
        "title": "CRA40 cold-vortex China-circulation study dataset",
        "spatial_domain": "70.125-165.125E, 14.875-80.125N (cell edges)",
        "source_file": source.name,
        "source_format": "CRA40 global GRIB; cropped without changing field values",
    })
    part = output.with_suffix(".part.nc")
    if part.exists():
        part.unlink()
    encoding = {name: {"zlib": True, "complevel": 4} for name in cropped.data_vars}
    try:
        to_netcdf_compat(cropped, part, engine="netcdf4", encoding=encoding)
    finally:
        cropped.close()
    after_write = source.stat()
    if (before.st_size, before.st_mtime_ns) != (after_write.st_size, after_write.st_mtime_ns):
        part.unlink(missing_ok=True)
        return "source_changed", output
    output.parent.mkdir(parents=True, exist_ok=True)
    part.replace(output)
    return "written", output


def crop_one_job(job: tuple[Path, Path, Path, bool]) -> tuple[Path, str, Path]:
    """Pickle-safe worker wrapper retaining the source path for the manifest."""
    source, source_root, target_root, overwrite = job
    status, output = crop_one(source, source_root, target_root, overwrite=overwrite)
    return source, status, output


def iter_grib_files(source_root: Path):
    return (path for path in source_root.rglob("*") if path.is_file() and path.suffix.lower() in GRIB_SUFFIXES)


def filter_by_resolution(files, resolution: str | None):
    """Keep only CRA40 filenames with the requested native resolution."""
    if resolution is None:
        return list(files)
    marker = f"_{resolution}_"
    return [path for path in files if marker in path.name]


def _write_result(writer: csv.DictWriter, source: Path, status: str, output: Path, processed: int, pause_seconds: float) -> None:
    writer.writerow({"source": str(source), "output": str(output), "status": status})
    print(f"{processed}: {status} {source.name}")
    if pause_seconds > 0:
        time.sleep(pause_seconds)


def main(source_root: Path, target_root: Path, limit: int | None, overwrite: bool, pause_seconds: float, workers: int, resolution: str | None) -> None:
    manifest = target_root / "crop_manifest.csv"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    write_header = not manifest.exists()
    processed = 0
    with manifest.open("a", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("source", "output", "status"))
        if write_header:
            writer.writeheader()
        sources = filter_by_resolution(iter_grib_files(source_root), resolution)
        if limit is not None:
            sources = sources[:limit]
        if workers == 1:
            for source in sources:
                _, status, output = crop_one_job((source, source_root, target_root, overwrite))
                processed += 1
                _write_result(writer, source, status, output, processed, pause_seconds)
                stream.flush()
        else:
            jobs = [(source, source_root, target_root, overwrite) for source in sources]
            with ProcessPoolExecutor(max_workers=workers) as pool:
                futures = [pool.submit(crop_one_job, job) for job in jobs]
                for future in as_completed(futures):
                    source, status, output = future.result()
                    processed += 1
                    _write_result(writer, source, status, output, processed, pause_seconds)
                    stream.flush()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--pause-seconds", type=float, default=0.0, help="idle time between files; use this while a download is active")
    parser.add_argument("--workers", type=int, default=1, help="independent crop workers; use 1 while downloads are active")
    parser.add_argument("--resolution", choices=("0P25", "2P50"), help="only process one CRA40 native resolution")
    args = parser.parse_args()
    main(args.source, args.target, args.limit, args.overwrite, args.pause_seconds, args.workers, args.resolution)
