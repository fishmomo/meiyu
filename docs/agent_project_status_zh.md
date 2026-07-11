# 梅雨锋项目 Agent 进度与待办状态

## 1. 文档目的

这份文档用于告诉后续 Agent：

- 当前已经完成了什么
- 哪些内容已经过 review，可以视为稳定基线
- 后续最适合从哪里继续接手

## 2. 当前已完成的稳定基线

### 2.1 旧工程整理与新流水线基础层

- 旧工程脚本的用途、输入输出关系已做梳理
- 新流水线已拆出 `inventory / masks / geometry / profiles / subareas / statistics / diagnostics`
- `pipeline.runner` CLI 已恢复并可用
- `manifest`、`override`、`step gating` 已打通

### 2.2 front1 V1 已完成任务

| Task | 状态 | 内容 |
|------|------|------|
| 1 | 已完成 | front1 掩膜资产显式认证 (`73fada7`, `5ab0764`) |
| 2 | 已完成 | CRA40 rh/temp/w 变量映射 (`fb2df49`, `21f899e`) |
| 3 | 已完成 | runner 支持 front1 multivar (`ef9fc97`) |
| 4 | 已完成 | 逐变量 subarea_mean (`e03287f`) |
| 5 | 已完成 | 最小 diagnostics 图件 (`aae8820`) |
| 6 | 已完成 | 文档与真实 smoke (`1378233`) |

### 2.3 接续 Agent 完成的后续主线

| 扩展 | 状态 | 提交 | 说明 |
|------|------|------|------|
| 更多时次 | 已完成 | `650c53f` | front1/2 时次限制解除，资产存在性验证 |
| ERA5 接入 | 已完成 | `85f274e` | `pipeline/core/era5_fields.py`，按月 nc 按时次切片 |
| diagnostics 完整图件 | 已完成 | `040ff81` | 新增几何总览图 + 统计对比图，共 3 类诊断图 |

## 3. 当前已验证案例

| manifest | dataset | front | time | variables |
|----------|---------|-------|------|-----------|
| `cra40_front2_20170622T18.yml` | CRA40 | front2 | 2017-06-22T18 | rh |
| `cra40_front1_20170622T18.yml` | CRA40 | front1 | 2017-06-22T18 | rh/temp/w |
| `cra40_front1_20170622T12.yml` | CRA40 | front1 | 2017-06-22T12 | rh/temp/w |
| `cra40_front2_20170623T00.yml` | CRA40 | front2 | 2017-06-23T00 | rh |
| `era5_front2_20170622T18.yml` | ERA5 | front2 | 2017-06-22T18 | rh/temp/w |

## 4. 当前未完成的后续主线

### 4.1 多案例批处理与批量调度

- 状态：未完成
- 目标：支持一次运行多个 case manifest，输出对比摘要

### 4.2 更丰富的诊断图
- 状态：未完成（当前有 3 类图：几何总览、剖面 overview、统计对比）
- 可扩展：连续帧图、组合剖面图、锋面识别辅助图等

### 4.3 legacy 产物全面对齐
- 状态：未完成
- 目标：把 `merge_csv` 的完整 CSV 批量和 legacy 图件风格纳入新流水线

## 5. 当前最需要避免的误操作

- 不要把 `front1` 再次静默映射回 `front2`
- 不要绕开 `manifest_loader.py` 里已经建立的显式认证边界
- 不要在 `runner.py` 里重新塞入分散的变量文件名/字段分支
- 不要直接改坏 `tests/test_runner_step.py` 的既有回归约束

## 6. 一句话状态总结

`mask -> geometry -> profiles -> subareas -> statistics -> diagnostics`

全部 step 已落地并验证，支持 CRA40 + ERA5 双数据源、front1 + front2 双锋面、多变量（rh/temp/w）、多时次。
