"""Build formal NetCDF datasets for one or more low-trough cold-front cases."""

from __future__ import annotations

import argparse

from low_trough_cold_front_subset import CASE_WINDOWS
from low_trough_cold_front_subset import case_times
from low_trough_cold_front_research_data import build_diagnostic_dataset
from low_trough_cold_front_research_data import build_research_dataset


def main(case_names: list[str], *, diagnostic_levels: bool, overwrite: bool) -> None:
    build = build_diagnostic_dataset if diagnostic_levels else build_research_dataset
    for case_name in case_names:
        times = case_times(case_name)
        for index, time_utc in enumerate(times, start=1):
            print(f"{case_name} {index}/{len(times)} {build(case_name, time_utc, overwrite=overwrite)}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", choices=tuple(CASE_WINDOWS))
    parser.add_argument("--diagnostic-levels", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    arguments = parser.parse_args()
    main(arguments.case or list(CASE_WINDOWS), diagnostic_levels=arguments.diagnostic_levels, overwrite=arguments.overwrite)
