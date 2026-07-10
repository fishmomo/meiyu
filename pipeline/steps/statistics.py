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
