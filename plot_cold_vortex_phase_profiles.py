"""Plot formation, maturity, and terminal meridional profiles from cropped data."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
import numpy as np
from matplotlib import pyplot as plt
from metpy.calc import dewpoint_from_relative_humidity, equivalent_potential_temperature
from metpy.units import units

from cold_vortex_research_data import DATA_ROOT, research_dataset_path
from nc_compat import open_dataset_compat


matplotlib.use("Agg")
ROOT = Path(__file__).resolve().parent
EVENT = "2021_september"
PHASE_TIMES = ("2021090800", "2021090818", "2021091118")
OUT = ROOT / "data" / "processed" / "cold_vortex" / "event_diagnostics" / EVENT


def _profile(time_utc: str) -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray], float]:
    with (ROOT / "data" / "processed" / "cold_vortex" / "event_tracks" / EVENT / "event_track.csv").open(encoding="utf-8", newline="") as stream:
        record = next(row for row in csv.DictReader(stream) if row["time_utc"] == time_utc)
    center_lon = float(record["refined_center_longitude_deg_e"])
    dataset = open_dataset_compat(research_dataset_path(DATA_ROOT, EVENT, time_utc))
    try:
        levels = dataset.isobaricInhPa.values
        keep = (levels >= 200) & (levels <= 1000)
        levels = levels[keep]
        section = dataset[["t", "r", "w"]].isel(isobaricInhPa=np.flatnonzero(keep)).sel(longitude=center_lon, method="nearest")
        temperature = np.asarray(section.t.values, dtype=float)
        rh = np.asarray(section.r.values, dtype=float)
        thetae = equivalent_potential_temperature(
            levels[:, None] * units.hPa,
            temperature * units.kelvin,
            dewpoint_from_relative_humidity(temperature * units.kelvin, (rh / 100.0) * units.dimensionless),
        ).magnitude
        return section.latitude.values, levels, {"temperature": temperature, "rh": rh, "omega": np.asarray(section.w.values, dtype=float), "thetae": thetae}, float(section.longitude.values)
    finally:
        dataset.close()


def main() -> None:
    settings = (("temperature", "Temperature (K)", "coolwarm"), ("rh", "RH (%)", "YlGnBu"), ("omega", "Omega (Pa s^-1; negative = ascent)", "PuOr_r"))
    figure, axes = plt.subplots(3, 3, figsize=(14, 10), sharex=True, sharey=True, constrained_layout=True)
    for row, time_utc in enumerate(PHASE_TIMES):
        latitude, levels, fields, actual_lon = _profile(time_utc)
        for column, (field, label, cmap) in enumerate(settings):
            axis = axes[row, column]
            values = fields[field]
            if field == "omega":
                limit = np.nanpercentile(np.abs(values), 98)
                contours = axis.contourf(latitude, levels, values, levels=np.linspace(-limit, limit, 19), cmap=cmap, extend="both")
            else:
                contours = axis.contourf(latitude, levels, values, levels=18, cmap=cmap, extend="both")
            theta_contours = axis.contour(latitude, levels, fields["thetae"], colors="black", linewidths=0.65, levels=8)
            axis.clabel(theta_contours, fmt="%.0f", fontsize=6)
            axis.invert_yaxis(); axis.set_title(label, fontsize=9)
            axis.set_ylabel(f"{time_utc} | pressure (hPa)\nlon={actual_lon:.2f}E", fontsize=8)
            figure.colorbar(contours, ax=axis, shrink=0.82)
    for axis in axes[-1]:
        axis.set_xlabel("Latitude (N)")
    figure.suptitle("2021 September cold vortex: centre-longitude meridional profiles; black = theta-e (K)")
    OUT.mkdir(parents=True, exist_ok=True)
    figure.savefig(OUT / "formation_maturity_terminal_meridional_profiles.png", dpi=200)
    plt.close(figure)


if __name__ == "__main__":
    main()
