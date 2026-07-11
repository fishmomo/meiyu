import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Any

import numpy as np

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

    # Draw normal direction arrows at each section
    n_sections = len(geometry.centerline_x)
    for i in range(min(n_sections, len(geometry.normal_x))):
        cx = geometry.centerline_x[i]
        cy = geometry.centerline_y[i]
        nx = geometry.normal_x[i]
        ny = geometry.normal_y[i]
        scale = 2.0
        ax.arrow(cx, cy, nx * scale, ny * scale, head_width=0.3, head_length=0.2, fc="blue", ec="blue", alpha=0.6)

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
