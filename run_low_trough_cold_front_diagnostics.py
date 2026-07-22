"""Write time-resolved 2-D diagnostics for low-trough cold-front cases."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from low_trough_cold_front_subset import CASE_WINDOWS
from low_trough_cold_front_subset import case_times
from low_trough_cold_front_research_data import read_level
from nc_compat import open_dataset_compat
from pipeline.core.low_trough_cold_front import LowTroughColdFrontInput
from pipeline.core.low_trough_cold_front import calculate_low_trough_cold_front
from pipeline.core.low_trough_cold_front import tfp_in_strong_gradient
from pipeline.core.low_trough_cold_front_features import FrontLine
from pipeline.core.low_trough_cold_front_features import extract_primary_front_line
from pipeline.core.low_trough_cold_front_features import extract_trough_axis
from pipeline.core.low_trough_cold_front_features import signed_front_trough_separation_deg


ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = ROOT / "outputs" / "low_trough_cold_front"


def read_input(case_name: str, time_utc: str) -> LowTroughColdFrontInput:
    """Read 850/500-hPa fields from the formal cropped NetCDF dataset."""
    temperature, lats, lons = read_level(case_name, time_utc, "t", 850)
    relative_humidity, _, _ = read_level(case_name, time_utc, "r", 850)
    u, _, _ = read_level(case_name, time_utc, "u", 850)
    v, _, _ = read_level(case_name, time_utc, "v", 850)
    geopotential_height_500, _, _ = read_level(case_name, time_utc, "gh", 500)
    return LowTroughColdFrontInput(
        lons=lons,
        lats=lats,
        temperature=temperature,
        relative_humidity=relative_humidity,
        u=u,
        v=v,
        geopotential_height_500=geopotential_height_500,
    )


def _symmetric_limit(values: np.ndarray, percentile: float = 98.0) -> float:
    value = float(np.nanpercentile(np.abs(values), percentile))
    return value if np.isfinite(value) and value > 0 else 1.0


def read_manual_front_mask(mask_dir: Path, time_utc: str, lats: np.ndarray, lons: np.ndarray) -> np.ndarray | None:
    """Read one GUI-selected front mask when it exactly matches the diagnostic grid."""
    filename = f"front_mask_{time_utc[:8]}_{time_utc[8:]}.nc"
    path = mask_dir / filename
    if not path.exists():
        return None
    dataset = open_dataset_compat(path)
    try:
        if "meiyu_front_mask" not in dataset:
            raise ValueError(f"{path.name} does not contain meiyu_front_mask")
        mask = dataset["meiyu_front_mask"]
        if mask.shape != (len(lats), len(lons)) or not np.array_equal(mask.latitude.values, lats) or not np.array_equal(mask.longitude.values, lons):
            raise ValueError(f"{path.name} does not match the diagnostic latitude-longitude grid")
        return np.asarray(mask.values, dtype=bool)
    finally:
        dataset.close()


def _draw_manual_front_mask(axis, lons: np.ndarray, lats: np.ndarray, mask: np.ndarray) -> None:
    axis.contour(
        lons, lats, np.asarray(mask, dtype=float), levels=[0.5], colors="#0057B8", linewidths=2.0, zorder=9,
    )


def _draw_synoptic_features(axis, front: FrontLine | None, trough: FrontLine | None) -> None:
    """Overlay the objective first-pass front and trough in weather-map style."""
    if trough is not None:
        axis.plot(trough.longitude, trough.latitude, color="black", linestyle="--", linewidth=1.8, label="500 hPa trough axis")
    if front is None:
        return
    axis.plot(front.longitude, front.latitude, color="#0066CC", linewidth=2.2, label="objective cold-front line")
    marker_indices = np.linspace(0, front.longitude.size - 1, min(9, max(2, front.longitude.size // 10)), dtype=int)
    # Filled triangles are the standard weather-map cold-front symbol.  The
    # exact warm-side orientation will be refined when the final edited line
    # is confirmed; this first-pass symbol establishes the front geometry.
    axis.scatter(front.longitude[marker_indices], front.latitude[marker_indices], marker=(3, 0, 0), s=34, color="#0066CC", zorder=7)


def feature_summary(case_name: str, time_utc: str) -> dict[str, float | str]:
    result = calculate_low_trough_cold_front(read_input(case_name, time_utc))
    front = extract_primary_front_line(result.lons, result.lats, result.tfp, result.theta_gradient, result.candidate_mask)
    trough = extract_trough_axis(result.lons, result.lats, result.geopotential_height_500)
    return {
        "time_utc": time_utc,
        "front_points": 0 if front is None else int(front.longitude.size),
        "trough_points": 0 if trough is None else int(trough.longitude.size),
        "front_trough_zonal_separation_deg": float("nan") if front is None or trough is None else signed_front_trough_separation_deg(front, trough),
    }


def write_overview(case_name: str, time_utc: str, *, manual_mask_dir: Path | None = None) -> Path:
    """Create one three-panel cold-front/low-trough diagnostic figure."""
    result = calculate_low_trough_cold_front(read_input(case_name, time_utc))
    front = extract_primary_front_line(result.lons, result.lats, result.tfp, result.theta_gradient, result.candidate_mask)
    trough = extract_trough_axis(result.lons, result.lats, result.geopotential_height_500)
    lons, lats = np.meshgrid(result.lons, result.lats)
    manual_mask = None if manual_mask_dir is None else read_manual_front_mask(manual_mask_dir, time_utc, result.lats, result.lons)
    output_dir = OUTPUT_ROOT / case_name / ("diagnostics_manual_front_overlay" if manual_mask is not None else "diagnostics")
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = "_manual_front_mask" if manual_mask is not None else ""
    output = output_dir / f"{case_name}_{time_utc}_850_front_500_trough{suffix}.png"

    figure, axes = plt.subplots(1, 3, figsize=(18, 5.8), constrained_layout=True)
    title_time = f"{time_utc[:4]}-{time_utc[4:6]}-{time_utc[6:8]} {time_utc[8:]} UTC"

    gradient_scale = max(float(np.nanpercentile(result.theta_gradient, 99.0)), 1e-7)
    panel = axes[0].contourf(
        lons, lats, result.theta_gradient * 1e5,
        levels=np.linspace(0.0, gradient_scale * 1e5, 13), cmap="YlOrRd", extend="max",
    )
    tfp_for_plot = tfp_in_strong_gradient(result.tfp, result.theta_gradient, percentile=85.0)
    axes[0].contour(lons, lats, tfp_for_plot * 1e10, levels=[0.0], colors="cyan", linewidths=1.1)
    axes[0].contour(lons, lats, result.candidate_mask.astype(float), levels=[0.5], colors="#FFD700", linewidths=1.5)
    axes[0].quiver(lons[::8, ::8], lats[::8, ::8], result.u[::8, ::8], result.v[::8, ::8], scale=230)
    if manual_mask is None:
        _draw_synoptic_features(axes[0], front, trough)
    figure.colorbar(panel, ax=axes[0], label=r"|∇θ$_e$| (10$^{-5}$ K m$^{-1}$)")
    axes[0].set_title("850 hPa θ gradient / TFP / candidate")

    advection_6h = result.cold_advection * 21600.0
    advection_limit = _symmetric_limit(advection_6h)
    panel = axes[1].contourf(
        lons, lats, advection_6h,
        levels=np.linspace(-advection_limit, advection_limit, 15), cmap="RdBu_r", extend="both",
    )
    axes[1].contour(lons, lats, result.divergence * 1e5, levels=[0.0], colors="black", linewidths=0.9)
    axes[1].contour(lons, lats, result.candidate_mask.astype(float), levels=[0.5], colors="#FFD700", linewidths=1.5)
    if manual_mask is None:
        _draw_synoptic_features(axes[1], front, trough)
    figure.colorbar(panel, ax=axes[1], label="850 hPa temperature advection (K / 6 h)")
    axes[1].set_title("cold advection / convergence / candidate")

    frontogenesis = result.frontogenesis * 1e9
    frontogenesis_limit = _symmetric_limit(frontogenesis)
    panel = axes[2].contourf(
        lons, lats, frontogenesis,
        levels=np.linspace(-frontogenesis_limit, frontogenesis_limit, 15), cmap="PuOr_r", extend="both",
    )
    height_levels = np.arange(
        np.floor(np.nanmin(result.geopotential_height_500) / 40.0) * 40.0,
        np.ceil(np.nanmax(result.geopotential_height_500) / 40.0) * 40.0 + 1.0,
        40.0,
    )
    contours = axes[2].contour(lons, lats, result.geopotential_height_500, levels=height_levels, colors="black", linewidths=0.8)
    axes[2].clabel(contours, fmt="%d", fontsize=7)
    axes[2].contour(lons, lats, result.candidate_mask.astype(float), levels=[0.5], colors="#FFD700", linewidths=1.5)
    if manual_mask is None:
        _draw_synoptic_features(axes[2], front, trough)
    figure.colorbar(panel, ax=axes[2], label=r"850 hPa frontogenesis (10$^{-9}$ K m$^{-1}$ s$^{-1}$)")
    axes[2].set_title("850 hPa frontogenesis / 500 hPa height")

    for axis in axes:
        axis.set(xlim=(90.0, 135.0), ylim=(20.0, 50.0), xlabel="Longitude (°E)", ylabel="Latitude (°N)")
        axis.grid(alpha=0.25, linewidth=0.4)
        if manual_mask is not None:
            _draw_manual_front_mask(axis, lons, lats, manual_mask)
    if manual_mask is None:
        axes[0].legend(loc="lower left", fontsize=7, framealpha=0.85)
    figure.suptitle(f"{case_name}: {title_time}", fontsize=13)
    figure.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(figure)
    return output


def main(case_names: list[str], manual_mask_dir: Path | None = None) -> None:
    for case_name in case_names:
        times = case_times(case_name)
        summaries: list[dict[str, float | str]] = []
        for index, time_utc in enumerate(times, start=1):
            if manual_mask_dir is not None and not (manual_mask_dir / f"front_mask_{time_utc[:8]}_{time_utc[8:]}.nc").exists():
                continue
            output = write_overview(case_name, time_utc, manual_mask_dir=manual_mask_dir)
            summaries.append(feature_summary(case_name, time_utc))
            print(f"{case_name} {index}/{len(times)} {output}", flush=True)
        summary_path = OUTPUT_ROOT / case_name / "front_trough_summary.csv"
        with summary_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(summaries[0]))
            writer.writeheader()
            writer.writerows(summaries)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", choices=tuple(CASE_WINDOWS))
    parser.add_argument("--manual-front-mask-dir", type=Path)
    args = parser.parse_args()
    main(args.case or ["2017_may21_23"], manual_mask_dir=args.manual_front_mask_dir)
