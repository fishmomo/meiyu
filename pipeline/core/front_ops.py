from skimage import measure

import numpy as np


def extract_largest_contour(mask: np.ndarray) -> np.ndarray:
    contours = measure.find_contours(mask.astype(float), level=0.5)
    if not contours:
        raise ValueError("No contour found for the supplied mask")
    return max(contours, key=lambda item: item.shape[0])


def contour_to_lonlat(
    contour: np.ndarray,
    lons: np.ndarray,
    lats: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    lon_index = np.clip(contour[:, 1].astype(int), 0, len(lons) - 1)
    lat_index = np.clip(contour[:, 0].astype(int), 0, len(lats) - 1)
    return lons[lon_index], lats[lat_index]


def fit_polynomial_centerline(
    x: np.ndarray,
    y: np.ndarray,
    degree: int,
    dense_points: int,
    n_sections: int,
) -> tuple[np.poly1d, np.ndarray, np.ndarray]:
    if x.shape != y.shape:
        raise ValueError("x and y must have the same shape")
    if x.size == 0:
        raise ValueError("x and y must not be empty")
    if degree < 0:
        raise ValueError("degree must be non-negative")

    # 轮廓映射到经纬度后常会出现重复 x，这里先做聚合，降低拟合病态性。
    order = np.argsort(x)
    x_sorted = x[order]
    y_sorted = y[order]
    unique_x, inverse = np.unique(x_sorted, return_inverse=True)
    if unique_x.size < degree + 1:
        raise ValueError("Not enough unique x points for the requested degree")

    y_sum = np.zeros(unique_x.size, dtype=float)
    counts = np.zeros(unique_x.size, dtype=int)
    np.add.at(y_sum, inverse, y_sorted)
    np.add.at(counts, inverse, 1)
    y_fit_input = y_sum / counts

    x_center = float(unique_x.mean())
    x_scale = float(unique_x.std())
    if x_scale == 0.0:
        x_scale = 1.0

    x_normalized = (unique_x - x_center) / x_scale
    normalized_curve = np.poly1d(np.polyfit(x_normalized, y_fit_input, deg=degree))
    transform = np.poly1d([1.0 / x_scale, -x_center / x_scale])
    curve = normalized_curve(transform)
    x_dense = np.linspace(np.min(unique_x), np.max(unique_x), dense_points)
    y_dense = curve(x_dense)

    dx = np.diff(x_dense)
    dy = np.diff(y_dense)
    arc_steps = np.sqrt(dx**2 + dy**2)
    arc_length = np.concatenate(([0.0], np.cumsum(arc_steps)))

    arc_uniform = np.linspace(0.0, arc_length[-1], n_sections)
    x_sample = np.interp(arc_uniform, arc_length, x_dense)
    y_sample = curve(x_sample)
    return curve, x_sample, y_sample


def estimate_unit_normals(
    curve: np.poly1d,
    x_sample: np.ndarray,
    delta_x: float,
) -> tuple[np.ndarray, np.ndarray]:
    slope = (curve(x_sample + delta_x) - curve(x_sample - delta_x)) / (
        2.0 * delta_x
    )
    tangent_norm = np.sqrt(1.0 + slope**2)
    tx = 1.0 / tangent_norm
    ty = slope / tangent_norm
    return -ty, tx


def build_normal_offsets(
    nx: np.ndarray,
    ny: np.ndarray,
    distance: float,
    n_points: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if nx.shape != ny.shape:
        raise ValueError("nx and ny must have the same shape")

    offsets = np.linspace(-distance, distance, n_points)
    sampled_x = np.array([offsets * value for value in nx])
    sampled_y = np.array([offsets * value for value in ny])
    return offsets, sampled_x, sampled_y
