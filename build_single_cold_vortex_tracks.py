"""Build one continuous core-body track for each literature cold-vortex case."""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib
import numpy as np
from matplotlib import pyplot as plt

from build_literature_cold_vortex_regions import _cell_area_km2, _read_500
from cold_vortex_regions import refine_center_to_z500_minimum


matplotlib.use("Agg")
ROOT = Path(__file__).resolve().parent
SCREEN = ROOT / "data" / "processed" / "cold_vortex" / "strict_case_screening" / "2017aug_2021sep_2021nov_strict_candidates.csv"
REGIONS = ROOT / "data" / "processed" / "cold_vortex" / "literature_cases" / "circulation_regions"
OUT = ROOT / "data" / "processed" / "cold_vortex" / "event_tracks"
EVENTS = (
    ("2017_august_east", "2017_august", "2017081200", "2017081406", "2017081212", 47.5, 137.5),
    ("2021_september", "2021_september", "2021090800", "2021091118", "2021090818", 50.0, 115.0),
    ("2021_november", "2021_november", "2021110712", "2021111218", "2021110800", 40.0, 120.0),
)


def _times(first: str, last: str) -> list[str]:
    current = datetime.strptime(first, "%Y%m%d%H")
    end = datetime.strptime(last, "%Y%m%d%H")
    output: list[str] = []
    while current <= end:
        output.append(current.strftime("%Y%m%d%H"))
        current += timedelta(hours=6)
    return output


def _load_direct_masks() -> dict[str, dict[str, np.ndarray]]:
    direct: dict[str, dict[str, np.ndarray]] = {}
    for csv_path in REGIONS.glob("*_circulation_regions.csv"):
        npz_path = REGIONS / f"{csv_path.name.removesuffix('_circulation_regions.csv')}_circulation_masks.npz"
        with csv_path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        arrays = dict(np.load(npz_path, allow_pickle=True))
        for row in rows:
            if row["status"] != "complete":
                continue
            index = int(np.flatnonzero(arrays["sample"] == row["sample"])[0])
            direct[row["sample"]] = {
                "body": arrays["closed_circulation_body"][index].astype(bool),
                "latitude": arrays["latitude"], "longitude": arrays["longitude"],
                "center_lat": float(row["refined_center_latitude_deg_n"]),
                "center_lon": float(row["refined_center_longitude_deg_e"]),
                "center_z": float(row["refined_center_z500_gpm"]),
            }
    return direct


def _select_track(rows: list[dict[str, str]], first: str, last: str, seed_time: str, seed_lat: float, seed_lon: float) -> dict[str, dict[str, str]]:
    by_time: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if first <= row["time_utc"] <= last:
            by_time[row["time_utc"]].append(row)
    track: dict[str, dict[str, str]] = {}
    seed = min(by_time[seed_time], key=lambda row: abs(float(row["center_latitude_deg_n"]) - seed_lat) + abs(float(row["center_longitude_deg_e"]) - seed_lon))
    track[seed_time] = seed
    previous = seed
    previous_time = datetime.strptime(seed_time, "%Y%m%d%H")
    unmatched = 0
    for time_utc in _times(seed_time, last)[1:]:
        current_time = datetime.strptime(time_utc, "%Y%m%d%H")
        multiplier = (current_time - previous_time).total_seconds() / (6 * 3600)
        choices = [
            row for row in by_time[time_utc]
            if abs(float(row["center_longitude_deg_e"]) - float(previous["center_longitude_deg_e"])) <= 5 * multiplier
            and abs(float(row["center_latitude_deg_n"]) - float(previous["center_latitude_deg_n"])) <= 2.5 * multiplier
        ]
        if not choices:
            unmatched += 1
            if unmatched >= 2:
                break
            continue
        previous = min(choices, key=lambda row: abs(float(row["center_longitude_deg_e"]) - float(previous["center_longitude_deg_e"])) + abs(float(row["center_latitude_deg_n"]) - float(previous["center_latitude_deg_n"])))
        previous_time = current_time
        unmatched = 0
        track[time_utc] = previous
    previous = seed
    for time_utc in reversed(_times(first, seed_time)[:-1]):
        choices = [row for row in by_time[time_utc] if abs(float(row["center_longitude_deg_e"]) - float(previous["center_longitude_deg_e"])) <= 5 and abs(float(row["center_latitude_deg_n"]) - float(previous["center_latitude_deg_n"])) <= 2.5]
        if not choices:
            break
        previous = min(choices, key=lambda row: abs(float(row["center_longitude_deg_e"]) - float(previous["center_longitude_deg_e"])) + abs(float(row["center_latitude_deg_n"]) - float(previous["center_latitude_deg_n"])))
        track[time_utc] = previous
    return track


def _translate(mask: np.ndarray, lat_shift: int, lon_shift: int) -> np.ndarray:
    output = np.zeros_like(mask, dtype=bool)
    source_rows, source_cols = np.where(mask)
    destination_rows = source_rows - lat_shift  # latitude coordinate is descending
    destination_cols = source_cols + lon_shift
    valid = (destination_rows >= 0) & (destination_rows < mask.shape[0]) & (destination_cols >= 0) & (destination_cols < mask.shape[1])
    output[destination_rows[valid], destination_cols[valid]] = True
    return output


def _phase(index: int, count: int, maturity: int, source: str) -> str:
    if source.startswith("terminal_inherited"):
        return "dissipation"
    if index == 0:
        return "formation"
    if index < maturity:
        return "development"
    if index == maturity:
        return "maturity"
    return "decay"


def _plot(event: str, records: list[dict[str, object]], masks: list[np.ndarray], latitude: np.ndarray, longitude: np.ndarray) -> None:
    columns = 4
    rows = int(np.ceil(len(records) / columns))
    figure, axes = plt.subplots(rows, columns, figsize=(4.1 * columns, 3.6 * rows), constrained_layout=True)
    for axis, record, mask in zip(np.ravel(axes), records, masks):
        style = "--" if str(record["range_source"]).startswith("inherited") else "-"
        color = "#f16913" if style == "--" else "#d7301f"
        axis.contour(longitude, latitude, mask, levels=[0.5], colors=color, linewidths=1.6, linestyles=style)
        axis.plot(float(record["refined_center_longitude_deg_e"]), float(record["refined_center_latitude_deg_n"]), "+", color="black", ms=8, mew=1.3)
        axis.set(xlim=(90, 170), ylim=(20, 70), xlabel="Longitude (°E)", ylabel="Latitude (°N)")
        axis.grid(alpha=0.25, linewidth=0.5)
        axis.set_title(f"{record['time_utc']} | {record['phase']}\n{record['range_source']}", fontsize=8)
    for axis in np.ravel(axes)[len(records):]:
        axis.remove()
    figure.suptitle("Solid red: observed closed body; dashed orange: inherited body; +: tracked center", fontsize=10)
    figure.savefig(OUT / event / "track_body_qc.png", dpi=180)
    plt.close(figure)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with SCREEN.open(encoding="utf-8", newline="") as stream:
        candidates = list(csv.DictReader(stream))
    direct = _load_direct_masks()
    for event, period, first, last, seed_time, seed_lat, seed_lon in EVENTS:
        event_dir = OUT / event; event_dir.mkdir(exist_ok=True)
        selected = _select_track([row for row in candidates if row["period"] == period], first, last, seed_time, seed_lat, seed_lon)
        records: list[dict[str, object]] = []
        masks: list[np.ndarray] = []
        previous: dict[str, object] | None = None
        for time_utc in sorted(selected):
            row = selected[time_utc]
            sample = f"{period}_{time_utc}_{float(row['center_latitude_deg_n']):.2f}N_{float(row['center_longitude_deg_e']):.2f}E"
            item = direct.get(sample)
            if previous is not None:
                previous_time = datetime.strptime(str(previous["time_utc"]), "%Y%m%d%H")
                current_time = datetime.strptime(time_utc, "%Y%m%d%H")
                if current_time - previous_time == timedelta(hours=12) and item is not None:
                    gap_time = (previous_time + timedelta(hours=6)).strftime("%Y%m%d%H")
                    gap_lat = (float(previous["refined_center_latitude_deg_n"]) + float(item["center_lat"])) / 2
                    gap_lon = (float(previous["refined_center_longitude_deg_e"]) + float(item["center_lon"])) / 2
                    gap_z = (float(previous["refined_center_z500_gpm"]) + float(item["center_z"])) / 2
                    lat_shift = round((gap_lat - float(previous["refined_center_latitude_deg_n"])) / 0.25)
                    lon_shift = round((gap_lon - float(previous["refined_center_longitude_deg_e"])) / 0.25)
                    gap_mask = _translate(previous["mask"], lat_shift, lon_shift)
                    gap_record = {
                        "event": event, "time_utc": gap_time,
                        "objective_center_latitude_deg_n": "", "objective_center_longitude_deg_e": "",
                        "refined_center_latitude_deg_n": round(gap_lat, 2), "refined_center_longitude_deg_e": round(gap_lon, 2),
                        "refined_center_z500_gpm": round(gap_z, 2), "range_source": "inherited_interpolated_gap_body",
                        "body_grid_cells_0p25": int(gap_mask.sum()), "mask": gap_mask,
                    }
                    records.append(gap_record); masks.append(gap_mask); previous = gap_record
            if item is not None:
                mask = item["body"]
                center_lat, center_lon, center_z = float(item["center_lat"]), float(item["center_lon"]), float(item["center_z"])
                source = "observed_closed"
            else:
                z500 = _read_500("GPH", "gh", time_utc)
                center_lat, center_lon, center_z = refine_center_to_z500_minimum(z500.values, z500.latitude.values, z500.longitude.values, candidate_latitude=float(row["center_latitude_deg_n"]), candidate_longitude=float(row["center_longitude_deg_e"]))
                if previous is None:
                    raise RuntimeError(f"cannot inherit the first body at {event} {time_utc}")
                lat_shift = round((center_lat - float(previous["refined_center_latitude_deg_n"])) / 0.25)
                lon_shift = round((center_lon - float(previous["refined_center_longitude_deg_e"])) / 0.25)
                mask = _translate(previous["mask"], lat_shift, lon_shift)
                source = "inherited_previous_body"
            record = {
                "event": event, "time_utc": time_utc, "objective_center_latitude_deg_n": row["center_latitude_deg_n"], "objective_center_longitude_deg_e": row["center_longitude_deg_e"],
                "refined_center_latitude_deg_n": round(center_lat, 2), "refined_center_longitude_deg_e": round(center_lon, 2), "refined_center_z500_gpm": round(center_z, 2),
                "range_source": source, "body_grid_cells_0p25": int(mask.sum()),
            }
            record["mask"] = mask
            records.append(record); masks.append(mask); previous = record
        if event == "2021_november" and previous is not None:
            last_time = datetime.strptime(str(previous["time_utc"]), "%Y%m%d%H")
            terminal_time = (last_time + timedelta(hours=6)).strftime("%Y%m%d%H")
            if terminal_time <= last:
                terminal_mask = previous["mask"].copy()
                terminal_record = {
                    "event": event, "time_utc": terminal_time,
                    "objective_center_latitude_deg_n": "", "objective_center_longitude_deg_e": "",
                    "refined_center_latitude_deg_n": previous["refined_center_latitude_deg_n"], "refined_center_longitude_deg_e": previous["refined_center_longitude_deg_e"],
                    "refined_center_z500_gpm": previous["refined_center_z500_gpm"], "range_source": "terminal_inherited_previous_body_no_center",
                    "body_grid_cells_0p25": int(terminal_mask.sum()), "mask": terminal_mask,
                }
                records.append(terminal_record); masks.append(terminal_mask)
        observed_indices = [index for index, record in enumerate(records) if record["range_source"] == "observed_closed"]
        maturity = min(observed_indices, key=lambda index: float(records[index]["refined_center_z500_gpm"]))
        area = _cell_area_km2(direct[next(iter(direct))]["latitude"], direct[next(iter(direct))]["longitude"])
        for index, record in enumerate(records):
            record["phase"] = _phase(index, len(records), maturity, str(record["range_source"]))
            record["body_area_km2_approx"] = round(float(np.broadcast_to(area, record["mask"].shape)[record["mask"]].sum()), 1)
            del record["mask"]
        with (event_dir / "event_track.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)
        np.savez_compressed(event_dir / "event_track_core_masks.npz", time_utc=np.array([record["time_utc"] for record in records]), range_source=np.array([record["range_source"] for record in records]), phase=np.array([record["phase"] for record in records]), latitude=direct[next(iter(direct))]["latitude"], longitude=direct[next(iter(direct))]["longitude"], core_body=np.stack(masks))
        _plot(event, records, masks, direct[next(iter(direct))]["latitude"], direct[next(iter(direct))]["longitude"])


if __name__ == "__main__":
    main()
