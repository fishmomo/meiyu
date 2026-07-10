# 梅雨锋项目 Agent 进度与待办状态

## 1. 文档目的

这份文档用于告诉后续 Agent：

- 当前已经完成了什么
- 哪些内容已经过 review，可以视为稳定基线
- 哪些内容只是已实现、但还没最终收口
- 后续最适合从哪里继续接手

## 2. 当前已完成的稳定基线

以下内容已经完成并可视为当前稳定基线：

### 2.1 旧工程整理与新流水线基础层

- 旧工程脚本的用途、输入输出关系已做梳理
- 新流水线已拆出 `inventory / masks / geometry / profiles / subareas / statistics / diagnostics`
- `pipeline.runner` CLI 已恢复并可用
- `manifest`、`override`、`step gating` 已打通

相关文档：

- [docs/pipeline_quickstart_zh.md](/H:/邢台观测站/CWR_project/meiyu_new/docs/pipeline_quickstart_zh.md)
- [docs/pipeline_architecture_mapping_zh.md](/H:/邢台观测站/CWR_project/meiyu_new/docs/pipeline_architecture_mapping_zh.md)

### 2.2 front1 V1 已完成任务

#### Task 1

- 状态：已完成，已 review clean
- 内容：`front1` 掩膜资产显式认证，并锁定到 `2017-06-22T18`
- 关键提交：
  - `73fada7` `feat: add explicit front1 mask asset resolution`
  - `5ab0764` `fix: lock front1 v1 target time`

#### Task 2

- 状态：已完成，已 review clean
- 内容：CRA40 `rh/temp/w` 变量映射与取数层建立完成
- 关键提交：
  - `fb2df49` `feat: add cra40 multi-variable profile field resolver`
  - `21f899e` `fix: restrict front1 cra40 profile mapping scope`

#### Task 3

- 状态：已完成，已 review clean
- 内容：runner 已支持：
  - `CRA40 + front2 + 2017-06-22T18 + rh`
  - `CRA40 + front1 + 2017-06-22T18 + rh/temp/w`
- 新增：
  - [cra40_front1_20170622T18.yml](/H:/邢台观测站/CWR_project/meiyu_new/manifests/cases/cra40_front1_20170622T18.yml)
- 关键提交：
  - `ef9fc97` `feat: add front1 v1 runner baseline`

#### Task 4

- 状态：已完成，review clean（由接续 Agent 收口）
- 内容：front1/front2 的 runner 统计摘要补入逐变量 `subarea_mean`
- 关键提交：
  - `e03287f` `feat: add front1 subarea statistics summaries`

#### Task 5

- 状态：已完成，已验证
- 内容：最小 diagnostics 图件落盘
- 新增：
  - [pipeline/steps/diagnostics.py](/H:/邢台观测站/CWR_project/meiyu_new/pipeline/steps/diagnostics.py)
  - [tests/test_diagnostics_step.py](/H:/邢台观测站/CWR_project/meiyu_new/tests/test_diagnostics_step.py)
- 修改：
  - `pipeline/runner.py` 接入 diagnostics step
  - `tests/test_runner_step.py` 增补 diagnostics 断言
  - `manifests/cases/cra40_front1_20170622T18.yml` 与 `cra40_front2_20170622T18.yml` 增加 `diagnostics: true`
- 关键提交：
  - `aae8820` `feat: add front1 minimal diagnostics outputs`

#### Task 6

- 状态：已完成，已验证
- 内容：补齐 front1 V1 文档与真实 smoke
- 修改：
  - [docs/pipeline_quickstart_zh.md](/H:/邢台观测站/CWR_project/meiyu_new/docs/pipeline_quickstart_zh.md)：增补 front1 V1 运行方式、diagnostics 说明
  - [docs/pipeline_architecture_mapping_zh.md](/H:/邢台观测站/CWR_project/meiyu_new/docs/pipeline_architecture_mapping_zh.md)：更新 front1/diagnostics/多变量迁移状态
  - [README.md](/H:/邢台观测站/CWR_project/meiyu_new/README.md)：更新当前支持边界与 front1 入口

## 3. 当前未完成的后续主线

### 3.1 扩展更多时次

- 状态：未完成
- 目标：把 front1/front2 从单时次扩展到更多研究时次
- 重点：先在 `masks` 层验证更多时次的资产存在性，再逐步扩展 runner 支持边界

### 3.2 ERA5 接入

- 状态：未完成
- 目标：把 ERA5 拉进统一入口的分层结构
- 重点：先验证 ERA5 数据读取、坐标对齐、剖面抽样，再进入 runner

### 3.3 diagnostics 完整图件总调度

- 状态：未完成
- 目标：从最小剖面 overview 扩展到连续帧、组合图、更多诊断量图件
- 重点：保持 diagnostics 只消费 step 结果，不反向侵入底层

### 3.4 多案例批处理与批量调度

- 状态：未完成
- 目标：支持一次运行多个 case manifest

## 4. 后续 Agent 最推荐的接手顺序

如果目标是尽快缩短周期，建议按下面顺序接手：

1. 扩展更多时次：先补 `masks` 资产，再扩 runner
2. ERA5 接入：先在 step 层验证，再进 runner
3. diagnostics 完整图件：在现有 `pipeline/steps/diagnostics.py` 基础上增量扩展

## 5. 当前最需要避免的误操作

- 不要把 `front1` 再次静默映射回 `front2`
- 不要绕开 `manifest_loader.py` 里已经建立的 front1 V1 显式认证边界
- 不要在 `runner.py` 里重新塞入分散的变量文件名/字段分支
- 不要直接改坏 `tests/test_runner_step.py` 的既有 front2 回归约束
- 不要为了“先跑通”去放松边界，再把隐患留给后续 Agent

## 6. 一句话状态总结

当前 `front1 V1` 已经完成到：

`掩膜显式认证 -> CRA40 多变量映射 -> front1/front2 runner 主线 -> 子区域逐变量统计 -> 最小 diagnostics 图件 -> 使用文档`

下一步最关键的，不是重新理解整个项目，而是继续把：

`更多时次 -> ERA5 接入 -> diagnostics 完整图件总调度`

这三段收口。
