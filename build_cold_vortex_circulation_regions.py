"""Build 2017 Northeast China cold-vortex circulation masks from CRA40."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib
import numpy as np
import xarray as xr
from matplotlib import pyplot as plt
from shapely.geometry import mapping

from cold_vortex_regions import (
    connected_positive_vorticity_mask,
    outermost_closed_contour,
    polygon_mask,
    refine_center_to_z500_minimum,
    relative_vorticity,
)


matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw" / "cra40" / "2017"
OUTPUT_DIR = ROOT / "data" / "processed" / "cold_vortex" / "2017" / "circulation_regions"
LAT_NORTH, LAT_SOUTH, LON_WEST, LON_EAST = 70.0, 20.0, 90.0, 170.0


@dataclass(frozen=True)
class EventCenter:
    event: str
    time_utc: str
    latitude: float
    longitude: float


EVENT_CENTERS = (
    EventCenter("northern_short_lived", "2017050400", 50.0, 117.5),
    EventCenter("northern_short_lived", "2017050406", 52.5, 120.0),
    EventCenter("northern_short_lived", "2017050412", 55.0, 120.0),
    EventCenter("northern_short_lived", "2017050418", 55.0, 122.5),
    EventCenter("northern_short_lived", "2017050500", 57.5, 122.5),
    EventCenter("northern_short_lived", "2017050506", 57.5, 122.5),
    EventCenter("northern_short_lived", "2017050512", 57.5, 122.5),
    EventCenter("southern_long_lived", "2017050500", 50.0, 115.0),
    EventCenter("southern_long_lived", "2017050506", 47.5, 120.0),
    EventCenter("southern_long_lived", "2017050512", 47.5, 122.5),
    EventCenter("southern_long_lived", "2017050518", 47.5, 125.0),
    EventCenter("southern_long_lived", "2017050600", 47.5, 127.5),
    EventCenter("southern_long_lived", "2017050606", 47.5, 130.0),
    EventCenter("southern_long_lived", "2017050612", 47.5, 132.5),
    EventCenter("southern_long_lived", "2017050618", 50.0, 135.0),
    EventCenter("southern_long_lived", "2017050700", 50.0, 135.0),
    EventCenter("southern_long_lived", "2017050706", 50.0, 135.0),
    EventCenter("southern_long_lived", "2017050712", 50.0, 135.0),
)


def _cra40_path(variable: str, time_utc: str) -> Path:
    pattern = f"CRA40_{variable}_{time_utc}_GLB_0P25_HOUR_V1_0_0.grib2"
    matches = list(RAW_DIR.glob(f"*/{pattern}"))
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one CRA40 file for {pattern}, found {matches}")
    return matches[0]


def _read_500hpa(variable: str, data_var: str, time_utc: str) -> xr.DataArray:
    dataset = xr.open_dataset(
        _cra40_path(variable, time_utc),
        engine="cfgrib",
        backend_kwargs={"filter_by_keys": {"typeOfLevel": "isobaricInhPa"}, "indexpath": ""},
    )
    return dataset[data_var].sel(
        isobaricInhPa=500,
        latitude=slice(LAT_NORTH, LAT_SOUTH),
        longitude=slice(LON_WEST, LON_EAST),
    ).load()


def _cell_area_km2(latitude: np.ndarray, longitude: np.ndarray) -> np.ndarray:
    radius_km = 6371.0
    dlat = np.deg2rad(abs(float(latitude[1] - latitude[0])))
    dlon = np.deg2rad(abs(float(longitude[1] - longitude[0])))
    return radius_km**2 * dlat * dlon * np.cos(np.deg2rad(latitude))[:, None]


def _touches_edge(mask: np.ndarray) -> bool:
    return bool(mask[0].any() or mask[-1].any() or mask[:, 0].any() or mask[:, -1].any())


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    features: list[dict[str, object]] = []
    masks: list[tuple[EventCenter, xr.Dataset]] = []

    for item in EVENT_CENTERS:
        z500 = _read_500hpa("GPH", "gh", item.time_utc)
        u500 = _read_500hpa("WIU", "u", item.time_utc)
        v500 = _read_500hpa("WIV", "v", item.time_utc)
        latitude = z500.latitude.values
        longitude = z500.longitude.values
        center_latitude, center_longitude, center_z500 = refine_center_to_z500_minimum(
            z500.values,
            latitude,
            longitude,
            candidate_latitude=item.latitude,
            candidate_longitude=item.longitude,
        )
        closed = outermost_closed_contour(
            z500.values,
            latitude,
            longitude,
            center_latitude=center_latitude,
            center_longitude=center_longitude,
        )
        if closed is None:
            records.append(
                {
                    "event": item.event,
                    "time_utc": item.time_utc,
                    "objective_center_latitude_deg_n": item.latitude,
                    "objective_center_longitude_deg_e": item.longitude,
                    "refined_center_latitude_deg_n": center_latitude,
                    "refined_center_longitude_deg_e": center_longitude,
                    "refined_center_z500_gpm": round(center_z500, 2),
                    "outermost_closed_contour_gpm": "",
                    "body_grid_cells_0p25": 0,
                    "body_area_km2_approx": 0,
                    "peripheral_grid_cells_0p25": 0,
                    "peripheral_area_km2_approx": 0,
                    "influence_grid_cells_0p25": 0,
                    "influence_area_km2_approx": 0,
                    "peripheral_touches_calculation_domain_edge": "",
                    "calculation_domain": "20-70N,90-170E",
                    "status": "no_40gpm_closed_body",
                }
            )
            continue

        body = polygon_mask(closed.polygon, latitude, longitude)
        vort = relative_vorticity(u500.values, v500.values, latitude, longitude)
        peripheral = connected_positive_vorticity_mask(vort, latitude, longitude, closed.polygon)
        peripheral &= ~body
        influence = body | peripheral
        area_km2 = _cell_area_km2(latitude, longitude)
        masks.append((item, xr.Dataset(
                {
                    "closed_circulation_body": (("latitude", "longitude"), body),
                    "connected_positive_vorticity_periphery": (("latitude", "longitude"), peripheral),
                    "circulation_influence_region": (("latitude", "longitude"), influence),
                },
                coords={"latitude": latitude, "longitude": longitude},
            ).expand_dims(event=[item.event], time_utc=[item.time_utc])))
        records.append(
            {
                "event": item.event,
                "time_utc": item.time_utc,
                "objective_center_latitude_deg_n": item.latitude,
                "objective_center_longitude_deg_e": item.longitude,
                "refined_center_latitude_deg_n": center_latitude,
                "refined_center_longitude_deg_e": center_longitude,
                "refined_center_z500_gpm": round(center_z500, 2),
                "outermost_closed_contour_gpm": closed.level_gpm,
                "body_grid_cells_0p25": int(body.sum()),
                "body_area_km2_approx": round(float(area_km2[body].sum()), 1),
                "peripheral_grid_cells_0p25": int(peripheral.sum()),
                "peripheral_area_km2_approx": round(float(area_km2[peripheral].sum()), 1),
                "influence_grid_cells_0p25": int(influence.sum()),
                "influence_area_km2_approx": round(float(area_km2[influence].sum()), 1),
                "peripheral_touches_calculation_domain_edge": _touches_edge(peripheral),
                "calculation_domain": "20-70N,90-170E",
                "status": "complete",
            }
        )
        features.append(
            {
                "type": "Feature",
                "properties": {"event": item.event, "time_utc": item.time_utc, "kind": "closed_circulation_body", "contour_gpm": closed.level_gpm, "refined_center_latitude_deg_n": center_latitude, "refined_center_longitude_deg_e": center_longitude},
                "geometry": mapping(closed.polygon),
            }
        )

    with (OUTPUT_DIR / "20170504_20170507_circulation_regions.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    with (OUTPUT_DIR / "20170504_20170507_closed_bodies.geojson").open("w", encoding="utf-8") as stream:
        json.dump({"type": "FeatureCollection", "features": features}, stream, ensure_ascii=False)
    xr.concat([layer for _, layer in masks], dim="sample").to_netcdf(OUTPUT_DIR / "20170504_20170507_circulation_masks.nc")

    for event in sorted({item.event for item in EVENT_CENTERS}):
        event_samples = [(item, layer) for item, layer in masks if item.event == event]
        if not event_samples:
            continue
        figure, axes = plt.subplots(1, len(event_samples), figsize=(4 * len(event_samples), 4), constrained_layout=True)
        for axis, (item, layer) in zip(np.atleast_1d(axes), event_samples):
            axis.contourf(longitude, latitude, layer["circulation_influence_region"].values, levels=[0.5, 1.5], colors=["#b8e186"], alpha=0.6)
            axis.contourf(longitude, latitude, layer["closed_circulation_body"].values, levels=[0.5, 1.5], colors=["#2166ac"], alpha=0.7)
            axis.plot(item.longitude, item.latitude, "k+", ms=8, mew=1.5)
            axis.set(title=f"{item.time_utc} UTC", xlabel="Longitude (°E)", ylabel="Latitude (°N)", xlim=(LON_WEST, LON_EAST), ylim=(LAT_SOUTH, LAT_NORTH))
        figure.savefig(OUTPUT_DIR / f"{event}_circulation_region_qc.png", dpi=160)
        plt.close(figure)


if __name__ == "__main__":
    main()
