"""Plot one cold-vortex snapshot solely from the cropped research dataset."""

from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np
from matplotlib import pyplot as plt

from cold_vortex_diagnostics import moisture_flux_convergence
from cold_vortex_research_data import read_level


matplotlib.use("Agg")
ROOT = Path(__file__).resolve().parent
EVENT = "2021_september"
TIME = "2021090800"
TRACK = ROOT / "data" / "processed" / "cold_vortex" / "event_tracks" / EVENT / "event_track_core_masks.npz"
OUT = ROOT / "data" / "processed" / "cold_vortex" / "event_diagnostics" / EVENT


def main() -> None:
    z500, latitude, longitude = read_level(EVENT, TIME, "gh", 500)
    u850, _, _ = read_level(EVENT, TIME, "u", 850)
    v850, _, _ = read_level(EVENT, TIME, "v", 850)
    q850, _, _ = read_level(EVENT, TIME, "q", 850)
    omega700, _, _ = read_level(EVENT, TIME, "w", 700)
    mask = np.load(TRACK)["core_body"][0]
    mfc850 = moisture_flux_convergence(
        specific_humidity=q850, u=u850, v=v850, latitude=latitude, longitude=longitude,
    ) * 1e7
    figure, axes = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    for axis, field, title, cmap in (
        (axes[0], mfc850, "850 hPa moisture-flux convergence (10^-7 s^-1; positive = convergence)", "BrBG"),
        (axes[1], omega700, "700 hPa omega (Pa s^-1; negative = ascent)", "PuOr_r"),
    ):
        limit = np.nanpercentile(np.abs(field), 98)
        image = axis.contourf(longitude, latitude, field, levels=np.linspace(-limit, limit, 19), cmap=cmap, extend="both")
        contours = axis.contour(longitude, latitude, z500, levels=np.arange(5200, 5901, 40), colors="black", linewidths=1.3)
        axis.clabel(contours, fmt="%d", fontsize=8, colors="black")
        axis.contour(longitude, latitude, mask, levels=[0.5], colors="#d7301f", linewidths=1.8)
        axis.set(xlim=(90, 170), ylim=(20, 70), xlabel="Longitude (E)", ylabel="Latitude (N)", title=title)
        axis.grid(alpha=0.2)
        figure.colorbar(image, ax=axis, shrink=0.86)
    figure.suptitle("2021-09-08 00 UTC | cropped CRA40 research dataset | red = tracked cold-vortex core")
    OUT.mkdir(parents=True, exist_ok=True)
    figure.savefig(OUT / "2021090800_cropped_data_mfc850_omega700.png", dpi=200)
    plt.close(figure)


if __name__ == "__main__":
    main()
