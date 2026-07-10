# Geometry Mask Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the shared legacy "front mask -> fitted centerline -> normal sampling frame" logic into the new `pipeline/geometry` layer so later `profiles` and `subareas` steps can depend on a real geometry object instead of placeholder arrays.

**Architecture:** Keep the migration conservative. First extract reusable numerical helpers into `pipeline/core/front_ops.py`, then expose one mask-driven entrypoint in `pipeline/steps/geometry.py`. The new code should mimic the current legacy fitting idea instead of redesigning the science.

**Tech Stack:** Python 3.12, `numpy`, `skimage.measure`, standard library `unittest`

## Global Constraints

- Preserve the current scientific baseline: migrate shared geometry mechanics, do not redesign the front-identification method.
- Keep the scope inside `geometry`; do not pull `profiles`, `subareas`, or `runner` into this slice.
- New tests must use synthetic masks first, then one lightweight real-mask smoke command for `CRA40 front2 2017-06-22T18`.
- Keep comments concise and in Chinese where they materially help explain the migration logic.

---

### Task 1: Add Reusable Core Geometry Helpers

**Files:**
- Modify: `pipeline/core/front_ops.py`
- Modify: `tests/test_geometry_step.py`

**Interfaces:**
- Produces: `extract_largest_contour(mask: np.ndarray) -> np.ndarray`
- Produces: `contour_to_lonlat(contour: np.ndarray, lons: np.ndarray, lats: np.ndarray) -> tuple[np.ndarray, np.ndarray]`
- Produces: `fit_polynomial_centerline(x: np.ndarray, y: np.ndarray, degree: int, dense_points: int, n_sections: int) -> tuple[np.poly1d, np.ndarray, np.ndarray]`
- Produces: `estimate_unit_normals(curve: np.poly1d, x_sample: np.ndarray, delta_x: float) -> tuple[np.ndarray, np.ndarray]`
- Consumes later: `build_normal_offsets(nx, ny, distance, n_points)` already exists and stays the offset builder

- [ ] **Step 1: Write the failing helper tests**

```python
def test_extract_largest_contour_rejects_empty_mask(self) -> None:
    from pipeline.core.front_ops import extract_largest_contour

    with self.assertRaisesRegex(ValueError, "No contour found"):
        extract_largest_contour(np.zeros((5, 5), dtype=bool))


def test_fit_centerline_and_normals_from_synthetic_points(self) -> None:
    from pipeline.core.front_ops import (
        estimate_unit_normals,
        fit_polynomial_centerline,
    )

    x = np.linspace(100.0, 110.0, 20)
    y = 0.1 * (x - 105.0) ** 2 + 25.0
    curve, x_sample, y_sample = fit_polynomial_centerline(
        x,
        y,
        degree=2,
        dense_points=200,
        n_sections=6,
    )
    nx, ny = estimate_unit_normals(curve, x_sample, delta_x=0.1)

    self.assertEqual(x_sample.shape, (6,))
    self.assertEqual(y_sample.shape, (6,))
    np.testing.assert_allclose(np.sqrt(nx**2 + ny**2), np.ones(6), atol=1e-6)
```

- [ ] **Step 2: Run the geometry test file to verify failure**

Run: `conda run -n cwr_py312 python -m unittest tests.test_geometry_step -v`
Expected: failing import errors for the new helper functions

- [ ] **Step 3: Implement the minimal helpers in `pipeline/core/front_ops.py`**

```python
from skimage import measure


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
    x_index = np.clip(contour[:, 1].astype(int), 0, len(lons) - 1)
    y_index = np.clip(contour[:, 0].astype(int), 0, len(lats) - 1)
    return lons[x_index], lats[y_index]


def fit_polynomial_centerline(
    x: np.ndarray,
    y: np.ndarray,
    degree: int,
    dense_points: int,
    n_sections: int,
) -> tuple[np.poly1d, np.ndarray, np.ndarray]:
    curve = np.poly1d(np.polyfit(x, y, deg=degree))
    x_dense = np.linspace(np.min(x), np.max(x), dense_points)
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
    slope_plus = curve(x_sample + delta_x)
    slope_minus = curve(x_sample - delta_x)
    slopes = (slope_plus - slope_minus) / (2.0 * delta_x)
    tx = 1.0 / np.sqrt(1.0 + slopes**2)
    ty = slopes / np.sqrt(1.0 + slopes**2)
    return -ty, tx
```

- [ ] **Step 4: Run the geometry test file to verify it passes**

Run: `conda run -n cwr_py312 python -m unittest tests.test_geometry_step -v`
Expected: `OK`

### Task 2: Expose One Real Mask-Driven Geometry Entry

**Files:**
- Modify: `pipeline/steps/geometry.py`
- Modify: `tests/test_geometry_step.py`

**Interfaces:**
- Consumes: `extract_largest_contour`, `contour_to_lonlat`, `fit_polynomial_centerline`, `estimate_unit_normals`, `build_normal_offsets`
- Produces: `build_geometry_from_mask(mask: np.ndarray, lons: np.ndarray, lats: np.ndarray, degree: int = 4, dense_points: int = 1000, n_sections: int = 10, distance: float = 1.0, n_points: int = 20, delta_x: float = 0.1) -> GeometryResult`
- Produces: `GeometryResult` enriched with `contour_x`, `contour_y`, `centerline_x`, `centerline_y`, `normal_x`, `normal_y`

- [ ] **Step 1: Write the failing mask-driven geometry test**

```python
def test_build_geometry_from_mask_returns_sampling_frame(self) -> None:
    from pipeline.steps.geometry import build_geometry_from_mask

    mask = np.zeros((20, 20), dtype=bool)
    for idx in range(4, 16):
        mask[idx, max(idx - 1, 0):min(idx + 2, 20)] = True

    lons = np.linspace(100.0, 110.0, 20)
    lats = np.linspace(30.0, 20.0, 20)

    result = build_geometry_from_mask(
        mask,
        lons,
        lats,
        degree=2,
        dense_points=200,
        n_sections=6,
        distance=1.5,
        n_points=7,
        delta_x=0.1,
    )

    self.assertEqual(result.centerline_x.shape, (6,))
    self.assertEqual(result.centerline_y.shape, (6,))
    self.assertEqual(result.sampled_dx.shape, (6, 7))
    self.assertEqual(result.sampled_dy.shape, (6, 7))
    self.assertGreater(result.contour_x.size, 0)
```

- [ ] **Step 2: Run the geometry test file to verify failure**

Run: `conda run -n cwr_py312 python -m unittest tests.test_geometry_step -v`
Expected: `ImportError` or attribute error for `build_geometry_from_mask`

- [ ] **Step 3: Implement the mask-driven geometry step**

```python
@dataclass(slots=True)
class GeometryResult:
    offsets: np.ndarray
    sampled_dx: np.ndarray
    sampled_dy: np.ndarray
    contour_x: np.ndarray
    contour_y: np.ndarray
    centerline_x: np.ndarray
    centerline_y: np.ndarray
    normal_x: np.ndarray
    normal_y: np.ndarray


def build_geometry_from_mask(
    mask: np.ndarray,
    lons: np.ndarray,
    lats: np.ndarray,
    degree: int = 4,
    dense_points: int = 1000,
    n_sections: int = 10,
    distance: float = 1.0,
    n_points: int = 20,
    delta_x: float = 0.1,
) -> GeometryResult:
    contour = extract_largest_contour(mask)
    contour_x, contour_y = contour_to_lonlat(contour, lons, lats)
    curve, centerline_x, centerline_y = fit_polynomial_centerline(
        contour_x,
        contour_y,
        degree=degree,
        dense_points=dense_points,
        n_sections=n_sections,
    )
    normal_x, normal_y = estimate_unit_normals(
        curve,
        centerline_x,
        delta_x=delta_x,
    )
    offsets, sampled_dx, sampled_dy = build_normal_offsets(
        normal_x,
        normal_y,
        distance=distance,
        n_points=n_points,
    )
    return GeometryResult(
        offsets=offsets,
        sampled_dx=sampled_dx,
        sampled_dy=sampled_dy,
        contour_x=contour_x,
        contour_y=contour_y,
        centerline_x=centerline_x,
        centerline_y=centerline_y,
        normal_x=normal_x,
        normal_y=normal_y,
    )
```

- [ ] **Step 4: Run the geometry test file and one real-mask smoke command**

Run: `conda run -n cwr_py312 python -m unittest tests.test_geometry_step -v`
Expected: `OK`

Run: `conda run -n cwr_py312 python -c "from pipeline.steps.masks import resolve_case_masks; from pipeline.steps.geometry import build_geometry_from_mask; from nc_compat import open_dataset_compat; assets=resolve_case_masks('front2','2017-06-22T18'); ds=open_dataset_compat(assets['front_mask']); result=build_geometry_from_mask(ds['ind_area_bool'].values, ds['lon'].values, ds['lat'].values, n_sections=8, n_points=9); print(result.centerline_x.shape); print(result.sampled_dx.shape)"`
Expected:

```text
(8,)
(8, 9)
```

## Self-Review

### Spec coverage

- This slice covers the first real `geometry` migration step from legacy shared logic.
- It intentionally does not migrate profile interpolation, subarea segmentation, or runner integration yet.

### Placeholder scan

- No `TODO` or `TBD` placeholders remain.
- Every task names exact files, functions, and verification commands.

### Type consistency

- `GeometryResult` stays the single geometry container.
- `build_geometry_from_mask(...)` becomes the mask-driven step entry.
- Core helpers stay in `pipeline/core/front_ops.py` so later `profiles` and `subareas` can reuse them.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-07-geometry-mask-migration.md`. Continue with the already chosen execution mode: **Subagent-Driven**.
