from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from metpy.calc import dewpoint_from_relative_humidity
from metpy.calc import divergence
from metpy.calc import equivalent_potential_temperature
from metpy.calc import frontogenesis
from metpy.calc import gradient
from metpy.calc import lat_lon_grid_deltas
from metpy.calc import potential_temperature
from metpy.units import units

from nc_compat import open_dataset_compat


REQUIRED_ERA5_DYNAMICS_VARS = ("u", "v", "q", "t", "r")


@dataclass(frozen=True, slots=True)
class Era5DynamicsInput:
    lons: np.ndarray
    lats: np.ndarray
    temperature: np.ndarray
    relative_humidity: np.ndarray
    specific_humidity: np.ndarray
    u: np.ndarray
    v: np.ndarray


@dataclass(frozen=True, slots=True)
class Era5DynamicsResult:
    lons: np.ndarray
    lats: np.ndarray
    thetae: np.ndarray
    thetae_gradient: np.ndarray
    divergence: np.ndarray
    moisture_flux_convergence: np.ndarray
    frontogenesis: np.ndarray
    u: np.ndarray
    v: np.ndarray


def read_era5_dynamics(
    path: Path,
    target_time: str,
    level_hpa: float,
    lats: np.ndarray,
    lons: np.ndarray,
) -> Era5DynamicsInput:
    ds = open_dataset_compat(path)
    missing = [name for name in REQUIRED_ERA5_DYNAMICS_VARS if name not in ds]
    if missing:
        raise ValueError(f"ERA5 dynamics dataset is missing variables: {missing}")

    try:
        selected = ds[list(REQUIRED_ERA5_DYNAMICS_VARS)].sel(
            valid_time=np.datetime64(target_time),
            pressure_level=float(level_hpa),
        ).sel(
            latitude=np.asarray(lats, dtype=float),
            longitude=np.asarray(lons, dtype=float),
        )
    except KeyError as exc:
        raise ValueError(
            "ERA5 dynamics requires exact target time, pressure level, and grid "
            f"coordinates: time={target_time}, level={level_hpa} hPa"
        ) from exc
    expected_shape = (len(lats), len(lons))
    arrays = {
        name: np.asarray(selected[name].values, dtype=float)
        for name in REQUIRED_ERA5_DYNAMICS_VARS
    }
    mismatched = {
        name: values.shape
        for name, values in arrays.items()
        if values.shape != expected_shape
    }
    if mismatched:
        raise ValueError(
            f"ERA5 dynamics fields do not match target grid {expected_shape}: {mismatched}"
        )

    return Era5DynamicsInput(
        lons=np.asarray(selected["longitude"].values, dtype=float),
        lats=np.asarray(selected["latitude"].values, dtype=float),
        temperature=arrays["t"],
        relative_humidity=arrays["r"],
        specific_humidity=arrays["q"],
        u=arrays["u"],
        v=arrays["v"],
    )


def _relative_humidity_quantity(values: np.ndarray):
    rh = np.asarray(values, dtype=float)
    finite = rh[np.isfinite(rh)]
    if finite.size and np.nanmax(finite) > 1.5:
        rh = rh / 100.0
    return rh * units.dimensionless


def calculate_era5_dynamics(
    data: Era5DynamicsInput,
    level_hpa: float,
) -> Era5DynamicsResult:
    expected_shape = (len(data.lats), len(data.lons))
    fields = {
        "temperature": data.temperature,
        "relative_humidity": data.relative_humidity,
        "specific_humidity": data.specific_humidity,
        "u": data.u,
        "v": data.v,
    }
    mismatched = {
        name: np.asarray(value).shape
        for name, value in fields.items()
        if np.asarray(value).shape != expected_shape
    }
    if mismatched:
        raise ValueError(
            f"ERA5 dynamics fields do not match coordinate grid {expected_shape}: {mismatched}"
        )

    temperature = np.asarray(data.temperature, dtype=float) * units.kelvin
    rh = _relative_humidity_quantity(data.relative_humidity)
    pressure = float(level_hpa) * units.hPa
    dewpoint = dewpoint_from_relative_humidity(temperature, rh)
    thetae = equivalent_potential_temperature(pressure, temperature, dewpoint)
    theta = potential_temperature(pressure, temperature)
    u_wind = np.asarray(data.u, dtype=float) * units("m/s")
    v_wind = np.asarray(data.v, dtype=float) * units("m/s")
    q = np.asarray(data.specific_humidity, dtype=float) * units.dimensionless
    dx, dy = lat_lon_grid_deltas(data.lons, data.lats)

    grad_y, grad_x = gradient(thetae, deltas=(dy, dx))
    thetae_gradient = np.sqrt(grad_x**2 + grad_y**2)
    div = divergence(u_wind, v_wind, dx=dx, dy=dy)
    moisture_convergence = -divergence(q * u_wind, q * v_wind, dx=dx, dy=dy)
    fg = frontogenesis(theta, u_wind, v_wind, dx=dx, dy=dy)

    return Era5DynamicsResult(
        lons=np.asarray(data.lons, dtype=float),
        lats=np.asarray(data.lats, dtype=float),
        thetae=np.asarray(thetae.to("kelvin").magnitude, dtype=float),
        thetae_gradient=np.asarray(
            thetae_gradient.to("kelvin / meter").magnitude,
            dtype=float,
        ),
        divergence=np.asarray(div.to("1 / second").magnitude, dtype=float),
        moisture_flux_convergence=np.asarray(
            moisture_convergence.to("1 / second").magnitude,
            dtype=float,
        ),
        frontogenesis=np.asarray(
            fg.to("kelvin / meter / second").magnitude,
            dtype=float,
        ),
        u=np.asarray(data.u, dtype=float),
        v=np.asarray(data.v, dtype=float),
    )
