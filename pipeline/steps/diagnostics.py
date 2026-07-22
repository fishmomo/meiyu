import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Any

import numpy as np
from metpy.calc import dewpoint_from_relative_humidity
from metpy.calc import equivalent_potential_temperature
from metpy.calc import gradient
from metpy.calc import lat_lon_grid_deltas
from metpy.units import units

from pipeline.core.section_ops import build_section_xy
from pipeline.steps.geometry import GeometryResult
from pipeline.steps.profiles import ProfileBundle


def write_front_diagnostics(
    case_name: str,
    output_dir: Path,
    geometry: GeometryResult,
    profile_bundles: dict[str, ProfileBundle],
    statistics: dict[str, Any],
) -> list[str]:
    """Write minimal diagnostic figures for a front case.

    Returns paths of written figure files.
    """
    figure_paths: list[str] = []

    if not profile_bundles:
        return figure_paths

    n_vars = len(profile_bundles)
    fig, axes = plt.subplots(n_vars, 1, figsize=(8, 3 * n_vars), squeeze=False)

    for ax, (var_name, bundle) in zip(axes.flat, profile_bundles.items()):
        data = bundle.values.mean(axis=1)
        if len(bundle.levels) > 0 and len(bundle.levels) == data.shape[1]:
            level_labels = bundle.levels
            ylabel = "Pressure Level (hPa)"
        else:
            level_labels = np.arange(data.shape[1])
            ylabel = "Level index"
        sections = np.arange(data.shape[0])
        cf = ax.contourf(sections, level_labels, data.T, levels=20, cmap="RdBu_r")
        ax.set_title(f"{var_name.upper()} Profile")
        ax.set_xlabel("Section")
        ax.set_ylabel(ylabel)
        ax.invert_yaxis()
        fig.colorbar(cf, ax=ax)

    figure_path = output_dir / f"{case_name}_profiles_overview.png"
    fig.savefig(figure_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    figure_paths.append(str(figure_path))

    return figure_paths


def write_geometry_diagnostics(
    case_name: str,
    output_dir: Path,
    geometry: GeometryResult,
    mask_bool: np.ndarray,
    lons: np.ndarray,
    lats: np.ndarray,
) -> list[str]:
    """Write geometry overview figure showing mask contour, centerline, and sections.

    Returns paths of written figure files.
    """
    figure_paths: list[str] = []

    fig, ax = plt.subplots(figsize=(10, 8))

    # Show mask boundary
    ax.contour(lons, lats, mask_bool.astype(float), levels=[0.5], colors="black", linewidths=1.5)

    # Draw contour from geometry result
    if len(geometry.contour_x) > 0:
        ax.plot(geometry.contour_x, geometry.contour_y, "k-", linewidth=1.0, alpha=0.5, label="contour")

    # Draw centerline
    ax.plot(geometry.centerline_x, geometry.centerline_y, "r-", linewidth=2, label="centerline")

    # Draw centerline points (section positions)
    if len(geometry.centerline_x) > 0:
        ax.scatter(geometry.centerline_x, geometry.centerline_y, c="red", s=30, zorder=5)

    # Draw the actual sampling sections used by profile extraction.
    sample_x, sample_y = build_section_xy(geometry)
    for i, (section_x, section_y) in enumerate(zip(sample_x, sample_y)):
        label = "profile section" if i == 0 else None
        ax.plot(section_x, section_y, color="orange", linewidth=1.2, alpha=0.9, label=label)
        ax.text(
            section_x[len(section_x) // 2],
            section_y[len(section_y) // 2],
            str(i),
            fontsize=8,
            color="black",
        )

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(f"{case_name} Geometry Overview")
    ax.legend(loc="upper right")

    figure_path = output_dir / f"{case_name}_geometry_overview.png"
    fig.savefig(figure_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    figure_paths.append(str(figure_path))

    return figure_paths


def write_statistics_diagnostics(
    case_name: str,
    output_dir: Path,
    statistics: dict[str, Any],
) -> list[str]:
    """Write statistics bar chart comparing front_mean vs subarea_mean per variable.

    Returns paths of written figure files.
    """
    figure_paths: list[str] = []

    variables_info = statistics.get("variables", {})
    if not variables_info:
        return figure_paths

    var_names = list(variables_info.keys())
    front_vals = [
        variables_info[v].get("front_mean", 0) for v in var_names
    ]
    subarea_vals = [
        variables_info[v].get("subarea_mean") for v in var_names
    ]

    x = np.arange(len(var_names))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 5))
    bars1 = ax.bar(x - width / 2, front_vals, width, label="front_mean", color="steelblue")
    bars2 = ax.bar(x + width / 2, [s if s is not None else 0 for s in subarea_vals], width, label="subarea_mean", color="coral")

    ax.set_ylabel("Mean value")
    ax.set_title(f"{case_name} Statistics Comparison")
    ax.set_xticks(x)
    ax.set_xticklabels(var_names)
    ax.legend()

    figure_path = output_dir / f"{case_name}_statistics_comparison.png"
    fig.savefig(figure_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    figure_paths.append(str(figure_path))

    return figure_paths


def _field_and_levels(
    field_cache: dict[str, tuple[np.ndarray, np.ndarray]],
    variable: str,
) -> tuple[np.ndarray, np.ndarray] | None:
    value = field_cache.get(variable)
    if value is None:
        return None
    return value


def _relative_humidity_units(values: np.ndarray):
    arr = np.asarray(values, dtype=float)
    if np.nanmax(arr) > 1.5:
        return (arr / 100.0) * units.dimensionless
    return arr * units.dimensionless


def _thetae_cube(
    field_cache: dict[str, tuple[np.ndarray, np.ndarray]],
) -> tuple[np.ndarray, np.ndarray] | None:
    rh_value = _field_and_levels(field_cache, "rh")
    temp_value = _field_and_levels(field_cache, "temp")
    if rh_value is None or temp_value is None:
        return None

    rh, rh_levels = rh_value
    temp, temp_levels = temp_value
    n_levels = min(rh.shape[0], temp.shape[0], len(rh_levels), len(temp_levels))
    if n_levels == 0:
        return None

    levels = np.asarray(temp_levels[:n_levels], dtype=float)
    pressure = levels[:, None, None] * units.hPa
    temperature = np.asarray(temp[:n_levels], dtype=float) * units.kelvin
    relative_humidity = _relative_humidity_units(np.asarray(rh[:n_levels], dtype=float))
    dewpoint = dewpoint_from_relative_humidity(temperature, relative_humidity)
    thetae = equivalent_potential_temperature(pressure, temperature, dewpoint)
    return np.asarray(thetae.magnitude, dtype=float), levels


def _thetae_profile_bundle(
    profile_bundles: dict[str, ProfileBundle],
) -> ProfileBundle | None:
    rh = profile_bundles.get("rh")
    temp = profile_bundles.get("temp")
    if rh is None or temp is None:
        return None

    n_levels = min(rh.values.shape[2], temp.values.shape[2], len(temp.levels))
    if n_levels == 0:
        return None

    levels = np.asarray(temp.levels[:n_levels], dtype=float)
    pressure = levels[None, None, :] * units.hPa
    temperature = np.asarray(temp.values[:, :, :n_levels], dtype=float) * units.kelvin
    relative_humidity = _relative_humidity_units(
        np.asarray(rh.values[:, :, :n_levels], dtype=float)
    )
    dewpoint = dewpoint_from_relative_humidity(temperature, relative_humidity)
    thetae = equivalent_potential_temperature(pressure, temperature, dewpoint)
    return ProfileBundle(
        variable="thetae",
        values=np.asarray(thetae.magnitude, dtype=float),
        levels=levels,
    )


def _horizontal_gradient_magnitude(
    field: np.ndarray,
    lons: np.ndarray,
    lats: np.ndarray,
) -> np.ndarray:
    """Return horizontal gradient magnitude using physical grid spacing (K m-1)."""
    dx, dy = lat_lon_grid_deltas(lons, lats)
    grad_y, grad_x = gradient(
        np.asarray(field, dtype=float) * units.kelvin,
        deltas=(dy, dx),
    )
    magnitude = np.sqrt(grad_x**2 + grad_y**2)
    return np.asarray(magnitude.to("kelvin / meter").magnitude, dtype=float)


def _plot_mask_points(ax, lons: np.ndarray, lats: np.ndarray, mask: np.ndarray, **kwargs) -> None:
    lon2d, lat2d = np.meshgrid(lons, lats)
    ax.scatter(lon2d[mask], lat2d[mask], **kwargs)


def _format_map_axes(ax, title: str) -> None:
    ax.set_title(title, loc="left")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_xlim(95, 130)
    ax.set_ylim(20, 40)


def _write_field_overlay(
    case_name: str,
    output_dir: Path,
    suffix: str,
    field: np.ndarray,
    lons: np.ndarray,
    lats: np.ndarray,
    mask_bool: np.ndarray,
    label: str,
    cmap: str,
    submask: np.ndarray | None = None,
) -> str:
    fig, ax = plt.subplots(figsize=(10, 8))
    cf = ax.contourf(lons, lats, field, levels=12, cmap=cmap, extend="both")
    ax.contour(lons, lats, mask_bool.astype(float), levels=[0.5], colors="black", linewidths=1.2)
    _plot_mask_points(ax, lons, lats, mask_bool, s=5, color="green", alpha=0.55)
    if submask is not None:
        _plot_mask_points(ax, lons, lats, submask, s=12, color="red", alpha=0.85)
    _format_map_axes(ax, f"{case_name} {label}")
    fig.colorbar(cf, ax=ax, label=label)
    path = output_dir / f"{case_name}_{suffix}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def _write_subarea_overlay(
    case_name: str,
    output_dir: Path,
    geometry: GeometryResult,
    mask_bool: np.ndarray,
    lons: np.ndarray,
    lats: np.ndarray,
    submask: np.ndarray | None,
) -> str:
    sample_x, sample_y = build_section_xy(geometry)
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.contour(lons, lats, mask_bool.astype(float), levels=[0.5], colors="black", linewidths=1.2)
    _plot_mask_points(ax, lons, lats, mask_bool, s=5, color="lightgray", alpha=0.7)
    if submask is not None:
        _plot_mask_points(ax, lons, lats, submask, s=12, color="red", alpha=0.9)
    ax.plot(geometry.centerline_x, geometry.centerline_y, color="blue", linewidth=1.8, label="centerline")
    for idx, (section_x, section_y) in enumerate(zip(sample_x, sample_y)):
        ax.plot(section_x, section_y, color="orange", linewidth=1.0, alpha=0.9)
        ax.text(section_x[len(section_x) // 2], section_y[len(section_y) // 2], str(idx), fontsize=8)
    _format_map_axes(ax, f"{case_name} subarea and sections")
    ax.legend(loc="upper right")
    path = output_dir / f"{case_name}_subarea_overlay.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def _variable_plot_settings(variable: str) -> tuple[str, str, int | None]:
    if variable == "rh":
        return "YlGnBu", "RH (%)", 0
    if variable == "temp":
        return "coolwarm", "Temperature (K)", None
    if variable == "w":
        return "RdBu_r", "Vertical velocity", None
    return "viridis", variable.upper(), None


def _write_sections_panel(
    case_name: str,
    output_dir: Path,
    bundle: ProfileBundle,
    thetae_bundle: ProfileBundle | None = None,
) -> str:
    n_profiles = bundle.values.shape[0]
    ncols = min(5, max(1, n_profiles))
    nrows = int(np.ceil(n_profiles / ncols))
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(4 * ncols, 3 * nrows), squeeze=False, constrained_layout=True)
    cmap, label, _ = _variable_plot_settings(bundle.variable)
    levels = bundle.levels if len(bundle.levels) == bundle.values.shape[2] else np.arange(bundle.values.shape[2])
    x = np.arange(bundle.values.shape[1])
    last_cf = None
    for idx in range(n_profiles):
        ax = axes.flat[idx]
        data = bundle.values[idx].T
        last_cf = ax.contourf(x, levels, data, levels=12, cmap=cmap, extend="both")
        if thetae_bundle is not None:
            thetae = thetae_bundle.values[idx].T
            cs = ax.contour(x, thetae_bundle.levels, thetae, colors="black", linewidths=0.7, levels=8)
            ax.clabel(cs, inline=True, fontsize=7, fmt="%.0f")
        ax.invert_yaxis()
        ax.set_title(f"Section {idx}")
        ax.set_xticks([])
        if idx % ncols == 0:
            ax.set_ylabel("Pressure (hPa)")
        else:
            ax.set_yticks([])
    for idx in range(n_profiles, nrows * ncols):
        fig.delaxes(axes.flat[idx])
    if last_cf is not None:
        fig.colorbar(last_cf, ax=axes.ravel().tolist(), shrink=0.8, pad=0.02, label=label)

    suffix = f"sections_{bundle.variable}"
    if thetae_bundle is not None:
        suffix = f"{suffix}_thetae"
    path = output_dir / f"{case_name}_{suffix}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def write_cra40_research_diagnostics(
    case_name: str,
    output_dir: Path,
    geometry: GeometryResult,
    mask_bool: np.ndarray,
    lons: np.ndarray,
    lats: np.ndarray,
    submask: np.ndarray | None,
    profile_bundles: dict[str, ProfileBundle],
    field_cache: dict[str, tuple[np.ndarray, np.ndarray]],
) -> list[str]:
    """Write CRA40 legacy-style research diagnostic figures."""
    figure_paths: list[str] = []

    thetae_value = _thetae_cube(field_cache)
    if thetae_value is not None:
        thetae, levels = thetae_value
        level_index = int(np.argmin(np.abs(levels - 850.0)))
        thetae_gradient = _horizontal_gradient_magnitude(
            thetae[level_index],
            lons,
            lats,
        )
        figure_paths.append(
            _write_field_overlay(
                case_name,
                output_dir,
                "thetae_gradient_mask_overlay",
                thetae_gradient,
                lons,
                lats,
                mask_bool,
                "|theta-e gradient| (K m-1)",
                "YlOrRd",
            )
        )

    precip_value = field_cache.get("precip")
    if precip_value is not None:
        precip, _ = precip_value
        figure_paths.append(
            _write_field_overlay(
                case_name,
                output_dir,
                "precip_mask_overlay",
                np.asarray(precip, dtype=float),
                lons,
                lats,
                mask_bool,
                "6h precipitation (mm)",
                "YlGnBu",
            )
        )

    figure_paths.append(
        _write_subarea_overlay(
            case_name,
            output_dir,
            geometry,
            mask_bool,
            lons,
            lats,
            submask,
        )
    )

    for variable in ("rh", "temp", "w"):
        bundle = profile_bundles.get(variable)
        if bundle is not None:
            figure_paths.append(_write_sections_panel(case_name, output_dir, bundle))

    thetae_bundle = _thetae_profile_bundle(profile_bundles)
    if thetae_bundle is not None:
        for variable in ("rh", "w"):
            bundle = profile_bundles.get(variable)
            if bundle is not None:
                figure_paths.append(
                    _write_sections_panel(
                        case_name,
                        output_dir,
                        bundle,
                        thetae_bundle=thetae_bundle,
                    )
                )

    return figure_paths
