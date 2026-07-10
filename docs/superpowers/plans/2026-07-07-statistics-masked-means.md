# Statistics Masked Means Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the shared "掩膜约束下的网格平均" logic into the new pipeline so `statistics` can directly consume complete front masks or subarea masks.

**Architecture:** Keep the migration minimal. First add pure masked-mean helpers in a new `pipeline/core/stat_ops.py`, then expose step-level wrappers in `pipeline/steps/statistics.py`. The first version only computes masked means and masked mean series; it does not migrate CSV aggregation or legacy plotting.

**Tech Stack:** Python 3.12, `numpy`, standard library `unittest`

## Global Constraints

- Preserve the current scientific baseline: this slice only migrates masked grid averaging, not CSV assembly or figure generation.
- The core helper must work for both a single 2D field and a time-stacked 3D field series.
- The step layer must stay generic and accept either a complete front mask or a subarea mask.
- Finish with one lightweight real-case smoke that compares full front mask mean and subarea mask mean on CRA40 `front2 2017-06-22T18`.

---

### Task 1: Add Core Masked Mean Helpers

**Files:**
- Create: `pipeline/core/stat_ops.py`
- Modify: `tests/test_statistics_step.py`

**Interfaces:**
- Produces: `masked_grid_mean(field: np.ndarray, mask_bool: np.ndarray) -> float`
- Produces: `masked_grid_series_mean(field_series: np.ndarray, mask_bool: np.ndarray) -> np.ndarray`
- Preserves later: step layer can still expose a simple `grid_mean(...)`

- [ ] **Step 1: Write the failing core masked mean tests**

```python
import unittest

import numpy as np


class StatisticsStepTest(unittest.TestCase):
    def test_masked_grid_mean_uses_only_true_mask_points(self) -> None:
        from pipeline.core.stat_ops import masked_grid_mean

        field = np.array([[1.0, 2.0], [3.0, 4.0]])
        mask = np.array([[True, False], [True, False]])

        self.assertEqual(masked_grid_mean(field, mask), 2.0)

    def test_masked_grid_series_mean_returns_one_value_per_time(self) -> None:
        from pipeline.core.stat_ops import masked_grid_series_mean

        field_series = np.array(
            [
                [[1.0, 2.0], [3.0, 4.0]],
                [[2.0, 4.0], [6.0, 8.0]],
            ]
        )
        mask = np.array([[True, False], [True, False]])

        series = masked_grid_series_mean(field_series, mask)

        np.testing.assert_array_equal(series, np.array([2.0, 4.0]))
```

- [ ] **Step 2: Run the statistics test file to verify failure**

Run: `conda run -n cwr_py312 python -m unittest tests.test_statistics_step -v`
Expected: import error for `pipeline.core.stat_ops`

- [ ] **Step 3: Implement the minimal masked mean helpers**

```python
# pipeline/core/stat_ops.py
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
```

- [ ] **Step 4: Run the statistics test file to verify it passes**

Run: `conda run -n cwr_py312 python -m unittest tests.test_statistics_step -v`
Expected: `OK`

### Task 2: Expose Generic Statistics Step Wrappers

**Files:**
- Modify: `pipeline/steps/statistics.py`
- Modify: `tests/test_statistics_step.py`

**Interfaces:**
- Consumes: `masked_grid_mean`, `masked_grid_series_mean`
- Produces: `build_masked_mean(variable: str, field: np.ndarray, mask_bool: np.ndarray) -> float`
- Produces: `build_masked_series(variable: str, field_series: np.ndarray, mask_bool: np.ndarray) -> np.ndarray`
- Preserves: `grid_mean(values: np.ndarray) -> float`

- [ ] **Step 1: Write the failing step-wrapper tests**

```python
def test_build_masked_mean_wraps_core_mean(self) -> None:
    from pipeline.steps.statistics import build_masked_mean

    field = np.array([[1.0, 2.0], [3.0, 4.0]])
    mask = np.array([[True, False], [True, False]])

    self.assertEqual(build_masked_mean("rh", field, mask), 2.0)


def test_build_masked_series_wraps_core_series(self) -> None:
    from pipeline.steps.statistics import build_masked_series

    field_series = np.array(
        [
            [[1.0, 2.0], [3.0, 4.0]],
            [[2.0, 4.0], [6.0, 8.0]],
        ]
    )
    mask = np.array([[True, False], [True, False]])

    np.testing.assert_array_equal(
        build_masked_series("rh", field_series, mask),
        np.array([2.0, 4.0]),
    )
```

- [ ] **Step 2: Run the statistics test file to verify failure**

Run: `conda run -n cwr_py312 python -m unittest tests.test_statistics_step -v`
Expected: missing function errors for `build_masked_mean` and `build_masked_series`

- [ ] **Step 3: Implement the step-level wrappers**

```python
# pipeline/steps/statistics.py
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
```

- [ ] **Step 4: Run the statistics test file and one real-case smoke command**

Run: `conda run -n cwr_py312 python -m unittest tests.test_statistics_step -v`
Expected: `OK`

Run: `conda run -n cwr_py312 python -c "from nc_compat import open_dataset_compat; from project_paths import cra40_file, cra40_front_mask, cra40_front2_subarea; from pipeline.steps.statistics import build_masked_mean; ds=open_dataset_compat(cra40_file('CRA40_RHU_2017062218_GLB_0P25_HOUR_V1_0_0.grib2')); front=open_dataset_compat(cra40_front_mask(2,'2017-06-22T18')); sub=open_dataset_compat(cra40_front2_subarea('area2_lonlat_0622T18.nc')); front_field=ds['r'].sel(latitude=front['latitude'], longitude=front['longitude'], method='nearest').isel(isobaricInhPa=0).values; sub_field=ds['r'].sel(latitude=sub['latitude'], longitude=sub['longitude'], method='nearest').isel(isobaricInhPa=0).values; full_mean=build_masked_mean('rh', front_field, front['ind_area_bool'].values); sub_mean=build_masked_mean('rh', sub_field, sub['ind_area_bool'].values); print(round(full_mean, 6)); print(round(sub_mean, 6))"`
Expected:

```text
[a finite float]
[a finite float]
```

## Self-Review

### Spec coverage

- This slice migrates the generic masked averaging kernel for both full masks and subarea masks.
- It intentionally does not migrate CSV merge logic or legacy plotting.

### Placeholder scan

- No `TODO`, `TBD`, or vague placeholders remain.
- Every task includes exact files, code, and verification commands.

### Type consistency

- Pure statistics helpers live in `pipeline/core/stat_ops.py`.
- Step-level wrappers live in `pipeline/steps/statistics.py`.
- `build_masked_mean(...)` and `build_masked_series(...)` are the generic statistics entries for downstream reuse.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-07-statistics-masked-means.md`. Continue with the already chosen execution mode: **Subagent-Driven**.
