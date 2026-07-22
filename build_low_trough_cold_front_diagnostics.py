"""Write GUI-ready 2-D low-trough cold-front diagnostic NetCDF files."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import xarray as xr

from low_trough_cold_front_subset import CASE_WINDOWS, case_times
from low_trough_cold_front_research_data import DATA_ROOT, read_level
from nc_compat import to_netcdf_compat
from pipeline.core.low_trough_cold_front import LowTroughColdFrontInput, calculate_low_trough_cold_front, tfp_in_strong_gradient


OUTPUT_ROOT = DATA_ROOT / "front_diagnostics"


def output_path(case_name: str, time_utc: str) -> Path:
    return OUTPUT_ROOT / case_name / f"CRA40_{time_utc}_0P25_70E140E_15N60N_850_front_500_trough.nc"


def build_diagnostic_file(case_name: str, time_utc: str, *, overwrite: bool = False) -> Path:
    output = output_path(case_name, time_utc)
    if output.exists() and not overwrite:
        return output
    temperature, lats, lons = read_level(case_name, time_utc, "t", 850)
    rh, _, _ = read_level(case_name, time_utc, "r", 850)
    u, _, _ = read_level(case_name, time_utc, "u", 850)
    v, _, _ = read_level(case_name, time_utc, "v", 850)
    gh_500, _, _ = read_level(case_name, time_utc, "gh", 500)
    result = calculate_low_trough_cold_front(LowTroughColdFrontInput(lons, lats, temperature, rh, u, v, gh_500))
    coords = {"latitude": result.lats, "longitude": result.lons}
    fields = {
        "t_850": (temperature, "K"), "r_850": (rh, "1"), "u_850": (u, "m s-1"), "v_850": (v, "m s-1"),
        "gh_500": (result.geopotential_height_500, "m"), "theta_850": (result.theta, "K"),
        "theta_gradient_850": (result.theta_gradient, "K m-1"), "tfp_850": (result.tfp, "K m-2"),
        "cold_advection_850": (result.cold_advection, "K s-1"), "convergence_850": (-result.divergence, "s-1"),
        "frontogenesis_850": (result.frontogenesis, "K m-1 s-1"),
        "front_candidate_mask_850": (result.candidate_mask.astype(np.int8), "1"),
        "tfp_strong_gradient_mask_850": (np.isfinite(tfp_in_strong_gradient(result.tfp, result.theta_gradient)).astype(np.int8), "1"),
    }
    dataset = xr.Dataset({name: (("latitude", "longitude"), np.asarray(values, dtype=np.float32), {"units": units}) for name, (values, units) in fields.items()}, coords=coords)
    dataset.attrs.update({"title": "CRA40 850-hPa cold-front and 500-hPa trough diagnostics", "case": case_name, "time_utc": time_utc, "source_dataset": "cropped CRA40 diagnostic-level NetCDF", "spatial_domain": "70-140E, 15-60N", "smoothing_sigma_grid_cells": 1.5, "candidate_gradient_percentile": 97.0, "tfp_display_gradient_percentile": 85.0, "temperature_advection_convention": "-V dot grad(T); negative is cold advection", "primary_front_fields": "theta_gradient_850, tfp_850, cold_advection_850, convergence_850, frontogenesis_850, gh_500"})
    encoding = {name: {"zlib": True, "complevel": 4, "dtype": "float32"} for name in dataset.data_vars}
    to_netcdf_compat(dataset, output, engine="netcdf4", encoding=encoding)
    dataset.close()
    return output


def main(case_names: list[str], overwrite: bool) -> None:
    for case_name in case_names:
        times = case_times(case_name)
        for index, time_utc in enumerate(times, start=1):
            print(f"{case_name} {index}/{len(times)} {build_diagnostic_file(case_name, time_utc, overwrite=overwrite)}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", choices=tuple(CASE_WINDOWS))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    main(args.case or list(CASE_WINDOWS), args.overwrite)
