# Profiles Geometry Sampling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the shared legacy "沿法线采样 3D 场并堆叠为多个剖面" logic into the new `pipeline/profiles` layer so later RH/W/theta-e workflows can share one variable-agnostic sampler.

**Architecture:** Keep the migration narrow. First extend `pipeline/core/section_ops.py` with geometry-driven sample-grid and interpolation helpers, then expose one step-level entry in `pipeline/steps/profiles.py` that consumes `GeometryResult` and returns a `ProfileBundle`.

**Tech Stack:** Python 3.12, `numpy`, `scipy.interpolate.RegularGridInterpolator`, standard library `unittest`

## Global Constraints

- Reuse the new `GeometryResult` instead of rebuilding geometry inside `profiles`.
- This slice only migrates variable-agnostic profile sampling and bundling; it does not migrate plotting style or variable-specific file reading.
- Tests should start from synthetic arrays and exact gridpoint sampling.
- Keep comments concise and in Chinese only where they explain non-obvious scientific or shape logic.

---

### Task 1: Add Geometry-Driven Section Sampling Helpers

**Files:**
- Modify: `pipeline/core/section_ops.py`
- Modify: `tests/test_profiles_step.py`

**Interfaces:**
- Consumes: `GeometryResult.centerline_x`, `GeometryResult.centerline_y`, `GeometryResult.sampled_dx`, `GeometryResult.sampled_dy`
- Produces: `build_section_xy(geometry: GeometryResult) -> tuple[np.ndarray, np.ndarray]`
- Produces: `sample_3d_field_along_sections(field: np.ndarray, levels: np.ndarray, lats: np.ndarray, lons: np.ndarray, sample_x: np.ndarray, sample_y: np.ndarray) -> np.ndarray`
- Preserves: `stack_profiles(profiles: list[np.ndarray]) -> np.ndarray`

- [ ] **Step 1: Write the failing section sampling tests**

```python
def test_build_section_xy_adds_centerline_and_offsets(self) -> None:
    from pipeline.steps.geometry import GeometryResult
    from pipeline.core.section_ops import build_section_xy

    geometry = GeometryResult(
        offsets=np.array([-1.0, 1.0]),
        sampled_dx=np.array([[0.0, 1.0], [0.0, 1.0]]),
        sampled_dy=np.array([[0.0, 0.0], [0.0, 0.0]]),
        contour_x=np.array([], dtype=float),
        contour_y=np.array([], dtype=float),
        centerline_x=np.array([100.0, 101.0]),
        centerline_y=np.array([30.0, 31.0]),
        normal_x=np.array([1.0, 1.0]),
        normal_y=np.array([0.0, 0.0]),
    )

    sample_x, sample_y = build_section_xy(geometry)

    np.testing.assert_array_equal(
        sample_x,
        np.array([[100.0, 101.0], [101.0, 102.0]]),
    )
    np.testing.assert_array_equal(
        sample_y,
        np.array([[30.0, 30.0], [31.0, 31.0]]),
    )


def test_sample_3d_field_along_sections_returns_expected_shape(self) -> None:
    from pipeline.core.section_ops import sample_3d_field_along_sections

    levels = np.array([1000.0, 900.0])
    lats = np.array([31.0, 30.0])
    lons = np.array([100.0, 101.0, 102.0])
    field = np.arange(2 * 2 * 3, dtype=float).reshape(2, 2, 3)
    sample_x = np.array([[100.0, 101.0], [101.0, 102.0]])
    sample_y = np.array([[30.0, 30.0], [31.0, 31.0]])

    profiles = sample_3d_field_along_sections(
        field,
        levels,
        lats,
        lons,
        sample_x,
        sample_y,
    )

    self.assertEqual(profiles.shape, (2, 2, 2))
    np.testing.assert_array_equal(profiles[0, 0], field[:, 1, 0])
```

- [ ] **Step 2: Run the profiles test file to verify failure**

Run: `conda run -n cwr_py312 python -m unittest tests.test_profiles_step -v`
Expected: import errors for the new helper functions

- [ ] **Step 3: Implement minimal reusable section sampling helpers**

```python
from scipy.interpolate import RegularGridInterpolator


def build_section_xy(geometry: GeometryResult) -> tuple[np.ndarray, np.ndarray]:
    centerline_x = geometry.centerline_x[:, None]
    centerline_y = geometry.centerline_y[:, None]
    return centerline_x + geometry.sampled_dx, centerline_y + geometry.sampled_dy


def sample_3d_field_along_sections(
    field: np.ndarray,
    levels: np.ndarray,
    lats: np.ndarray,
    lons: np.ndarray,
    sample_x: np.ndarray,
    sample_y: np.ndarray,
) -> np.ndarray:
    interp = RegularGridInterpolator(
        (levels, lats, lons),
        field,
        bounds_error=False,
        fill_value=np.nan,
    )
    profiles: list[np.ndarray] = []
    for section_x, section_y in zip(sample_x, sample_y):
        section_points = []
        for sx, sy in zip(section_x, section_y):
            for lev in levels:
                section_points.append([lev, sy, sx])
        sampled = interp(np.array(section_points))
        profiles.append(sampled.reshape(len(section_x), len(levels)))
    return np.stack(profiles, axis=0)
```

- [ ] **Step 4: Run the profiles test file to verify it passes**

Run: `conda run -n cwr_py312 python -m unittest tests.test_profiles_step -v`
Expected: `OK`

### Task 2: Expose One Geometry-Aware Profiles Entry

**Files:**
- Modify: `pipeline/steps/profiles.py`
- Modify: `tests/test_profiles_step.py`

**Interfaces:**
- Consumes: `build_section_xy`, `sample_3d_field_along_sections`, `stack_profiles`
- Produces: `build_profile_bundle_from_field(variable: str, field: np.ndarray, levels: np.ndarray, lats: np.ndarray, lons: np.ndarray, geometry: GeometryResult) -> ProfileBundle`
- Preserves: `build_profile_bundle(variable, profiles)`

- [ ] **Step 1: Write the failing profile bundle from field test**

```python
def test_build_profile_bundle_from_field_keeps_variable_and_shape(self) -> None:
    from pipeline.steps.geometry import GeometryResult
    from pipeline.steps.profiles import build_profile_bundle_from_field

    geometry = GeometryResult(
        offsets=np.array([-1.0, 1.0]),
        sampled_dx=np.array([[0.0, 1.0], [0.0, 1.0]]),
        sampled_dy=np.array([[0.0, 0.0], [0.0, 0.0]]),
        contour_x=np.array([], dtype=float),
        contour_y=np.array([], dtype=float),
        centerline_x=np.array([100.0, 101.0]),
        centerline_y=np.array([30.0, 31.0]),
        normal_x=np.array([1.0, 1.0]),
        normal_y=np.array([0.0, 0.0]),
    )
    levels = np.array([1000.0, 900.0])
    lats = np.array([31.0, 30.0])
    lons = np.array([100.0, 101.0, 102.0])
    field = np.arange(2 * 2 * 3, dtype=float).reshape(2, 2, 3)

    bundle = build_profile_bundle_from_field(
        "rh",
        field,
        levels,
        lats,
        lons,
        geometry,
    )

    self.assertEqual(bundle.variable, "rh")
    self.assertEqual(bundle.values.shape, (2, 2, 2))
```

- [ ] **Step 2: Run the profiles test file to verify failure**

Run: `conda run -n cwr_py312 python -m unittest tests.test_profiles_step -v`
Expected: import error for `build_profile_bundle_from_field`

- [ ] **Step 3: Implement the geometry-aware profiles step**

```python
def build_profile_bundle_from_field(
    variable: str,
    field: np.ndarray,
    levels: np.ndarray,
    lats: np.ndarray,
    lons: np.ndarray,
    geometry: GeometryResult,
) -> ProfileBundle:
    sample_x, sample_y = build_section_xy(geometry)
    sampled_profiles = sample_3d_field_along_sections(
        field,
        levels,
        lats,
        lons,
        sample_x,
        sample_y,
    )
    return ProfileBundle(variable=variable, values=sampled_profiles)
```

- [ ] **Step 4: Run the profiles test file**

Run: `conda run -n cwr_py312 python -m unittest tests.test_profiles_step -v`
Expected: `OK`

## Self-Review

### Spec coverage

- This slice migrates the shared interpolation-and-stack logic from legacy profile scripts.
- It intentionally does not migrate figure rendering or variable-specific readers yet.

### Placeholder scan

- No `TODO`, `TBD`, or vague "handle later" placeholders remain.

### Type consistency

- `GeometryResult` remains the single geometry carrier.
- `ProfileBundle` remains the single profile container.
- Sampling helpers live in `pipeline/core/section_ops.py`, while step-level bundling stays in `pipeline/steps/profiles.py`.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-07-profiles-geometry-sampling.md`. Continue with the already chosen execution mode: **Subagent-Driven**.
