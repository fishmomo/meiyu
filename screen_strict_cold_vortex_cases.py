"""Screen downloaded CRA40 periods for objectively identified closed NCCVs."""

from __future__ import annotations

import csv
from collections import defaultdict
import argparse
from pathlib import Path

import numpy as np
import xarray as xr

from cold_vortex_regions import outermost_closed_contour


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw" / "cra40"
OUT = ROOT / "data" / "processed" / "cold_vortex" / "strict_case_screening"
PERIODS = (
    ("2017_august", "20170810", "20170816"),
    ("2021_september", "20210906", "20210913"),
    ("2021_november", "20211105", "20211112"),
)


def _file(variable: str, time_utc: str) -> Path:
    name = f"CRA40_{variable}_{time_utc}_GLB_2P50_HOUR_V1_0_0.grib2"
    matches = sorted(RAW.glob(f"{time_utc[:4]}/{time_utc[:8]}/{name}"))
    if len(matches) != 1:
        raise RuntimeError(f"missing or duplicate {name}: {matches}")
    return matches[0]


def _field(variable: str, field: str, time_utc: str) -> xr.DataArray:
    dataset = xr.open_dataset(
        _file(variable, time_utc),
        engine="cfgrib",
        backend_kwargs={"filter_by_keys": {"typeOfLevel": "isobaricInhPa"}, "indexpath": ""},
    )
    return dataset[field].load()


def _candidate_indices(gh: xr.DataArray, temperature: xr.DataArray) -> list[tuple[int, int]]:
    latitude = gh.latitude.values
    longitude = gh.longitude.values
    z500 = gh.sel(isobaricInhPa=500).values
    thickness = gh.sel(isobaricInhPa=400).values - gh.sel(isobaricInhPa=850).values
    t500 = temperature.sel(isobaricInhPa=500).values
    candidates: list[tuple[int, int]] = []
    for row in range(1, len(latitude) - 1):
        if not 35.0 <= latitude[row] <= 60.0:
            continue
        for column in range(1, len(longitude) - 1):
            if not 115.0 <= longitude[column] <= 145.0:
                continue
            neighborhood = z500[row - 1 : row + 2, column - 1 : column + 2]
            if not np.all(z500[row, column] < np.delete(neighborhood.ravel(), 4)):
                continue
            if not np.any(thickness[row - 1 : row + 2, column - 1 : column + 2] > thickness[row, column]):
                continue
            temperature_window = t500[row - 1 : row + 2, column - 1 : column + 2]
            if not np.any(temperature_window[:, 2] - 2 * temperature_window[:, 1] + temperature_window[:, 0] > 0):
                continue
            candidates.append((row, column))
    candidates.sort(key=lambda location: z500[location])
    kept: list[tuple[int, int]] = []
    for row, column in candidates:
        if all(abs(row - old_row) > 2 or abs(column - old_column) > 2 for old_row, old_column in kept):
            kept.append((row, column))
    return kept


def _track_summaries(records: list[dict[str, object]]) -> list[dict[str, object]]:
    """Track consecutive 6-hour candidates with the published displacement limits."""
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in records:
        grouped[str(record["period"])].append(record)

    summaries: list[dict[str, object]] = []
    for period, period_records in grouped.items():
        by_time: dict[str, list[dict[str, object]]] = defaultdict(list)
        for record in period_records:
            by_time[str(record["time_utc"])].append(record)
        active: list[list[dict[str, object]]] = []
        tracks: list[list[dict[str, object]]] = []
        for time_utc in sorted(by_time):
            candidates = by_time[time_utc]
            used: set[int] = set()
            continuing: list[list[dict[str, object]]] = []
            for track in active:
                previous = track[-1]
                compatible = [
                    index
                    for index, candidate in enumerate(candidates)
                    if index not in used
                    and abs(float(candidate["center_longitude_deg_e"]) - float(previous["center_longitude_deg_e"])) <= 5.0
                    and abs(float(candidate["center_latitude_deg_n"]) - float(previous["center_latitude_deg_n"])) <= 2.5
                ]
                if not compatible:
                    tracks.append(track)
                    continue
                index = min(
                    compatible,
                    key=lambda item: (
                        abs(float(candidates[item]["center_longitude_deg_e"]) - float(previous["center_longitude_deg_e"]))
                        + abs(float(candidates[item]["center_latitude_deg_n"]) - float(previous["center_latitude_deg_n"]))
                    ),
                )
                track.append(candidates[index])
                used.add(index)
                continuing.append(track)
            active = continuing + [[candidate] for index, candidate in enumerate(candidates) if index not in used]
        tracks.extend(active)

        for sequence, track in enumerate(tracks, start=1):
            start = track[0]
            end = track[-1]
            duration_hours = (len(track) - 1) * 6
            summaries.append(
                {
                    "period": period,
                    "track_id": f"{period}_{sequence:02d}",
                    "start_utc": start["time_utc"],
                    "end_utc": end["time_utc"],
                    "continuous_6h_records": len(track),
                    "duration_hours": duration_hours,
                    "meets_48h_duration": duration_hours >= 48,
                    "start_latitude_deg_n": start["center_latitude_deg_n"],
                    "start_longitude_deg_e": start["center_longitude_deg_e"],
                    "end_latitude_deg_n": end["center_latitude_deg_n"],
                    "end_longitude_deg_e": end["center_longitude_deg_e"],
                    "any_strict_closed_40gpm": any(
                        str(item["strict_closed_40gpm"]).lower() == "true" for item in track
                    ),
                }
            )
    return summaries


def _day(value: str) -> np.datetime64:
    if len(value) != 8 or not value.isdigit():
        raise ValueError(f"day must use YYYYMMDD: {value}")
    return np.datetime64(f"{value[:4]}-{value[4:6]}-{value[6:]}")


def main(first_day_override: str | None = None, last_day_override: str | None = None, reset: bool = False) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "2017aug_2021sep_2021nov_strict_candidates.csv"
    records_by_key: dict[tuple[str, str, float, float], dict[str, object]] = {}
    if target.exists() and not reset:
        with target.open(encoding="utf-8", newline="") as stream:
            for record in csv.DictReader(stream):
                key = (
                    record["period"],
                    record["time_utc"],
                    float(record["center_latitude_deg_n"]),
                    float(record["center_longitude_deg_e"]),
                )
                records_by_key[key] = record
    requested_first = _day(first_day_override) if first_day_override else None
    requested_last = _day(last_day_override) if last_day_override else None
    for period, first_day, last_day in PERIODS:
        day = np.datetime64(f"{first_day[:4]}-{first_day[4:6]}-{first_day[6:]}" )
        end = np.datetime64(f"{last_day[:4]}-{last_day[4:6]}-{last_day[6:]}" )
        if requested_first is not None:
            day = max(day, requested_first)
        if requested_last is not None:
            end = min(end, requested_last)
        while day <= end:
            day_text = str(day).replace("-", "")
            for hour in ("00", "06", "12", "18"):
                time_utc = f"{day_text}{hour}"
                gh = _field("GPH", "gh", time_utc)
                temperature = _field("TEM", "t", time_utc)
                latitude = gh.latitude.values
                longitude = gh.longitude.values
                z500 = gh.sel(isobaricInhPa=500).values
                for row, column in _candidate_indices(gh, temperature):
                    contour = outermost_closed_contour(
                        z500,
                        latitude,
                        longitude,
                        center_latitude=float(latitude[row]),
                        center_longitude=float(longitude[column]),
                    )
                    record = {
                        "period": period,
                        "time_utc": time_utc,
                        "center_latitude_deg_n": float(latitude[row]),
                        "center_longitude_deg_e": float(longitude[column]),
                        "center_z500_gpm": round(float(z500[row, column]), 2),
                        "strict_closed_40gpm": contour is not None,
                        "outermost_closed_contour_gpm": "" if contour is None else contour.level_gpm,
                    }
                    records_by_key[(period, time_utc, float(latitude[row]), float(longitude[column]))] = record
            day += np.timedelta64(1, "D")
    records = sorted(records_by_key.values(), key=lambda item: (str(item["period"]), str(item["time_utc"])))
    with target.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    tracks = _track_summaries(records)
    track_target = OUT / "2017aug_2021sep_2021nov_candidate_tracks.csv"
    with track_target.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(tracks[0]))
        writer.writeheader()
        writer.writerows(tracks)
    strict = [record for record in records if record["strict_closed_40gpm"]]
    qualifying = [track for track in tracks if track["meets_48h_duration"]]
    print(
        f"candidates={len(records)} strict_closed={len(strict)} "
        f"tracks={len(tracks)} duration_48h={len(qualifying)} output={target}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--first-day")
    parser.add_argument("--last-day")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    main(args.first_day, args.last_day, args.reset)
