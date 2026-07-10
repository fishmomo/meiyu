import numpy as np


def masked_grid_mean(field: np.ndarray, mask_bool: np.ndarray) -> float:
    values = np.asarray(field, dtype=float)[np.asarray(mask_bool, dtype=bool)]
    return float(np.nanmean(values))


def masked_grid_series_mean(
    field_series: np.ndarray,
    mask_bool: np.ndarray,
) -> np.ndarray:
    data = np.asarray(field_series, dtype=float)
    mask = np.asarray(mask_bool, dtype=bool)
    return np.array([masked_grid_mean(frame, mask) for frame in data], dtype=float)
