import csv
from pathlib import Path
from typing import Any

import numpy as np

from pipeline.core.stat_ops import masked_grid_mean, masked_grid_series_mean


def grid_mean(values: np.ndarray) -> float:
    return float(np.nanmean(values))


def build_masked_mean(
    variable: str,
    field: np.ndarray,
    mask_bool: np.ndarray,
) -> float:
    _ = variable
    return masked_grid_mean(field, mask_bool)


def build_masked_series(
    variable: str,
    field_series: np.ndarray,
    mask_bool: np.ndarray,
) -> np.ndarray:
    _ = variable
    return masked_grid_series_mean(field_series, mask_bool)


def write_statistics_csv(
    output_dir: Path,
    case_name: str,
    statistics: dict[str, Any],
) -> str:
    """Write per-variable statistics summary to a CSV file.

    Returns the path of the written file.
    """
    variables_info = statistics.get("variables", {})
    filepath = output_dir / f"{case_name}_statistics.csv"
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["variable", "front_mean", "subarea_mean", "subarea_status"])
        for var_name, info in variables_info.items():
            writer.writerow([
                var_name,
                info.get("front_mean", ""),
                info.get("subarea_mean", ""),
                info.get("subarea_status", "completed"),
            ])
    return str(filepath)
