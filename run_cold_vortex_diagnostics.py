"""Generate first-pass circulation, moisture, and thermodynamic diagnostics.

The calculation is deliberately limited to fields already downloaded for the
three tracked cold-vortex cases.  It does not calculate cloud-water resources,
precipitation budgets, or surface evaporation.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib
import numpy as np
import xarray as xr
from matplotlib import pyplot as plt

from build_literature_cold_vortex_regions import _cell_area_km2
from cold_vortex_diagnostics import core_summary, moisture_flux_convergence
from cold_vortex_regions import relative_vorticity
from cold_vortex_research_data import diagnostic_dataset_path, read_level, research_dataset_path


matplotlib.use("Agg")
ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw" / "cra40"
TRACKS = ROOT / "data" / "processed" / "cold_vortex" / "event_tracks"
OUT = ROOT / "data" / "processed" / "cold_vortex" / "event_diagnostics"
DOMAIN = {"latitude": slice(70.0, 20.0), "longitude": slice(90.0, 170.0)}
FIELD_NAMES = {"GPH": "gh", "WIU": "u", "WIV": "v", "VVP": "w", "RHU": "r", "SHU": "q", "TEM": "t"}


def cropped_dataset_path(data_root: Path, event: str, time_utc: str) -> Path | None:
    """Return the preferred existing full or diagnostic-level cropped dataset."""
    full = research_dataset_path(data_root, event, time_utc)
    if full.exists():
        return full
    diagnostic = diagnostic_dataset_path(data_root, event, time_utc)
    return diagnostic if diagnostic.exists() else None


def _path(variable: str, time_utc: str) -> Path:
    name = f"CRA40_{variable}_{time_utc}_GLB_0P25_HOUR_V1_0_0.grib2"
    matches = list(RAW.glob(f"{time_utc[:4]}/{time_utc[:8]}/{name}"))
    if len(matches) != 1:
        raise RuntimeError(f"expected one {name}, found {matches}")
    return matches[0]


def _read_level(event: str, variable: str, time_utc: str, level_hpa: int) -> xr.DataArray:
    data_file = cropped_dataset_path(ROOT / "data" / "derived" / "cra40_cold_vortex_90E170E_20N70N", event, time_utc)
    if data_file is not None:
        values, latitude, longitude = read_level(event, time_utc, FIELD_NAMES[variable], level_hpa)
        return xr.DataArray(values, coords={"latitude": latitude, "longitude": longitude}, dims=("latitude", "longitude"))
    dataset = xr.open_dataset(
        _path(variable, time_utc), engine="cfgrib",
        backend_kwargs={"filter_by_keys": {"typeOfLevel": "isobaricInhPa"}, "indexpath": ""},
    )
    return dataset[FIELD_NAMES[variable]].sel(isobaricInhPa=level_hpa, **DOMAIN).load()


def _load_track(event: str) -> tuple[list[dict[str, str]], dict[str, np.ndarray]]:
    event_dir = TRACKS / event
    with (event_dir / "event_track.csv").open(encoding="utf-8", newline="") as stream:
        records = list(csv.DictReader(stream))
    masks = dict(np.load(event_dir / "event_track_core_masks.npz", allow_pickle=True))
    if [row["time_utc"] for row in records] != list(masks["time_utc"]):
        raise ValueError(f"{event}: CSV and core-mask times differ")
    return records, masks


def _fields_at_time(event: str, time_utc: str) -> tuple[dict[str, np.ndarray], np.ndarray, np.ndarray]:
    z500 = _read_level(event, "GPH", time_utc, 500)
    u500 = _read_level(event, "WIU", time_utc, 500)
    v500 = _read_level(event, "WIV", time_utc, 500)
    u850 = _read_level(event, "WIU", time_utc, 850)
    v850 = _read_level(event, "WIV", time_utc, 850)
    q850 = _read_level(event, "SHU", time_utc, 850)
    rh850 = _read_level(event, "RHU", time_utc, 850)
    rh500 = _read_level(event, "RHU", time_utc, 500)
    t850 = _read_level(event, "TEM", time_utc, 850)
    t500 = _read_level(event, "TEM", time_utc, 500)
    w700 = _read_level(event, "VVP", time_utc, 700)
    latitude, longitude = z500.latitude.values, z500.longitude.values
    return {
        "z500_gpm": z500.values,
        "vorticity500_s_inv": relative_vorticity(u500.values, v500.values, latitude, longitude),
        "wind850_m_s": np.hypot(u850.values, v850.values),
        "q850_kg_kg": q850.values,
        "mfc850_kg_kg_m_s_inv": moisture_flux_convergence(
            specific_humidity=q850.values, u=u850.values, v=v850.values,
            latitude=latitude, longitude=longitude,
        ),
        "w700_pa_s": w700.values,
        "rh850_percent": rh850.values,
        "rh500_percent": rh500.values,
        "t850_minus_t500_k": t850.values - t500.values,
    }, latitude, longitude


def _write_timeseries(event: str, records: list[dict[str, float | str]], output_dir: Path) -> Path:
    metrics = (
        ("refined_center_z500_gpm", "Tracked centre Z500 (gpm)"),
        ("core_area_km2", "Core area (10^6 km^2)"),
        ("vorticity500_s_inv", "Core mean zeta500 (10^-5 s^-1)"),
    )
    scale = {"vorticity500_s_inv": 1e5, "core_area_km2": 1e-6}
    figure, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True, constrained_layout=True)
    x = np.arange(len(records))
    labels = [str(row["time_utc"])[4:] for row in records]
    phases = [str(row["phase"]) for row in records]
    for axis, (field, label) in zip(axes.ravel(), metrics):
        values = np.array([float(row[field]) for row in records]) * scale.get(field, 1.0)
        axis.plot(x, values, marker="o", ms=3, color="#2166ac")
        for index, phase in enumerate(phases):
            if phase == "maturity":
                axis.axvline(index, color="#b2182b", lw=1.0, ls="--")
        axis.set_ylabel(label, fontsize=8)
        axis.grid(alpha=0.25)
    axes[-1].set_xticks(x[::max(1, len(x) // 8)])
    axes[-1].set_xticklabels(labels[::max(1, len(x) // 8)], rotation=40, ha="right", fontsize=8)
    figure.suptitle(f"{event}: moving cold-vortex core evolution; dashed red = preliminary maturity", fontsize=11)
    path = output_dir / "core_evolution_timeseries.png"
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return path


def _write_phase_maps(event: str, records: list[dict[str, float | str]], masks: dict[str, np.ndarray], fields: dict[str, dict[str, np.ndarray]], output_dir: Path) -> Path:
    selected = [0, next(index for index, row in enumerate(records) if row["phase"] == "maturity"), len(records) - 1]
    figure, axes = plt.subplots(3, 2, figsize=(12, 12), constrained_layout=True)
    longitude, latitude = masks["longitude"], masks["latitude"]
    for row_index, index in enumerate(selected):
        record = records[index]; values = fields[str(record["time_utc"])]
        for column, (field, title, cmap, scale) in enumerate((
            ("mfc850_kg_kg_m_s_inv", "850 hPa moisture-flux convergence", "BrBG", 1e7),
            ("w700_pa_s", "700 hPa omega", "PuOr_r", 1.0),
        )):
            axis = axes[row_index, column]
            data = values[field] * scale
            finite = data[np.isfinite(data)]
            limit = np.nanpercentile(np.abs(finite), 98) if finite.size else 1.0
            image = axis.contourf(longitude, latitude, data, levels=np.linspace(-limit, limit, 17), cmap=cmap, extend="both")
            axis.contour(longitude, latitude, values["z500_gpm"], colors="0.25", linewidths=0.45, levels=10)
            axis.contour(longitude, latitude, masks["core_body"][index], levels=[0.5], colors="#d7301f", linewidths=1.5)
            axis.plot(float(record["refined_center_longitude_deg_e"]), float(record["refined_center_latitude_deg_n"]), "+", color="black", ms=8, mew=1.4)
            axis.set(xlim=(90, 170), ylim=(20, 70), xlabel="Longitude (E)", ylabel="Latitude (N)")
            axis.set_title(f"{record['time_utc']} | {record['phase']} | {title}", fontsize=8)
            figure.colorbar(image, ax=axis, shrink=0.82)
    figure.suptitle("Red boundary: tracked cold-vortex core; black contours: Z500", fontsize=10)
    path = output_dir / "formation_maturity_terminal_structure.png"
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return path


def run_event(event: str) -> list[Path]:
    track, masks = _load_track(event)
    output_dir = OUT / event; output_dir.mkdir(parents=True, exist_ok=True)
    cell_area = np.broadcast_to(_cell_area_km2(masks["latitude"], masks["longitude"]), masks["core_body"][0].shape)
    records: list[dict[str, float | str]] = []
    fields_by_time: dict[str, dict[str, np.ndarray]] = {}
    for index, track_row in enumerate(track):
        time_utc = track_row["time_utc"]
        fields, latitude, longitude = _fields_at_time(event, time_utc)
        if not np.array_equal(latitude, masks["latitude"]) or not np.array_equal(longitude, masks["longitude"]):
            raise ValueError(f"{event} {time_utc}: CRA40 grid differs from the saved track mask")
        summary = core_summary(core_mask=masks["core_body"][index], cell_area_km2=cell_area, fields=fields)
        records.append({
            "event": event, "time_utc": time_utc, "phase": track_row["phase"], "range_source": track_row["range_source"],
            "refined_center_latitude_deg_n": track_row["refined_center_latitude_deg_n"], "refined_center_longitude_deg_e": track_row["refined_center_longitude_deg_e"],
            "refined_center_z500_gpm": track_row["refined_center_z500_gpm"], **summary,
        })
        fields_by_time[time_utc] = fields
    csv_path = output_dir / "core_diagnostics_timeseries.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)
    return [csv_path, _write_timeseries(event, records, output_dir), _write_phase_maps(event, records, masks, fields_by_time, output_dir)]


def main(events: list[str]) -> None:
    for event in events:
        outputs = run_event(event)
        print(event, *outputs, sep="\n  ")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", action="append", choices=("2017_august_east", "2021_september", "2021_november"))
    args = parser.parse_args()
    main(args.event or ["2017_august_east", "2021_september", "2021_november"])
