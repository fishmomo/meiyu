"""Summarize tracked candidates from a completed strict cold-vortex screening."""

from __future__ import annotations

import csv

from screen_strict_cold_vortex_cases import OUT, _track_summaries


SOURCE = OUT / "2017aug_2021sep_2021nov_strict_candidates.csv"
TARGET = OUT / "2017aug_2021sep_2021nov_candidate_tracks.csv"


def main() -> None:
    with SOURCE.open(encoding="utf-8", newline="") as stream:
        records = list(csv.DictReader(stream))
    tracks = _track_summaries(records)
    with TARGET.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(tracks[0]))
        writer.writeheader()
        writer.writerows(tracks)
    qualifying = [track for track in tracks if track["meets_48h_duration"]]
    print(f"tracks={len(tracks)} duration_48h={len(qualifying)} output={TARGET}")


if __name__ == "__main__":
    main()
