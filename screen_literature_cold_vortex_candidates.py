"""Screen the literature-event library with the common 2.5-degree criteria."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import xarray as xr

from cold_vortex_regions import outermost_closed_contour
from screen_strict_cold_vortex_cases import _candidate_indices


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw" / "cra40"
OUT = ROOT / "data" / "processed" / "cold_vortex" / "literature_candidate_screening"


@dataclass(frozen=True)
class Candidate:
    name: str
    first_day: str
    last_day: str
    literature_event: str


CANDIDATES = (
    Candidate("2005_june_10", "20050607", "20050613", "2005-06-10"),
    Candidate("2005_august_22", "20050819", "20050825", "2005-08-22"),
    Candidate("2015_october_09", "20151006", "20151012", "2015-10-09"),
    Candidate("2017_may_05", "20170502", "20170508", "2017-05-05"),
    Candidate("2018_july_12", "20180709", "20180717", "2018-07-12--14"),
    Candidate("2019_june_28", "20190625", "20190702", "2019-06-28--29"),
    Candidate("2019_july_03", "20190630", "20190706", "2019-07-03"),
    Candidate("2019_july_28", "20190725", "20190801", "2019-07-28--29"),
    Candidate("2019_august_16", "20190813", "20190819", "2019-08-16"),
    Candidate("2020_august_03", "20200731", "20200807", "2020-08-03--04"),
    Candidate("2020_august_12", "20200809", "20200817", "2020-08-12--14"),
    Candidate("2020_september", "20200830", "20200907", "2020-09-02--04"),
    Candidate("2021_june_17", "20210614", "20210622", "2021-06-17--19"),
    Candidate("2021_july_07", "20210704", "20210712", "2021-07-07--09"),
    Candidate("2021_july_13", "20210710", "20210717", "2021-07-13--14"),
    Candidate("2021_july_24", "20210721", "20210729", "2021-07-24--26"),
    Candidate("2021_july_31", "20210728", "20210804", "2021-07-31--08-01"),
    Candidate("2023_june_01", "20230529", "20230604", "2023-06-01"),
)
CANDIDATE_FIELDS = ("candidate", "literature_event", "time_utc", "status", "center_latitude_deg_n", "center_longitude_deg_e", "center_z500_gpm", "strict_closed_40gpm", "outermost_closed_contour_gpm")


def _times(first_day: str, last_day: str) -> list[str]:
    current = datetime.strptime(first_day + "00", "%Y%m%d%H")
    last = datetime.strptime(last_day + "18", "%Y%m%d%H")
    result: list[str] = []
    while current <= last:
        result.append(current.strftime("%Y%m%d%H"))
        current += timedelta(hours=6)
    return result


def _path(variable: str, time_utc: str) -> Path:
    return RAW / time_utc[:4] / time_utc[:8] / f"CRA40_{variable}_{time_utc}_GLB_2P50_HOUR_V1_0_0.grib2"


def _read(variable: str, field: str, time_utc: str) -> xr.DataArray:
    dataset = xr.open_dataset(
        _path(variable, time_utc), engine="cfgrib",
        backend_kwargs={"filter_by_keys": {"typeOfLevel": "isobaricInhPa"}, "indexpath": ""},
    )
    try:
        return dataset[field].load()
    finally:
        dataset.close()


def _summarize_tracks(records: list[dict[str, object]]) -> list[dict[str, object]]:
    """Greedily track strict candidates, allowing one unmatched 6-hour step."""
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    all_times = sorted({str(record["time_utc"]) for record in records})
    for record in records:
        if str(record.get("strict_closed_40gpm", "False")) == "True":
            grouped[str(record["time_utc"])].append(record)
    active: list[dict[str, object]] = []
    completed: list[dict[str, object]] = []
    for time_utc in all_times:
        time = datetime.strptime(time_utc, "%Y%m%d%H")
        candidates = grouped.get(time_utc, [])
        used: set[int] = set()
        continuing: list[dict[str, object]] = []
        for track in active:
            previous = track["records"][-1]
            previous_time = datetime.strptime(str(previous["time_utc"]), "%Y%m%d%H")
            multiplier = (time - previous_time).total_seconds() / (6 * 3600)
            compatible = [
                index for index, item in enumerate(candidates)
                if index not in used
                and abs(float(item["center_longitude_deg_e"]) - float(previous["center_longitude_deg_e"])) <= 5 * multiplier
                and abs(float(item["center_latitude_deg_n"]) - float(previous["center_latitude_deg_n"])) <= 2.5 * multiplier
            ]
            if compatible:
                index = min(compatible, key=lambda value: abs(float(candidates[value]["center_longitude_deg_e"]) - float(previous["center_longitude_deg_e"])) + abs(float(candidates[value]["center_latitude_deg_n"]) - float(previous["center_latitude_deg_n"])))
                track["records"].append(candidates[index])
                track["max_gap_hours"] = max(int(track["max_gap_hours"]), int(multiplier * 6))
                track["unmatched"] = 0
                used.add(index)
                continuing.append(track)
            else:
                track["unmatched"] = int(track["unmatched"]) + 1
                if int(track["unmatched"]) <= 1:
                    continuing.append(track)
                else:
                    completed.append(track)
        for index, candidate in enumerate(candidates):
            if index not in used:
                continuing.append({"records": [candidate], "unmatched": 0, "max_gap_hours": 0})
        active = continuing
    completed.extend(active)
    output: list[dict[str, object]] = []
    for index, track in enumerate(completed, start=1):
        values = track["records"]
        if not values:
            continue
        first, last = values[0], values[-1]
        duration = int((datetime.strptime(str(last["time_utc"]), "%Y%m%d%H") - datetime.strptime(str(first["time_utc"]), "%Y%m%d%H")).total_seconds() / 3600)
        output.append({
            "track_id": f"track_{index:02d}", "start_utc": first["time_utc"], "end_utc": last["time_utc"],
            "recognized_records": len(values), "duration_hours": duration, "max_gap_hours": track["max_gap_hours"],
            "meets_48h_duration": duration >= 48,
            "start_latitude_deg_n": first["center_latitude_deg_n"], "start_longitude_deg_e": first["center_longitude_deg_e"],
            "end_latitude_deg_n": last["center_latitude_deg_n"], "end_longitude_deg_e": last["center_longitude_deg_e"],
        })
    return output


def _write_tracks(candidate: Candidate, records: list[dict[str, object]]) -> int:
    tracks = _summarize_tracks(records)
    for track in tracks:
        track.update({"candidate": candidate.name, "literature_event": candidate.literature_event})
    track_path = OUT / f"{candidate.name}_tracks.csv"
    with track_path.open("w", encoding="utf-8", newline="") as stream:
        fields = ("candidate", "literature_event", "track_id", "start_utc", "end_utc", "recognized_records", "duration_hours", "max_gap_hours", "meets_48h_duration", "start_latitude_deg_n", "start_longitude_deg_e", "end_latitude_deg_n", "end_longitude_deg_e")
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader(); writer.writerows(tracks)
    return sum(bool(item["meets_48h_duration"]) for item in tracks)


def screen(candidate: Candidate) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    for time_utc in _times(candidate.first_day, candidate.last_day):
        paths = [_path(variable, time_utc) for variable in ("GPH", "TEM")]
        if not all(path.exists() for path in paths):
            records.append({"candidate": candidate.name, "literature_event": candidate.literature_event, "time_utc": time_utc, "status": "missing_2p5_input"})
            continue
        gh = _read("GPH", "gh", time_utc)
        temperature = _read("TEM", "t", time_utc)
        latitude, longitude = gh.latitude.values, gh.longitude.values
        z500 = gh.sel(isobaricInhPa=500).values
        locations = _candidate_indices(gh, temperature)
        if not locations:
            records.append({"candidate": candidate.name, "literature_event": candidate.literature_event, "time_utc": time_utc, "status": "no_objective_candidate"})
        for row, column in locations:
            contour = outermost_closed_contour(z500, latitude, longitude, center_latitude=float(latitude[row]), center_longitude=float(longitude[column]))
            records.append({
                "candidate": candidate.name, "literature_event": candidate.literature_event, "time_utc": time_utc, "status": "identified",
                "center_latitude_deg_n": float(latitude[row]), "center_longitude_deg_e": float(longitude[column]),
                "center_z500_gpm": round(float(z500[row, column]), 2), "strict_closed_40gpm": contour is not None,
                "outermost_closed_contour_gpm": "" if contour is None else contour.level_gpm,
            })
    csv_path = OUT / f"{candidate.name}_candidates.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CANDIDATE_FIELDS, extrasaction="ignore")
        writer.writeheader(); writer.writerows(records)
    qualifying = _write_tracks(candidate, records)
    print(candidate.name, f"records={len(records)} qualifying={qualifying}")


def resummarize(candidate: Candidate) -> None:
    with (OUT / f"{candidate.name}_candidates.csv").open(encoding="utf-8", newline="") as stream:
        records = list(csv.DictReader(stream))
    seen = {str(record["time_utc"]) for record in records}
    for time_utc in _times(candidate.first_day, candidate.last_day):
        if time_utc not in seen:
            records.append({"candidate": candidate.name, "literature_event": candidate.literature_event, "time_utc": time_utc, "status": "no_objective_candidate"})
    records.sort(key=lambda item: str(item["time_utc"]))
    with (OUT / f"{candidate.name}_candidates.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CANDIDATE_FIELDS, extrasaction="ignore")
        writer.writeheader(); writer.writerows(records)
    qualifying = _write_tracks(candidate, records)
    print(candidate.name, f"resummarized_records={len(records)} qualifying={qualifying}")


def main(names: list[str], resummarize_only: bool) -> None:
    selected = [item for item in CANDIDATES if not names or item.name in names]
    unknown = set(names) - {item.name for item in CANDIDATES}
    if unknown:
        raise ValueError(f"unknown candidates: {sorted(unknown)}")
    for candidate in selected:
        (resummarize if resummarize_only else screen)(candidate)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", action="append")
    parser.add_argument("--resummarize", action="store_true")
    args = parser.parse_args()
    main(args.candidate or [], args.resummarize)
