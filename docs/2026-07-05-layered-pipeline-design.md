# 梅雨锋研究新流水线重构设计（2026-07-05）

## 1. 目标

本次重构不是继续修改旧工程脚本，而是在旧工程已经跑通的基础上，重塑一套可复用、可配置、可分步执行的研究流水线。

目标有四个：

1. 保留原研究思路，不破坏既有科学分析链路。
2. 将旧脚本中的分散能力重组为稳定模块。
3. 统一输入数据路径、输出路径、命名和日志。
4. 为后续相似课题提供可复制的研究路径模板。

本轮重构的前提是：

- 旧工程脚本已经在当前项目路径下基本跑通。
- 人工识别成果、掩膜、offset、子区域、CSV 统计结果已经就位。
- 当前项目已经具备 `project_paths.py` 和 `nc_compat.py` 两个基础设施。

## 2. 重构原则

### 2.1 保守迁移

第一版新流水线只重构“组织方式”和“模块边界”，不追求改写全部算法细节。

原则上：

- 先抽公共能力
- 再封装分步任务
- 最后再决定哪些旧计算逻辑值得进一步纯化

### 2.2 研究流程优先

模块划分以研究流程为主，不以旧脚本文件名为主。

也就是说，新流水线回答的是：

- 现在在研究流程的哪一步
- 这一步输入什么
- 这一步输出什么

而不是简单回答“调用了哪个旧脚本”

### 2.3 旧工程可对照

重构阶段保留旧脚本作为参考基线，不删除、不覆盖、不直接改造成新框架。

新流水线应当能做到：

- 新输出可以和旧输出对照
- 新模块的输入输出可以追溯回旧研究步骤

### 2.4 优先复用人工识别成果

第一版不把重点放在“自动识别锋面”，而是优先围绕已经存在的人工识别掩膜成果组织流程。

这是因为当前最有价值的研究资产是：

- 人工识别打点结果
- 已形成的锋面掩膜
- 已形成的 offset 掩膜
- 已形成的子区域掩膜
- 已形成的统计输出

## 3. 推荐目录结构

建议在项目下新增一个新流水线目录，例如：

```text
pipeline/
  __init__.py
  config.py
  runner.py
  steps/
    __init__.py
    inventory.py
    diagnostics.py
    masks.py
    geometry.py
    profiles.py
    subareas.py
    statistics.py
  io/
    __init__.py
    readers.py
    writers.py
    manifest.py
  core/
    __init__.py
    paths.py
    time_utils.py
    mask_ops.py
    front_ops.py
    section_ops.py
    plot_ops.py
  schemas/
    pipeline_config.yaml
```

同时建议在输出目录中逐步建立新规范：

```text
outputs/
  figures/
    era5/
    cra40/
    profiles/
    subareas/
    statistics/
  manifests/
  logs/
```

旧目录 `outputs/legacy_figures/` 保留，用于对照。

## 4. 新流水线分层

### 4.1 `inventory`

职责：

- 检查环境依赖
- 检查原始数据是否齐全
- 检查中间掩膜和统计结果是否齐全
- 输出项目清单和缺失报告

输入：

- `data/raw/`
- `data/interim/`
- `data/processed/`

输出：

- `outputs/manifests/data_inventory.json`
- `outputs/logs/inventory_*.log`

对应旧工程角色：

- 本轮人工梳理出的“旧工程跑通基线”

### 4.2 `diagnostics`

职责：

- 生成重要诊断物理量时序图和个例图
- 作为人工识别或复核的依据

输入：

- ERA5 原始资料
- CRA40 原始资料

输出：

- 诊断图
- 可选的清单文件

对应旧脚本：

- `frontal_info_graphic_identification.py`
- `frontal_processing_CRA40.py` 中的诊断绘图部分

### 4.3 `masks`

职责：

- 读取人工掩膜
- 统一经纬网格
- 输出标准掩膜
- 生成扩展掩膜和 offset 掩膜

输入：

- 人工识别掩膜
- 目标网格定义

输出：

- 标准锋面掩膜
- extend 掩膜
- offset 掩膜

对应旧脚本：

- `front_grid_lon_lat_unification.py`
- `frontal_processing_CRA40.py` 中的 offset 掩膜输出部分

### 4.4 `geometry`

职责：

- 从某一时次锋面掩膜中提取边界
- 拟合锋面中心曲线
- 对曲线进行等分
- 生成切线/法线采样框架

输入：

- 某时次锋面掩膜

输出：

- 曲线拟合结果
- 采样点
- 切线/法线截面几何信息

对应旧脚本：

- `frontal1_process_w.py`
- `frontal1_process_rh.py`
- `frontal2_process.py`
- `frontal1_process_SelectSubArea.py`

### 4.5 `profiles`

职责：

- 沿切线提取多物理量剖面
- 输出 RH、温度、垂直速度、theta-e 等剖面图

输入：

- 几何模块输出的切线/法线采样框架
- CRA40 或 ERA5 对应时次资料

输出：

- 单变量剖面图
- 组合剖面图
- 可选中间数组

对应旧脚本：

- `frontal1_process_w.py`
- `frontal1_process_rh.py`
- `frontal2_process.py`

### 4.6 `subareas`

职责：

- 根据切线之间的区域关系筛选锋面子区域
- 输出子区域掩膜

输入：

- 几何模块输出
- 锋面主掩膜

输出：

- 子区域掩膜 nc
- 子区域可视化图

对应旧脚本：

- `frontal1_process_SelectSubArea.py`

### 4.7 `statistics`

职责：

- 基于完整锋面掩膜或子区域掩膜，对目标物理量做网格平均
- 输出 CSV 统计序列
- 输出统计图

输入：

- 掩膜
- 外部物理量网格数据

输出：

- CSV
- PNG

对应旧脚本：

- `merge_csv.py`
- `merge_csv fengmian2.py`

## 5. 输入输出规范

### 5.1 输入数据分层

保留现有路径体系：

- `data/raw/era5/`
- `data/raw/cra40/`
- `data/interim/manual_masks/`
- `data/processed/mask_statistics/`

新流水线不再直接写死任何外部盘符路径。

### 5.2 输出数据分层

建议新流水线统一分三类输出：

1. `outputs/figures/`
2. `outputs/manifests/`
3. `outputs/logs/`

其中：

- 旧工程兼容输出仍允许写入 `outputs/legacy_figures/`
- 新模块默认写入 `outputs/figures/`

### 5.3 命名规范

建议统一文件名元素：

- 数据源：`era5` / `cra40`
- 锋面：`front1` / `front2`
- 类型：`mask` / `extend` / `offset` / `subarea` / `profile` / `series`
- 变量：`sp` / `thetae` / `rh` / `w` / `temp`
- 时间：`YYYY-MM-DDTHH`

示例：

- `cra40_front2_offset_2017-06-26T06.nc`
- `cra40_front2_subarea_area2_2017-06-22T18.nc`
- `cra40_front2_sp_series_2017-06-22T18_to_2017-06-28T06.png`

## 6. 配置方式

第一版建议使用单一配置文件驱动，而不是命令行上堆很多参数。

建议配置内容包含：

- 数据源选择
- 锋面编号
- 目标时段
- 目标时次
- 是否生成图
- 是否复用已有掩膜
- 子区域划分参数
- 统计变量清单

配置文件示意：

```yaml
case_name: meiyu_front2_20170622T18
dataset: cra40
front_id: front2
time:
  target: 2017-06-22T18
mask:
  reuse_existing: true
profiles:
  variables: [rh, temp, w, thetae]
subareas:
  enabled: true
statistics:
  enabled: true
```

## 7. 第一版实施范围

第一版只做“可复用骨架 + 已验证能力迁移”，不做过度设计。

### 第一版必须完成

1. 建立新流水线目录骨架
2. 抽出统一配置与统一路径入口
3. 实现 `inventory`
4. 实现 `masks`
5. 实现 `geometry`
6. 实现 `profiles`
7. 实现 `subareas`
8. 实现 `statistics`
9. 至少提供一个可跑通的 CRA40 front2 示例链路

### 第一版可以暂缓

1. 全量 ERA5/CRA40 双源统一接口的高度抽象
2. 自动识别锋面算法
3. 全部旧图风格统一重绘
4. 大规模 CLI 子命令系统
5. 并行调度和批量案例管理

## 8. 旧脚本到新模块的映射

### 旧脚本保留但不再作为最终接口

- `front_grid_lon_lat_unification.py`
  - 迁移目标：`steps/masks.py`

- `frontal_info_graphic_identification.py`
  - 迁移目标：`steps/diagnostics.py`

- `frontal_processing_CRA40.py`
  - 迁移目标：`steps/diagnostics.py` + `steps/masks.py`

- `frontal1_process_w.py`
  - 迁移目标：`steps/geometry.py` + `steps/profiles.py`

- `frontal1_process_rh.py`
  - 迁移目标：`steps/geometry.py` + `steps/profiles.py`

- `frontal2_process.py`
  - 迁移目标：`steps/geometry.py` + `steps/profiles.py`

- `frontal1_process_SelectSubArea.py`
  - 迁移目标：`steps/subareas.py`

- `merge_csv.py`
  - 迁移目标：`steps/statistics.py`

- `merge_csv fengmian2.py`
  - 迁移目标：`steps/statistics.py`

## 9. 错误处理与日志

第一版就应该纳入统一日志，不再只靠 `print(...)`。

建议：

- 每一步输出开始/结束日志
- 每一步记录输入文件、输出文件
- 缺文件时给出明确建议路径
- 可选写出 `manifest.json`

重点不是做复杂日志系统，而是确保“研究链条可回溯”。

## 10. 验收标准

当第一版新流水线满足以下条件时，视为重构成功：

1. 能基于配置执行一个 CRA40 front2 个例链路
2. 能复用现有人工掩膜成果
3. 能输出切线/法线几何结果
4. 能输出至少一组剖面结果
5. 能输出至少一个子区域掩膜
6. 能输出至少一个统计结果
7. 输出路径和命名不再依赖旧外部盘符
8. 结果可以与旧工程产物做人工对照

## 11. 不做项

本轮明确不做：

1. 不删除旧脚本
2. 不宣称自动识别替代人工识别
3. 不在第一版里追求所有案例全自动批量化
4. 不在未对照旧结果前就彻底替换旧工程

## 12. 推荐实施顺序

推荐按以下顺序进入实现：

1. 建立新目录骨架与配置入口
2. 完成 `inventory`
3. 完成 `masks`
4. 完成 `geometry`
5. 完成 `profiles`
6. 完成 `subareas`
7. 完成 `statistics`
8. 用 `CRA40 front2 2017-06-22T18` 做第一条完整验证链

## 13. 当前建议

当前建议正式按本设计推进。

下一步应进入：

- 写实现计划
- 再开始逐模块落代码

而不是继续扩展旧脚本本身。
