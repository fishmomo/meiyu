# Quickstart Guide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 产出一份面向使用者的中文快速使用指南，让研究者可以基于当前已验证的新流水线能力实际运行 `CRA40 front2 2017-06-22T18` 这一条最小链路。

**Architecture:** 先从现有实现与真实数据资产中提取已验证事实，再把这些事实组织成一份“环境准备 -> 能力边界 -> 最小示例 -> 常见问题 -> 输出定位”的用户文档。文档只覆盖当前已经验证过的能力，不把未来规划写成现成功能。

**Tech Stack:** Markdown、Python 3.12、conda 环境 `cwr_py312`、现有 `pipeline/` 模块、现有 `docs/` 文档、真实 CRA40/掩膜案例数据。

## Global Constraints

- 文档必须使用中文编写。
- 文档必须优先回答“怎么用”，而不是展开全部架构原理。
- 文档只能写当前已经真实验证过的能力与路径。
- 文档中的最小示例必须使用项目内真实案例 `CRA40 front2 2017-06-22T18`。
- 文档必须明确说明中文路径兼容层 `nc_compat.py` 的使用背景。
- 文档必须明确说明主掩膜与子区域掩膜可能不在同一网格上，统计前需要按各自坐标对齐字段。
- 新文档目标文件固定为 `docs/pipeline_quickstart_zh.md`。

---

### Task 1: 固化快速使用指南正文

**Files:**
- Create: `docs/pipeline_quickstart_zh.md`
- Test: `docs/superpowers/specs/2026-07-07-quickstart-guide-design.md`

**Interfaces:**
- Consumes: `pipeline/config.py::load_case_config(path: Path) -> PipelineCaseConfig`
- Consumes: `pipeline/runner.py::run_case(cfg) -> dict[str, object]`
- Consumes: `pipeline/steps/masks.py::resolve_case_masks(front_id: str, target_time: str) -> dict[str, str]`
- Consumes: `pipeline/steps/geometry.py::build_geometry_from_mask(...) -> GeometryResult`
- Consumes: `pipeline/steps/profiles.py::build_profile_bundle_from_field(...) -> ProfileBundle`
- Consumes: `pipeline/steps/subareas.py::build_subarea_mask(...) -> np.ndarray`
- Consumes: `pipeline/steps/statistics.py::build_masked_mean(...) -> float`
- Produces: 一份可直接阅读和照着执行的快速使用指南

- [ ] **Step 1: 核对指南需要覆盖的已验证事实**

检查以下依据，确保文档只写已验证内容：

- `docs/superpowers/specs/2026-07-07-quickstart-guide-design.md`
- `docs/legacy_project_smoke_status_2026-07-05.md`
- `pipeline/config.py`
- `pipeline/runner.py`
- `pipeline/steps/masks.py`
- `pipeline/steps/geometry.py`
- `pipeline/steps/profiles.py`
- `pipeline/steps/subareas.py`
- `pipeline/steps/statistics.py`
- `project_paths.py`
- `nc_compat.py`

- [ ] **Step 2: 用真实案例补齐文档中的关键事实**

提取以下真实信息并写入文档：

- 虚拟环境名 `cwr_py312`
- 配置文件 `pipeline/schemas/pipeline_config.yaml`
- 主掩膜路径 `data/interim/manual_masks/cra40/front2/2017-06-22T18.nc`
- extend 掩膜路径 `data/interim/manual_masks/cra40/front2_extend/2017-06-22T18.nc`
- 子区域掩膜路径 `data/interim/manual_masks/cra40/front2_subareas/area2_lonlat_0622T18.nc`
- CRA40 RHU 文件 `data/raw/cra40/CRA40_RHU_2017062218_GLB_0P25_HOUR_V1_0_0.grib2`
- 真实探测得到的维度/变量名与最小输出形状

- [ ] **Step 3: 编写正式快速使用指南**

文档至少包含以下章节：

```md
# 梅雨锋新流水线快速使用指南
## 1. 这份指南适合谁
## 2. 运行前准备
## 3. 当前流水线能做什么
## 4. 最小可运行示例
## 5. 常见问题
## 6. 输出与后续定位
```

写作要求：

- 用项目内真实路径与真实案例
- 对每一步标注输入、调用、输出、正常现象
- 明确 `runner.py` 是基础入口，不是完整总调度器
- 明确 `xr.open_dataset(...)` 在中文路径下可能失败，应优先使用 `open_dataset_compat(...)`

- [ ] **Step 4: 保存文档并检查 Markdown 可读性**

检查以下内容：

- 章节顺序是否符合 spec
- 代码块是否可直接复制
- 路径是否与项目内真实文件一致
- 是否把“未完全串联能力”误写成“已经一键完成”

Run: 人工通读 `docs/pipeline_quickstart_zh.md`
Expected: 文档结构完整、术语一致、没有占位符

### Task 2: 用真实链路核对文档示例

**Files:**
- Modify: `docs/pipeline_quickstart_zh.md`

**Interfaces:**
- Consumes: `nc_compat.py::open_dataset_compat(path_like, **kwargs) -> xr.Dataset`
- Consumes: `pipeline.steps.geometry.build_geometry_from_mask(...) -> GeometryResult`
- Consumes: `pipeline.steps.profiles.build_profile_bundle_from_field(...) -> ProfileBundle`
- Consumes: `pipeline.steps.subareas.build_subarea_mask(...) -> np.ndarray`
- Consumes: `pipeline.steps.statistics.build_masked_mean(...) -> float`
- Produces: 与真实运行结果一致的示例说明

- [ ] **Step 1: 运行真实最小链路并记录关键结果**

Run:

```powershell
conda run -n cwr_py312 python -c "from pathlib import Path; import numpy as np; from nc_compat import open_dataset_compat; from pipeline.steps.geometry import build_geometry_from_mask; from pipeline.steps.profiles import build_profile_bundle_from_field; from pipeline.steps.subareas import build_subarea_mask; from pipeline.steps.statistics import build_masked_mean; mask_ds=open_dataset_compat(Path('data/interim/manual_masks/cra40/front2/2017-06-22T18.nc')); mask=mask_ds['ind_area_bool'].values.astype(bool); lons=mask_ds['lon'].values; lats=mask_ds['lat'].values; geometry=build_geometry_from_mask(mask, lons, lats, degree=4, dense_points=1000, n_sections=8, distance=1.0, n_points=9, delta_x=0.1); print('geometry', geometry.centerline_x.shape, geometry.sampled_dx.shape); rh_ds=open_dataset_compat(Path('data/raw/cra40/CRA40_RHU_2017062218_GLB_0P25_HOUR_V1_0_0.grib2')); field3d=rh_ds['r'].isel(isobaricInhPa=slice(0,37)).sel(latitude=lats, longitude=lons, method='nearest').values; levels=rh_ds['isobaricInhPa'].isel(isobaricInhPa=slice(0,37)).values; bundle=build_profile_bundle_from_field('rh', field3d, levels, lats, lons, geometry); print('bundle', bundle.values.shape); lon2d, lat2d=np.meshgrid(lons, lats); submask=build_subarea_mask(lon2d, lat2d, mask, geometry, start_section=1, end_section=4); print('submask', submask.shape, int(submask.sum())); print('front_mean', float(build_masked_mean('rh', field3d[0], mask))); sub_ds=open_dataset_compat(Path('data/interim/manual_masks/cra40/front2_subareas/area2_lonlat_0622T18.nc')); sub_bool=sub_ds['ind_area_bool'].values.astype(bool); sub_lons=sub_ds['lon'].values; sub_lats=sub_ds['lat'].values; sub_field=rh_ds['r'].isel(isobaricInhPa=0).sel(latitude=sub_lats, longitude=sub_lons, method='nearest').values; print('sub_mean', float(build_masked_mean('rh', sub_field, sub_bool)))"
```

Expected:

- `geometry.centerline_x.shape == (8,)`
- `geometry.sampled_dx.shape == (8, 9)`
- `bundle.values.shape == (8, 9, 37)`
- `submask.shape == (81, 141)`
- 能得到完整锋面与子区域的两个均值结果

- [ ] **Step 2: 把真实结果写回文档**

把真实运行得到的关键输出，写成“正常现象参考值”：

- 几何结果维度
- 剖面 bundle 维度
- 子区域掩膜大小与点数
- 统计均值示例

- [ ] **Step 3: 再做一次内容一致性检查**

检查以下问题：

- 文档示例代码与当前模块签名是否一致
- 文档是否明确指出子区域统计必须重新按子区域网格取场
- 文档是否明确指出中文路径下的兼容打开方式

Run: 人工对照 `docs/pipeline_quickstart_zh.md` 与当前实现
Expected: 示例、路径、函数名、输出描述一致
