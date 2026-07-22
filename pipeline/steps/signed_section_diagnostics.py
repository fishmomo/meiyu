from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from metpy.calc import dewpoint_from_relative_humidity
from metpy.calc import equivalent_potential_temperature
from metpy.units import units

from pipeline.core.section_orientation import apply_section_orientation
from pipeline.core.section_orientation import build_section_orientation
from pipeline.steps.geometry import GeometryResult
from pipeline.steps.profiles import ProfileBundle


def build_thetae_sections(
    rh: ProfileBundle,
    temp: ProfileBundle,
) -> ProfileBundle:
    if rh.values.ndim != 3 or temp.values.ndim != 3:
        raise ValueError("rh and temp profiles must be three-dimensional")
    if len(rh.levels) == 0 or len(temp.levels) == 0:
        raise ValueError("rh and temp profiles require pressure levels")
    if rh.values.shape[:2] != temp.values.shape[:2]:
        raise ValueError("rh and temp section shapes must match")
    if rh.values.shape[2] != len(rh.levels):
        raise ValueError("rh profile values and pressure levels must match")
    if temp.values.shape[2] != len(temp.levels):
        raise ValueError("temp profile values and pressure levels must match")
    rh_levels = np.asarray(rh.levels, dtype=float)
    temp_levels = np.asarray(temp.levels, dtype=float)
    if rh_levels.shape != temp_levels.shape or not np.allclose(
        rh_levels,
        temp_levels,
        rtol=0.0,
        atol=1e-6,
    ):
        raise ValueError("rh and temp pressure levels must match in the same order")

    levels = temp_levels
    temperature = np.asarray(temp.values, dtype=float) * units.kelvin
    rh_values = np.asarray(rh.values, dtype=float)
    finite = rh_values[np.isfinite(rh_values)]
    if finite.size and np.nanmax(finite) > 1.5:
        rh_values = rh_values / 100.0
    relative_humidity = rh_values * units.dimensionless
    pressure = levels[None, None, :] * units.hPa
    dewpoint = dewpoint_from_relative_humidity(temperature, relative_humidity)
    thetae = equivalent_potential_temperature(pressure, temperature, dewpoint)
    return ProfileBundle(
        variable="thetae",
        values=np.asarray(thetae.magnitude, dtype=float),
        levels=levels,
    )


def _plot_settings(variable: str) -> tuple[str, str]:
    base_variable = variable.removesuffix("_thetae")
    if base_variable == "rh":
        return "YlGnBu", "RH (%)"
    if base_variable == "temp":
        return "coolwarm", "Temperature (K)"
    if base_variable == "w":
        return "RdBu_r", "Vertical velocity"
    return "viridis", base_variable.upper()


def _write_signed_panel(
    case_name: str,
    output_dir: Path,
    variable: str,
    values: np.ndarray,
    levels: np.ndarray,
    distances_km: np.ndarray,
    orientation_status: tuple[str, ...],
    thetae: np.ndarray | None = None,
    thetae_levels: np.ndarray | None = None,
) -> str:
    n_sections = values.shape[0]
    ncols = min(5, max(1, n_sections))
    nrows = int(np.ceil(n_sections / ncols))
    fig, axes = plt.subplots(
        nrows,
        ncols,
        figsize=(4 * ncols, 3.2 * nrows),
        squeeze=False,
        constrained_layout=True,
    )
    cmap, label = _plot_settings(variable)
    last_cf = None
    active_axes = []
    for index in range(n_sections):
        ax = axes.flat[index]
        active_axes.append(ax)
        last_cf = ax.contourf(
            distances_km[index],
            levels,
            values[index].T,
            levels=12,
            cmap=cmap,
            extend="both",
        )
        if thetae is not None:
            if thetae_levels is None:
                raise ValueError("thetae_levels are required with thetae contours")
            contours = ax.contour(
                distances_km[index],
                thetae_levels,
                thetae[index].T,
                colors="black",
                linewidths=0.7,
                levels=8,
            )
            ax.clabel(contours, inline=True, fontsize=7, fmt="%.0f")
        ax.axvline(0.0, color="black", linestyle="--", linewidth=0.7)
        ax.invert_yaxis()
        ax.set_title(f"Section {index}")
        ax.set_xlabel("Distance from front centre (km)\nCold (-) | Warm (+)")
        if index % ncols == 0:
            ax.set_ylabel("Pressure (hPa)")
        else:
            ax.set_yticklabels([])
        if orientation_status[index] == "orientation_unresolved":
            ax.text(
                0.02,
                0.04,
                "orientation unresolved",
                transform=ax.transAxes,
                fontsize=7,
                color="darkred",
                bbox={"facecolor": "white", "alpha": 0.7, "edgecolor": "none"},
            )
    for index in range(n_sections, nrows * ncols):
        fig.delaxes(axes.flat[index])
    if last_cf is not None:
        fig.colorbar(last_cf, ax=active_axes, shrink=0.8, pad=0.02, label=label)

    path = output_dir / f"{case_name}_sections_{variable}_signed_km.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def write_signed_section_diagnostics(
    case_name: str,
    output_dir: Path,
    geometry: GeometryResult,
    profile_bundles: dict[str, ProfileBundle],
    threshold_k: float = 0.5,
) -> tuple[list[str], dict[str, Any]]:
    rh = profile_bundles.get("rh")
    temp = profile_bundles.get("temp")
    if rh is None or temp is None:
        return [], {
            "status": "skipped",
            "reason": "rh and temp are required for signed orientation",
        }

    thetae = build_thetae_sections(rh, temp)
    level_index = int(np.argmin(np.abs(thetae.levels - 850.0)))
    orientation = build_section_orientation(
        geometry,
        thetae.values[:, :, level_index],
        threshold_k=threshold_k,
    )
    oriented = {
        name: apply_section_orientation(bundle.values, orientation)
        for name, bundle in profile_bundles.items()
        if name in {"rh", "temp", "w"}
    }
    oriented_thetae = apply_section_orientation(thetae.values, orientation)

    paths: list[str] = []
    for name in ("rh", "temp", "w"):
        if name in oriented:
            paths.append(
                _write_signed_panel(
                    case_name,
                    output_dir,
                    name,
                    oriented[name],
                    profile_bundles[name].levels,
                    orientation.distances_km,
                    orientation.status,
                )
            )
    for name in ("rh", "w"):
        if name in oriented:
            paths.append(
                _write_signed_panel(
                    case_name,
                    output_dir,
                    f"{name}_thetae",
                    oriented[name],
                    profile_bundles[name].levels,
                    orientation.distances_km,
                    orientation.status,
                    thetae=oriented_thetae,
                    thetae_levels=thetae.levels,
                )
            )
    return paths, {
        "status": "completed",
        "distance_unit": "km",
        "orientation": list(orientation.status),
    }
