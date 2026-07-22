"""Build 0.25-degree circulation regions for the three literature cold-vortex cases."""

from __future__ import annotations

import csv
import json
import argparse
from pathlib import Path

import numpy as np
import xarray as xr
from shapely.geometry import mapping

from cold_vortex_regions import (
    connected_positive_vorticity_mask,
    outermost_closed_contour,
    polygon_mask,
    refine_center_to_z500_minimum,
    relative_vorticity,
)


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw" / "cra40"
SCREEN = ROOT / "data" / "processed" / "cold_vortex" / "strict_case_screening" / "2017aug_2021sep_2021nov_strict_candidates.csv"
OUT = ROOT / "data" / "processed" / "cold_vortex" / "literature_cases" / "circulation_regions"
WINDOWS = {
    "2017_august": ("2017081200", "2017081418"),
    "2021_september": ("2021090800", "2021091118"),
    "2021_november": ("2021110700", "2021111218"),
}
LAT_NORTH, LAT_SOUTH, LON_WEST, LON_EAST = 70.0, 20.0, 90.0, 170.0


def _path(variable: str, time_utc: str) -> Path:
    name = f"CRA40_{variable}_{time_utc}_GLB_0P25_HOUR_V1_0_0.grib2"
    matches = list(RAW.glob(f"{time_utc[:4]}/{time_utc[:8]}/{name}"))
    if len(matches) != 1:
        raise RuntimeError(f"expected one {name}, found {matches}")
    return matches[0]


def _read_500(variable: str, field: str, time_utc: str) -> xr.DataArray:
    dataset = xr.open_dataset(
        _path(variable, time_utc), engine="cfgrib",
        backend_kwargs={"filter_by_keys": {"typeOfLevel": "isobaricInhPa"}, "indexpath": ""},
    )
    return dataset[field].sel(
        isobaricInhPa=500,
        latitude=slice(LAT_NORTH, LAT_SOUTH), longitude=slice(LON_WEST, LON_EAST),
    ).load()


def _cell_area_km2(latitude: np.ndarray, longitude: np.ndarray) -> np.ndarray:
    radius_km = 6371.0
    dlat = np.deg2rad(abs(float(latitude[1] - latitude[0])))
    dlon = np.deg2rad(abs(float(longitude[1] - longitude[0])))
    return radius_km**2 * dlat * dlon * np.cos(np.deg2rad(latitude))[:, None]


def _rows(first_time: str | None = None, last_time: str | None = None) -> list[dict[str, str]]:
    with SCREEN.open(encoding="utf-8", newline="") as stream:
        source = csv.DictReader(stream)
        return [
            row for row in source
            if row["strict_closed_40gpm"] == "True"
            and row["period"] in WINDOWS
            and WINDOWS[row["period"]][0] <= row["time_utc"] <= WINDOWS[row["period"]][1]
            and (first_time is None or row["time_utc"] >= first_time)
            and (last_time is None or row["time_utc"] <= last_time)
        ]


def main(first_time: str | None = None, last_time: str | None = None) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    features: list[dict[str, object]] = []
    layers: list[xr.Dataset] = []
    for row in _rows(first_time, last_time):
        event, time_utc = row["period"], row["time_utc"]
        objective_lat, objective_lon = float(row["center_latitude_deg_n"]), float(row["center_longitude_deg_e"])
        sample = f"{event}_{time_utc}_{objective_lat:.2f}N_{objective_lon:.2f}E"
        z500 = _read_500("GPH", "gh", time_utc)
        u500 = _read_500("WIU", "u", time_utc)
        v500 = _read_500("WIV", "v", time_utc)
        latitude, longitude = z500.latitude.values, z500.longitude.values
        center_lat, center_lon, center_z500 = refine_center_to_z500_minimum(
            z500.values, latitude, longitude,
            candidate_latitude=objective_lat, candidate_longitude=objective_lon,
        )
        closed = outermost_closed_contour(
            z500.values, latitude, longitude,
            center_latitude=center_lat, center_longitude=center_lon,
        )
        base = {
            "event": event, "sample": sample, "time_utc": time_utc,
            "objective_center_latitude_deg_n": objective_lat,
            "objective_center_longitude_deg_e": objective_lon,
            "refined_center_latitude_deg_n": center_lat,
            "refined_center_longitude_deg_e": center_lon,
            "refined_center_z500_gpm": round(center_z500, 2),
        }
        if closed is None:
            records.append({**base, "status": "no_high_resolution_closed_body"})
            continue
        body = polygon_mask(closed.polygon, latitude, longitude)
        periphery = connected_positive_vorticity_mask(
            relative_vorticity(u500.values, v500.values, latitude, longitude),
            latitude, longitude, closed.polygon,
        ) & ~body
        influence = body | periphery
        area = np.broadcast_to(_cell_area_km2(latitude, longitude), body.shape)
        records.append({
            **base, "status": "complete", "outermost_closed_contour_gpm": closed.level_gpm,
            "body_grid_cells_0p25": int(body.sum()), "body_area_km2_approx": round(float(area[body].sum()), 1),
            "periphery_grid_cells_0p25": int(periphery.sum()), "periphery_area_km2_approx": round(float(area[periphery].sum()), 1),
            "influence_grid_cells_0p25": int(influence.sum()), "influence_area_km2_approx": round(float(area[influence].sum()), 1),
        })
        layers.append(xr.Dataset({
            "closed_circulation_body": (("latitude", "longitude"), body),
            "connected_positive_vorticity_periphery": (("latitude", "longitude"), periphery),
            "circulation_influence_region": (("latitude", "longitude"), influence),
        }, coords={"latitude": latitude, "longitude": longitude}).expand_dims(sample=[sample]).assign_coords(
            event=("sample", [event]), time_utc=("sample", [time_utc]),
        ))
        features.append({"type": "Feature", "properties": {**base, "contour_gpm": closed.level_gpm}, "geometry": mapping(closed.polygon)})
    label = f"{first_time or 'all'}_{last_time or 'all'}"
    with (OUT / f"literature_cases_{label}_circulation_regions.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader(); writer.writerows(records)
    with (OUT / f"literature_cases_{label}_closed_bodies.geojson").open("w", encoding="utf-8") as stream:
        json.dump({"type": "FeatureCollection", "features": features}, stream, ensure_ascii=False)
    if layers:
        merged = xr.concat(layers, dim="sample")
        np.savez_compressed(
            OUT / f"literature_cases_{label}_circulation_masks.npz",
            sample=merged.sample.values,
            event=merged.event.values,
            time_utc=merged.time_utc.values,
            latitude=merged.latitude.values,
            longitude=merged.longitude.values,
            closed_circulation_body=merged.closed_circulation_body.values,
            connected_positive_vorticity_periphery=merged.connected_positive_vorticity_periphery.values,
            circulation_influence_region=merged.circulation_influence_region.values,
        )
    print(f"samples={len(records)} complete={len(layers)} output={OUT}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--first-time")
    parser.add_argument("--last-time")
    args = parser.parse_args()
    main(args.first_time, args.last_time)
