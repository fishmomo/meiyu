# Subareas Between Sections Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the legacy "两条切线之间的锋面子区域裁剪" logic into the new pipeline so `subareas` can directly consume a real `GeometryResult` and a main front mask.

**Architecture:** Keep the migration conservative. First extract the pure geometric clipping logic into a new `pipeline/core/subarea_ops.py`, then expose one step-level wrapper in `pipeline/steps/subareas.py`. The first version stays generic: it accepts `start_section` and `end_section` instead of binding to `area1` or `area2`.

**Tech Stack:** Python 3.12, `numpy`, standard library `unittest`

## Global Constraints

- Preserve the current scientific baseline: reuse the legacy two-line clipping idea from `Get_Area_latlon(i_start, i_end)`.
- Keep the interface generic with `start_section` and `end_section`; do not hardcode `area1` / `area2`.
- This slice only migrates subarea geometry and mask selection; it does not write netCDF files yet.
- Tests should begin with synthetic masks and section lines; one lightweight real-case smoke on CRA40 `front2 2017-06-22T18` is required before completion.

---

### Task 1: Add Core Between-Sections Clipping Helpers

**Files:**
- Create: `pipeline/core/subarea_ops.py`
- Modify: `tests/test_subareas_step.py`

**Interfaces:**
- Produces: `section_line_coefficients(section_x: np.ndarray, section_y: np.ndarray) -> tuple[float, float, float]`
- Produces: `select_points_between_sections(points_lonlat: np.ndarray, start_section_x: np.ndarray, start_section_y: np.ndarray, end_section_x: np.ndarray, end_section_y: np.ndarray) -> np.ndarray`
- Consumes later: point cloud from the main front mask

- [ ] **Step 1: Write the failing clipping tests**

```python
import unittest

import numpy as np


class SubareaStepTest(unittest.TestCase):
    def test_select_points_between_vertical_sections(self) -> None:
        from pipeline.core.subarea_ops import select_points_between_sections

        points = np.array(
            [
                [1.0, 0.0],
                [2.0, 0.0],
                [3.0, 0.0],
                [4.0, 0.0],
            ]
        )
        start_x = np.array([1.5, 1.5])
        start_y = np.array([-1.0, 1.0])
        end_x = np.array([3.5, 3.5])
        end_y = np.array([-1.0, 1.0])

        selected = select_points_between_sections(
            points,
            start_x,
            start_y,
            end_x,
            end_y,
        )

        np.testing.assert_array_equal(
            selected,
            np.array(
                [
                    [2.0, 0.0],
                    [3.0, 0.0],
                ]
            ),
        )
```

- [ ] **Step 2: Run the subareas test file to verify failure**

Run: `conda run -n cwr_py312 python -m unittest tests.test_subareas_step -v`
Expected: import error for `pipeline.core.subarea_ops`

- [ ] **Step 3: Implement the minimal clipping helpers**

```python
# pipeline/core/subarea_ops.py
import numpy as np


def section_line_coefficients(
    section_x: np.ndarray,
    section_y: np.ndarray,
) -> tuple[float, float, float]:
    x1, y1 = float(section_x[0]), float(section_y[0])
    x2, y2 = float(section_x[-1]), float(section_y[-1])
    a = y1 - y2
    b = x2 - x1
    c = x1 * y2 - x2 * y1
    return a, b, c


def select_points_between_sections(
    points_lonlat: np.ndarray,
    start_section_x: np.ndarray,
    start_section_y: np.ndarray,
    end_section_x: np.ndarray,
    end_section_y: np.ndarray,
) -> np.ndarray:
    a1, b1, c1 = section_line_coefficients(start_section_x, start_section_y)
    a2, b2, c2 = section_line_coefficients(end_section_x, end_section_y)

    vals1 = a1 * points_lonlat[:, 0] + b1 * points_lonlat[:, 1] + c1
    vals2 = a2 * points_lonlat[:, 0] + b2 * points_lonlat[:, 1] + c2

    mask_a = vals1 <= 0
    mask_b = vals2 > 0
    return points_lonlat[mask_a & mask_b]
```

- [ ] **Step 4: Run the subareas test file to verify it passes**

Run: `conda run -n cwr_py312 python -m unittest tests.test_subareas_step -v`
Expected: `OK`

### Task 2: Expose A Geometry-Aware Subarea Mask Step

**Files:**
- Modify: `pipeline/steps/subareas.py`
- Modify: `tests/test_subareas_step.py`

**Interfaces:**
- Consumes: `GeometryResult.centerline_x`, `GeometryResult.centerline_y`, `GeometryResult.sampled_dx`, `GeometryResult.sampled_dy`
- Consumes: `select_points_between_sections(...)`
- Produces: `build_subarea_mask(mask_lon2d: np.ndarray, mask_lat2d: np.ndarray, mask_bool: np.ndarray, geometry: GeometryResult, start_section: int, end_section: int) -> np.ndarray`
- Preserves: `build_subarea_filename(front_id: str, area_id: str, target_time: str) -> str`

- [ ] **Step 1: Write the failing geometry-aware subarea mask test**

```python
def test_build_subarea_mask_from_geometry(self) -> None:
    from pipeline.steps.geometry import GeometryResult
    from pipeline.steps.subareas import build_subarea_mask

    lon2d, lat2d = np.meshgrid(
        np.array([1.0, 2.0, 3.0, 4.0]),
        np.array([0.0]),
    )
    mask_bool = np.array([[True, True, True, True]])
    geometry = GeometryResult(
        offsets=np.array([-1.0, 1.0]),
        sampled_dx=np.array(
            [
                [0.0, 0.0],
                [0.0, 0.0],
                [0.0, 0.0],
            ]
        ),
        sampled_dy=np.array(
            [
                [-1.0, 1.0],
                [-1.0, 1.0],
                [-1.0, 1.0],
            ]
        ),
        contour_x=np.array([], dtype=float),
        contour_y=np.array([], dtype=float),
        centerline_x=np.array([1.5, 2.5, 3.5]),
        centerline_y=np.array([0.0, 0.0, 0.0]),
        normal_x=np.array([0.0, 0.0, 0.0]),
        normal_y=np.array([1.0, 1.0, 1.0]),
    )

    subarea_mask = build_subarea_mask(
        lon2d,
        lat2d,
        mask_bool,
        geometry,
        start_section=0,
        end_section=2,
    )

    np.testing.assert_array_equal(
        subarea_mask,
        np.array([[False, True, True, False]]),
    )
```

- [ ] **Step 2: Run the subareas test file to verify failure**

Run: `conda run -n cwr_py312 python -m unittest tests.test_subareas_step -v`
Expected: import error or missing function error for `build_subarea_mask`

- [ ] **Step 3: Implement the geometry-aware step wrapper**

```python
# pipeline/steps/subareas.py
import numpy as np

from pipeline.core.subarea_ops import select_points_between_sections
from pipeline.steps.geometry import GeometryResult


def build_subarea_filename(front_id: str, area_id: str, target_time: str) -> str:
    return f"{front_id}_subarea_{area_id}_{target_time}.nc"


def build_subarea_mask(
    mask_lon2d: np.ndarray,
    mask_lat2d: np.ndarray,
    mask_bool: np.ndarray,
    geometry: GeometryResult,
    start_section: int,
    end_section: int,
) -> np.ndarray:
    points = np.c_[mask_lon2d[mask_bool], mask_lat2d[mask_bool]]
    selected = select_points_between_sections(
        points,
        geometry.centerline_x[start_section] + geometry.sampled_dx[start_section],
        geometry.centerline_y[start_section] + geometry.sampled_dy[start_section],
        geometry.centerline_x[end_section] + geometry.sampled_dx[end_section],
        geometry.centerline_y[end_section] + geometry.sampled_dy[end_section],
    )

    output_mask = np.zeros(mask_bool.shape, dtype=bool)
    for lon_value, lat_value in selected:
        point_mask = (mask_lon2d == lon_value) & (mask_lat2d == lat_value)
        output_mask[point_mask] = True
    return output_mask
```

- [ ] **Step 4: Run the subareas test file and one real-case smoke command**

Run: `conda run -n cwr_py312 python -m unittest tests.test_subareas_step -v`
Expected: `OK`

Run: `conda run -n cwr_py312 python -c "import numpy as np; from nc_compat import open_dataset_compat; from project_paths import cra40_front_mask; from pipeline.steps.geometry import build_geometry_from_mask; from pipeline.steps.subareas import build_subarea_mask; ds=open_dataset_compat(cra40_front_mask(2,'2017-06-22T18')); lon2d, lat2d = np.meshgrid(ds['lon'].values, ds['lat'].values); geometry=build_geometry_from_mask(ds['ind_area_bool'].values, ds['lon'].values, ds['lat'].values, n_sections=10, n_points=20); submask=build_subarea_mask(lon2d, lat2d, ds['ind_area_bool'].values, geometry, start_section=1, end_section=4); print(int(submask.sum())); print(submask.shape)"`
Expected:

```text
[a positive integer]
(81, 141)
```

## Self-Review

### Spec coverage

- This slice migrates the generic between-sections clipping kernel.
- It intentionally does not hardcode `area1` / `area2`, and it does not write netCDF output yet.

### Placeholder scan

- No `TODO`, `TBD`, or vague placeholders remain.
- Every step includes exact files, code, and verification commands.

### Type consistency

- `build_subarea_mask(...)` is the single step-level entry for geometry-aware subarea selection.
- Pure clipping math stays in `pipeline/core/subarea_ops.py`.
- Naming stays in `build_subarea_filename(...)`, separate from geometry filtering.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-07-subareas-between-sections.md`. Continue with the already chosen execution mode: **Subagent-Driven**.
