# Front1 V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在新流水线中打通 `CRA40 + front1 + 2017-06-22T18 + rh/temp/w` 的单个可研究个例，使研究者可以通过统一 manifest/runner 生成 front1 的几何、剖面、子区域、统计和最小诊断图件。

**Architecture:** 延续当前 front2 已验证主线，采用“保守桥接式”扩展：先显式认证 front1 掩膜资产，再在 `masks -> geometry -> profiles -> subareas -> statistics -> diagnostics -> runner` 链路中逐层加 front1 与多变量支持。避免把 `front1` 静默映射为 `front2`，避免把 runner 扩展成散乱的特判脚本。

**Tech Stack:** Python 3.12 (`cwr_py312`), unittest/pytest, xarray/numpy, 现有 `pipeline.steps.*` 与 `project_paths.py` 路径体系, manifest YAML 子集解析器

## Global Constraints

- 只支持 `CRA40`
- 只支持 `front1`
- 只支持 `2017-06-22T18`
- `ERA5` 本轮不接入
- `front1` 资产必须显式认证，不允许静默复用 `front2`
- 几何层继续复用现有 `GeometryResult`
- 剖面变量仅扩展到 `rh / temp / w`
- 子区域优先围绕“主掩膜 + geometry 动态生成”
- diagnostics 只做最小可研究图件，不做批量总调度器
- runner 顶层输出继续保持结构化摘要，不回退到 legacy 大脚本式打印

---

## File Structure

- `pipeline/core/mask_ops.py`
  负责显式解析 CRA40 front1 掩膜、extend 掩膜、可选已有子区域掩膜，并对缺失资产给出明确错误。
- `pipeline/steps/masks.py`
  负责根据 `front_id + target_time` 选择 front1/front2 资产解析分支，但只暴露统一的 `resolve_case_masks(...)` 接口。
- `pipeline/core/cra40_fields.py`（新建）
  负责 `rh / temp / w` 三个变量到 CRA40 输入文件、变量名、垂直维名的映射与取数，避免散落到 runner。
- `pipeline/steps/diagnostics.py`（新建）
  负责最小诊断图件生成，只消费 geometry/profile/subarea/statistics 结果，不直接掺入底层算法。
- `pipeline/manifest_loader.py`
  负责 front1 manifest、变量列表、diagnostics 开关与输入路径解析。
- `pipeline/runner.py`
  负责把 front1 V1 主线串起来，支持 `rh/temp/w`，并在顶层摘要中保持稳定结构。
- `manifests/cases/cra40_front1_20170622T18.yml`（新建）
  front1 V1 的统一研究入口。
- `tests/test_mask_step.py`
  增补 front1 资产认证测试。
- `tests/test_manifest_loader.py`
  增补 front1 manifest 与多变量 override 测试。
- `tests/test_profiles_step.py`
  增补多变量读取辅助逻辑测试。
- `tests/test_runner_step.py`
  增补 front1 V1 集成级摘要测试与 CLI 调用测试。
- `tests/test_diagnostics_step.py`（新建）
  验证最小图件成功落盘。
- `docs/pipeline_quickstart_zh.md`
  增补 front1 V1 的运行方式。
- `docs/pipeline_architecture_mapping_zh.md`
  补充新旧映射中 front1 V1 的落点与边界。

### Task 1: 认证 Front1 掩膜资产边界

**Files:**
- Modify: `pipeline/core/mask_ops.py`
- Modify: `pipeline/steps/masks.py`
- Test: `tests/test_mask_step.py`

**Interfaces:**
- Consumes: `project_paths.cra40_front_mask(front_no: int, dt: str) -> str`, `project_paths.cra40_front_extend(front_no: int, dt: str) -> str`
- Produces: `existing_cra40_front1_mask_assets(target_time: str) -> dict[str, str]`, `resolve_case_masks(front_id: str, target_time: str) -> dict[str, str]`

- [ ] **Step 1: 写 front1 掩膜资产失败测试**

```python
def test_resolve_existing_cra40_front1_assets(self) -> None:
    from pipeline.steps.masks import resolve_case_masks

    assets = resolve_case_masks("front1", "2017-06-22T18")
    self.assertIn("front_mask", assets)
    self.assertIn("extend_mask", assets)
    self.assertTrue(assets["front_mask"].endswith("front1\\2017-06-22T18.nc"))
    self.assertTrue(assets["extend_mask"].endswith("front1\\extend\\2017-06-22T18.nc"))


def test_front1_mask_assets_raise_when_mask_is_missing(self) -> None:
    from pipeline.steps.masks import resolve_case_masks

    with patch("pipeline.core.mask_ops.cra40_front_mask", return_value="H:\\fake\\front1_missing.nc"):
        with self.assertRaises(FileNotFoundError):
            resolve_case_masks("front1", "2017-06-22T18")
```

- [ ] **Step 2: 运行测试确认当前失败**

Run: `conda run -n cwr_py312 python -m pytest tests/test_mask_step.py -v`
Expected: FAIL，提示 `front1` 目前不受支持或找不到 `existing_cra40_front1_mask_assets`

- [ ] **Step 3: 写最小 front1 资产解析实现**

```python
def existing_cra40_front1_mask_assets(target_time: str) -> dict[str, str]:
    return {
        "front_mask": _require_existing(cra40_front_mask(1, target_time)),
        "extend_mask": _require_existing(cra40_front_extend(1, target_time)),
    }


def resolve_case_masks(front_id: str, target_time: str) -> dict[str, str]:
    if front_id == "front1":
        return existing_cra40_front1_mask_assets(target_time)
    if front_id == "front2":
        return existing_cra40_front2_mask_assets(target_time)
    raise ValueError(f"unsupported front id: {front_id}")
```

- [ ] **Step 4: 重新运行掩膜测试确认通过**

Run: `conda run -n cwr_py312 python -m pytest tests/test_mask_step.py -v`
Expected: PASS，front1/front2 资产都能被显式区分

- [ ] **Step 5: 提交**

```bash
git add tests/test_mask_step.py pipeline/core/mask_ops.py pipeline/steps/masks.py
git commit -m "feat: add explicit front1 mask asset resolution"
```

### Task 2: 建立 CRA40 多变量读取映射

**Files:**
- Create: `pipeline/core/cra40_fields.py`
- Modify: `pipeline/manifest_loader.py`
- Test: `tests/test_manifest_loader.py`
- Test: `tests/test_profiles_step.py`

**Interfaces:**
- Consumes: `project_paths.cra40_file(filename: str) -> str`
- Produces: `resolve_cra40_profile_input(variable: str) -> Path`, `read_cra40_profile_cube(variable: str, input_path: Path, lats: np.ndarray, lons: np.ndarray) -> tuple[np.ndarray, np.ndarray]`

- [ ] **Step 1: 写变量映射失败测试**

```python
def test_resolve_cra40_profile_input_supports_front1_v1_variables(self) -> None:
    from pipeline.core.cra40_fields import resolve_cra40_profile_input

    self.assertTrue(str(resolve_cra40_profile_input("rh")).endswith(".grib2"))
    self.assertTrue(str(resolve_cra40_profile_input("temp")).endswith(".grib2"))
    self.assertTrue(str(resolve_cra40_profile_input("w")).endswith(".grib2"))


def test_resolve_cra40_profile_input_rejects_unknown_variable(self) -> None:
    from pipeline.core.cra40_fields import resolve_cra40_profile_input

    with self.assertRaisesRegex(ValueError, "unsupported CRA40 profile variable"):
        resolve_cra40_profile_input("thetae")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `conda run -n cwr_py312 python -m pytest tests/test_manifest_loader.py tests/test_profiles_step.py -v`
Expected: FAIL，提示 `pipeline.core.cra40_fields` 不存在或变量解析接口不存在

- [ ] **Step 3: 写最小变量映射实现**

```python
CRA40_PROFILE_SPECS = {
    "rh": {"filename": "CRA40_RHU_2017062218_GLB_0P25_HOUR_V1_0_0.grib2", "field": "r", "level": "isobaricInhPa"},
    "temp": {"filename": "CRA40_TMP_2017062218_GLB_0P25_HOUR_V1_0_0.grib2", "field": "t", "level": "isobaricInhPa"},
    "w": {"filename": "CRA40_VVEL_2017062218_GLB_0P25_HOUR_V1_0_0.grib2", "field": "w", "level": "isobaricInhPa"},
}


def resolve_cra40_profile_input(variable: str) -> Path:
    try:
        spec = CRA40_PROFILE_SPECS[variable]
    except KeyError as exc:
        raise ValueError(f"unsupported CRA40 profile variable: {variable}") from exc
    return Path(cra40_file(spec["filename"]))
```

- [ ] **Step 4: 写最小取数实现并接入测试**

```python
def read_cra40_profile_cube(
    variable: str,
    input_path: Path,
    lats: np.ndarray,
    lons: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    spec = CRA40_PROFILE_SPECS[variable]
    ds = open_dataset_compat(input_path)
    cube = ds[spec["field"]].isel({spec["level"]: slice(0, 37)}).sel(
        latitude=lats,
        longitude=lons,
        method="nearest",
    ).values
    levels = ds[spec["level"]].isel({spec["level"]: slice(0, 37)}).values
    return cube, levels
```

- [ ] **Step 5: 重新运行映射测试确认通过**

Run: `conda run -n cwr_py312 python -m pytest tests/test_manifest_loader.py tests/test_profiles_step.py -v`
Expected: PASS，`rh/temp/w` 三个变量都可解析

- [ ] **Step 6: 提交**

```bash
git add pipeline/core/cra40_fields.py pipeline/manifest_loader.py tests/test_manifest_loader.py tests/test_profiles_step.py
git commit -m "feat: add cra40 multi-variable profile field resolver"
```

### Task 3: 扩展 Runner 支持 Front1 V1 与多变量剖面

**Files:**
- Modify: `pipeline/runner.py`
- Modify: `pipeline/manifest_loader.py`
- Create: `manifests/cases/cra40_front1_20170622T18.yml`
- Test: `tests/test_runner_step.py`

**Interfaces:**
- Consumes: `resolve_case_masks(front_id: str, target_time: str) -> dict[str, str]`, `read_cra40_profile_cube(variable: str, input_path: Path, lats: np.ndarray, lons: np.ndarray) -> tuple[np.ndarray, np.ndarray]`
- Produces: `run_case(cfg) -> dict[str, object]`, `run_case_from_manifest(path: Path, overrides: dict[str, object] | None = None) -> dict[str, object]`

- [ ] **Step 1: 写 front1 runner 失败测试**

```python
def test_run_case_from_front1_manifest_returns_multivariable_summary(self) -> None:
    from pipeline.runner import run_case_from_manifest

    summary = run_case_from_manifest(
        Path("manifests/cases/cra40_front1_20170622T18.yml")
    )

    self.assertEqual(summary["case_name"], "cra40_front1_20170622T18")
    self.assertEqual(summary["geometry"]["section_shape"], [8, 9])
    self.assertEqual(set(summary["profiles"]["variables"].keys()), {"rh", "temp", "w"})
    self.assertEqual(summary["statistics"]["status"], "completed")
```

- [ ] **Step 2: 运行 front1 runner 测试确认失败**

Run: `conda run -n cwr_py312 python -m pytest tests/test_runner_step.py -v`
Expected: FAIL，提示 front1 manifest 缺失或 runner 仍只支持 front2/rh

- [ ] **Step 3: 写 manifest 与 runner 最小扩展**

```python
def _validate_supported_case(cfg) -> None:
    supported = {
        ("cra40", "front2", "2017-06-22T18"),
        ("cra40", "front1", "2017-06-22T18"),
    }
    case_key = (cfg.dataset, cfg.front_id, cfg.target_time)
    if case_key not in supported:
        raise ValueError("runner only supports the verified CRA40 front1/front2 2017-06-22T18 pipeline in this version")


def _get_profile_variables(cfg: Any) -> list[str]:
    profiles = getattr(cfg, "profiles", None)
    variables = getattr(profiles, "variables", None) if profiles is not None else None
    if not variables:
        raise ValueError("runner requires at least one profile variable")
    return [str(variable) for variable in variables]
```

- [ ] **Step 4: 按变量循环生成 profiles/statistics 摘要**

```python
profile_summaries = {}
statistics_by_variable = {}
for variable in profile_variables:
    input_path = _get_profile_input_path(cfg, variable)
    field3d, levels = read_cra40_profile_cube(variable, input_path, lats, lons)
    if profiles_enabled:
        bundle = build_profile_bundle_from_field(variable, field3d, levels, lats, lons, geometry)
        profile_summaries[variable] = {
            "bundle_shape": list(bundle.values.shape),
            "status": "completed",
        }
    if statistics_enabled:
        statistics_by_variable[variable] = {
            "front_mean": float(build_masked_mean(variable, field3d[0], mask_bool)),
        }
```

- [ ] **Step 5: 重新运行 runner 测试确认 front1 主线通过**

Run: `conda run -n cwr_py312 python -m pytest tests/test_runner_step.py -v`
Expected: PASS，`front1` manifest 可以输出多变量结构化摘要

- [ ] **Step 6: 提交**

```bash
git add pipeline/runner.py pipeline/manifest_loader.py manifests/cases/cra40_front1_20170622T18.yml tests/test_runner_step.py
git commit -m "feat: add front1 v1 runner baseline"
```

### Task 4: 接通 Front1 子区域与完整区统计

**Files:**
- Modify: `pipeline/runner.py`
- Modify: `tests/test_runner_step.py`
- Test: `tests/test_statistics_step.py`
- Test: `tests/test_subareas_step.py`

**Interfaces:**
- Consumes: `build_subarea_mask(mask_lon2d, mask_lat2d, mask_bool, geometry, start_section: int, end_section: int) -> np.ndarray`, `build_masked_mean(variable: str, field: np.ndarray, mask: np.ndarray) -> float`
- Produces: runner summary 中的 `subareas` 和 `statistics["variables"][variable]`

- [ ] **Step 1: 写 front1 子区域统计失败测试**

```python
def test_front1_summary_contains_subarea_statistics_for_each_variable(self) -> None:
    summary = self._run_front1_manifest()

    self.assertEqual(summary["subareas"]["status"], "completed")
    for variable in ("rh", "temp", "w"):
        item = summary["statistics"]["variables"][variable]
        self.assertIn("front_mean", item)
        self.assertIn("subarea_mean", item)
```

- [ ] **Step 2: 运行相关测试确认失败**

Run: `conda run -n cwr_py312 python -m pytest tests/test_runner_step.py tests/test_statistics_step.py tests/test_subareas_step.py -v`
Expected: FAIL，front1 摘要里尚无逐变量子区域统计结构

- [ ] **Step 3: 最小实现逐变量统计摘要**

```python
statistics_summary = {
    "enabled": True,
    "status": "completed",
    "variables": statistics_by_variable,
}

if subareas_enabled:
    for variable in profile_variables:
        statistics_by_variable[variable]["subarea_mean"] = float(
            build_masked_mean(variable, field_cache[variable][0], submask)
        )
```

- [ ] **Step 4: 重新运行统计与子区域测试确认通过**

Run: `conda run -n cwr_py312 python -m pytest tests/test_runner_step.py tests/test_statistics_step.py tests/test_subareas_step.py -v`
Expected: PASS，front1 主区域与子区域统计都可输出

- [ ] **Step 5: 提交**

```bash
git add pipeline/runner.py tests/test_runner_step.py tests/test_statistics_step.py tests/test_subareas_step.py
git commit -m "feat: add front1 subarea statistics summaries"
```

### Task 5: 增加最小 Diagnostics 图件落盘

**Files:**
- Create: `pipeline/steps/diagnostics.py`
- Modify: `pipeline/runner.py`
- Create: `tests/test_diagnostics_step.py`
- Modify: `tests/test_runner_step.py`

**Interfaces:**
- Consumes: `GeometryResult`, `dict[str, ProfileBundle] | dict[str, dict[str, object]]`, `dict[str, object]` statistics, `ensure_case_dirs(case_name: str) -> dict[str, Path]`
- Produces: `write_front_diagnostics(case_name: str, output_dir: Path, geometry: GeometryResult, profile_bundles: dict[str, ProfileBundle], statistics: dict[str, object]) -> list[str]`

- [ ] **Step 1: 写 diagnostics 落盘失败测试**

```python
def test_write_front_diagnostics_creates_png_files(self) -> None:
    outputs = write_front_diagnostics(
        case_name="demo_case",
        output_dir=self.tmp_path,
        geometry=self.geometry,
        profile_bundles={"rh": self.bundle},
        statistics={"variables": {"rh": {"front_mean": 80.0, "subarea_mean": 82.0}}},
    )
    self.assertGreaterEqual(len(outputs), 1)
    for output in outputs:
        self.assertTrue(Path(output).exists())
        self.assertTrue(str(output).endswith(".png"))
```

- [ ] **Step 2: 运行 diagnostics 测试确认失败**

Run: `conda run -n cwr_py312 python -m pytest tests/test_diagnostics_step.py -v`
Expected: FAIL，提示 `pipeline.steps.diagnostics` 不存在

- [ ] **Step 3: 写最小图件输出实现**

```python
def write_front_diagnostics(... ) -> list[str]:
    figure_paths = []
    figure_path = output_dir / f"{case_name}_profiles_overview.png"
    fig, axes = plt.subplots(len(profile_bundles), 1, figsize=(8, 3 * len(profile_bundles)))
    ...
    fig.savefig(figure_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    figure_paths.append(str(figure_path))
    return figure_paths
```

- [ ] **Step 4: 在 runner 中受控接入 diagnostics**

```python
diagnostics_enabled = _is_step_enabled(cfg, "diagnostics")
if diagnostics_enabled:
    figure_paths = write_front_diagnostics(
        cfg.case_name,
        output_dirs["figures"],
        geometry,
        profile_bundle_cache,
        statistics_summary,
    )
    diagnostics_summary = {"status": "completed", "files": figure_paths}
else:
    diagnostics_summary = {"enabled": False, "status": "skipped"}
```

- [ ] **Step 5: 重新运行 diagnostics 与 runner 测试**

Run: `conda run -n cwr_py312 python -m pytest tests/test_diagnostics_step.py tests/test_runner_step.py -v`
Expected: PASS，runner 摘要包含 diagnostics 文件列表

- [ ] **Step 6: 提交**

```bash
git add pipeline/steps/diagnostics.py pipeline/runner.py tests/test_diagnostics_step.py tests/test_runner_step.py
git commit -m "feat: add front1 minimal diagnostics outputs"
```

### Task 6: 补齐文档与真实 front1 冒烟

**Files:**
- Modify: `docs/pipeline_quickstart_zh.md`
- Modify: `docs/pipeline_architecture_mapping_zh.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: `python -m pipeline.runner --manifest manifests/cases/cra40_front1_20170622T18.yml`
- Produces: front1 V1 的用户运行说明、旧工程到新流水线映射补充、最终真实冒烟记录

- [ ] **Step 1: 写 front1 使用说明补充内容**

```markdown
## Front1 V1 运行

```bash
conda run -n cwr_py312 python -m pipeline.runner --manifest manifests/cases/cra40_front1_20170622T18.yml
```

默认输出：
- front1 几何摘要
- `rh / temp / w` 三变量剖面摘要
- front1 子区域统计摘要
- 最小 diagnostics 图件
```

- [ ] **Step 2: 写旧工程映射补充内容**

```markdown
- `frontal1_process_rh.py` / `frontal1_process_w.py`
  现对应新流水线中的 `geometry + profiles + diagnostics`
- `frontal1_process_SelectSubArea.py`
  现对应新流水线中的 `subareas + statistics`
```

- [ ] **Step 3: 运行真实 front1 冒烟**

Run: `conda run -n cwr_py312 python -m pipeline.runner --manifest manifests/cases/cra40_front1_20170622T18.yml`
Expected: return code `0`，stdout 输出 JSON 摘要，`outputs/.../figures` 下生成至少一张 `.png`

- [ ] **Step 4: 回归测试**

Run: `conda run -n cwr_py312 python -m pytest tests/test_mask_step.py tests/test_manifest_loader.py tests/test_profiles_step.py tests/test_statistics_step.py tests/test_subareas_step.py tests/test_runner_step.py tests/test_diagnostics_step.py -v`
Expected: PASS，front2 既有能力不回退，front1 V1 新能力稳定

- [ ] **Step 5: 提交**

```bash
git add docs/pipeline_quickstart_zh.md docs/pipeline_architecture_mapping_zh.md README.md
git commit -m "docs: add front1 v1 usage and mapping guide"
```

## Self-Review

### 1. Spec coverage

- `front1 资产必须显式认证`：Task 1 覆盖
- `geometry 继续复用 GeometryResult`：Task 3 依旧复用，未引入新几何对象
- `rh / temp / w` 三变量进入 profiles：Task 2 与 Task 3 覆盖
- `front1 子区域掩膜/统计`：Task 4 覆盖
- `最小 diagnostics 图件`：Task 5 覆盖
- `manifest / runner 统一入口`：Task 3 覆盖
- `quickstart 与映射文档`：Task 6 覆盖
- `ERA5 本轮不接入`：全局约束已锁定，任务中无 ERA5 内容

### 2. Placeholder scan

- 未使用 `TBD` / `TODO` / “后续补充” 之类占位语
- 每个任务都给出明确文件、接口、测试命令和提交命令
- 每个代码步骤都提供了实际函数名与最小代码骨架

### 3. Type consistency

- `resolve_case_masks(front_id, target_time) -> dict[str, str]` 在 Task 1/3 中保持一致
- `read_cra40_profile_cube(...) -> tuple[np.ndarray, np.ndarray]` 在 Task 2/3 中保持一致
- diagnostics 接口统一为 `write_front_diagnostics(...) -> list[str]`
- runner 顶层摘要约定为 `profiles["variables"]` 与 `statistics["variables"]`，在 Task 3/4/5 中保持一致
