# Runner Manifest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a manifest-driven entry path for the verified CRA40 front2 case so the runner consumes declared case defaults plus limited runtime overrides instead of hard-coded case constants.

**Architecture:** Add a thin manifest layer beside the existing pipeline steps. A case YAML file declares metadata, enabled steps, step parameters, and inputs; loader code parses and validates it into typed runtime config; the runner consumes that runtime config while keeping the current verified-chain boundary and summary output.

**Tech Stack:** Python 3.12, dataclasses, pathlib, existing `pipeline.steps.*`, `project_paths.py`, `nc_compat.py`, `pytest`

## Global Constraints

- Only support one verified case in this round: `CRA40 front2 2017-06-22T18`.
- Keep the current structured runner summary shape: `case_name`, `inventory`, `masks`, `outputs`, `geometry`, `profiles`, `subareas`, `statistics`.
- Support both `relative_path` and `logical_name` input resolution, preferring `relative_path` when both exist.
- Allow only limited, explicit runtime overrides on known fields.
- Do not add `front1`, `ERA5`, `diagnostics`, full output naming rules, batch scheduling, or generic CLI behavior in this round.
- The current workspace is not a usable git repository, so commit steps are replaced by local verification and change review.

---

### Task 1: Add Manifest Models And Sample Case File

**Files:**
- Create: `H:\邢台观测站\CWR_project\meiyu_new\pipeline\manifest_models.py`
- Create: `H:\邢台观测站\CWR_project\meiyu_new\manifests\cases\cra40_front2_20170622T18.yml`
- Test: `H:\邢台观测站\CWR_project\meiyu_new\tests\test_manifest_loader.py`

**Interfaces:**
- Produces: `ManifestInputRef`, `ManifestGeometryParams`, `ManifestProfilesParams`, `ManifestSubareasParams`, `ManifestSpec`, `RunnerRuntimeConfig`
- Produces: sample case manifest at `manifests/cases/cra40_front2_20170622T18.yml`

- [ ] **Step 1: Write the failing manifest read test**

```python
from pathlib import Path

from pipeline.manifest_loader import load_manifest


def test_load_manifest_reads_verified_case_defaults():
    manifest = load_manifest(
        Path("manifests/cases/cra40_front2_20170622T18.yml")
    )
    assert manifest.case_name == "cra40_front2_20170622T18"
    assert manifest.dataset == "cra40"
    assert manifest.front_id == "front2"
    assert manifest.target_time == "2017-06-22T18"
    assert manifest.steps["geometry"] is True
    assert manifest.geometry.n_sections == 8
    assert manifest.profiles.variables == ["rh"]
    assert manifest.subareas.start_section == 1
    assert manifest.inputs["rh"].logical_name == "CRA40_RHU_2017062218_GLB_0P25_HOUR_V1_0_0.grib2"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `conda run -n cwr_py312 python -m pytest tests/test_manifest_loader.py::test_load_manifest_reads_verified_case_defaults -v`

Expected: FAIL with import error or missing loader/model symbols.

- [ ] **Step 3: Write the sample manifest file**

```yaml
case_name: cra40_front2_20170622T18
dataset: cra40
front_id: front2
target_time: 2017-06-22T18

steps:
  inventory: true
  masks: true
  geometry: true
  profiles: true
  subareas: true
  statistics: true

params:
  geometry:
    degree: 4
    dense_points: 1000
    n_sections: 8
    distance: 1.0
    n_points: 9
    delta_x: 0.1
  profiles:
    variables:
      - rh
  subareas:
    start_section: 1
    end_section: 4

inputs:
  rh:
    logical_name: CRA40_RHU_2017062218_GLB_0P25_HOUR_V1_0_0.grib2
```

- [ ] **Step 4: Write the model definitions**

```python
from dataclasses import dataclass, field


@dataclass(slots=True)
class ManifestInputRef:
    logical_name: str | None = None
    relative_path: str | None = None


@dataclass(slots=True)
class ManifestGeometryParams:
    degree: int
    dense_points: int
    n_sections: int
    distance: float
    n_points: int
    delta_x: float


@dataclass(slots=True)
class ManifestProfilesParams:
    variables: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ManifestSubareasParams:
    start_section: int
    end_section: int


@dataclass(slots=True)
class ManifestSpec:
    case_name: str
    dataset: str
    front_id: str
    target_time: str
    steps: dict[str, bool]
    geometry: ManifestGeometryParams
    profiles: ManifestProfilesParams
    subareas: ManifestSubareasParams
    inputs: dict[str, ManifestInputRef]


@dataclass(slots=True)
class RunnerRuntimeConfig:
    case_name: str
    dataset: str
    front_id: str
    target_time: str
    steps: dict[str, bool]
    geometry: ManifestGeometryParams
    profiles: ManifestProfilesParams
    subareas: ManifestSubareasParams
    resolved_inputs: dict[str, str]
```

- [ ] **Step 5: Run the test again**

Run: `conda run -n cwr_py312 python -m pytest tests/test_manifest_loader.py::test_load_manifest_reads_verified_case_defaults -v`

Expected: still FAIL, now because loader is not implemented.

- [ ] **Step 6: Review local changes**

Run: `git diff -- pipeline/manifest_models.py manifests/cases/cra40_front2_20170622T18.yml tests/test_manifest_loader.py`

Expected: readable staged-in-spirit diff for models, manifest file, and test skeleton.

### Task 2: Implement Manifest Loader, Validation, And Override Merge

**Files:**
- Create: `H:\邢台观测站\CWR_project\meiyu_new\pipeline\manifest_loader.py`
- Modify: `H:\邢台观测站\CWR_project\meiyu_new\tests\test_manifest_loader.py`
- Modify: `H:\邢台观测站\CWR_project\meiyu_new\pipeline\config.py`

**Interfaces:**
- Consumes: `ManifestSpec`, `RunnerRuntimeConfig`, `ManifestInputRef`
- Produces: `load_manifest(path: Path) -> ManifestSpec`
- Produces: `build_runtime_config(path: Path, overrides: dict[str, object] | None = None) -> RunnerRuntimeConfig`
- Produces: `load_case_config(path: Path) -> PipelineCaseConfig` remains usable for legacy compatibility

- [ ] **Step 1: Expand tests for override merge and input resolution**

```python
from pathlib import Path

import pytest

from pipeline.manifest_loader import build_runtime_config


def test_build_runtime_config_allows_known_overrides():
    cfg = build_runtime_config(
        Path("manifests/cases/cra40_front2_20170622T18.yml"),
        overrides={
            "params.geometry.n_sections": 6,
            "params.subareas.start_section": 2,
        },
    )
    assert cfg.geometry.n_sections == 6
    assert cfg.subareas.start_section == 2


def test_build_runtime_config_rejects_unknown_override_key():
    with pytest.raises(ValueError, match="unknown override key"):
        build_runtime_config(
            Path("manifests/cases/cra40_front2_20170622T18.yml"),
            overrides={"params.geometry.unknown": 1},
        )


def test_build_runtime_config_resolves_logical_input_name():
    cfg = build_runtime_config(
        Path("manifests/cases/cra40_front2_20170622T18.yml")
    )
    assert cfg.resolved_inputs["rh"].endswith(
        "CRA40_RHU_2017062218_GLB_0P25_HOUR_V1_0_0.grib2"
    )
```

- [ ] **Step 2: Run the manifest loader test file**

Run: `conda run -n cwr_py312 python -m pytest tests/test_manifest_loader.py -v`

Expected: FAIL because `load_manifest` and `build_runtime_config` are not implemented.

- [ ] **Step 3: Implement the loader and merge helpers**

```python
from copy import deepcopy
from pathlib import Path

from pipeline.manifest_models import (
    ManifestGeometryParams,
    ManifestInputRef,
    ManifestProfilesParams,
    ManifestSpec,
    ManifestSubareasParams,
    RunnerRuntimeConfig,
)
from project_paths import cra40_file, project_root


ALLOWED_OVERRIDE_KEYS = {
    "steps.profiles",
    "steps.subareas",
    "params.geometry.n_sections",
    "params.geometry.delta_x",
    "params.subareas.start_section",
    "params.subareas.end_section",
    "params.profiles.variables",
}


def load_manifest(path: Path) -> ManifestSpec:
    parsed = _parse_manifest_yaml(path)
    return ManifestSpec(
        case_name=str(parsed["case_name"]),
        dataset=str(parsed["dataset"]),
        front_id=str(parsed["front_id"]),
        target_time=str(parsed["target_time"]),
        steps={k: bool(v) for k, v in parsed["steps"].items()},
        geometry=ManifestGeometryParams(**parsed["params"]["geometry"]),
        profiles=ManifestProfilesParams(
            variables=list(parsed["params"]["profiles"]["variables"])
        ),
        subareas=ManifestSubareasParams(**parsed["params"]["subareas"]),
        inputs={
            key: ManifestInputRef(
                logical_name=value.get("logical_name"),
                relative_path=value.get("relative_path"),
            )
            for key, value in parsed.get("inputs", {}).items()
        },
    )


def build_runtime_config(
    path: Path,
    overrides: dict[str, object] | None = None,
) -> RunnerRuntimeConfig:
    manifest = load_manifest(path)
    data = _manifest_to_mutable_dict(manifest)
    _apply_overrides(data, overrides or {})
    resolved_inputs = {
        key: _resolve_input_path(ref)
        for key, ref in manifest.inputs.items()
    }
    return RunnerRuntimeConfig(
        case_name=data["case_name"],
        dataset=data["dataset"],
        front_id=data["front_id"],
        target_time=data["target_time"],
        steps=data["steps"],
        geometry=ManifestGeometryParams(**data["params"]["geometry"]),
        profiles=ManifestProfilesParams(
            variables=list(data["params"]["profiles"]["variables"])
        ),
        subareas=ManifestSubareasParams(**data["params"]["subareas"]),
        resolved_inputs=resolved_inputs,
    )
```

- [ ] **Step 4: Keep `pipeline/config.py` as a compatibility entry**

```python
from dataclasses import dataclass, field
from pathlib import Path

from pipeline.manifest_loader import build_runtime_config


@dataclass(slots=True)
class PipelineCaseConfig:
    case_name: str
    dataset: str
    front_id: str
    target_time: str
    profile_variables: list[str] = field(default_factory=list)


def load_case_config(path: Path) -> PipelineCaseConfig:
    runtime = build_runtime_config(path)
    return PipelineCaseConfig(
        case_name=runtime.case_name,
        dataset=runtime.dataset,
        front_id=runtime.front_id,
        target_time=runtime.target_time,
        profile_variables=list(runtime.profiles.variables),
    )
```

- [ ] **Step 5: Run the manifest loader tests**

Run: `conda run -n cwr_py312 python -m pytest tests/test_manifest_loader.py -v`

Expected: PASS

- [ ] **Step 6: Compile the new loader files**

Run: `python -m py_compile pipeline\\manifest_models.py pipeline\\manifest_loader.py pipeline\\config.py tests\\test_manifest_loader.py`

Expected: no output

### Task 3: Convert Runner To Consume Manifest Runtime Config

**Files:**
- Modify: `H:\邢台观测站\CWR_project\meiyu_new\pipeline\runner.py`
- Modify: `H:\邢台观测站\CWR_project\meiyu_new\tests\test_runner_step.py`

**Interfaces:**
- Consumes: `RunnerRuntimeConfig`
- Produces: `run_case(cfg: RunnerRuntimeConfig) -> dict[str, object]`
- Produces: `run_case_from_manifest(path: Path, overrides: dict[str, object] | None = None) -> dict[str, object]`

- [ ] **Step 1: Add a runner test that starts from manifest**

```python
from pathlib import Path

from pipeline.runner import run_case_from_manifest


def test_run_case_from_manifest_returns_verified_summary():
    summary = run_case_from_manifest(
        Path("manifests/cases/cra40_front2_20170622T18.yml")
    )
    assert summary["geometry"]["centerline_points"] == 8
    assert summary["geometry"]["section_shape"] == [8, 9]
    assert summary["profiles"]["bundle_shape"] == [8, 9, 37]
    assert summary["subareas"]["selected_points"] == 48
    assert "front_mean" in summary["statistics"]
    assert "subarea_mean" in summary["statistics"]
```

- [ ] **Step 2: Run the targeted runner test**

Run: `conda run -n cwr_py312 python -m pytest tests/test_runner_step.py::test_run_case_from_manifest_returns_verified_summary -v`

Expected: FAIL because `run_case_from_manifest` does not exist.

- [ ] **Step 3: Update the runner to use runtime config and manifest inputs**

```python
from pathlib import Path

import numpy as np

from nc_compat import open_dataset_compat
from pipeline.core.paths import ensure_case_dirs
from pipeline.manifest_loader import build_runtime_config
from pipeline.steps.geometry import build_geometry_from_mask
from pipeline.steps.inventory import build_inventory_report
from pipeline.steps.masks import resolve_case_masks
from pipeline.steps.profiles import build_profile_bundle_from_field
from pipeline.steps.statistics import build_masked_mean
from pipeline.steps.subareas import build_subarea_mask


def run_case_from_manifest(
    path: Path,
    overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    return run_case(build_runtime_config(path, overrides=overrides))
```

- [ ] **Step 4: Replace hard-coded geometry and profile settings with config fields**

```python
geometry = build_geometry_from_mask(
    mask_bool,
    lons,
    lats,
    degree=cfg.geometry.degree,
    dense_points=cfg.geometry.dense_points,
    n_sections=cfg.geometry.n_sections,
    distance=cfg.geometry.distance,
    n_points=cfg.geometry.n_points,
    delta_x=cfg.geometry.delta_x,
)

profile_variable = cfg.profiles.variables[0]
rh_path = Path(cfg.resolved_inputs[profile_variable])
```

- [ ] **Step 5: Run the full runner test file**

Run: `conda run -n cwr_py312 python -m pytest tests/test_runner_step.py -v`

Expected: PASS

- [ ] **Step 6: Run py_compile on runner and tests**

Run: `python -m py_compile pipeline\\runner.py tests\\test_runner_step.py`

Expected: no output

### Task 4: Add Real Smoke Verification And Quickstart Doc Touch-Up

**Files:**
- Modify: `H:\邢台观测站\CWR_project\meiyu_new\docs\pipeline_quickstart_zh.md`
- Modify: `H:\邢台观测站\CWR_project\meiyu_new\docs\pipeline_architecture_mapping_zh.md`

**Interfaces:**
- Consumes: `run_case_from_manifest(path, overrides=None)`
- Produces: updated user-facing examples and maintainer-facing note that runner is now manifest-driven

- [ ] **Step 1: Run a real manifest-driven smoke command**

Run: `conda run -n cwr_py312 python -c "from pathlib import Path; from pipeline.runner import run_case_from_manifest; summary = run_case_from_manifest(Path('manifests/cases/cra40_front2_20170622T18.yml')); print(summary['geometry']); print(summary['profiles']); print(summary['subareas']); print(summary['statistics'])"`

Expected: printed summary including `centerline_points == 8`, `bundle_shape == [8, 9, 37]`, and both mean values.

- [ ] **Step 2: Update quickstart to use the manifest entry path**

```markdown
conda run -n cwr_py312 python -c "from pathlib import Path; from pipeline.runner import run_case_from_manifest; import pprint; pprint.pp(run_case_from_manifest(Path('manifests/cases/cra40_front2_20170622T18.yml')))"
```

- [ ] **Step 3: Update architecture doc to note manifest layer**

```markdown
- `manifests/cases/*.yml`：研究案例默认定义层。
- `pipeline/manifest_loader.py`：把案例声明解析成 runner 可执行配置。
- `pipeline/runner.py`：当前已改为消费 manifest 运行配置，而不是直接写死案例常量。
```

- [ ] **Step 4: Re-run targeted tests after doc-affecting code is stable**

Run: `conda run -n cwr_py312 python -m pytest tests/test_manifest_loader.py tests/test_runner_step.py -v`

Expected: PASS

- [ ] **Step 5: Review final local diff**

Run: `git diff -- pipeline/manifest_models.py pipeline/manifest_loader.py pipeline/config.py pipeline/runner.py tests/test_manifest_loader.py tests/test_runner_step.py docs/pipeline_quickstart_zh.md docs/pipeline_architecture_mapping_zh.md manifests/cases/cra40_front2_20170622T18.yml`

Expected: coherent manifest-layer diff with docs aligned to code.

- [ ] **Step 6: Record that git commit is intentionally skipped**

```text
Workspace is not a usable git repository in this directory, so verification replaces commit for this round.
```

## Self-Review

### Spec coverage

- Manifest file location and structure: covered by Task 1.
- Runtime overrides and known-field validation: covered by Task 2.
- Runner consuming parsed runtime config: covered by Task 3.
- Docs alignment and smoke verification: covered by Task 4.
- Out-of-scope items like `front1`, `ERA5`, `diagnostics`, output naming, and batch runner are not assigned tasks, matching the spec.

### Placeholder scan

- No `TODO`, `TBD`, or “implement later” placeholders remain.
- Each task includes exact file paths, commands, and concrete code snippets.

### Type consistency

- `ManifestSpec` is loaded by `load_manifest`.
- `RunnerRuntimeConfig` is returned by `build_runtime_config`.
- `run_case_from_manifest` consumes a manifest path and optional overrides.
- `run_case` consumes `RunnerRuntimeConfig`.

