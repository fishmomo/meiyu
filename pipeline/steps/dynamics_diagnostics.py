from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from pipeline.core.era5_dynamics import Era5DynamicsResult


def _level_token(level_hpa: float) -> str:
    return str(int(level_hpa)) if float(level_hpa).is_integer() else f"{level_hpa:g}"


def _overlay_mask(
    ax,
    lons: np.ndarray,
    lats: np.ndarray,
    mask_bool: np.ndarray,
) -> None:
    mask = np.asarray(mask_bool, dtype=bool)
    if mask.shape != (len(lats), len(lons)):
        raise ValueError(
            "front mask shape must match dynamics grid: "
            f"{mask.shape} != {(len(lats), len(lons))}"
        )
    if mask.any() and not mask.all():
        ax.contour(
            lons,
            lats,
            mask.astype(float),
            levels=[0.5],
            colors="black",
            linewidths=1.4,
        )


def _symmetric_levels(field: np.ndarray, count: int = 13) -> np.ndarray:
    finite = np.abs(np.asarray(field, dtype=float))
    finite = finite[np.isfinite(finite)]
    limit = float(np.nanpercentile(finite, 98.0)) if finite.size else 0.0
    if limit == 0.0:
        limit = 1.0
    return np.linspace(-limit, limit, count)


def _write_signed_map(
    path: Path,
    title: str,
    label: str,
    field: np.ndarray,
    lons: np.ndarray,
    lats: np.ndarray,
    mask_bool: np.ndarray,
) -> str:
    fig, ax = plt.subplots(figsize=(10, 7))
    cf = ax.contourf(
        lons,
        lats,
        field,
        levels=_symmetric_levels(field),
        cmap="RdBu_r",
        extend="both",
    )
    _overlay_mask(ax, lons, lats, mask_bool)
    ax.set_title(title)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    fig.colorbar(cf, ax=ax, label=label)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def write_era5_dynamics_diagnostics(
    case_name: str,
    target_time: str,
    level_hpa: float,
    output_dir: Path,
    mask_bool: np.ndarray,
    result: Era5DynamicsResult,
) -> list[str]:
    lons = np.asarray(result.lons, dtype=float)
    lats = np.asarray(result.lats, dtype=float)
    level = _level_token(level_hpa)
    title_prefix = f"ERA5 {target_time} {level} hPa"
    paths: list[str] = []

    fig, ax = plt.subplots(figsize=(10, 7))
    gradient = np.asarray(result.thetae_gradient, dtype=float)
    finite_gradient = gradient[np.isfinite(gradient)]
    if finite_gradient.size and np.nanmax(finite_gradient) > np.nanmin(finite_gradient):
        gradient_levels = np.linspace(
            float(np.nanmin(finite_gradient)),
            float(np.nanpercentile(finite_gradient, 98.0)),
            12,
        )
    else:
        centre = float(finite_gradient[0]) if finite_gradient.size else 0.0
        gradient_levels = np.linspace(centre - 0.5, centre + 0.5, 12)
    cf = ax.contourf(
        lons,
        lats,
        gradient,
        levels=gradient_levels,
        cmap="YlOrRd",
        extend="max",
    )
    thetae_contours = ax.contour(
        lons,
        lats,
        result.thetae,
        colors="black",
        linewidths=0.7,
        levels=8,
    )
    ax.clabel(thetae_contours, inline=True, fontsize=7, fmt="%.0f")
    stride_y = max(1, len(lats) // 18)
    stride_x = max(1, len(lons) // 18)
    lon2d, lat2d = np.meshgrid(lons, lats)
    quiver = ax.quiver(
        lon2d[::stride_y, ::stride_x],
        lat2d[::stride_y, ::stride_x],
        result.u[::stride_y, ::stride_x],
        result.v[::stride_y, ::stride_x],
        color="royalblue",
        scale=500,
        width=0.002,
    )
    ax.quiverkey(
        quiver,
        0.80,
        0.96,
        10.0,
        "10 m s-1",
        labelpos="E",
        coordinates="axes",
    )
    _overlay_mask(ax, lons, lats, mask_bool)
    ax.set_title(f"{title_prefix} theta-e gradient and wind")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    fig.colorbar(cf, ax=ax, label="|theta-e gradient| (K m-1)")
    gradient_path = output_dir / f"{case_name}_{level}_thetae_gradient_wind.png"
    fig.savefig(gradient_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    paths.append(str(gradient_path))

    products = (
        (
            "divergence",
            np.asarray(result.divergence) * 1e5,
            "Divergence (10^-5 s^-1; negative = convergence)",
            "horizontal divergence",
        ),
        (
            "moisture_flux_convergence",
            np.asarray(result.moisture_flux_convergence) * 1e5,
            "Moisture-flux convergence (10^-5 s^-1; positive = convergence)",
            "moisture-flux convergence",
        ),
        (
            "frontogenesis",
            np.asarray(result.frontogenesis) * 1e9,
            "Frontogenesis (10^-9 K m^-1 s^-1; positive = frontogenesis)",
            "kinematic frontogenesis",
        ),
    )
    for suffix, field, label, title in products:
        paths.append(
            _write_signed_map(
                output_dir / f"{case_name}_{level}_{suffix}.png",
                f"{title_prefix} {title}",
                label,
                field,
                lons,
                lats,
                mask_bool,
            )
        )
    return paths
