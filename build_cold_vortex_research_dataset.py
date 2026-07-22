"""Create the cropped CRA40 research-data batch for tracked cold-vortex events."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from cold_vortex_research_data import build_diagnostic_dataset, build_research_dataset


ROOT = Path(__file__).resolve().parent
TRACKS = ROOT / "data" / "processed" / "cold_vortex" / "event_tracks"
EVENTS = ("2017_august_east", "2021_september", "2021_november")


def main(events: list[str], overwrite: bool, diagnostic_levels: bool) -> None:
    for event in events:
        with (TRACKS / event / "event_track.csv").open(encoding="utf-8", newline="") as stream:
            times = [row["time_utc"] for row in csv.DictReader(stream)]
        for index, time_utc in enumerate(times, start=1):
            build = build_diagnostic_dataset if diagnostic_levels else build_research_dataset
            print(f"{event} {index}/{len(times)} {build(event, time_utc, overwrite=overwrite)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", action="append", choices=EVENTS)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--diagnostic-levels", action="store_true")
    args = parser.parse_args()
    main(args.event or list(EVENTS), args.overwrite, args.diagnostic_levels)
