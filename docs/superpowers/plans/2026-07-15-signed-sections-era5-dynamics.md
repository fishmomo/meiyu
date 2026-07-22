# Signed Cross-Front Sections and ERA5 Dynamics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add cold-to-warm signed-distance section figures for CRA40 and ERA5, plus four self-consistent 850 hPa ERA5 dynamical diagnostic maps.

**Architecture:** Keep computation in two focused core modules: one for paired-point great-circle section coordinates and orientation, and one for co-located ERA5 dynamics. Add two plotting modules that consume computed arrays, then connect them through manifest-declared inputs in `pipeline.runner` without changing existing CRA40 product names.

**Tech Stack:** Python 3.12, NumPy, Xarray, SciPy, Matplotlib Agg, MetPy/Pint, existing manifest loader and `nc_compat`.

## Global Constraints

- Cold side is negative distance, fitted front centre is zero, and warm/moist side is positive distance.
- Endpoint orientation uses the median of the outermost two samples and requires an absolute theta-e contrast of at least `0.5 K`.
- Physical derivatives use latitude/longitude-aware spacing; core arrays retain unscaled SI-style units.
- ERA5 dynamics use only co-located `u / v / q / t / r` from the manifest-declared ERA5 dataset at the selected time and `850 hPa`.
- Existing eleven CRA40 PNG products and filenames remain unchanged.
- Missing optional dynamics produce diagnostics `partial` with an exact warning; they do not report false `completed`.
- Do not combine CRA40 thermodynamics with ERA5 dynamics.

---

## File Structure

- Create `pipeline/core/section_orientation.py`: signed great-circle distances, theta-e endpoint orientation, and profile flipping.
- Create `pipeline/core/era5_dynamics.py`: ERA5 dynamics input/result dataclasses, NetCDF adapter, and physical calculations.
- Create `pipeline/steps/signed_section_diagnostics.py`: five signed-km section products.
- Create `pipeline/steps/dynamics_diagnostics.py`: four ERA5 850 hPa dynamics maps.
- Modify `pipeline/manifest_models.py`: diagnostics parameters in manifest/runtime models.
- Modify `pipeline/manifest_loader.py`: defaults, parsing, mutable config, and optional level override.
- Modify `pipeline/runner.py`: read declared dynamics input, call both new diagnostics components, and report component status/warnings.
- Modify `manifests/cases/era5_front2_20170628T18.yml`: declare `inputs.dynamics` and `params.diagnostics.level_hpa`.
- Create `tests/test_section_orientation.py` and `tests/test_era5_dynamics.py`.
- Modify `tests/test_diagnostics_step.py`, `tests/test_manifest_loader.py`, and `tests/test_runner_step.py`.

---

### Task 1: Add Manifest Diagnostics Parameters

**Files:**
- Modify: `pipeline/manifest_models.py`
- Modify: `pipeline/manifest_loader.py`
- Modify: `tests/test_manifest_loader.py`
- Modify: `manifests/cases/era5_front2_20170628T18.yml`

**Interfaces:**
- Produces: `ManifestDiagnosticsParams(level_hpa: float = 850.0)`
- Produces: `RunnerRuntimeConfig.diagnostics: ManifestDiagnosticsParams`
- Produces: `RunnerRuntimeConfig.resolved_inputs["dynamics"]`

- [ ] **Step 1: Write failing manifest tests**

Add tests that load the real ERA5 manifest and assert:

```python
def test_era5_dynamics_manifest_declares_level_and_input():
    cfg = build_runtime_config(
        Path("manifests/cases/era5_front2_20170628T18.yml")
    )
    assert cfg.diagnostics.level_hpa == 850.0
    assert cfg.resolved_inputs["dynamics"].endswith("data\\raw\\era5\\201706.nc")


def test_manifest_without_diagnostics_params_defaults_to_850():
    cfg = build_runtime_config(Path("manifests/cases/cra40_front2_20170622T18.yml"))
    assert cfg.diagnostics.level_hpa == 850.0
```

- [ ] **Step 2: Run the tests and confirm the missing model field**

Run:

```powershell
conda run -n cwr_py312 python -m pytest tests/test_manifest_loader.py -k "dynamics_manifest or diagnostics_params" -v
```

Expected: failure because `RunnerRuntimeConfig` has no `diagnostics` field.

- [ ] **Step 3: Add the model and loader support**

Add:

```python
@dataclass(slots=True)
class ManifestDiagnosticsParams:
    level_hpa: float = 850.0
```

Add `diagnostics: ManifestDiagnosticsParams` to both `ManifestSpec` and `RunnerRuntimeConfig`. In `load_manifest`, use:

```python
diagnostics=ManifestDiagnosticsParams(
    level_hpa=float(
        parsed.get("params", {}).get("diagnostics", {}).get("level_hpa", 850.0)
    )
),
```

Copy the diagnostics value through `_manifest_to_mutable_dict` and `build_runtime_config`. Add `params.diagnostics.level_hpa` to `ALLOWED_OVERRIDE_KEYS`.

Update the ERA5 manifest with:

```yaml
  diagnostics:
    level_hpa: 850

inputs:
  dynamics:
    relative_path: data/raw/era5/201706.nc
```

Keep the existing `rh`, `temp`, and `w` input entries.

- [ ] **Step 4: Run manifest tests**

Run:

```powershell
conda run -n cwr_py312 python -m pytest tests/test_manifest_loader.py -v
```

Expected: all manifest loader tests pass.

- [ ] **Step 5: Commit the isolated task files if working on an authorized feature branch**

```powershell
git add pipeline/manifest_models.py pipeline/manifest_loader.py tests/test_manifest_loader.py manifests/cases/era5_front2_20170628T18.yml
git commit -m "feat: declare ERA5 dynamics diagnostics input"
```

---

### Task 2: Build Signed Section Coordinates and Orientation

**Files:**
- Create: `pipeline/core/section_orientation.py`
- Create: `tests/test_section_orientation.py`

**Interfaces:**
- Consumes: `GeometryResult`, `thetae_sections: np.ndarray` shaped `(section, point)`
- Produces: `SectionOrientation(distances_km, flip, status)`
- Produces: `build_section_orientation(geometry, thetae_sections, threshold_k=0.5) -> SectionOrientation`
- Produces: `apply_section_orientation(values, orientation) -> np.ndarray`

- [ ] **Step 1: Write failing physical-distance and flip tests**

```python
def make_geometry_with_east_west_sections() -> GeometryResult:
    offsets = np.linspace(-1.0, 1.0, 9)
    return GeometryResult(
        offsets=offsets,
        sampled_dx=np.tile(offsets, (2, 1)),
        sampled_dy=np.zeros((2, 9)),
        contour_x=np.array([], dtype=float),
        contour_y=np.array([], dtype=float),
        centerline_x=np.array([110.0, 112.0]),
        centerline_y=np.array([30.0, 31.0]),
        normal_x=np.ones(2),
        normal_y=np.zeros(2),
    )


def test_build_section_orientation_centres_distance_and_keeps_warm_side_positive():
    geometry = make_geometry_with_east_west_sections()
    thetae = np.tile(np.linspace(330.0, 338.0, 9), (2, 1))
    result = build_section_orientation(geometry, thetae)
    assert np.allclose(result.distances_km[:, 4], 0.0)
    assert np.all(np.diff(result.distances_km, axis=1) > 0)
    assert result.flip.tolist() == [False, False]
    assert result.status == ("warm_side_positive", "warm_side_positive")


def test_build_section_orientation_flips_warm_side_on_left():
    geometry = make_geometry_with_east_west_sections()
    thetae = np.tile(np.linspace(338.0, 330.0, 9), (2, 1))
    result = build_section_orientation(geometry, thetae)
    values = np.tile(np.arange(9.0), (2, 1))
    oriented = apply_section_orientation(values, result)
    assert result.flip.tolist() == [True, True]
    assert np.array_equal(oriented[0], values[0, ::-1])
    assert np.all(np.diff(result.distances_km, axis=1) > 0)


def test_build_section_orientation_marks_weak_contrast_unresolved():
    geometry = make_geometry_with_east_west_sections()
    thetae = np.full((2, 9), 334.0)
    result = build_section_orientation(geometry, thetae)
    assert result.status == ("orientation_unresolved", "orientation_unresolved")
    assert not result.flip.any()
```

- [ ] **Step 2: Run and confirm missing module failure**

```powershell
conda run -n cwr_py312 python -m pytest tests/test_section_orientation.py -v
```

Expected: import failure for `pipeline.core.section_orientation`.

- [ ] **Step 3: Implement paired-point great-circle distances**

Implement the core with this public shape:

```python
from dataclasses import dataclass
import numpy as np
from pipeline.core.section_ops import build_section_xy
from pipeline.steps.geometry import GeometryResult

EARTH_RADIUS_KM = 6371.0088

@dataclass(frozen=True, slots=True)
class SectionOrientation:
    distances_km: np.ndarray
    flip: np.ndarray
    status: tuple[str, ...]

def _segment_distance_km(lon1, lat1, lon2, lat2) -> np.ndarray:
    lon1r, lat1r, lon2r, lat2r = map(np.radians, (lon1, lat1, lon2, lat2))
    dlon = lon2r - lon1r
    dlat = lat2r - lat1r
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1r) * np.cos(lat2r) * np.sin(dlon / 2) ** 2
    return EARTH_RADIUS_KM * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
```

For each section, cumulatively sum paired-point segment distances, subtract the distance at `n_points // 2`, and use median values from `[:2]` and `[-2:]`. If the first endpoint is warmer by at least `0.5 K`, reverse values and transform distance as `-distance[::-1]`. If contrast is weak or non-finite, preserve geometric order and mark unresolved.

- [ ] **Step 4: Run section-orientation tests**

```powershell
conda run -n cwr_py312 python -m pytest tests/test_section_orientation.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit if authorized**

```powershell
git add pipeline/core/section_orientation.py tests/test_section_orientation.py
git commit -m "feat: add signed cross-front section coordinates"
```

---

### Task 3: Write Five Signed-Kilometre Section Figures

**Files:**
- Create: `pipeline/steps/signed_section_diagnostics.py`
- Modify: `tests/test_diagnostics_step.py`

**Interfaces:**
- Consumes: `geometry`, `profile_bundles: dict[str, ProfileBundle]`
- Produces internal: `build_thetae_sections(rh: ProfileBundle, temp: ProfileBundle) -> ProfileBundle`
- Produces internal: `_write_signed_panel(case_name, output_dir, variable, values, levels, distances_km, orientation_status, thetae=None) -> str`
- Produces: `write_signed_section_diagnostics(case_name, output_dir, geometry, profile_bundles, threshold_k=0.5) -> tuple[list[str], dict[str, object]]`

- [ ] **Step 1: Write a failing filename and orientation-metadata test**

Use synthetic RH, temperature, and W bundles with 850 hPa included. Assert these exact filenames:

```python
expected = {
    "demo_sections_rh_signed_km.png",
    "demo_sections_temp_signed_km.png",
    "demo_sections_w_signed_km.png",
    "demo_sections_rh_thetae_signed_km.png",
    "demo_sections_w_thetae_signed_km.png",
}
paths, metadata = write_signed_section_diagnostics(
    "demo", tmp_path, geometry, bundles
)
assert {Path(path).name for path in paths} == expected
assert metadata["status"] == "completed"
assert metadata["distance_unit"] == "km"
```

- [ ] **Step 2: Run the focused test and confirm missing function failure**

```powershell
conda run -n cwr_py312 python -m pytest tests/test_diagnostics_step.py -k signed_section -v
```

- [ ] **Step 3: Implement theta-e section calculation and plotting**

The implementation must:

```python
def write_signed_section_diagnostics(
    case_name: str,
    output_dir: Path,
    geometry: GeometryResult,
    profile_bundles: dict[str, ProfileBundle],
    threshold_k: float = 0.5,
) -> tuple[list[str], dict[str, object]]:
    rh = profile_bundles.get("rh")
    temp = profile_bundles.get("temp")
    if rh is None or temp is None:
        return [], {"status": "skipped", "reason": "rh and temp are required"}

    thetae = build_thetae_sections(rh, temp)
    level_index = int(np.argmin(np.abs(thetae.levels - 850.0)))
    orientation = build_section_orientation(
        geometry,
        thetae.values[:, :, level_index],
        threshold_k=threshold_k,
    )
    oriented = {
        name: apply_section_orientation(bundle.values, orientation)
        for name, bundle in profile_bundles.items()
        if name in {"rh", "temp", "w"}
    }
    oriented_thetae = apply_section_orientation(thetae.values, orientation)
    paths = []
    for name in ("rh", "temp", "w"):
        if name in oriented:
            paths.append(_write_signed_panel(
                case_name, output_dir, name, oriented[name],
                profile_bundles[name].levels, orientation.distances_km,
                orientation.status,
            ))
    for name in ("rh", "w"):
        if name in oriented:
            paths.append(_write_signed_panel(
                case_name, output_dir, f"{name}_thetae", oriented[name],
                profile_bundles[name].levels, orientation.distances_km,
                orientation.status, thetae=oriented_thetae,
            ))
    return paths, {
        "status": "completed",
        "distance_unit": "km",
        "orientation": list(orientation.status),
    }
```

Calculate theta-e from RH and temperature profile bundles with MetPy, select the nearest 850 hPa index for orientation, call `build_section_orientation`, and apply the same flip decisions to RH, temperature, W, and theta-e. Use the per-section `distances_km` as the contour x-coordinate. Titles include `Cold side (-) | Warm side (+)`. Annotate only unresolved panels with `orientation unresolved`.

Do not alter or replace the existing `_write_sections_panel` outputs in `pipeline/steps/diagnostics.py`.

- [ ] **Step 4: Run diagnostics tests**

```powershell
conda run -n cwr_py312 python -m pytest tests/test_diagnostics_step.py -v
```

Expected: existing and new diagnostics tests pass.

- [ ] **Step 5: Commit if authorized**

```powershell
git add pipeline/steps/signed_section_diagnostics.py tests/test_diagnostics_step.py
git commit -m "feat: add signed-kilometre section plots"
```

---

### Task 4: Read and Calculate ERA5 850 hPa Dynamics

**Files:**
- Create: `pipeline/core/era5_dynamics.py`
- Create: `tests/test_era5_dynamics.py`

**Interfaces:**
- Produces: `Era5DynamicsInput(lons, lats, temperature, relative_humidity, specific_humidity, u, v)`
- Produces: `Era5DynamicsResult(lons, lats, thetae, thetae_gradient, divergence, moisture_flux_convergence, frontogenesis, u, v)`
- Produces: `read_era5_dynamics(path, target_time, level_hpa, lats, lons) -> Era5DynamicsInput`
- Produces: `calculate_era5_dynamics(data, level_hpa) -> Era5DynamicsResult`

- [ ] **Step 1: Write failing reader and numerical tests**

Tests must cover:

```python
def make_dynamics_input(
    u: float,
    v: float,
    q: float,
    t: float,
    rh: float,
) -> Era5DynamicsInput:
    lons = np.linspace(108.0, 112.0, 9)
    lats = np.linspace(28.0, 32.0, 9)
    shape = (len(lats), len(lons))
    return Era5DynamicsInput(
        lons=lons,
        lats=lats,
        temperature=np.full(shape, t),
        relative_humidity=np.full(shape, rh),
        specific_humidity=np.full(shape, q),
        u=np.full(shape, u),
        v=np.full(shape, v),
    )


def make_linear_flow_input(sign: float) -> Era5DynamicsInput:
    data = make_dynamics_input(u=0.0, v=0.0, q=0.01, t=290.0, rh=80.0)
    lon2d, lat2d = np.meshgrid(data.lons, data.lats)
    x_m = (lon2d - 110.0) * 111_000.0 * np.cos(np.radians(lat2d))
    y_m = (lat2d - 30.0) * 111_000.0
    return replace(data, u=sign * 1e-5 * x_m, v=sign * 1e-5 * y_m)


def test_uniform_wind_has_zero_divergence():
    data = make_dynamics_input(u=10.0, v=0.0, q=0.01, t=290.0, rh=80.0)
    result = calculate_era5_dynamics(data, 850.0)
    assert np.nanmax(np.abs(result.divergence)) < 1e-12


def test_linear_outflow_has_positive_divergence():
    data = make_linear_flow_input(sign=1.0)
    result = calculate_era5_dynamics(data, 850.0)
    assert float(np.nanmean(result.divergence)) > 0.0


def test_converging_moisture_flux_is_positive():
    data = make_linear_flow_input(sign=-1.0)
    result = calculate_era5_dynamics(data, 850.0)
    assert float(np.nanmean(result.moisture_flux_convergence)) > 0.0
```

Mock `open_dataset_compat` with an Xarray dataset and assert time, pressure, latitude, longitude selection returns the requested 2-D shapes and actual selected coordinates.

- [ ] **Step 2: Run and confirm missing module failure**

```powershell
conda run -n cwr_py312 python -m pytest tests/test_era5_dynamics.py -v
```

- [ ] **Step 3: Implement the reader and calculations**

The reader validates the exact required variables:

```python
REQUIRED_ERA5_DYNAMICS_VARS = ("u", "v", "q", "t", "r")
```

Select with:

```python
selected = ds[list(REQUIRED_ERA5_DYNAMICS_VARS)].sel(
    valid_time=np.datetime64(target_time),
    pressure_level=float(level_hpa),
    method="nearest",
).sel(latitude=lats, longitude=lons, method="nearest")
```

Calculations use:

```python
dx, dy = lat_lon_grid_deltas(data.lons, data.lats)
theta = potential_temperature(level_hpa * units.hPa, data.temperature * units.kelvin)
div = divergence(data.u * units("m/s"), data.v * units("m/s"), dx=dx, dy=dy)
mfc = -divergence(
    data.specific_humidity * data.u * units("m/s"),
    data.specific_humidity * data.v * units("m/s"),
    dx=dx,
    dy=dy,
)
fg = frontogenesis(theta, data.u * units("m/s"), data.v * units("m/s"), dx=dx, dy=dy)
```

Compute theta-e and its physical gradient from temperature and RH. Convert returned quantities to numeric arrays in `K`, `K m-1`, `s-1`, `s-1`, and `K m-1 s-1` respectively.

- [ ] **Step 4: Run dynamics numerical tests**

```powershell
conda run -n cwr_py312 python -m pytest tests/test_era5_dynamics.py -v
```

Expected: all reader and physical-field tests pass.

- [ ] **Step 5: Commit if authorized**

```powershell
git add pipeline/core/era5_dynamics.py tests/test_era5_dynamics.py
git commit -m "feat: calculate ERA5 frontal dynamics"
```

---

### Task 5: Write Four ERA5 Dynamics Maps

**Files:**
- Create: `pipeline/steps/dynamics_diagnostics.py`
- Modify: `tests/test_diagnostics_step.py`

**Interfaces:**
- Consumes: `Era5DynamicsResult`, mask, lons, lats, case time, level
- Produces: `write_era5_dynamics_diagnostics(case_name: str, target_time: str, level_hpa: float, output_dir: Path, mask_bool: np.ndarray, result: Era5DynamicsResult) -> list[str]`

- [ ] **Step 1: Write a failing plot-product test**

```python
expected = {
    "era5_demo_850_thetae_gradient_wind.png",
    "era5_demo_850_divergence.png",
    "era5_demo_850_moisture_flux_convergence.png",
    "era5_demo_850_frontogenesis.png",
}
paths = write_era5_dynamics_diagnostics(
    case_name="era5_demo",
    target_time="2017-06-28T18",
    level_hpa=850.0,
    output_dir=tmp_path,
    mask_bool=mask,
    result=result,
)
assert {Path(path).name for path in paths} == expected
```

- [ ] **Step 2: Run and confirm missing function failure**

```powershell
conda run -n cwr_py312 python -m pytest tests/test_diagnostics_step.py -k era5_dynamics -v
```

- [ ] **Step 3: Implement unit-aware maps**

Use a shared map helper that overlays the mask contour. Requirements:

- theta-e gradient filled contours in `K m-1`, theta-e contours, and thinned `u/v` quivers;
- divergence plotted as `10^5 s-1`, with negative values labelled convergence;
- moisture-flux convergence plotted as `10^5 s-1`;
- frontogenesis plotted as `10^9 K m-1 s-1`;
- diverging colour maps centred at zero for signed fields;
- every title includes `ERA5`, target time, and `850 hPa`.

The function uses `result.lons` and `result.lats`; it does not read files or calculate fields.

- [ ] **Step 4: Run diagnostics tests**

```powershell
conda run -n cwr_py312 python -m pytest tests/test_diagnostics_step.py -v
```

- [ ] **Step 5: Commit if authorized**

```powershell
git add pipeline/steps/dynamics_diagnostics.py tests/test_diagnostics_step.py
git commit -m "feat: add ERA5 dynamics maps"
```

---

### Task 6: Connect Runner Status, Signed Sections, and ERA5 Dynamics

**Files:**
- Modify: `pipeline/runner.py`
- Modify: `tests/test_runner_step.py`

**Interfaces:**
- Consumes all interfaces from Tasks 1–5.
- Produces diagnostics summary with existing keys plus `components` and `warnings`.

- [ ] **Step 1: Write failing runner tests**

Add a real-manifest assertion for all nine new filenames and a patched-failure assertion:

```python
def test_era5_case_writes_signed_sections_and_dynamics():
    summary = run_case_from_manifest(Path("manifests/cases/era5_front2_20170628T18.yml"))
    names = {Path(path).name for path in summary["diagnostics"]["files"]}
    expected = {
        "era5_front2_20170628T18_sections_rh_signed_km.png",
        "era5_front2_20170628T18_sections_temp_signed_km.png",
        "era5_front2_20170628T18_sections_w_signed_km.png",
        "era5_front2_20170628T18_sections_rh_thetae_signed_km.png",
        "era5_front2_20170628T18_sections_w_thetae_signed_km.png",
        "era5_front2_20170628T18_850_thetae_gradient_wind.png",
        "era5_front2_20170628T18_850_divergence.png",
        "era5_front2_20170628T18_850_moisture_flux_convergence.png",
        "era5_front2_20170628T18_850_frontogenesis.png",
    }
    assert expected <= names
    assert summary["diagnostics"]["status"] == "completed"
    assert summary["diagnostics"]["components"]["era5_dynamics"] == "completed"


def test_era5_dynamics_failure_reports_partial_without_losing_base_figures():
    with patch("pipeline.runner.read_era5_dynamics", side_effect=ValueError("missing q")):
        summary = run_case_from_manifest(Path("manifests/cases/era5_front2_20170628T18.yml"))
    assert summary["diagnostics"]["status"] == "partial"
    assert summary["diagnostics"]["components"]["base"] == "completed"
    assert summary["diagnostics"]["components"]["era5_dynamics"] == "failed"
    assert any("missing q" in warning for warning in summary["diagnostics"]["warnings"])
```

- [ ] **Step 2: Run the two tests and confirm missing product/status failures**

```powershell
conda run -n cwr_py312 python -m pytest tests/test_runner_step.py -k "signed_sections_and_dynamics or dynamics_failure_reports_partial" -v
```

- [ ] **Step 3: Integrate components in the diagnostics block**

Initialize:

```python
components = {"base": "completed", "signed_sections": "skipped", "era5_dynamics": "skipped"}
warnings: list[str] = []
```

When RH and temperature profile bundles exist, call `write_signed_section_diagnostics`; append paths and set its component status. For ERA5 with `resolved_inputs["dynamics"]`, call `read_era5_dynamics`, `calculate_era5_dynamics`, and `write_era5_dynamics_diagnostics`.

Catch `FileNotFoundError`, `KeyError`, `OSError`, and `ValueError` only around the optional ERA5 dynamics component. Store `f"ERA5 dynamics skipped: {exc}"`, set that component to `failed`, and set overall status to `partial`. Do not use a bare `except Exception`.

Return:

```python
diagnostics_summary = {
    "enabled": True,
    "status": "partial" if "failed" in components.values() else "completed",
    "files": figure_paths,
    "components": components,
    "warnings": warnings,
}
```

Preserve `_skipped_summary()` when diagnostics are disabled.

- [ ] **Step 4: Run runner and regression tests**

```powershell
conda run -n cwr_py312 python -m pytest tests/test_runner_step.py tests/test_diagnostics_step.py tests/test_era5_dynamics.py tests/test_section_orientation.py -v
```

Expected: all focused tests pass, including current CRA40 research filenames.

- [ ] **Step 5: Commit if authorized**

```powershell
git add pipeline/runner.py tests/test_runner_step.py
git commit -m "feat: integrate signed sections and ERA5 dynamics"
```

---

### Task 7: Real Smokes, Visual QA, Documentation, and Full Regression

**Files:**
- Modify: `docs/pipeline_quickstart_zh.md`
- Modify: `docs/pipeline_architecture_mapping_zh.md`
- Read: `outputs/figures/era5_front2_20170628T18/diagnostics/`
- Read: `outputs/figures/cra40_front2_20170628T18/diagnostics/`

**Interfaces:**
- Verifies the complete feature rather than adding a new code API.

- [ ] **Step 1: Run the real ERA5 target case**

```powershell
conda run -n cwr_py312 python -m pipeline.runner --manifest manifests/cases/era5_front2_20170628T18.yml
```

Expected: diagnostics status `completed`, five signed-km section PNGs, four ERA5 dynamics PNGs, existing base PNGs, and statistics CSV.

- [ ] **Step 2: Run the CRA40 regression smoke**

```powershell
conda run -n cwr_py312 python -m pipeline.runner --manifest manifests/cases/cra40_front2_20170628T18.yml
```

Expected: all previous CRA40 research filenames remain present, plus the new signed-km section figures; no ERA5 dynamics filename appears.

- [ ] **Step 3: Perform visual QA**

Open at least these files with the local image viewer:

- `era5_front2_20170628T18_sections_rh_thetae_signed_km.png`
- `era5_front2_20170628T18_850_thetae_gradient_wind.png`
- `era5_front2_20170628T18_850_divergence.png`
- `era5_front2_20170628T18_850_moisture_flux_convergence.png`
- `era5_front2_20170628T18_850_frontogenesis.png`

Verify signed axes, units, time, level, mask overlay, quiver density, zero-centred signed colour scales, and readable annotations. Correct plotting defects and rerun the focused plot tests after each correction.

- [ ] **Step 4: Update user and architecture documentation**

Document:

- exact nine new filenames;
- cold-negative/warm-positive convention and `0.5 K` unresolved threshold;
- ERA5-only dynamics data boundary;
- dynamics units and sign interpretation;
- `completed / partial / skipped` component semantics;
- commands for both verified `2017-06-28T18` manifests.

- [ ] **Step 5: Run full verification**

```powershell
conda run -n cwr_py312 python -m pytest tests/ -v
git diff --check
```

Expected: zero test failures and no whitespace errors. The existing NumPy binary-size runtime warning may remain documented as an environment warning; no new warnings are accepted from the feature code.

- [ ] **Step 6: Commit documentation if authorized**

```powershell
git add docs/pipeline_quickstart_zh.md docs/pipeline_architecture_mapping_zh.md
git commit -m "docs: explain signed sections and ERA5 dynamics"
```

---

## Final Review Checklist

- [ ] Every included spec requirement maps to a task above.
- [ ] CRA40 and ERA5 signed sections use the same distance/orientation API.
- [ ] ERA5 dynamics use one declared co-located dataset and never CRA40 arrays.
- [ ] Numerical tests verify field values/signs, not only PNG existence.
- [ ] Optional failures produce `partial` and a reason.
- [ ] Existing CRA40 outputs remain unchanged.
- [ ] Real ERA5 and CRA40 smokes and visual QA are complete.
- [ ] Full tests and `git diff --check` pass.
