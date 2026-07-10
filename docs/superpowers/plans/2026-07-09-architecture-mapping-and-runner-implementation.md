# Architecture Mapping And Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 产出第二份“技术架构与旧工程映射”文档，并把 `runner` 升级为可串联当前已验证 `CRA40 front2 2017-06-22T18` 链路的统一入口。

**Architecture:** 先补维护视角文档，固化新旧模块关系和迁移边界；再在现有 `pipeline.steps.*` 之上对 `runner` 做轻量串联，不提前泛化到尚未验证的 front1、ERA5 和多变量总控。`runner` 先返回结构化摘要，作为后续继续扩展的稳定壳层。

**Tech Stack:** Markdown、Python 3.12、`conda` 环境 `cwr_py312`、`xarray`、`cfgrib`、现有 `pipeline/` 模块、`nc_compat.py`、`unittest`

## Global Constraints

- 第二份文档必须使用中文编写。
- 第二份文档文件名固定为 `docs/pipeline_architecture_mapping_zh.md`。
- 文档必须清楚区分“已迁移并已验证”“已有模块边界但仍主要依赖 legacy”“尚未迁移到新流水线总入口”三类状态。
- `runner` 本轮只正式支持当前已验证链路，不提前泛化到 `front1 / ERA5 / 多变量` 总控。
- `runner` 本轮主要串联 `inventory -> masks -> geometry -> profiles -> subareas -> statistics`。
- `runner` 中 `profiles` 与 `statistics` 本轮只聚焦 `rh`。
- `runner` 中子区域参数固定使用已验证案例参数 `start_section=1`、`end_section=4`。
- `runner` 优先返回结构化摘要，不要求完整落盘全部中间文件。
- 数据读取必须沿用项目内路径体系，并优先使用 `nc_compat.py` 的兼容读取入口。

---

### Task 1: 编写技术架构与旧工程映射文档

**Files:**
- Create: `docs/pipeline_architecture_mapping_zh.md`
- Test: `docs/superpowers/specs/2026-07-09-architecture-mapping-and-runner-design.md`

**Interfaces:**
- Consumes: `docs/2026-07-05-layered-pipeline-design.md`
- Consumes: `docs/legacy_project_smoke_status_2026-07-05.md`
- Consumes: `docs/pipeline_quickstart_zh.md`
- Consumes: `pipeline/steps/inventory.py`
- Consumes: `pipeline/steps/masks.py`
- Consumes: `pipeline/steps/geometry.py`
- Consumes: `pipeline/steps/profiles.py`
- Consumes: `pipeline/steps/subareas.py`
- Consumes: `pipeline/steps/statistics.py`
- Produces: 面向维护者的“技术架构与旧工程映射”文档

- [ ] **Step 1: 核对文档需要覆盖的模块与 legacy 对应关系**

逐项确认以下映射关系是否进入文档：

- `inventory` -> 当前旧工程运行基线与环境依赖梳理
- `masks` -> `front_grid_lon_lat_unification.py`，以及 `frontal_processing_CRA40.py` 中 offset 掩膜相关输出
- `geometry` -> `frontal1_process_w.py`、`frontal1_process_rh.py`、`frontal2_process.py`、`frontal1_process_SelectSubArea.py`
- `profiles` -> `frontal1_process_w.py`、`frontal1_process_rh.py`、`frontal2_process.py`
- `subareas` -> `frontal1_process_SelectSubArea.py`
- `statistics` -> `merge_csv.py`、`merge_csv fengmian2.py`
- `diagnostics` -> 当前主要仍在 legacy 侧，对应 `frontal_info_graphic_identification.py` 与 `frontal_processing_CRA40.py` 中诊断图部分

- [ ] **Step 2: 编写文档主体结构**

文档至少包含以下章节：

```md
# 梅雨锋新流水线技术架构与旧工程映射
## 1. 文档目的与读者
## 2. 当前新流水线总体结构
## 3. 模块边界与职责
## 4. 新模块与旧脚本映射表
## 5. 已迁移能力与未迁移能力
## 6. 后续扩展接入建议
## 7. 与现有文档的使用顺序
```

- [ ] **Step 3: 在文档中写清三类迁移状态**

文档必须明确写出：

- 哪些能力已经迁移并通过真实案例验证
- 哪些能力已经有新模块边界，但当前仍主要依赖 legacy 结果或 legacy 输出
- 哪些能力还没有进入新流水线总入口

- [ ] **Step 4: 人工检查文档不与现有文档冲突**

Run: 人工对照 `docs/pipeline_architecture_mapping_zh.md`、`docs/pipeline_quickstart_zh.md`、`docs/2026-07-05-layered-pipeline-design.md`
Expected: 文档分工清晰，不重复快速使用指南，也不把规划误写成已完成能力

### Task 2: 为 runner 升级写失败测试与目标摘要结构

**Files:**
- Modify: `tests/test_runner_step.py`

**Interfaces:**
- Consumes: `pipeline.config.load_case_config(path: Path) -> PipelineCaseConfig`
- Consumes: `pipeline.runner.run_case(cfg) -> dict[str, object]`
- Produces: 覆盖升级后摘要结构与支持边界的测试

- [ ] **Step 1: 写 runner 返回扩展摘要的失败测试**

在 `tests/test_runner_step.py` 中新增或替换测试，要求 `run_case(cfg)` 返回：

- `geometry`
- `profiles`
- `subareas`
- `statistics`

并断言：

- `summary["geometry"]["centerline_points"] == 8`
- `summary["geometry"]["section_shape"] == [8, 9]`
- `summary["profiles"]["variable"] == "rh"`
- `summary["profiles"]["bundle_shape"] == [8, 9, 37]`
- `summary["subareas"]["mask_shape"] == [81, 141]`
- `summary["statistics"]` 同时包含 `front_mean` 与 `subarea_mean`

- [ ] **Step 2: 写 runner 非支持配置时的失败测试**

新增一个测试，构造不支持的配置并断言 `run_case(...)` 抛出清晰错误，例如：

```python
with self.assertRaisesRegex(ValueError, "only supports the verified CRA40 front2 pipeline"):
    run_case(cfg)
```

其中可以通过修改 `cfg.dataset` 或 `cfg.front_id` 来触发。

- [ ] **Step 3: 运行 runner 测试并确认先失败**

Run: `conda run -n cwr_py312 python -m pytest tests/test_runner_step.py -v`
Expected: FAIL，原因是当前 `runner` 还没有返回新的步骤摘要或没有进行支持边界校验

### Task 3: 实现 runner 的已验证链路串联

**Files:**
- Modify: `pipeline/runner.py`
- Optionally Modify: `pipeline/core/paths.py`

**Interfaces:**
- Consumes: `ensure_case_dirs(case_name: str) -> dict[str, Path]`
- Consumes: `build_inventory_report() -> dict[str, dict[str, object]]`
- Consumes: `resolve_case_masks(front_id: str, target_time: str) -> dict[str, str]`
- Consumes: `build_geometry_from_mask(mask, lons, lats, degree=4, dense_points=1000, n_sections=8, distance=1.0, n_points=9, delta_x=0.1) -> GeometryResult`
- Consumes: `build_profile_bundle_from_field(variable, field, levels, lats, lons, geometry) -> ProfileBundle`
- Consumes: `build_subarea_mask(mask_lon2d, mask_lat2d, mask_bool, geometry, start_section, end_section) -> np.ndarray`
- Consumes: `build_masked_mean(variable, field, mask_bool) -> float`
- Consumes: `nc_compat.open_dataset_compat(path_like, **kwargs) -> xr.Dataset`
- Produces: 升级后的 `run_case(cfg) -> dict[str, object]`

- [ ] **Step 1: 在 runner 中加入支持边界校验**

在 `run_case(cfg)` 开头新增校验，至少要求：

```python
if cfg.dataset != "cra40" or cfg.front_id != "front2":
    raise ValueError("runner only supports the verified CRA40 front2 pipeline in this version")
```

必要时可继续限制 `cfg.target_time`，但如果当前 `masks` 侧仍允许更多 `CRA40 front2` 时次，则保持“front2 已验证资产链路”边界即可。

- [ ] **Step 2: 实现主掩膜读取与 geometry 摘要**

使用 `open_dataset_compat(...)` 打开 `summary["masks"]["front_mask"]`，读取：

- `ind_area_bool`
- `lon`
- `lat`

然后调用 `build_geometry_from_mask(...)`，固定参数：

- `degree=4`
- `dense_points=1000`
- `n_sections=8`
- `distance=1.0`
- `n_points=9`
- `delta_x=0.1`

把结果写入摘要，例如：

```python
"geometry": {
    "centerline_points": int(geometry.centerline_x.shape[0]),
    "section_shape": list(geometry.sampled_dx.shape),
}
```

- [ ] **Step 3: 实现 RH 读取、profiles 摘要和完整锋面统计**

读取：

- `data/raw/cra40/CRA40_RHU_2017062218_GLB_0P25_HOUR_V1_0_0.grib2`

使用 `open_dataset_compat(...)`，按主掩膜 `lat/lon` 对齐字段，并取：

- `field3d = rh_ds["r"].isel(isobaricInhPa=slice(0, 37)).sel(...).values`
- `levels = rh_ds["isobaricInhPa"].isel(isobaricInhPa=slice(0, 37)).values`

调用：

- `build_profile_bundle_from_field("rh", field3d, levels, lats, lons, geometry)`
- `build_masked_mean("rh", field3d[0], mask_bool)`

把结果写入摘要，例如：

```python
"profiles": {
    "variable": "rh",
    "bundle_shape": list(bundle.values.shape),
},
"statistics": {
    "front_mean": float(front_mean),
}
```

- [ ] **Step 4: 实现 subareas 摘要与子区域统计**

先基于主掩膜网格调用：

- `build_subarea_mask(lon2d, lat2d, mask_bool, geometry, start_section=1, end_section=4)`

再单独打开：

- `summary["masks"]["subarea_mask"]`

按子区域掩膜自己的 `lat/lon` 重新从 RH 场中取：

- `sub_field = rh_ds["r"].isel(isobaricInhPa=0).sel(latitude=sub_lats, longitude=sub_lons, method="nearest").values`

调用：

- `build_masked_mean("rh", sub_field, sub_bool)`

把结果写入摘要，例如：

```python
"subareas": {
    "mask_shape": list(submask.shape),
    "selected_points": int(submask.sum()),
    "start_section": 1,
    "end_section": 4,
},
"statistics": {
    "front_mean": float(front_mean),
    "subarea_mean": float(subarea_mean),
}
```

- [ ] **Step 5: 保留原有 outputs/inventory/masks 摘要并合并新摘要**

最终返回结构需同时保留原有：

- `case_name`
- `inventory`
- `masks`
- `outputs`

并新增：

- `geometry`
- `profiles`
- `subareas`
- `statistics`

- [ ] **Step 6: 运行 runner 测试并确认通过**

Run: `conda run -n cwr_py312 python -m pytest tests/test_runner_step.py -v`
Expected: PASS

### Task 4: 用真实案例做 runner 冒烟并回填文档

**Files:**
- Modify: `docs/pipeline_architecture_mapping_zh.md`
- Modify: `docs/pipeline_quickstart_zh.md`

**Interfaces:**
- Consumes: `pipeline.runner.run_case(cfg) -> dict[str, object]`
- Produces: 与真实 `runner` 输出一致的文档描述

- [ ] **Step 1: 运行真实案例 runner 冒烟**

Run:

```powershell
conda run -n cwr_py312 python -c "from pathlib import Path; from pipeline.config import load_case_config; from pipeline.runner import run_case; cfg=load_case_config(Path('pipeline/schemas/pipeline_config.yaml')); summary=run_case(cfg); print(summary['geometry']); print(summary['profiles']); print(summary['subareas']); print(summary['statistics'])"
```

Expected:

- `geometry` 摘要能看到 8 个中心线点与 `[8, 9]`
- `profiles` 摘要能看到 `rh` 与 `[8, 9, 37]`
- `subareas` 摘要能看到 `[81, 141]`
- `statistics` 摘要能看到 `front_mean` 与 `subarea_mean`

- [ ] **Step 2: 把 runner 现状写回第二份文档**

在 `docs/pipeline_architecture_mapping_zh.md` 中明确写出：

- 当前 `runner` 已经串联了哪些模块
- 当前 `runner` 仍未覆盖哪些能力
- 当前 `runner` 的支持边界是什么

- [ ] **Step 3: 同步修正快速使用指南中的 runner 描述**

把 `docs/pipeline_quickstart_zh.md` 中关于 `runner` 的描述，从“只到 inventory + masks”更新为“已可串联当前已验证链路，但仍不是通用总控器”。

- [ ] **Step 4: 人工做一次跨文档一致性检查**

Run: 人工对照以下三个文件

- `docs/pipeline_quickstart_zh.md`
- `docs/pipeline_architecture_mapping_zh.md`
- `docs/superpowers/specs/2026-07-09-architecture-mapping-and-runner-design.md`

Expected: runner 边界、已迁移能力、未迁移能力和示例说明一致
