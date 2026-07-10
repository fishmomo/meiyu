# 新流水线第一版说明

## 1. 当前范围

`pipeline/` 目录已经落下第一版可复用骨架，当前可见模块包括：

- `config.py`：读取个例配置，当前样例配置是 `CRA40 front2 2017-06-22T18`。
- `core.paths`：统一创建 `outputs/figures/<case_name>/`、`logs/`、`manifests/` 等输出目录。
- `steps.inventory`：检查 `data/raw`、`data/interim`、`data/processed` 是否存在，并汇总关键依赖环境状态。
- `steps.masks`：按当前约束解析并校验 `CRA40 front2` 现成掩膜资产。
- `steps.geometry`：提供几何采样框架的基础数据结构与法向偏移计算封装。
- `steps.profiles`：提供剖面堆叠的基础数据结构与最小封装。
- `steps.subareas`：提供子区域结果命名的最小封装。
- `steps.statistics`：提供网格均值统计的最小封装。
- `runner.py`：串联配置读取后的首条执行入口。

补充说明：

- `pipeline/core/` 里还放了 `mask_ops`、`front_ops`、`section_ops`、`time_utils` 等底层辅助逻辑。
- 现阶段 `geometry / profiles / subareas / statistics` 已经有模块边界，但大部分仍是“先把接口和基础能力落位”，还不是 legacy 科学计算逻辑的完整迁入版。

## 2. 当前定位

这一版新流水线的定位很明确：

- 它是第一版可复用骨架。
- 它的目标是把现有研究脚本整理成可配置、可串联、可逐步迁移的结构。
- 它不是最终科学计算替代版，也不是要一次性取代 legacy 全部脚本。

当前很多科学细节仍以 legacy 脚本为基线。新流水线这一阶段主要负责三件事：

- 统一配置入口。
- 统一步骤边界和输出目录。
- 为后续逐步迁移 legacy 逻辑提供稳定壳层。

换句话说，旧工程当前仍承担“科学结果基线”的角色；新流水线当前主要承担“结构化、可复用、可串联”的角色。

## 3. 已接通链路

当前已经接通并有测试覆盖的第一条链路是：

- `CRA40 front2 2017-06-22T18`

这条链路目前能完成的事情是：

- 读取 `pipeline/schemas/pipeline_config.yaml`
- 创建当前 case 的输出目录
- 执行 `inventory` 检查
- 执行 `masks` 解析
- 返回包含 `case_name`、`inventory`、`masks`、`outputs` 的摘要结果

其中 `masks` 这一步当前已明确依赖并校验三类现成资产：

- `front_mask`
- `extend_mask`
- `subarea_mask`

现状上，这说明第一版已经把“配置 -> 目录 -> 资产清点 -> 掩膜接入”这条最小主干跑通了；但还没有把几何、剖面、子区域计算、统计计算完整接到 `runner` 里。

## 4. 现阶段如何使用

建议按最小步骤使用：

1. 先确认 `data/raw/`、`data/interim/manual_masks/`、`data/processed/` 已按当前工程约定准备好数据。
2. 检查 `pipeline/schemas/pipeline_config.yaml`，当前默认样例就是 `cra40_front2_2017-06-22T18`。
3. 在项目根目录加载配置并执行 `run_case(...)`。
4. 查看返回摘要中的 `inventory`、`masks`、`outputs`，确认目录创建和掩膜解析都成功。

如果只想理解“第一版已经通到哪里”，可以把它理解为：

- 现在适合把它当作新流水线壳层的入口与验收样例。
- 现在还不适合把它当作完整科研生产替代流程。

## 5. 下一步迁移建议

后续建议继续从 legacy 向 `geometry / profiles / subareas / statistics` 迁入，但应优先迁“稳定、可复用、输入输出清楚”的部分。

### 5.1 geometry

适合继续迁入：

- 从锋面掩膜提取边界、中心线、切线/法线采样框架的逻辑。
- `front1/front2` 剖面脚本里与几何构型直接相关、且不依赖具体变量绘图的部分。

优先参考：

- `frontal1_process_w.py`
- `frontal1_process_rh.py`
- `frontal2_process.py`
- `frontal1_process_SelectSubArea.py`

### 5.2 profiles

适合继续迁入：

- 沿剖面提取 RH、温度、垂直速度、theta-e 等变量的公共采样逻辑。
- 与变量无关的剖面拼接、堆叠、输出组织逻辑。

建议先迁“数据采样和结果组织”，后迁“绘图风格和版式细节”。

### 5.3 subareas

适合继续迁入：

- 基于几何框架划分锋面子区域的规则。
- 子区域掩膜生成与标准命名输出。

优先参考：

- `frontal1_process_SelectSubArea.py`

### 5.4 statistics

适合继续迁入：

- 基于整块掩膜或子区域掩膜做网格平均的公共逻辑。
- CSV 汇总与时间序列统计的通用部分。

优先参考：

- `merge_csv.py`
- `merge_csv fengmian2.py`

## 6. 建议的迁移原则

- 先保留 legacy 结果作为科学对照基线，不急着重写算法细节。
- 先把“输入是什么、输出是什么、文件落到哪里”固定下来，再逐步替换内部实现。
- 优先迁公共逻辑，不要先迁只服务单张图的零散绘图细节。
- 每迁一步，都尽量能继续回到 `CRA40 front2 2017-06-22T18` 这个样例链路做验证。

## 7. 一句话总结

当前这版新流水线已经具备“能接配置、能建目录、能盘点环境、能接入现成掩膜”的第一层骨架；后续工作的重点，是在不丢失 legacy 科学基线的前提下，逐步把 `geometry / profiles / subareas / statistics` 的核心逻辑迁进来。
