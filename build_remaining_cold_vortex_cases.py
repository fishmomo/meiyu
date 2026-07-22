"""Build high-resolution case packages for the remaining literature cold vortices."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
import argparse
import csv

import numpy as np

from cold_vortex_common_data import read_level
from cold_vortex_regions import outermost_closed_contour, polygon_mask, refine_center_to_z500_minimum
from nc_compat import TMP_ROOT


def track_records(records: list[dict[str, str]]) -> list[list[dict[str, str]]]:
    """Track strict 2.5-degree candidates, allowing one missing 6-hour step."""
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for record in records:
        if record.get("strict_closed_40gpm") == "True":
            grouped[record["time_utc"]].append(record)
    active: list[dict[str, object]] = []
    complete: list[list[dict[str, str]]] = []
    for time_utc in sorted({record["time_utc"] for record in records}):
        time = datetime.strptime(time_utc, "%Y%m%d%H")
        candidates = grouped.get(time_utc, [])
        used: set[int] = set(); continuing: list[dict[str, object]] = []
        for track in active:
            previous = track["records"][-1]
            elapsed = (time - datetime.strptime(previous["time_utc"], "%Y%m%d%H")).total_seconds() / 3600
            compatible = [i for i, item in enumerate(candidates) if i not in used and abs(float(item["center_longitude_deg_e"]) - float(previous["center_longitude_deg_e"])) <= 5 * elapsed / 6 and abs(float(item["center_latitude_deg_n"]) - float(previous["center_latitude_deg_n"])) <= 2.5 * elapsed / 6]
            if compatible:
                choice = min(compatible, key=lambda i: abs(float(candidates[i]["center_longitude_deg_e"]) - float(previous["center_longitude_deg_e"])) + abs(float(candidates[i]["center_latitude_deg_n"]) - float(previous["center_latitude_deg_n"])))
                track["records"].append(candidates[choice]); track["misses"] = 0; used.add(choice); continuing.append(track)
            else:
                track["misses"] += 1
                if track["misses"] <= 1:
                    continuing.append(track)
                else:
                    complete.append(track["records"])
        for index, candidate in enumerate(candidates):
            if index not in used:
                continuing.append({"records": [candidate], "misses": 0})
        active = continuing
    complete.extend(track["records"] for track in active)
    return complete


def high_resolution_body(record: dict[str, str]) -> tuple[dict[str, object], np.ndarray | None, np.ndarray, np.ndarray]:
    """Refine one objective center and extract its outermost 40-gpm Z500 body."""
    time_utc = record["time_utc"]
    z500, latitude, longitude = read_level("GPH", time_utc, 500)
    center_lat, center_lon, center_z = refine_center_to_z500_minimum(
        z500, latitude, longitude,
        candidate_latitude=float(record["center_latitude_deg_n"]),
        candidate_longitude=float(record["center_longitude_deg_e"]),
    )
    closed = outermost_closed_contour(z500, latitude, longitude, center_latitude=center_lat, center_longitude=center_lon)
    output = {
        "time_utc": time_utc,
        "objective_center_latitude_deg_n": record["center_latitude_deg_n"],
        "objective_center_longitude_deg_e": record["center_longitude_deg_e"],
        "refined_center_latitude_deg_n": center_lat,
        "refined_center_longitude_deg_e": center_lon,
        "refined_center_z500_gpm": center_z,
        "status": "observed_closed" if closed is not None else "no_high_resolution_closed_body",
        "outermost_closed_contour_gpm": "" if closed is None else closed.level_gpm,
    }
    return output, None if closed is None else polygon_mask(closed.polygon, latitude, longitude), latitude, longitude


def process_package(package: Path) -> None:
    """Write high-resolution closed-body records and masks for one review package."""
    source = package / "track" / "objective_candidate_tracks.csv"
    with source.open(encoding="utf-8", newline="") as stream:
        input_rows = list(csv.DictReader(stream))
    rows: list[dict[str, object]] = []; masks: list[np.ndarray] = []
    latitude = longitude = None
    for input_row in input_rows:
        result, mask, latitude, longitude = high_resolution_body(input_row)
        result.update({"candidate": input_row["candidate"], "track_id": input_row["track_id"], "duration_hours": input_row["duration_hours"]})
        rows.append(result); masks.append(np.zeros_like(latitude, shape=(len(latitude), len(longitude)), dtype=bool) if mask is None else mask)
    output = package / "regions" / "high_resolution_body_records.csv"
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    np.savez_compressed(package / "regions" / "high_resolution_body_masks.npz", time_utc=np.array([row["time_utc"] for row in rows]), candidate=np.array([row["candidate"] for row in rows]), track_id=np.array([row["track_id"] for row in rows]), latitude=latitude, longitude=longitude, core_body=np.stack(masks))
    for path in TMP_ROOT.glob("*"):
        if path.is_file():
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    args = parser.parse_args()
    process_package(args.package)
