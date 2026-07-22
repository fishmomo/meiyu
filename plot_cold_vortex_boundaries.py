"""Create time-step quality-control maps of cold-vortex diagnostic boundaries."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
import numpy as np
from matplotlib import pyplot as plt


matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parent
REGION_DIR = ROOT / "data" / "processed" / "cold_vortex" / "literature_cases" / "circulation_regions"
OUT = REGION_DIR / "boundary_qc"


def _base_name(csv_path: Path) -> str:
    return csv_path.name.removesuffix("_circulation_regions.csv")


def _draw_panel(axis: plt.Axes, row: dict[str, str], arrays: dict[str, np.ndarray]) -> None:
    longitude = arrays["longitude"]
    latitude = arrays["latitude"]
    sample_index = int(np.flatnonzero(arrays["sample"] == row["sample"])[0])
    body = arrays["closed_circulation_body"][sample_index]
    periphery = arrays["connected_positive_vorticity_periphery"][sample_index]
    influence = arrays["circulation_influence_region"][sample_index]
    axis.contour(longitude, latitude, influence, levels=[0.5], colors="#2b8cbe", linewidths=1.0)
    axis.contour(longitude, latitude, periphery, levels=[0.5], colors="#74a9cf", linewidths=0.8, linestyles="--")
    axis.contour(longitude, latitude, body, levels=[0.5], colors="#d7301f", linewidths=1.5)
    axis.plot(float(row["refined_center_longitude_deg_e"]), float(row["refined_center_latitude_deg_n"]), "+", color="black", ms=8, mew=1.4)
    axis.set_xlim(90, 170); axis.set_ylim(20, 70)
    axis.set_xticks([90, 110, 130, 150, 170]); axis.set_yticks([20, 30, 40, 50, 60, 70])
    axis.grid(alpha=0.25, linewidth=0.5)
    axis.set_title(f"{row['time_utc']}  {row['objective_center_latitude_deg_n']}N, {row['objective_center_longitude_deg_e']}E", fontsize=8)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for csv_path in sorted(REGION_DIR.glob("*_circulation_regions.csv")):
        with csv_path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        npz_path = REGION_DIR / f"{_base_name(csv_path)}_circulation_masks.npz"
        # These files are generated locally by build_literature_cold_vortex_regions.py.
        arrays = dict(np.load(npz_path, allow_pickle=True))
        complete = [row for row in rows if row["status"] == "complete"]
        columns = min(3, len(complete))
        figure, axes = plt.subplots(1, columns, figsize=(4.3 * columns, 3.8), constrained_layout=True)
        for axis, row in zip(np.atleast_1d(axes), complete):
            _draw_panel(axis, row, arrays)
            axis.set_xlabel("Longitude (°E)"); axis.set_ylabel("Latitude (°N)")
        figure.suptitle("Red: closed body; blue: circulation influence; dashed blue: connected positive-vorticity periphery; +: center", fontsize=9)
        figure.savefig(OUT / f"{_base_name(csv_path)}_boundary_qc.png", dpi=180)
        plt.close(figure)


if __name__ == "__main__":
    main()
