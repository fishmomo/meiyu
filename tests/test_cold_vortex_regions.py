import unittest

import numpy as np


def test_november_track_window_includes_extended_download_period():
    from build_single_cold_vortex_tracks import EVENTS

    events = {name: (first, last) for name, _, first, last, *_ in EVENTS}

    assert events["2021_november"] == ("2021110712", "2021111218")


def test_track_selection_recovers_after_one_unmatched_time_step():
    from build_single_cold_vortex_tracks import _select_track

    rows = [
        {"time_utc": "2021111012", "center_latitude_deg_n": "42.5", "center_longitude_deg_e": "132.5"},
        {"time_utc": "2021111018", "center_latitude_deg_n": "50.0", "center_longitude_deg_e": "137.5"},
        {"time_utc": "2021111100", "center_latitude_deg_n": "45.0", "center_longitude_deg_e": "137.5"},
    ]

    track = _select_track(rows, "2021111012", "2021111100", "2021111012", 42.5, 132.5)

    assert list(sorted(track)) == ["2021111012", "2021111100"]


def test_literature_candidate_library_has_eighteen_new_candidates():
    from screen_literature_cold_vortex_candidates import CANDIDATES

    assert len(CANDIDATES) == 18
    assert {item.name for item in CANDIDATES} >= {"2005_june_10", "2020_september", "2023_june_01"}


def test_candidate_track_summary_ignores_missing_input_records():
    from screen_literature_cold_vortex_candidates import _summarize_tracks

    assert _summarize_tracks([{"time_utc": "2005081900", "status": "missing_2p5_input"}]) == []


def test_candidate_track_summary_stops_after_two_unmatched_steps():
    from screen_literature_cold_vortex_candidates import _summarize_tracks

    records = [
        {"time_utc": "2005081900", "strict_closed_40gpm": True, "center_latitude_deg_n": 50.0, "center_longitude_deg_e": 120.0},
        {"time_utc": "2005081906", "status": "identified", "strict_closed_40gpm": False},
        {"time_utc": "2005081912", "status": "identified", "strict_closed_40gpm": False},
        {"time_utc": "2005081918", "strict_closed_40gpm": True, "center_latitude_deg_n": 50.0, "center_longitude_deg_e": 120.0},
    ]

    tracks = _summarize_tracks(records)

    assert len(tracks) == 2
    assert {track["duration_hours"] for track in tracks} == {0}


def test_candidate_resummary_inserts_no_candidate_time_steps(tmp_path, monkeypatch):
    import csv
    import screen_literature_cold_vortex_candidates as module

    candidate = module.Candidate("test_case", "20050819", "20050819", "test")
    monkeypatch.setattr(module, "OUT", tmp_path)
    with (tmp_path / "test_case_candidates.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("candidate", "literature_event", "time_utc", "status", "center_latitude_deg_n", "center_longitude_deg_e", "strict_closed_40gpm"))
        writer.writeheader()
        writer.writerows([
            {"candidate": "test_case", "literature_event": "test", "time_utc": "2005081900", "status": "identified", "center_latitude_deg_n": 50, "center_longitude_deg_e": 120, "strict_closed_40gpm": True},
            {"candidate": "test_case", "literature_event": "test", "time_utc": "2005081918", "status": "identified", "center_latitude_deg_n": 50, "center_longitude_deg_e": 120, "strict_closed_40gpm": True},
        ])

    module.resummarize(candidate)

    tracks = list(csv.DictReader((tmp_path / "test_case_tracks.csv").open(encoding="utf-8")))
    assert len(tracks) == 2
from shapely.geometry import Point, Polygon


class ColdVortexRegionTest(unittest.TestCase):
    def test_outermost_closed_contour_handles_multiple_paths_at_one_level(self) -> None:
        from cold_vortex_regions import outermost_closed_contour

        latitude = np.linspace(40.0, 50.0, 101)
        longitude = np.linspace(110.0, 120.0, 101)
        lon2d, lat2d = np.meshgrid(longitude, latitude)
        west_low = 5200.0 + 16.0 * ((lon2d - 112.5) ** 2 + (lat2d - 45.0) ** 2)
        east_low = 5200.0 + 16.0 * ((lon2d - 117.5) ** 2 + (lat2d - 45.0) ** 2)
        z500 = np.minimum(west_low, east_low)

        result = outermost_closed_contour(
            z500, latitude, longitude, center_latitude=45.0, center_longitude=112.5
        )

        self.assertIsNotNone(result)
        self.assertTrue(result.polygon.covers(Point(112.5, 45.0)))

    def test_outermost_closed_contour_encloses_center_at_highest_valid_level(self) -> None:
        from cold_vortex_regions import outermost_closed_contour

        latitude = np.linspace(40.0, 50.0, 101)
        longitude = np.linspace(110.0, 120.0, 101)
        lon2d, lat2d = np.meshgrid(longitude, latitude)
        z500 = 5200.0 + 16.0 * ((lon2d - 115.0) ** 2 + (lat2d - 45.0) ** 2)

        result = outermost_closed_contour(
            z500, latitude, longitude, center_latitude=45.0, center_longitude=115.0
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.level_gpm, 5560.0)
        self.assertTrue(result.polygon.covers(Point(115.0, 45.0)))

    def test_connected_positive_vorticity_keeps_only_component_touching_body(self) -> None:
        from cold_vortex_regions import connected_positive_vorticity_mask

        latitude = np.arange(5.0)
        longitude = np.arange(5.0)
        body = Polygon([(1.4, 1.4), (2.6, 1.4), (2.6, 2.6), (1.4, 2.6)])
        vorticity = np.zeros((5, 5), dtype=float)
        vorticity[1:4, 0:3] = 1.0
        vorticity[0, 4] = 1.0

        peripheral = connected_positive_vorticity_mask(
            vorticity, latitude, longitude, body
        )

        self.assertTrue(peripheral[1, 1])
        self.assertTrue(peripheral[3, 2])
        self.assertFalse(peripheral[0, 4])

    def test_polygon_mask_marks_grid_cells_inside_closed_body(self) -> None:
        from cold_vortex_regions import polygon_mask

        mask = polygon_mask(
            Polygon([(0.4, 0.4), (2.6, 0.4), (2.6, 2.6), (0.4, 2.6)]),
            np.arange(4.0),
            np.arange(4.0),
        )

        self.assertTrue(mask[1, 1])
        self.assertFalse(mask[0, 0])

    def test_relative_vorticity_is_positive_for_counterclockwise_solid_rotation(self) -> None:
        from cold_vortex_regions import relative_vorticity

        latitude = np.linspace(-1.0, 1.0, 21)
        longitude = np.linspace(-1.0, 1.0, 21)
        lon2d, lat2d = np.meshgrid(longitude, latitude)
        u = -np.deg2rad(lat2d)
        v = np.deg2rad(lon2d)

        vorticity = relative_vorticity(u, v, latitude, longitude, earth_radius_m=1.0)

        self.assertTrue(np.allclose(vorticity[2:-2, 2:-2], 2.0, atol=0.02))

    def test_refine_center_uses_z500_minimum_within_search_neighborhood(self) -> None:
        from cold_vortex_regions import refine_center_to_z500_minimum

        latitude = np.arange(40.0, 43.0, 0.25)
        longitude = np.arange(110.0, 113.0, 0.25)
        z500 = np.full((len(latitude), len(longitude)), 5400.0)
        z500[3, 7] = 5200.0

        latitude_out, longitude_out, height_out = refine_center_to_z500_minimum(
            z500, latitude, longitude, candidate_latitude=41.0, candidate_longitude=111.0
        )

        self.assertEqual((latitude_out, longitude_out, height_out), (40.75, 111.75, 5200.0))


if __name__ == "__main__":
    unittest.main()
