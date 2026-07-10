# Task 2 Report

## Scope

- Task: CRA40 多变量读取映射
- Allowed write set:
  - `pipeline/core/cra40_fields.py`
  - `pipeline/manifest_loader.py`
  - `tests/test_manifest_loader.py`
  - `tests/test_profiles_step.py`
- Dataset support: CRA40 only
- Time scope: `2017-06-22T18` only

## TDD Execution

1. Added failing tests first in:
   - `tests/test_manifest_loader.py`
   - `tests/test_profiles_step.py`
2. Ran:
   - `conda run -n cwr_py312 python -m pytest tests/test_manifest_loader.py tests/test_profiles_step.py -v`
3. Observed expected initial failure:
   - `ModuleNotFoundError: No module named 'pipeline.core.cra40_fields'`
4. Implemented the minimal mapping/reader layer and manifest integration.
5. Re-ran the same pytest target.
6. Fixed one test-double issue in the newly added profile-cube unit test.
7. Final result: all targeted tests passed.

## Implementation Summary

### 1. Added centralized CRA40 mapping layer

Created `pipeline/core/cra40_fields.py` with:

- `CRA40_PROFILE_SPECS`
- `resolve_cra40_profile_input(variable: str) -> Path`
- `read_cra40_profile_cube(variable: str, input_path: Path, lats: np.ndarray, lons: np.ndarray) -> tuple[np.ndarray, np.ndarray]`

The mapping is centralized as:

- `rh`:
  - filename: `CRA40_RHU_2017062218_GLB_0P25_HOUR_V1_0_0.grib2`
  - field: `r`
  - level: `isobaricInhPa`
- `temp`:
  - filename: `CRA40_TEM_2017062218_GLB_0P25_HOUR_V1_0_0.grib2`
  - field: `t`
  - level: `isobaricInhPa`
- `w`:
  - filename: `CRA40_VVP_2017062218_GLB_0P25_HOUR_V1_0_0.grib2`
  - field: `w`
  - level: `isobaricInhPa`

Unknown variables raise:

- `ValueError("unsupported CRA40 profile variable: ...")`

### 2. Concentrated CRA40 profile path resolution in `manifest_loader`

Updated `pipeline/manifest_loader.py` so CRA40 profile inputs keyed by:

- `rh`
- `temp`
- `w`

are resolved through `resolve_cra40_profile_input(...)`, which keeps filename differences inside the mapping layer instead of scattering them across multiple steps.

Resolution priority is now:

1. `relative_path` if explicitly provided
2. CRA40 profile-variable mapping if input key is `rh/temp/w`
3. legacy CRA40 `logical_name` resolution via `cra40_file(...)` for non-profile inputs

### 3. Test coverage added

Added/updated tests to verify:

- `resolve_cra40_profile_input("rh" | "temp" | "w")` returns the expected CRA40 files
- unknown variables are rejected
- runtime input resolution prefers centralized CRA40 mapping for `rh/temp/w`
- `read_cra40_profile_cube(...)` uses the mapped field name and level dimension and slices the first 37 pressure levels

## Clarification Applied

brief 中的 TMP/VVEL 示例已按 controller clarification 更正为 TEM/VVP。

Applied controller clarification exactly as instructed:

- `temp` -> `CRA40_TEM_2017062218_GLB_0P25_HOUR_V1_0_0.grib2`, field `t`
- `w` -> `CRA40_VVP_2017062218_GLB_0P25_HOUR_V1_0_0.grib2`, field `w`
- `rh` -> `CRA40_RHU_2017062218_GLB_0P25_HOUR_V1_0_0.grib2`, field `r`
- level dimension for all three: `isobaricInhPa`

## Verification

Command run:

```bash
conda run -n cwr_py312 python -m pytest tests/test_manifest_loader.py tests/test_profiles_step.py -v
```

Result:

- `16 passed`

## Notes / Concerns

- This task only adds the mapping and cube-reading interfaces plus manifest-side resolution. It does not modify runner/statistics/diagnostics behavior, per task constraints.
- `read_cra40_profile_cube(...)` is implemented and tested, but the current runner path is intentionally untouched in this task.

## Fix Loop 1

### Reviewer boundary issue addressed

This fix loop tightened the manifest-side activation boundary for the CRA40 multi-variable mapping path.

Updated behavior:

1. `pipeline/core/cra40_fields.py` remains a pure CRA40 mapping/read layer.
2. `pipeline/manifest_loader.py` now owns the explicit front1 V1 activation check.
3. The `rh/temp/w` mapping path is enabled only when all of the following are true:
   - `dataset == "cra40"`
   - `front_id == "front1"`
   - `target_time == "2017-06-22T18"`
   - the input key is one of `rh/temp/w`
   - the manifest explicitly declares `logical_name`
   - that `logical_name` exactly matches the expected filename in `CRA40_PROFILE_SPECS`
4. `relative_path` still takes precedence and remains the explicit override path.
5. Non-front1 or non-`2017-06-22T18` manifests do not silently fall through to the front1 V1 mapping assets.
6. Existing front2 baseline behavior stays on the legacy `cra40_file(ref.logical_name)` path.

### Additional test coverage

Added boundary tests for:

- front1 + `2017-06-22T18` + correct `logical_name` for `rh/temp/w` -> success
- front1 + `2017-06-22T18` + missing `logical_name` -> rejected
- front1 + `2017-06-22T18` + wrong `logical_name` -> rejected
- non-front1 manifest -> does not use the front1 V1 automatic mapping path
- non-`2017-06-22T18` manifest -> does not use the front1 V1 automatic mapping path

### Fix-loop verification

Command run:

```bash
conda run -n cwr_py312 python -m pytest tests/test_manifest_loader.py tests/test_profiles_step.py -v
```

Result:

- `20 passed`
