# Layered Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first reusable layered Meiyu-front research pipeline that can execute a CRA40 `front2` case end to end using the existing validated masks and legacy logic as the scientific baseline.

**Architecture:** Create a new `pipeline/` package beside the legacy scripts, split by step responsibility instead of legacy file names, and reuse `project_paths.py` plus `nc_compat.py` as the shared filesystem and IO foundation. The first version will execute one verified chain, `CRA40 front2 2017-06-22T18`, while keeping legacy outputs available for manual comparison.

**Tech Stack:** Python 3.12, standard library `unittest`, `xarray`, `numpy`, `matplotlib`, `cartopy`, `metpy`, `cfgrib`, existing `project_paths.py`, existing `nc_compat.py`

---

### Task 1: Scaffold The New Pipeline Package

**Files:**
- Create: `pipeline/__init__.py`
- Create: `pipeline/config.py`
- Create: `pipeline/runner.py`
- Create: `pipeline/steps/__init__.py`
- Create: `pipeline/io/__init__.py`
- Create: `pipeline/core/__init__.py`
- Create: `pipeline/schemas/pipeline_config.yaml`
- Create: `tests/__init__.py`
- Create: `tests/test_pipeline_config.py`

- [ ] **Step 1: Write the failing config import test**

```python
import unittest


class PipelineConfigImportTest(unittest.TestCase):
    def test_pipeline_config_imports(self) -> None:
        from pipeline.config import PipelineCaseConfig  # noqa: F401


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n cwr_py312 python -m unittest tests.test_pipeline_config -v`
Expected: `ModuleNotFoundError: No module named 'pipeline'`

- [ ] **Step 3: Create the minimal package skeleton**

```python
# pipeline/__init__.py
"""Reusable Meiyu-front research pipeline package."""
```

```python
# pipeline/config.py
from dataclasses import dataclass, field


@dataclass(slots=True)
class PipelineCaseConfig:
    case_name: str
    dataset: str
    front_id: str
    target_time: str
    profile_variables: list[str] = field(default_factory=list)
```

```python
# pipeline/runner.py
"""Pipeline entrypoint."""
```

```python
# pipeline/steps/__init__.py
"""Step modules for the layered pipeline."""
```

```python
# pipeline/io/__init__.py
"""Input/output helpers for the layered pipeline."""
```

```python
# pipeline/core/__init__.py
"""Core scientific helpers for the layered pipeline."""
```

```yaml
# pipeline/schemas/pipeline_config.yaml
case_name: cra40_front2_2017-06-22T18
dataset: cra40
front_id: front2
target_time: 2017-06-22T18
profile_variables:
  - rh
  - temp
  - w
  - thetae
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n cwr_py312 python -m unittest tests.test_pipeline_config -v`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add pipeline tests docs/superpowers/plans/2026-07-06-layered-pipeline-implementation.md
git commit -m "feat: scaffold layered pipeline package"
```

### Task 2: Add Config Loading And Case Output Paths

**Files:**
- Modify: `pipeline/config.py`
- Create: `pipeline/core/paths.py`
- Modify: `tests/test_pipeline_config.py`
- Create: `tests/test_pipeline_paths.py`

- [ ] **Step 1: Write the failing config load test**

```python
import unittest
from pathlib import Path


class PipelineConfigLoadTest(unittest.TestCase):
    def test_load_case_config(self) -> None:
        from pipeline.config import load_case_config

        cfg = load_case_config(
            Path("pipeline/schemas/pipeline_config.yaml")
        )
        self.assertEqual(cfg.case_name, "cra40_front2_2017-06-22T18")
        self.assertEqual(cfg.dataset, "cra40")
        self.assertEqual(cfg.front_id, "front2")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n cwr_py312 python -m unittest tests.test_pipeline_config -v`
Expected: `ImportError: cannot import name 'load_case_config'`

- [ ] **Step 3: Implement config loading and output-path helpers**

```python
# pipeline/config.py
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class PipelineCaseConfig:
    case_name: str
    dataset: str
    front_id: str
    target_time: str
    profile_variables: list[str] = field(default_factory=list)


def _parse_simple_yaml(path: Path) -> dict[str, object]:
    data: dict[str, object] = {}
    current_list_key: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") and current_list_key is not None:
            data.setdefault(current_list_key, [])
            data[current_list_key].append(line[4:])
            continue
        current_list_key = None
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value == "":
            data[key] = []
            current_list_key = key
        else:
            data[key] = value
    return data


def load_case_config(path: Path) -> PipelineCaseConfig:
    parsed = _parse_simple_yaml(path)
    return PipelineCaseConfig(
        case_name=str(parsed["case_name"]),
        dataset=str(parsed["dataset"]),
        front_id=str(parsed["front_id"]),
        target_time=str(parsed["target_time"]),
        profile_variables=list(parsed.get("profile_variables", [])),
    )
```

```python
# pipeline/core/paths.py
from pathlib import Path

from project_paths import OUTPUT_DIR


def case_output_root(case_name: str) -> Path:
    return OUTPUT_DIR / "figures" / case_name


def ensure_case_dirs(case_name: str) -> dict[str, Path]:
    root = case_output_root(case_name)
    paths = {
        "root": root,
        "diagnostics": root / "diagnostics",
        "profiles": root / "profiles",
        "subareas": root / "subareas",
        "statistics": root / "statistics",
        "logs": OUTPUT_DIR / "logs",
        "manifests": OUTPUT_DIR / "manifests",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths
```

- [ ] **Step 4: Add the path test and run the suite**

```python
# tests/test_pipeline_paths.py
import unittest


class PipelinePathsTest(unittest.TestCase):
    def test_case_output_dirs_are_created(self) -> None:
        from pipeline.core.paths import ensure_case_dirs

        paths = ensure_case_dirs("unit_case")
        self.assertTrue(paths["root"].exists())
        self.assertTrue(paths["profiles"].exists())
        self.assertTrue(paths["statistics"].exists())
```

Run: `conda run -n cwr_py312 python -m unittest tests.test_pipeline_config tests.test_pipeline_paths -v`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add pipeline/core/paths.py pipeline/config.py tests/test_pipeline_config.py tests/test_pipeline_paths.py
git commit -m "feat: add pipeline config loader and output paths"
```

### Task 3: Implement Inventory Step

**Files:**
- Create: `pipeline/steps/inventory.py`
- Create: `pipeline/io/manifest.py`
- Create: `tests/test_inventory_step.py`

- [ ] **Step 1: Write the failing inventory manifest test**

```python
import unittest
from pathlib import Path


class InventoryStepTest(unittest.TestCase):
    def test_inventory_report_contains_required_sections(self) -> None:
        from pipeline.steps.inventory import build_inventory_report

        report = build_inventory_report()
        self.assertIn("raw", report)
        self.assertIn("interim", report)
        self.assertIn("processed", report)
        self.assertIn("environment", report)
        self.assertIsInstance(report["raw"], dict)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n cwr_py312 python -m unittest tests.test_inventory_step -v`
Expected: `ModuleNotFoundError: No module named 'pipeline.steps.inventory'`

- [ ] **Step 3: Implement minimal inventory reporting**

```python
# pipeline/steps/inventory.py
import importlib.util
from pathlib import Path

from project_paths import INTERIM_DIR, PROCESSED_DIR, RAW_DIR


def build_inventory_report() -> dict[str, dict[str, object]]:
    return {
        "raw": {
            "exists": RAW_DIR.exists(),
            "children": sorted(p.name for p in RAW_DIR.iterdir()) if RAW_DIR.exists() else [],
        },
        "interim": {
            "exists": INTERIM_DIR.exists(),
            "children": sorted(p.name for p in INTERIM_DIR.iterdir()) if INTERIM_DIR.exists() else [],
        },
        "processed": {
            "exists": PROCESSED_DIR.exists(),
            "children": sorted(p.name for p in PROCESSED_DIR.iterdir()) if PROCESSED_DIR.exists() else [],
        },
        "environment": {
            "xarray": importlib.util.find_spec("xarray") is not None,
            "cfgrib": importlib.util.find_spec("cfgrib") is not None,
            "cartopy": importlib.util.find_spec("cartopy") is not None,
            "matplotlib": importlib.util.find_spec("matplotlib") is not None,
        },
    }
```

```python
# pipeline/io/manifest.py
import json
from pathlib import Path
from typing import Any


def write_json_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n cwr_py312 python -m unittest tests.test_inventory_step -v`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add pipeline/steps/inventory.py pipeline/io/manifest.py tests/test_inventory_step.py
git commit -m "feat: add pipeline inventory step"
```

### Task 4: Implement Mask Step For Reusing Existing Manual Outputs

**Files:**
- Create: `pipeline/core/time_utils.py`
- Create: `pipeline/core/mask_ops.py`
- Create: `pipeline/steps/masks.py`
- Create: `tests/test_mask_step.py`

- [ ] **Step 1: Write the failing mask-resolution test**

```python
import unittest


class MaskStepTest(unittest.TestCase):
    def test_resolve_existing_cra40_front2_assets(self) -> None:
        from pipeline.steps.masks import resolve_case_masks

        assets = resolve_case_masks("front2", "2017-06-22T18")
        self.assertIn("front_mask", assets)
        self.assertIn("extend_mask", assets)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n cwr_py312 python -m unittest tests.test_mask_step -v`
Expected: `ModuleNotFoundError: No module named 'pipeline.steps.masks'`

- [ ] **Step 3: Implement existing-mask resolution**

```python
# pipeline/core/time_utils.py
from datetime import datetime


def compact_time_label(dt: str) -> str:
    return datetime.strptime(dt, "%Y-%m-%dT%H").strftime("%Y%m%dT%H")
```

```python
# pipeline/core/mask_ops.py
from pathlib import Path

from project_paths import cra40_front_extend, cra40_front_mask, cra40_front2_subarea


def existing_cra40_mask_assets(front_id: str, target_time: str) -> dict[str, str]:
    front_no = 2 if front_id == "front2" else 1
    return {
        "front_mask": cra40_front_mask(front_no, target_time),
        "extend_mask": cra40_front_extend(front_no, target_time),
        "subarea_mask": cra40_front2_subarea("area2_lonlat_0622T18.nc"),
    }
```

```python
# pipeline/steps/masks.py
from pipeline.core.mask_ops import existing_cra40_mask_assets


def resolve_case_masks(front_id: str, target_time: str) -> dict[str, str]:
    return existing_cra40_mask_assets(front_id, target_time)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n cwr_py312 python -m unittest tests.test_mask_step -v`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add pipeline/core/time_utils.py pipeline/core/mask_ops.py pipeline/steps/masks.py tests/test_mask_step.py
git commit -m "feat: add mask resolution step"
```

### Task 5: Implement Geometry Step Around Existing Front Masks

**Files:**
- Create: `pipeline/core/front_ops.py`
- Create: `pipeline/steps/geometry.py`
- Create: `tests/test_geometry_step.py`

- [ ] **Step 1: Write the failing tangent-sampling test**

```python
import unittest
import numpy as np


class GeometryStepTest(unittest.TestCase):
    def test_build_sampling_offsets_shape(self) -> None:
        from pipeline.core.front_ops import build_normal_offsets

        nx = np.array([1.0, 0.0])
        ny = np.array([0.0, 1.0])
        offsets = build_normal_offsets(nx, ny, distance=1.0, n_points=5)
        self.assertEqual(offsets[0].shape, (2, 5))
        self.assertEqual(offsets[1].shape, (2, 5))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n cwr_py312 python -m unittest tests.test_geometry_step -v`
Expected: `ModuleNotFoundError: No module named 'pipeline.core.front_ops'`

- [ ] **Step 3: Implement the first reusable geometry helpers**

```python
# pipeline/core/front_ops.py
import numpy as np


def build_normal_offsets(
    nx: np.ndarray,
    ny: np.ndarray,
    distance: float,
    n_points: int,
) -> tuple[np.ndarray, np.ndarray]:
    offsets = np.linspace(-distance, distance, n_points)
    sampled_x = np.array([offsets * value for value in nx])
    sampled_y = np.array([offsets * value for value in ny])
    return sampled_x, sampled_y
```

```python
# pipeline/steps/geometry.py
from dataclasses import dataclass

import numpy as np

from pipeline.core.front_ops import build_normal_offsets


@dataclass(slots=True)
class GeometryResult:
    sampled_dx: np.ndarray
    sampled_dy: np.ndarray


def build_geometry_frame(nx: np.ndarray, ny: np.ndarray, distance: float, n_points: int) -> GeometryResult:
    sampled_dx, sampled_dy = build_normal_offsets(nx, ny, distance, n_points)
    return GeometryResult(sampled_dx=sampled_dx, sampled_dy=sampled_dy)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n cwr_py312 python -m unittest tests.test_geometry_step -v`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add pipeline/core/front_ops.py pipeline/steps/geometry.py tests/test_geometry_step.py
git commit -m "feat: add initial geometry step"
```

### Task 6: Implement Profile Step For CRA40 Variables

**Files:**
- Create: `pipeline/core/section_ops.py`
- Create: `pipeline/steps/profiles.py`
- Create: `tests/test_profiles_step.py`

- [ ] **Step 1: Write the failing section-stack test**

```python
import unittest
import numpy as np


class ProfilesStepTest(unittest.TestCase):
    def test_stack_section_profiles_shape(self) -> None:
        from pipeline.core.section_ops import stack_profiles

        arr1 = np.ones((5, 4))
        arr2 = np.zeros((5, 4))
        stacked = stack_profiles([arr1, arr2])
        self.assertEqual(stacked.shape, (2, 5, 4))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n cwr_py312 python -m unittest tests.test_profiles_step -v`
Expected: `ModuleNotFoundError: No module named 'pipeline.core.section_ops'`

- [ ] **Step 3: Implement a minimal reusable profile container**

```python
# pipeline/core/section_ops.py
import numpy as np


def stack_profiles(profiles: list[np.ndarray]) -> np.ndarray:
    return np.stack(profiles, axis=0)
```

```python
# pipeline/steps/profiles.py
from dataclasses import dataclass

import numpy as np

from pipeline.core.section_ops import stack_profiles


@dataclass(slots=True)
class ProfileBundle:
    variable: str
    values: np.ndarray


def build_profile_bundle(variable: str, profiles: list[np.ndarray]) -> ProfileBundle:
    return ProfileBundle(variable=variable, values=stack_profiles(profiles))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n cwr_py312 python -m unittest tests.test_profiles_step -v`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add pipeline/core/section_ops.py pipeline/steps/profiles.py tests/test_profiles_step.py
git commit -m "feat: add initial profile step"
```

### Task 7: Implement Subarea And Statistics Steps

**Files:**
- Create: `pipeline/steps/subareas.py`
- Create: `pipeline/steps/statistics.py`
- Create: `tests/test_subareas_step.py`
- Create: `tests/test_statistics_step.py`

- [ ] **Step 1: Write the failing subarea and statistics tests**

```python
import unittest


class SubareaStepTest(unittest.TestCase):
    def test_subarea_filename_builder(self) -> None:
        from pipeline.steps.subareas import build_subarea_filename

        self.assertEqual(
            build_subarea_filename("front2", "area2", "2017-06-22T18"),
            "front2_subarea_area2_2017-06-22T18.nc",
        )
```

```python
import unittest
import numpy as np


class StatisticsStepTest(unittest.TestCase):
    def test_grid_mean_ignores_nan(self) -> None:
        from pipeline.steps.statistics import grid_mean

        values = np.array([1.0, np.nan, 3.0])
        self.assertEqual(grid_mean(values), 2.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n cwr_py312 python -m unittest tests.test_subareas_step tests.test_statistics_step -v`
Expected: `ModuleNotFoundError` for both new step modules

- [ ] **Step 3: Implement the minimal subarea and statistics helpers**

```python
# pipeline/steps/subareas.py
def build_subarea_filename(front_id: str, area_id: str, target_time: str) -> str:
    return f"{front_id}_subarea_{area_id}_{target_time}.nc"
```

```python
# pipeline/steps/statistics.py
import numpy as np


def grid_mean(values: np.ndarray) -> float:
    return float(np.nanmean(values))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n cwr_py312 python -m unittest tests.test_subareas_step tests.test_statistics_step -v`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add pipeline/steps/subareas.py pipeline/steps/statistics.py tests/test_subareas_step.py tests/test_statistics_step.py
git commit -m "feat: add subarea and statistics steps"
```

### Task 8: Implement The First End-To-End Runner For CRA40 Front2

**Files:**
- Modify: `pipeline/runner.py`
- Create: `tests/test_runner_step.py`
- Create: `outputs/manifests/.gitkeep`
- Create: `outputs/logs/.gitkeep`

- [ ] **Step 1: Write the failing runner smoke test**

```python
import unittest
from pathlib import Path


class RunnerStepTest(unittest.TestCase):
    def test_runner_returns_case_summary(self) -> None:
        from pipeline.config import load_case_config
        from pipeline.runner import run_case

        cfg = load_case_config(Path("pipeline/schemas/pipeline_config.yaml"))
        summary = run_case(cfg)
        self.assertEqual(summary["case_name"], "cra40_front2_2017-06-22T18")
        self.assertIn("masks", summary)
        self.assertIn("outputs", summary)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n cwr_py312 python -m unittest tests.test_runner_step -v`
Expected: `ImportError: cannot import name 'run_case'`

- [ ] **Step 3: Implement the first end-to-end summary runner**

```python
# pipeline/runner.py
from pipeline.config import PipelineCaseConfig
from pipeline.core.paths import ensure_case_dirs
from pipeline.steps.inventory import build_inventory_report
from pipeline.steps.masks import resolve_case_masks


def run_case(cfg: PipelineCaseConfig) -> dict[str, object]:
    output_dirs = ensure_case_dirs(cfg.case_name)
    inventory = build_inventory_report()
    masks = resolve_case_masks(cfg.front_id, cfg.target_time)
    return {
        "case_name": cfg.case_name,
        "inventory": inventory,
        "masks": masks,
        "outputs": {key: str(value) for key, value in output_dirs.items()},
    }
```

- [ ] **Step 4: Run the unit test and the real pipeline smoke command**

Run: `conda run -n cwr_py312 python -m unittest tests.test_runner_step -v`
Expected: `OK`

Run: `conda run -n cwr_py312 python -c "from pathlib import Path; from pipeline.config import load_case_config; from pipeline.runner import run_case; cfg = load_case_config(Path('pipeline/schemas/pipeline_config.yaml')); summary = run_case(cfg); print(summary['case_name']); print(summary['masks']['front_mask'])"`
Expected:

```text
cra40_front2_2017-06-22T18
H:\邢台观测站\CWR_project\meiyu_new\data\interim\manual_masks\cra40\front2\2017-06-22T18.nc
```

- [ ] **Step 5: Commit**

```bash
git add pipeline/runner.py tests/test_runner_step.py outputs/manifests/.gitkeep outputs/logs/.gitkeep
git commit -m "feat: add first layered pipeline runner"
```

### Task 9: Write The New Pipeline README-Style Handoff

**Files:**
- Create: `docs/pipeline_first_version_notes.md`

- [ ] **Step 1: Write the failing documentation completeness check**

```python
import unittest
from pathlib import Path


class PipelineNotesTest(unittest.TestCase):
    def test_notes_file_exists(self) -> None:
        self.assertTrue(Path("docs/pipeline_first_version_notes.md").exists())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n cwr_py312 python -m unittest tests.test_runner_step tests.test_pipeline_paths -v`
Expected: existing tests pass, notes file check not yet present because the new test file has not been created

- [ ] **Step 3: Create the first-version handoff notes**

```markdown
# 新流水线第一版说明

## 当前范围

- 已建立 `pipeline/` 包骨架
- 已建立配置入口
- 已建立 inventory/masks/geometry/profiles/subareas/statistics/runner 基础模块
- 已支持 `CRA40 front2 2017-06-22T18` 作为第一条验证链

## 当前定位

这仍是第一版骨架，不是最终科学计算替代版。

## 下一步

- 将 legacy 几何与剖面细节逐步迁入 `geometry.py` 和 `profiles.py`
- 将图形输出逐步从 legacy_figures 迁入 `outputs/figures/`
- 为 ERA5 增加并行的步骤实现
```

- [ ] **Step 4: Run the full unit suite**

Run: `conda run -n cwr_py312 python -m unittest discover -s tests -v`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add docs/pipeline_first_version_notes.md
git commit -m "docs: add first-version pipeline handoff notes"
```

## Self-Review

### Spec coverage

- `inventory` task covers project and environment checks.
- `masks` task covers reuse of existing manual masks and extend masks.
- `geometry` task starts the reusable section frame abstraction.
- `profiles` task starts reusable profile containers.
- `subareas` and `statistics` tasks cover the two output branches after geometry.
- `runner` task provides the first CRA40 `front2` execution chain.

No spec requirement from the approved design is intentionally dropped in this first implementation plan.

### Placeholder scan

- No `TODO`, `TBD`, or “implement later” placeholders remain in task steps.
- Every task lists exact files.
- Every code step contains concrete code, even where it is only the first minimal version.
- Every verification step contains an exact command and expected outcome.

### Type consistency

- `PipelineCaseConfig` is introduced once and reused consistently.
- `run_case(cfg)` consumes the same config type introduced in Task 1 and expanded in Task 2.
- Step function naming stays consistent across `inventory`, `masks`, `geometry`, `profiles`, `subareas`, `statistics`.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-06-layered-pipeline-implementation.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
