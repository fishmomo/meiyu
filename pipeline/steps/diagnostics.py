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

    Parameters
    ----------
    case_name : str
        Case identifier used in output filenames.
    output_dir : Path
        Directory where figures are written.
    geometry : GeometryResult
        Geometry sampling framework.
    profile_bundles : dict[str, ProfileBundle]
        Per-variable profile bundles.
    statistics : dict[str, Any]
        Structured statistics summary (for annotations).

    Returns
    -------
    list[str]
        Paths of written figure files.
    """
    figure_paths: list[str] = []

    if not profile_bundles:
        return figure_paths

    n_vars = len(profile_bundles)
    fig, axes = plt.subplots(n_vars, 1, figsize=(8, 3 * n_vars), squeeze=False)

    for ax, (var_name, bundle) in zip(axes.flat, profile_bundles.items()):
        # bundle.values shape: (n_sections, n_points, n_levels)
        data = bundle.values.mean(axis=1)  # (n_sections, n_levels)
        levels = np.arange(data.shape[1])
        sections = np.arange(data.shape[0])

        cf = ax.contourf(sections, levels, data.T, levels=20, cmap="RdBu_r")
        ax.set_title(f"{var_name.upper()} Profile")
        ax.set_xlabel("Section")
        ax.set_ylabel("Level index")
        fig.colorbar(cf, ax=ax)

    figure_path = output_dir / f"{case_name}_profiles_overview.png"
    fig.savefig(figure_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    figure_paths.append(str(figure_path))

    return figure_paths
