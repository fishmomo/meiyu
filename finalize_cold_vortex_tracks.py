"""Turn high-resolution candidate bodies into continuous independent events.

The implementation follows the agreed three-level rule: short (<=12 h)
closure gaps inherit a translated neighbouring body when the closed share is
at least 80%; longer/poorly closed gaps use a compact moving core window; and
each event receives one additional 6-hour terminal diagnostic time.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from scipy import ndimage


TIME_FORMAT = "%Y%m%d%H"


def _time(value: str) -> datetime:
    return datetime.strptime(value, TIME_FORMAT)


def _timestamp(value: datetime) -> str:
    return value.strftime(TIME_FORMAT)


def _center(row: dict[str, str]) -> tuple[float, float]:
    return float(row["refined_center_latitude_deg_n"]), float(row["refined_center_longitude_deg_e"])


def _contained_duplicate(first: list[dict[str, str]], second: list[dict[str, str]]) -> bool:
    """Whether every time in the shorter track has the same high-res center."""
    shorter, longer = (first, second) if len(first) <= len(second) else (second, first)
    lookup = {row["time_utc"]: row for row in longer}
    if not all(row["time_utc"] in lookup for row in shorter):
        return False
    return all(
        abs(_center(row)[0] - _center(lookup[row["time_utc"]])[0]) <= 0.26
        and abs(_center(row)[1] - _center(lookup[row["time_utc"]])[1]) <= 0.26
        for row in shorter
    )


def independent_tracks(rows: list[dict[str, str]]) -> list[list[dict[str, str]]]:
    """Split spatially distinct tracks and remove contained duplicate tracks."""
    tracks = [sorted(group, key=lambda row: row["time_utc"]) for _, group in _group_rows(rows).items()]
    retained: list[list[dict[str, str]]] = []
    for track in tracks:
        if any(_contained_duplicate(track, other) and len(track) < len(other) for other in tracks):
            continue
        retained.append(track)
    return sorted(retained, key=lambda track: (track[0]["time_utc"], track[0]["track_id"]))


def _group_rows(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["track_id"], []).append(row)
    return grouped


def _translate_mask(mask: np.ndarray, source: tuple[float, float], target: tuple[float, float], latitude: np.ndarray, longitude: np.ndarray) -> np.ndarray:
    lat_step = float(np.abs(np.diff(latitude)).mean())
    lon_step = float(np.abs(np.diff(longitude)).mean())
    shift = ((source[0] - target[0]) / lat_step, (target[1] - source[1]) / lon_step)
    return ndimage.shift(mask.astype(float), shift=shift, order=0, mode="constant", cval=0.0, prefilter=False) >= 0.5


def _fixed_core(center: tuple[float, float], latitude: np.ndarray, longitude: np.ndarray, half_width_deg: float = 2.0) -> np.ndarray:
    return (np.abs(latitude[:, None] - center[0]) <= half_width_deg) & (np.abs(longitude[None, :] - center[1]) <= half_width_deg)


def continuous_event(track: list[dict[str, str]], masks: dict[tuple[str, str], np.ndarray], latitude: np.ndarray, longitude: np.ndarray, event_id: str) -> tuple[list[dict[str, object]], list[np.ndarray]]:
    """Apply the three-level closure rule to one independent candidate track."""
    by_time = {row["time_utc"]: row for row in track}
    start, end = _time(track[0]["time_utc"]), _time(track[-1]["time_utc"])
    times = [_timestamp(start + timedelta(hours=6 * index)) for index in range(int((end - start).total_seconds() // 21600) + 1)]
    closed_share = sum(row["status"] == "observed_closed" for row in track) / len(track)
    missing = [stamp for stamp in times if stamp not in by_time or by_time[stamp]["status"] != "observed_closed"]
    # Evaluate each *continuous* missing segment separately.  Several isolated
    # one-step gaps must not be treated as one long gap.
    missing_run_length: dict[str, int] = {}
    index = 0
    while index < len(times):
        if times[index] not in missing:
            index += 1
            continue
        end_index = index
        while end_index + 1 < len(times) and times[end_index + 1] in missing:
            end_index += 1
        for gap_time in times[index : end_index + 1]:
            missing_run_length[gap_time] = end_index - index + 1
        index = end_index + 1
    output: list[dict[str, object]] = []
    output_masks: list[np.ndarray] = []
    observed_times = [stamp for stamp in times if stamp in by_time and by_time[stamp]["status"] == "observed_closed"]

    def position(stamp: str) -> tuple[float, float]:
        if stamp in by_time:
            return _center(by_time[stamp])
        before = max((candidate for candidate in by_time if candidate < stamp), default=None)
        after = min((candidate for candidate in by_time if candidate > stamp), default=None)
        if before and after:
            fraction = (_time(stamp) - _time(before)).total_seconds() / (_time(after) - _time(before)).total_seconds()
            a, b = _center(by_time[before]), _center(by_time[after])
            return a[0] + fraction * (b[0] - a[0]), a[1] + fraction * (b[1] - a[1])
        return _center(by_time[before or after])

    for stamp in times:
        center = position(stamp)
        row = by_time.get(stamp)
        if row is not None and row["status"] == "observed_closed":
            mask = masks[(row["track_id"], stamp)]
            method = "observed_closed"
        elif closed_share >= 0.8 and missing_run_length[stamp] <= 2:
            source_stamp = min(observed_times, key=lambda candidate: abs(_time(candidate) - _time(stamp)))
            source_row = by_time[source_stamp]
            mask = _translate_mask(masks[(source_row["track_id"], source_stamp)], _center(source_row), center, latitude, longitude)
            method = "inherited_translated" if row is not None else "interpolated_inherited"
        else:
            mask = _fixed_core(center, latitude, longitude)
            method = "fixed_core_window"
        source = row or {}
        output.append({
            "event_id": event_id, "time_utc": stamp, "region_method": method,
            "refined_center_latitude_deg_n": center[0], "refined_center_longitude_deg_e": center[1],
            "refined_center_z500_gpm": source.get("refined_center_z500_gpm", ""),
            "outermost_closed_contour_gpm": source.get("outermost_closed_contour_gpm", ""),
            "is_terminal_diagnostic": False,
        })
        output_masks.append(mask)

    last_center = position(times[-1])
    if len(times) > 1:
        prior_center = position(times[-2])
        terminal_center = (last_center[0] + last_center[0] - prior_center[0], last_center[1] + last_center[1] - prior_center[1])
    else:
        terminal_center = last_center
    final_mask = output_masks[-1]
    terminal_mask = _translate_mask(final_mask, last_center, terminal_center, latitude, longitude)
    output.append({
        "event_id": event_id, "time_utc": _timestamp(_time(times[-1]) + timedelta(hours=6)),
        "region_method": "terminal_inherited_translated", "refined_center_latitude_deg_n": terminal_center[0],
        "refined_center_longitude_deg_e": terminal_center[1], "refined_center_z500_gpm": "",
        "outermost_closed_contour_gpm": "", "is_terminal_diagnostic": True,
    })
    output_masks.append(terminal_mask)
    return output, output_masks


def finalize_package(package: Path) -> None:
    """Write independent-event inventory plus continuous body records/masks."""
    region_dir = package / "regions"
    with (region_dir / "high_resolution_body_records.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    archive = np.load(region_dir / "high_resolution_body_masks.npz")
    latitude, longitude = archive["latitude"], archive["longitude"]
    stored_masks = {
        (track_id, stamp): mask
        for track_id, stamp, mask in zip(archive["track_id"].astype(str), archive["time_utc"].astype(str), archive["core_body"])
    }
    event_rows: list[dict[str, object]] = []
    event_masks: list[np.ndarray] = []
    inventory: list[dict[str, object]] = []
    for number, track in enumerate(independent_tracks(rows), start=1):
        event_id = f"{package.name}_event_{number:02d}"
        records, masks = continuous_event(track, stored_masks, latitude, longitude, event_id)
        event_rows.extend(records); event_masks.extend(masks)
        inventory.append({"event_id": event_id, "source_track_id": track[0]["track_id"], "start_utc": records[0]["time_utc"], "end_utc": records[-1]["time_utc"], "recognized_records": len(track), "continuous_records": len(records), "closed_body_records": sum(row["status"] == "observed_closed" for row in track)})
    with (package / "track" / "independent_events.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(inventory[0])); writer.writeheader(); writer.writerows(inventory)
    with (region_dir / "continuous_body_records.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(event_rows[0])); writer.writeheader(); writer.writerows(event_rows)
    np.savez_compressed(region_dir / "continuous_body_masks.npz", event_id=np.array([row["event_id"] for row in event_rows]), time_utc=np.array([row["time_utc"] for row in event_rows]), latitude=latitude, longitude=longitude, core_body=np.stack(event_masks))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    finalize_package(parser.parse_args().package)
