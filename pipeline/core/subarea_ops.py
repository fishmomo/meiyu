import numpy as np


def section_line_coefficients(
    section_x: np.ndarray,
    section_y: np.ndarray,
) -> tuple[float, float, float]:
    if section_x.size == 0 or section_y.size == 0:
        raise ValueError("section_x and section_y must not be empty")
    if section_x.shape != section_y.shape:
        raise ValueError("section_x and section_y must have the same shape")

    x1, y1 = float(section_x[0]), float(section_y[0])
    x2, y2 = float(section_x[-1]), float(section_y[-1])
    a = y1 - y2
    b = x2 - x1
    c = x1 * y2 - x2 * y1
    return a, b, c


def _line_side_values(
    points_lonlat: np.ndarray,
    section_x: np.ndarray,
    section_y: np.ndarray,
) -> np.ndarray:
    a, b, c = section_line_coefficients(section_x, section_y)
    return a * points_lonlat[:, 0] + b * points_lonlat[:, 1] + c


def select_points_between_sections(
    points_lonlat: np.ndarray,
    start_section_x: np.ndarray,
    start_section_y: np.ndarray,
    end_section_x: np.ndarray,
    end_section_y: np.ndarray,
) -> np.ndarray:
    points = np.asarray(points_lonlat, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError("points_lonlat must have shape (n_points, 2)")

    start_section = np.column_stack(
        [np.asarray(start_section_x, dtype=float), np.asarray(start_section_y, dtype=float)]
    )
    end_section = np.column_stack(
        [np.asarray(end_section_x, dtype=float), np.asarray(end_section_y, dtype=float)]
    )

    if start_section.shape[0] == 0 or end_section.shape[0] == 0:
        return points[:0]

    start_side = _line_side_values(points, start_section_x, start_section_y)
    end_side = _line_side_values(points, end_section_x, end_section_y)

    start_reference = float(_line_side_values(end_section.mean(axis=0, keepdims=True), start_section_x, start_section_y)[0])
    end_reference = float(_line_side_values(start_section.mean(axis=0, keepdims=True), end_section_x, end_section_y)[0])

    if start_reference == 0.0 or end_reference == 0.0:
        return points[:0]

    start_mask = start_side * start_reference >= 0.0
    end_mask = end_side * end_reference >= 0.0
    return points[start_mask & end_mask]
