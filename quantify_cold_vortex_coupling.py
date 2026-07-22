"""Quantify moisture-convergence and ascent placement inside a vortex core."""

from __future__ import annotations

import csv
import argparse
from pathlib import Path

import matplotlib
import numpy as np
from matplotlib import pyplot as plt

from build_literature_cold_vortex_regions import _cell_area_km2
from cold_vortex_diagnostics import moisture_flux_convergence
from cold_vortex_research_data import read_level


matplotlib.use("Agg")
ROOT = Path(__file__).resolve().parent
EVENTS = ("2017_august_east", "2021_september", "2021_november")
TRACK_ROOT = ROOT / "data" / "processed" / "cold_vortex" / "event_tracks"
OUT_ROOT = ROOT / "data" / "processed" / "cold_vortex" / "event_diagnostics"


def event_paths(event: str) -> tuple[Path, Path]:
    """Return the core-track and diagnostic-output directories for one event."""
    return TRACK_ROOT / event, OUT_ROOT / event


def _distance_km(lat0: float, lon0: float, lat1: float, lon1: float) -> float:
    radius_km = 6371.0
    lat0_rad, lat1_rad = np.deg2rad([lat0, lat1])
    dlat = lat1_rad - lat0_rad
    dlon = np.deg2rad(lon1 - lon0)
    value = np.sin(dlat / 2) ** 2 + np.cos(lat0_rad) * np.cos(lat1_rad) * np.sin(dlon / 2) ** 2
    return float(2 * radius_km * np.arcsin(np.sqrt(value)))


def _weighted_centroid(weights: np.ndarray, mask: np.ndarray, latitude: np.ndarray, longitude: np.ndarray, area: np.ndarray) -> tuple[float, float]:
    weighted = np.where(mask, np.maximum(weights, 0.0) * area, 0.0)
    total = weighted.sum()
    if total <= 0:
        return float("nan"), float("nan")
    lat2d, lon2d = np.meshgrid(latitude, longitude, indexing="ij")
    return float((weighted * lat2d).sum() / total), float((weighted * lon2d).sum() / total)


def centroid_separation(
    mfc_latitude: float,
    mfc_longitude: float,
    ascent_latitude: float,
    ascent_longitude: float,
    core_equivalent_radius_km: float,
) -> tuple[float, float]:
    """Return the separation of the two weighted centroids in km and core-radius units."""
    distance = _distance_km(mfc_latitude, mfc_longitude, ascent_latitude, ascent_longitude)
    return distance, distance / core_equivalent_radius_km


def conditional_area_weighted_mean(field: np.ndarray, condition: np.ndarray, area: np.ndarray) -> float:
    """Area-weighted field mean over the cells satisfying a physical condition."""
    valid = condition & np.isfinite(field)
    total_area = area[valid].sum()
    if total_area <= 0:
        return float("nan")
    return float((field[valid] * area[valid]).sum() / total_area)


def main(event: str) -> None:
    track_dir, output_dir = event_paths(event)
    with (track_dir / "event_track.csv").open(encoding="utf-8", newline="") as stream:
        track = list(csv.DictReader(stream))
    masks = np.load(track_dir / "event_track_core_masks.npz")
    latitude, longitude = masks["latitude"], masks["longitude"]
    area = np.broadcast_to(_cell_area_km2(latitude, longitude), masks["core_body"][0].shape)
    rows: list[dict[str, float | str]] = []
    for index, record in enumerate(track):
        time_utc = record["time_utc"]
        u850, _, _ = read_level(event, time_utc, "u", 850)
        v850, _, _ = read_level(event, time_utc, "v", 850)
        q850, _, _ = read_level(event, time_utc, "q", 850)
        omega700, _, _ = read_level(event, time_utc, "w", 700)
        mfc = moisture_flux_convergence(specific_humidity=q850, u=u850, v=v850, latitude=latitude, longitude=longitude)
        core = masks["core_body"][index].astype(bool)
        core_area = float(area[core].sum())
        radius = float(np.sqrt(core_area / np.pi))
        convergence = mfc > 0
        ascent = omega700 < 0
        coupled = core & convergence & ascent
        mfc_lat, mfc_lon = _weighted_centroid(mfc, core, latitude, longitude, area)
        ascent_lat, ascent_lon = _weighted_centroid(-omega700, core, latitude, longitude, area)
        center_lat = float(record["refined_center_latitude_deg_n"]); center_lon = float(record["refined_center_longitude_deg_e"])
        rows.append({
            "time_utc": time_utc, "phase": record["phase"], "core_area_km2": core_area, "core_equivalent_radius_km": radius,
            "mfc_positive_core_coverage_percent": float(100 * area[core & convergence].sum() / core_area),
            "ascent_core_coverage_percent": float(100 * area[core & ascent].sum() / core_area),
            "coupled_core_coverage_percent": float(100 * area[coupled].sum() / core_area),
            "mfc_positive_mean_s_inv": conditional_area_weighted_mean(mfc, core & convergence, area),
            "ascent_mean_pa_s_inv": conditional_area_weighted_mean(-omega700, core & ascent, area),
            "coupled_mfc_mean_s_inv": conditional_area_weighted_mean(mfc, coupled, area),
            "coupled_ascent_mean_pa_s_inv": conditional_area_weighted_mean(-omega700, coupled, area),
            "mfc_centroid_latitude_deg_n": mfc_lat, "mfc_centroid_longitude_deg_e": mfc_lon,
            "ascent_centroid_latitude_deg_n": ascent_lat, "ascent_centroid_longitude_deg_e": ascent_lon,
            "mfc_centroid_offset_km": _distance_km(center_lat, center_lon, mfc_lat, mfc_lon),
            "ascent_centroid_offset_km": _distance_km(center_lat, center_lon, ascent_lat, ascent_lon),
        })
        rows[-1]["mfc_centroid_offset_radius"] = float(rows[-1]["mfc_centroid_offset_km"]) / radius
        rows[-1]["ascent_centroid_offset_radius"] = float(rows[-1]["ascent_centroid_offset_km"]) / radius
        separation_km, separation_radius = centroid_separation(
            mfc_lat, mfc_lon, ascent_lat, ascent_lon, radius
        )
        rows[-1]["mfc_ascent_centroid_separation_km"] = separation_km
        rows[-1]["mfc_ascent_centroid_separation_radius"] = separation_radius
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "core_moisture_ascent_coupling.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    x = np.arange(len(rows)); labels = [row["time_utc"][4:] for row in rows]
    figure, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True, constrained_layout=True)
    axes[0].plot(x, [row["mfc_positive_core_coverage_percent"] for row in rows], marker="o", label="MFC > 0")
    axes[0].plot(x, [row["ascent_core_coverage_percent"] for row in rows], marker="s", label="omega < 0")
    axes[0].plot(x, [row["coupled_core_coverage_percent"] for row in rows], marker="^", label="both")
    axes[0].set(ylabel="core-area coverage (%)", title="Core coverage of convergence, ascent, and their co-location")
    axes[0].legend(); axes[0].grid(alpha=0.25)
    axes[1].plot(x, [row["mfc_centroid_offset_radius"] for row in rows], marker="o", label="MFC centroid")
    axes[1].plot(x, [row["ascent_centroid_offset_radius"] for row in rows], marker="s", label="ascent centroid")
    axes[1].plot(x, [row["mfc_ascent_centroid_separation_radius"] for row in rows], marker="^", label="MFC–ascent separation")
    axes[1].axhline(1.0, color="0.3", ls="--", lw=0.8, label="equivalent core radius")
    axes[1].set(ylabel="offset / equivalent core radius", xlabel="UTC time", title="Intensity-weighted centroid distance from vortex centre")
    axes[1].set_xticks(x[::2]); axes[1].set_xticklabels(labels[::2], rotation=40, ha="right")
    axes[1].legend(); axes[1].grid(alpha=0.25)
    figure.savefig(output_dir / "core_moisture_ascent_coupling_timeseries.png", dpi=200)
    plt.close(figure)
    figure, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True, constrained_layout=True)
    axes[0].plot(x, [row["mfc_positive_mean_s_inv"] * 1e7 for row in rows], marker="o", label="positive-MFC area")
    axes[0].plot(x, [row["coupled_mfc_mean_s_inv"] * 1e7 for row in rows], marker="^", label="coupled area")
    axes[0].set(ylabel="MFC intensity (10^-7 s^-1)", title="Conditional mean intensity within the cold-vortex core")
    axes[0].legend(); axes[0].grid(alpha=0.25)
    axes[1].plot(x, [row["ascent_mean_pa_s_inv"] for row in rows], marker="s", label="ascent area")
    axes[1].plot(x, [row["coupled_ascent_mean_pa_s_inv"] for row in rows], marker="^", label="coupled area")
    axes[1].set(ylabel="ascent magnitude (-omega, Pa s^-1)", xlabel="UTC time")
    axes[1].set_xticks(x[::2]); axes[1].set_xticklabels(labels[::2], rotation=40, ha="right")
    axes[1].legend(); axes[1].grid(alpha=0.25)
    figure.savefig(output_dir / "core_moisture_ascent_intensity_timeseries.png", dpi=200)
    plt.close(figure)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", action="append", choices=EVENTS)
    args = parser.parse_args()
    for selected_event in args.event or list(EVENTS):
        main(selected_event)
