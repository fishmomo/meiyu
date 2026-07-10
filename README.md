# Meiyu Front Research Pipeline

面向梅雨锋研究的项目仓库，包含两部分内容：

- `legacy` 风格的原始研究脚本
- 围绕已验证个例逐步抽象出的新流水线 `pipeline/`

当前仓库的目标不是把所有旧脚本一次性改写完，而是先保证旧工程可运行，再把其中稳定、可复用的部分沉淀成模块化流水线，方便后续在相似个例和相似研究任务中复用。

## 当前研究主线

整体研究思路为：

`再分析资料 -> 诊断物理量时序分布 -> 人工识别打点 -> 锋面掩膜数据 -> 拟合/切线 -> 多物理量剖面与子区域掩膜 -> 掩膜统计 -> 时序变化结果`

当前新流水线已经围绕一个已验证个例，形成了最小可复用链路：

`mask -> geometry -> profiles -> subareas -> statistics`

## 当前已验证案例

当前 `runner` 正式支持的边界是：

- 数据集：`CRA40`
- 锋面：`front2`
- 时次：`2017-06-22T18`
- 剖面变量：`rh`

入口示例：

```powershell
conda run -n cwr_py312 python -c "from pathlib import Path; from pipeline.runner import run_case_from_manifest; import pprint; pprint.pp(run_case_from_manifest(Path('manifests/cases/cra40_front2_20170622T18.yml')))"
```

如果要测试第二阶段的 step gating：

```powershell
conda run -n cwr_py312 python -c "from pathlib import Path; from pipeline.runner import run_case_from_manifest; import pprint; pprint.pp(run_case_from_manifest(Path('manifests/cases/cra40_front2_20170622T18.yml'), overrides={'steps.subareas': False, 'steps.statistics': True}))"
```

## 目录说明

- `pipeline/`：新流水线代码，包含 `core / steps / runner / manifest`
- `manifests/`：已验证案例入口
- `tests/`：新流水线测试
- `docs/`：中文使用说明、架构映射、实施与设计文档
- 根目录若干 `frontal*.py`、`merge_csv*.py`、`front_grid_lon_lat_unification.py`：旧工程脚本
- `skills/`：本项目过程中沉淀的可复用 skill

## 文档入口

建议按下面顺序阅读：

1. [快速使用指南](docs/pipeline_quickstart_zh.md)
2. [技术架构与旧工程映射](docs/pipeline_architecture_mapping_zh.md)
3. [旧脚本功能总表](docs/legacy_script_index_zh.md)
4. [旧工程冒烟状态记录](docs/legacy_project_smoke_status_2026-07-05.md)

## 数据说明

本仓库默认不上传原始数据和输出结果。

- `data/` 已在 `.gitignore` 中排除
- `outputs/` 已在 `.gitignore` 中排除

如果你在本地复现实验，需要自行准备对应的 CRA40 / ERA5 数据，并按项目内路径约定放置。

## 运行环境

- 推荐环境：`cwr_py312`
- 推荐平台：Windows
- 当前仓库对中文路径做了兼容处理，相关入口见 [nc_compat.py](nc_compat.py) 与 `skills/windows-chinese-science-path-compat/`

## 当前状态

当前仓库已经完成：

- 旧工程基础可运行性梳理
- 新流水线最小链路模块化
- manifest 入口
- runner 的 override / step gating
- 中文 quickstart 与架构映射文档

尚未完成：

- front1 统一入口
- ERA5 统一入口
- 多变量正式 runner 支持
- 完整 diagnostics 与图件总调度

## 说明

这是一个持续整理中的研究仓库。现阶段更适合把它看作：

- 一个可追溯的梅雨锋研究代码底座
- 一个正在从“个人研究工程”向“可复用研究流水线”演进的项目
